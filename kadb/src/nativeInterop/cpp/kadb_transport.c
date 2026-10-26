#include "kadb_transport.h"

#include <openssl/err.h>
#include <openssl/pem.h>
#include <openssl/ssl.h>
#include <openssl/x509.h>
#include <arpa/inet.h>
#include <errno.h>
#include <fcntl.h>
#include <limits.h>
#include <netdb.h>
#include <netinet/in.h>
#include <netinet/tcp.h>
#include <poll.h>
#include <pthread.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <strings.h>
#include <sys/socket.h>
#include <time.h>
#include <unistd.h>

typedef struct kadb_identity {
    EVP_PKEY *key;
    X509 *cert;
    char fingerprint[65];
    struct kadb_identity *next;
} kadb_identity;

struct kadb_io {
    pthread_mutex_t lock;
    pthread_mutex_t write_lock;
    int fd;
    int cancel_read;
    int cancel_write;
    int closed;
    int active;
    int connecting;
    int handshaking;
    int tls_ready;
    BIO_METHOD *socket_method;
    SSL_CTX *context;
    SSL *ssl;
    kadb_identity *identities;
};

static void set_error(char *error, size_t size, const char *message) {
    if (size > 0) snprintf(error, size, "%s", message);
}

static void system_error(char *error, size_t size, const char *operation) {
    if (size > 0) snprintf(error, size, "%s: %s", operation, strerror(errno));
}

static void tls_error(char *error, size_t size, const char *operation, int code) {
    char detail[256];
    unsigned long reason = ERR_get_error();
    if (reason) ERR_error_string_n(reason, detail, sizeof(detail));
    else snprintf(detail, sizeof(detail), "TLS error %d", code);
    if (size > 0) snprintf(error, size, "%s: %s", operation, detail);
}

static int64_t monotonic_ms(void) {
    struct timespec time;
    clock_gettime(CLOCK_MONOTONIC, &time);
    return (int64_t) time.tv_sec * 1000 + time.tv_nsec / 1000000;
}

static int64_t make_deadline(int64_t timeout_ms) {
    if (timeout_ms <= 0) return 0;
    int64_t now = monotonic_ms();
    return timeout_ms > INT64_MAX - now ? INT64_MAX : now + timeout_ms;
}

static int await_fd(kadb_io *io, int fd, short events, int64_t deadline, char *error, size_t size) {
    for (;;) {
        int64_t remaining = deadline ? deadline - monotonic_ms() : -1;
        if (deadline && remaining <= 0) {
            set_error(error, size, "Socket operation timed out");
            return 0;
        }
        struct pollfd descriptors[2] = {
            {.fd = fd, .events = events},
            {.fd = io->cancel_read, .events = POLLIN}
        };
        int result = poll(descriptors, 2, remaining > INT_MAX ? INT_MAX : (int) remaining);
        if (result > 0) {
            if (descriptors[1].revents) {
                set_error(error, size, "Socket closed");
                return 0;
            }
            return 1; /* The next I/O reports EOF or the precise socket error. */
        }
        if (result == 0) {
            set_error(error, size, "Socket operation timed out");
            return 0;
        }
        if (errno != EINTR) {
            system_error(error, size, "poll");
            return 0;
        }
    }
}

static int configure_fd(int fd, char *error, size_t size) {
    int flags = fcntl(fd, F_GETFL, 0);
    int descriptor_flags = fcntl(fd, F_GETFD, 0);
    if (flags < 0 || descriptor_flags < 0 || fcntl(fd, F_SETFL, flags | O_NONBLOCK) < 0 ||
        fcntl(fd, F_SETFD, descriptor_flags | FD_CLOEXEC) < 0) {
        system_error(error, size, "fcntl");
        return 0;
    }
    int yes = 1;
    setsockopt(fd, IPPROTO_TCP, TCP_NODELAY, &yes, sizeof(yes));
    /* JVM/Android always enable keepalive; an absent policy retains OS timings. */
    setsockopt(fd, SOL_SOCKET, SO_KEEPALIVE, &yes, sizeof(yes));
#ifdef SO_NOSIGPIPE
    if (setsockopt(fd, SOL_SOCKET, SO_NOSIGPIPE, &yes, sizeof(yes)) < 0) {
        system_error(error, size, "SO_NOSIGPIPE");
        return 0;
    }
#endif
    return 1;
}

static void end_io(kadb_io *io);

kadb_io *kadb_io_create(char *error, size_t error_size) {
    kadb_io *io = calloc(1, sizeof(*io));
    if (!io) {
        set_error(error, error_size, "Unable to allocate socket transport");
        return NULL;
    }
    io->fd = -1;
    if (pthread_mutex_init(&io->lock, NULL) != 0) {
        set_error(error, error_size, "Unable to initialize socket lock");
        free(io);
        return NULL;
    }
    if (pthread_mutex_init(&io->write_lock, NULL) != 0) {
        set_error(error, error_size, "Unable to initialize socket write lock");
        pthread_mutex_destroy(&io->lock);
        free(io);
        return NULL;
    }
    int cancellation[2];
    if (pipe(cancellation) != 0) {
        system_error(error, error_size, "Create cancellation pipe");
        pthread_mutex_destroy(&io->write_lock);
        pthread_mutex_destroy(&io->lock);
        free(io);
        return NULL;
    }
    io->cancel_read = cancellation[0];
    io->cancel_write = cancellation[1];
    for (int index = 0; index < 2; ++index) {
        int fd = cancellation[index];
        int flags = fcntl(fd, F_GETFL, 0);
        if (flags < 0 || fcntl(fd, F_SETFL, flags | O_NONBLOCK) < 0 ||
            fcntl(fd, F_SETFD, FD_CLOEXEC) < 0) {
            system_error(error, error_size, "Configure cancellation pipe");
            close(cancellation[0]);
            close(cancellation[1]);
            pthread_mutex_destroy(&io->write_lock);
            pthread_mutex_destroy(&io->lock);
            free(io);
            return NULL;
        }
    }
    return io;
}

kadb_io *kadb_io_adopt(int fd, char *error, size_t error_size) {
    if (fd < 0) {
        set_error(error, error_size, "Invalid socket descriptor");
        return NULL;
    }
    if (!configure_fd(fd, error, error_size)) {
        close(fd);
        return NULL;
    }
    kadb_io *io = kadb_io_create(error, error_size);
    if (!io) {
        close(fd);
        return NULL;
    }
    io->fd = fd;
    return io;
}

/* Connect uses an already-published owner. close() can mark it terminal before
 * DNS returns, or shutdown the in-flight nonblocking socket without recycling it. */
int kadb_io_connect_to(kadb_io *io, const char *host, int port, int64_t timeout_ms,
                      int idle, int interval, int count, char *error, size_t error_size) {
    if (!host || !*host || port < 1 || port > 65535 || timeout_ms < 0) {
        set_error(error, error_size, "Invalid connection parameters");
        kadb_io_close(io);
        return 0;
    }
    pthread_mutex_lock(&io->lock);
    if (io->closed || io->connecting || io->fd >= 0) {
        pthread_mutex_unlock(&io->lock);
        set_error(error, error_size, "Socket closed or already connected");
        return 0;
    }
    io->connecting = 1;
    ++io->active;
    pthread_mutex_unlock(&io->lock);
    int64_t deadline = make_deadline(timeout_ms);
    char service[6];
    snprintf(service, sizeof(service), "%d", port);
    struct addrinfo hints = {.ai_family = AF_UNSPEC, .ai_socktype = SOCK_STREAM};
    struct addrinfo *addresses = NULL;
    int lookup = getaddrinfo(host, service, &hints, &addresses);
    int connected = 0;
    if (lookup) set_error(error, error_size, gai_strerror(lookup));
    else set_error(error, error_size, "No address available for host");
    for (struct addrinfo *address = addresses; address; address = address->ai_next) {
        pthread_mutex_lock(&io->lock);
        int closed = io->closed;
        pthread_mutex_unlock(&io->lock);
        if (closed) {
            set_error(error, error_size, "Socket closed");
            break;
        }
        if (deadline && monotonic_ms() >= deadline) {
            set_error(error, error_size, "Socket operation timed out");
            break;
        }
        int fd = socket(address->ai_family, address->ai_socktype, address->ai_protocol);
        if (fd < 0) {
            system_error(error, error_size, "socket");
            continue;
        }
        if (!configure_fd(fd, error, error_size)) {
            close(fd);
            continue;
        }
        pthread_mutex_lock(&io->lock);
        if (io->closed) {
            pthread_mutex_unlock(&io->lock);
            close(fd);
            set_error(error, error_size, "Socket closed");
            break;
        }
        io->fd = fd;
        /* The nonblocking connect is initiated before close can shutdown the fd.
         * The cancellation pipe also wakes poll when shutdown returns ENOTCONN. */
        int result = connect(fd, address->ai_addr, address->ai_addrlen);
        int connect_errno = errno;
        pthread_mutex_unlock(&io->lock);
        errno = connect_errno;
        if (result < 0 && errno == EINPROGRESS) {
            if (await_fd(io, fd, POLLOUT, deadline, error, error_size)) {
                int failure = 0;
                socklen_t length = sizeof(failure);
                result = getsockopt(fd, SOL_SOCKET, SO_ERROR, &failure, &length);
                if (result == 0 && failure) {
                    errno = failure;
                    system_error(error, error_size, "connect");
                    result = -1;
                } else if (result < 0) system_error(error, error_size, "SO_ERROR");
            } else result = -1;
        } else if (result < 0) system_error(error, error_size, "connect");
        pthread_mutex_lock(&io->lock);
        if (io->closed) {
            set_error(error, error_size, "Socket closed");
            result = -1;
        }
        if (result < 0) {
            close(fd);
            io->fd = -1;
            pthread_mutex_unlock(&io->lock);
            continue;
        }
        if (idle > 0) {
#ifdef TCP_KEEPALIVE
            setsockopt(fd, IPPROTO_TCP, TCP_KEEPALIVE, &idle, sizeof(idle));
#else
            setsockopt(fd, IPPROTO_TCP, TCP_KEEPIDLE, &idle, sizeof(idle));
#endif
            setsockopt(fd, IPPROTO_TCP, TCP_KEEPINTVL, &interval, sizeof(interval));
            setsockopt(fd, IPPROTO_TCP, TCP_KEEPCNT, &count, sizeof(count));
        }
        connected = 1;
        pthread_mutex_unlock(&io->lock);
        break;
    }
    if (addresses) freeaddrinfo(addresses);
    pthread_mutex_lock(&io->lock);
    io->connecting = 0;
    pthread_mutex_unlock(&io->lock);
    if (!connected) kadb_io_close(io);
    end_io(io);
    return connected;
}

kadb_io *kadb_io_connect(const char *host, int port, int64_t timeout_ms,
                         int idle, int interval, int count, char *error, size_t error_size) {
    kadb_io *io = kadb_io_create(error, error_size);
    if (io && !kadb_io_connect_to(io, host, port, timeout_ms, idle, interval, count, error, error_size)) {
        kadb_io_free(io);
        return NULL;
    }
    return io;
}

/* sockaddr layout and byte order belong to POSIX, not Kotlin's shared protocol layer. */
int kadb_create_listener(int port, char *error, size_t error_size) {
    if (port < 0 || port > 65535) {
        set_error(error, error_size, "Invalid listener port");
        return -1;
    }
    int family = AF_INET6;
    int fd = socket(family, SOCK_STREAM, 0);
    if (fd < 0) {
        family = AF_INET;
        fd = socket(family, SOCK_STREAM, 0);
    }
    if (fd < 0) {
        system_error(error, error_size, "socket");
        return -1;
    }
    int one = 1, zero = 0, result;
    if (setsockopt(fd, SOL_SOCKET, SO_REUSEADDR, &one, sizeof(one)) != 0) goto failure;
    if (family == AF_INET6) {
        if (setsockopt(fd, IPPROTO_IPV6, IPV6_V6ONLY, &zero, sizeof(zero)) != 0) goto failure;
        struct sockaddr_in6 address = {0};
        address.sin6_family = AF_INET6;
        address.sin6_port = htons((uint16_t) port);
#ifdef __APPLE__
        address.sin6_len = sizeof(address);
#endif
        result = bind(fd, (struct sockaddr *) &address, sizeof(address));
    } else {
        struct sockaddr_in address = {0};
        address.sin_family = AF_INET;
        address.sin_port = htons((uint16_t) port);
        address.sin_addr.s_addr = htonl(INADDR_ANY);
#ifdef __APPLE__
        address.sin_len = sizeof(address);
#endif
        result = bind(fd, (struct sockaddr *) &address, sizeof(address));
    }
    if (result != 0 || listen(fd, SOMAXCONN) != 0) goto failure;
    int flags = fcntl(fd, F_GETFL, 0);
    int descriptor_flags = fcntl(fd, F_GETFD, 0);
    if (flags < 0 || descriptor_flags < 0 || fcntl(fd, F_SETFL, flags | O_NONBLOCK) < 0 ||
        fcntl(fd, F_SETFD, descriptor_flags | FD_CLOEXEC) < 0) goto failure;
    return fd;
failure:
    system_error(error, error_size, "Create listener");
    close(fd);
    return -1;
}

static int begin_io(kadb_io *io, char *error, size_t size) {
    pthread_mutex_lock(&io->lock);
    if (io->closed) {
        pthread_mutex_unlock(&io->lock);
        set_error(error, size, "Socket closed");
        return 0;
    }
    if (io->connecting || io->handshaking || io->fd < 0) {
        pthread_mutex_unlock(&io->lock);
        set_error(error, size, "Socket is not ready for I/O");
        return 0;
    }
    ++io->active;
    pthread_mutex_unlock(&io->lock);
    return 1;
}

/* Called with the state lock held after the last active operation leaves.
 * Close deterministically erases native TLS/key ownership; the cleaner is only
 * responsible for the small stable owner/locks after callers release it. */
static void release_closed_state(kadb_io *io) {
    if (!io->closed || io->active != 0) return;
    if (io->fd >= 0) {
        close(io->fd);
        io->fd = -1;
    }
    if (io->cancel_read >= 0) {
        close(io->cancel_read);
        io->cancel_read = -1;
    }
    if (io->cancel_write >= 0) {
        close(io->cancel_write);
        io->cancel_write = -1;
    }
    SSL_free(io->ssl);
    io->ssl = NULL;
    SSL_CTX_free(io->context);
    io->context = NULL;
    BIO_meth_free(io->socket_method);
    io->socket_method = NULL;
    kadb_identity *identity = io->identities;
    io->identities = NULL;
    while (identity) {
        kadb_identity *next = identity->next;
        EVP_PKEY_free(identity->key);
        X509_free(identity->cert);
        free(identity);
        identity = next;
    }
}

static void end_io(kadb_io *io) {
    pthread_mutex_lock(&io->lock);
    --io->active;
    release_closed_state(io);
    pthread_mutex_unlock(&io->lock);
}

int kadb_io_is_open(kadb_io *io) {
    pthread_mutex_lock(&io->lock);
    int open = !io->closed && !io->connecting && io->fd >= 0;
    pthread_mutex_unlock(&io->lock);
    return open;
}

void kadb_io_close(kadb_io *io) {
    if (!io) return;
    pthread_mutex_lock(&io->lock);
    if (!io->closed) {
        io->closed = 1;
        /* Independent wakeup works even while connect has not established TCP. */
        const uint8_t cancelled = 1;
        ssize_t written;
        do { written = write(io->cancel_write, &cancelled, sizeof(cancelled)); } while (written < 0 && errno == EINTR);
        if (io->fd >= 0) shutdown(io->fd, SHUT_RDWR);
        /* Do not recycle a descriptor or release SSL while a worker uses it. */
        release_closed_state(io);
    }
    pthread_mutex_unlock(&io->lock);
}

void kadb_io_free(kadb_io *io) {
    if (!io) return;
    kadb_io_close(io);
    if (io->cancel_read >= 0) close(io->cancel_read);
    if (io->cancel_write >= 0) close(io->cancel_write);
    pthread_mutex_destroy(&io->write_lock);
    pthread_mutex_destroy(&io->lock);
    free(io);
}

static int socket_send(int fd, const void *bytes, size_t size) {
#ifdef MSG_NOSIGNAL
    return (int) send(fd, bytes, size, MSG_NOSIGNAL);
#else
    /* Darwin's configure_fd installs SO_NOSIGPIPE on this socket. */
    return (int) send(fd, bytes, size, 0);
#endif
}

/* BoringSSL's default socket BIO uses write(), which raises SIGPIPE on Linux.
 * This owner-backed BIO uses per-call suppression and never changes the host
 * application's process-global signal disposition. */
static int socket_bio_write(BIO *bio, const char *bytes, int size) {
    kadb_io *io = BIO_get_data(bio);
    BIO_clear_retry_flags(bio);
    int result = socket_send(io->fd, bytes, (size_t) size);
    if (result < 0 && (errno == EAGAIN || errno == EWOULDBLOCK || errno == EINTR)) BIO_set_retry_write(bio);
    return result;
}

static int socket_bio_read(BIO *bio, char *bytes, int size) {
    kadb_io *io = BIO_get_data(bio);
    BIO_clear_retry_flags(bio);
    int result = (int) recv(io->fd, bytes, (size_t) size, 0);
    if (result < 0 && (errno == EAGAIN || errno == EWOULDBLOCK || errno == EINTR)) BIO_set_retry_read(bio);
    return result;
}

static long socket_bio_ctrl(BIO *bio, int command, long argument, void *pointer) {
    (void) bio;
    (void) argument;
    (void) pointer;
    return command == BIO_CTRL_FLUSH ? 1 : 0;
}

static BIO *make_socket_bio(kadb_io *io) {
    io->socket_method = BIO_meth_new(BIO_TYPE_SOURCE_SINK | 128, "Kadb owned POSIX socket");
    if (!io->socket_method || !BIO_meth_set_write(io->socket_method, socket_bio_write) ||
        !BIO_meth_set_read(io->socket_method, socket_bio_read) ||
        !BIO_meth_set_ctrl(io->socket_method, socket_bio_ctrl)) return NULL;
    BIO *bio = BIO_new(io->socket_method);
    if (bio) {
        BIO_set_data(bio, io);
        BIO_set_init(bio, 1);
    }
    return bio;
}

static int transfer(kadb_io *io, uint8_t *bytes, int size, int64_t timeout_ms,
                    int writing, char *error, size_t error_size) {
    if (size <= 0) return 0;
    if (!begin_io(io, error, error_size)) return -1;
    int64_t deadline = make_deadline(timeout_ms);
    int result = -1;
    for (;;) {
        pthread_mutex_lock(&io->lock);
        if (io->closed) {
            pthread_mutex_unlock(&io->lock);
            set_error(error, error_size, "Socket closed");
            result = -1;
            break;
        }
        short wait_for = writing ? POLLOUT : POLLIN;
        if (io->ssl) {
            ERR_clear_error();
            result = writing ? SSL_write(io->ssl, bytes, size) : SSL_read(io->ssl, bytes, size);
            int status = result > 0 ? SSL_ERROR_NONE : SSL_get_error(io->ssl, result);
            if (status == SSL_ERROR_ZERO_RETURN) result = 0;
            else if (status == SSL_ERROR_WANT_READ || status == SSL_ERROR_WANT_WRITE) {
                wait_for = status == SSL_ERROR_WANT_READ ? POLLIN : POLLOUT;
                result = -2;
            } else if (status != SSL_ERROR_NONE) {
                tls_error(error, error_size, writing ? "TLS write" : "TLS read", status);
                result = -1;
            }
        } else {
            result = writing ? socket_send(io->fd, bytes, (size_t) size)
                             : (int) recv(io->fd, bytes, (size_t) size, 0);
            if (result < 0) {
                if (errno == EAGAIN || errno == EWOULDBLOCK || errno == EINTR) result = -2;
                else system_error(error, error_size, writing ? "send" : "recv");
            }
        }
        pthread_mutex_unlock(&io->lock);
        if (result != -2) break;
        if (!await_fd(io, io->fd, wait_for, deadline, error, error_size)) {
            result = -1;
            break;
        }
    }
    /* SSL_write may retain a partially emitted record after WANT_WRITE. Even
     * plain writes can have committed a prefix in the caller's full-write loop.
     * Failure is terminal: a different buffer must never retry this stream. */
    if (writing && result <= 0) kadb_io_close(io);
    end_io(io);
    return result;
}

int kadb_io_read(kadb_io *io, uint8_t *bytes, int size, int64_t timeout_ms,
                 char *error, size_t error_size) {
    return transfer(io, bytes, size, timeout_ms, 0, error, error_size);
}

int kadb_io_write(kadb_io *io, const uint8_t *bytes, int size, int64_t timeout_ms,
                  char *error, size_t error_size) {
    pthread_mutex_lock(&io->write_lock);
    int result = transfer(io, (uint8_t *) bytes, size, timeout_ms, 1, error, error_size);
    pthread_mutex_unlock(&io->write_lock);
    return result;
}

int kadb_io_add_identity(kadb_io *io, const uint8_t *key_pem, size_t key_size,
                         const uint8_t *cert_pem, size_t cert_size,
                         const char *fingerprint_hex, char *error, size_t error_size) {
    if (key_size > INT_MAX || cert_size > INT_MAX || strlen(fingerprint_hex) != 64) {
        set_error(error, error_size, "Invalid TLS identity");
        return 0;
    }
    BIO *key_bio = BIO_new_mem_buf(key_pem, (int) key_size);
    BIO *cert_bio = BIO_new_mem_buf(cert_pem, (int) cert_size);
    kadb_identity *identity = calloc(1, sizeof(*identity));
    if (identity && key_bio && cert_bio) {
        identity->key = PEM_read_bio_PrivateKey(key_bio, NULL, NULL, NULL);
        identity->cert = PEM_read_bio_X509(cert_bio, NULL, NULL, NULL);
    }
    BIO_free(key_bio);
    BIO_free(cert_bio);
    if (!identity || !identity->key || !identity->cert ||
        X509_check_private_key(identity->cert, identity->key) != 1) {
        tls_error(error, error_size, "Load TLS identity", 0);
        if (identity) {
            EVP_PKEY_free(identity->key);
            X509_free(identity->cert);
            free(identity);
        }
        return 0;
    }
    memcpy(identity->fingerprint, fingerprint_hex, 65);
    pthread_mutex_lock(&io->lock);
    if (io->closed || io->ssl) {
        pthread_mutex_unlock(&io->lock);
        EVP_PKEY_free(identity->key);
        X509_free(identity->cert);
        free(identity);
        set_error(error, error_size, "TLS identity must be configured before handshake");
        return 0;
    }
    kadb_identity **tail = &io->identities;
    while (*tail) tail = &(*tail)->next;
    *tail = identity;
    pthread_mutex_unlock(&io->lock);
    return 1;
}

/* ADB advertises paired keys as O=AdbKey-0,CN=<SPKI SHA256>. Preserve issuer order. */
static int select_client_identity(SSL *ssl, void *argument) {
    kadb_io *io = argument;
    kadb_identity *selected = io->identities;
    const STACK_OF(X509_NAME) *issuers = SSL_get_client_CA_list(ssl);
    for (size_t i = 0; issuers && i < sk_X509_NAME_num(issuers); ++i) {
        X509_NAME *issuer = sk_X509_NAME_value(issuers, i);
        char organization[64], common_name[128];
        if (X509_NAME_get_text_by_NID(issuer, NID_organizationName, organization, sizeof(organization)) != 8 ||
            strcmp(organization, "AdbKey-0") != 0 ||
            X509_NAME_get_text_by_NID(issuer, NID_commonName, common_name, sizeof(common_name)) != 64) continue;
        for (kadb_identity *identity = io->identities; identity; identity = identity->next) {
            if (strcasecmp(identity->fingerprint, common_name) == 0) {
                selected = identity;
                goto found;
            }
        }
    }
found:
    return selected && SSL_use_certificate(ssl, selected->cert) == 1 &&
           SSL_use_PrivateKey(ssl, selected->key) == 1;
}

int kadb_io_start_tls(kadb_io *io, int64_t timeout_ms, char *error, size_t error_size) {
    if (!begin_io(io, error, error_size)) return 0;
    pthread_mutex_lock(&io->lock);
    if (io->ssl || !io->identities || io->active != 1) {
        pthread_mutex_unlock(&io->lock);
        set_error(error, error_size, "TLS requires an identity and an unencrypted socket");
        kadb_io_close(io);
        end_io(io);
        return 0;
    }
    io->handshaking = 1;
    io->context = SSL_CTX_new(TLS_method());
    int setup = io->context && SSL_CTX_set_min_proto_version(io->context, TLS1_3_VERSION) &&
                SSL_CTX_set_max_proto_version(io->context, TLS1_3_VERSION);
    if (setup) {
        /* ADB authenticates the client identity; pairing binds the otherwise untrusted server via SPAKE2. */
        SSL_CTX_set_verify(io->context, SSL_VERIFY_NONE, NULL);
        SSL_CTX_set_cert_cb(io->context, select_client_identity, io);
        io->ssl = SSL_new(io->context);
        BIO *bio = io->ssl ? make_socket_bio(io) : NULL;
        setup = io->ssl && bio;
        if (setup) {
            SSL_set_bio(io->ssl, bio, bio);
            SSL_set_connect_state(io->ssl);
        }
    }
    if (!setup) tls_error(error, error_size, "Configure TLS", 0);
    pthread_mutex_unlock(&io->lock);
    int64_t deadline = make_deadline(timeout_ms);
    int success = 0;
    while (setup) {
        pthread_mutex_lock(&io->lock);
        if (io->closed) {
            pthread_mutex_unlock(&io->lock);
            set_error(error, error_size, "Socket closed");
            break;
        }
        ERR_clear_error();
        int result = SSL_connect(io->ssl);
        int status = result == 1 ? SSL_ERROR_NONE : SSL_get_error(io->ssl, result);
        if (status != SSL_ERROR_NONE && status != SSL_ERROR_WANT_READ && status != SSL_ERROR_WANT_WRITE)
            tls_error(error, error_size, "TLS handshake", status);
        pthread_mutex_unlock(&io->lock);
        if (result == 1) {
            success = 1;
            break;
        }
        if (status != SSL_ERROR_WANT_READ && status != SSL_ERROR_WANT_WRITE) break;
        if (!await_fd(io, io->fd, status == SSL_ERROR_WANT_READ ? POLLIN : POLLOUT,
                      deadline, error, error_size)) break;
    }
    pthread_mutex_lock(&io->lock);
    io->handshaking = 0;
    io->tls_ready = success;
    pthread_mutex_unlock(&io->lock);
    if (!success) kadb_io_close(io);
    end_io(io);
    return success;
}

int kadb_io_export_pairing_key(kadb_io *io, uint8_t *output, size_t output_size,
                              char *error, size_t error_size) {
    /* sizeof intentionally includes the trailing NUL used by AOSP pairing. No context. */
    static const char label[] = "adb-label";
    pthread_mutex_lock(&io->lock);
    int success = !io->closed && io->tls_ready && io->ssl && output_size == 64 &&
                  SSL_export_keying_material(io->ssl, output, output_size,
                                             label, sizeof(label), NULL, 0, 0);
    if (!success) tls_error(error, error_size, "Export pairing key", 0);
    pthread_mutex_unlock(&io->lock);
    return success;
}
