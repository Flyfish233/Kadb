#ifdef NDEBUG
#error "Native transport tests require assertions; compile with -UNDEBUG"
#endif

/* Standalone integration test: compile with the same prefixed BoringSSL as the iOS bridge. */
#include "kadb_transport.h"
#include <openssl/evp.h>
#include <openssl/pem.h>
#include <openssl/rsa.h>
#include <openssl/sha.h>
#include <openssl/ssl.h>
#include <openssl/x509.h>
#include <assert.h>
#include <arpa/inet.h>
#include <netinet/in.h>
#include <pthread.h>
#include <signal.h>
#include <fcntl.h>
#ifdef __linux__
#include <dirent.h>
#endif
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <unistd.h>

typedef struct {
    EVP_PKEY *key;
    X509 *cert;
    BIO *key_pem;
    BIO *cert_pem;
    char fingerprint[65];
} identity;

static identity generate_identity(int serial) {
    identity result = {0};
    BIGNUM *exponent = BN_new();
    assert(BN_set_word(exponent, RSA_F4));
    RSA *rsa = RSA_new();
    assert(RSA_generate_key_ex(rsa, 2048, exponent, NULL));
    BN_free(exponent);
    result.key = EVP_PKEY_new();
    assert(EVP_PKEY_assign_RSA(result.key, rsa));
    result.cert = X509_new();
    assert(X509_set_version(result.cert, 2));
    assert(ASN1_INTEGER_set(X509_get_serialNumber(result.cert), serial));
    assert(X509_gmtime_adj(X509_getm_notBefore(result.cert), -60));
    assert(X509_gmtime_adj(X509_getm_notAfter(result.cert), 86400));
    assert(X509_set_pubkey(result.cert, result.key));
    X509_NAME *name = X509_get_subject_name(result.cert);
    assert(X509_NAME_add_entry_by_txt(name, "CN", MBSTRING_ASC,
                                    (const unsigned char *) "Kadb test", -1, -1, 0));
    assert(X509_set_issuer_name(result.cert, name));
    assert(X509_sign(result.cert, result.key, EVP_sha256()));
    result.key_pem = BIO_new(BIO_s_mem());
    result.cert_pem = BIO_new(BIO_s_mem());
    assert(PEM_write_bio_PrivateKey(result.key_pem, result.key, NULL, NULL, 0, NULL, NULL));
    assert(PEM_write_bio_X509(result.cert_pem, result.cert));
    unsigned char *der = NULL;
    int length = i2d_PUBKEY(result.key, &der);
    assert(length > 0);
    uint8_t digest[32];
    SHA256(der, (size_t) length, digest);
    OPENSSL_free(der);
    for (int i = 0; i < 32; ++i) snprintf(result.fingerprint + i * 2, 3, "%02X", digest[i]);
    return result;
}

static void free_identity(identity *identity) {
    BIO_free(identity->key_pem);
    BIO_free(identity->cert_pem);
    X509_free(identity->cert);
    EVP_PKEY_free(identity->key);
}

static void add_identity(kadb_io *io, identity *identity) {
    char *key_bytes, *cert_bytes, error[512];
    long key_size = BIO_get_mem_data(identity->key_pem, &key_bytes);
    long cert_size = BIO_get_mem_data(identity->cert_pem, &cert_bytes);
    assert(kadb_io_add_identity(io, (const uint8_t *) key_bytes, key_size,
                               (const uint8_t *) cert_bytes, cert_size,
                               identity->fingerprint, error, sizeof(error)) == 1);
}

static int accept_certificate(int verified, X509_STORE_CTX *context) {
    (void) verified;
    (void) context;
    return 1;
}

typedef struct {
    int fd;
    SSL_CTX *context;
    X509 *expected_client;
} server_args;

static void *tls_server(void *argument) {
    server_args *args = argument;
    uint8_t bytes[64];
    assert(recv(args->fd, bytes, 4, MSG_WAITALL) == 4 && memcmp(bytes, "CNXN", 4) == 0);
    assert(send(args->fd, "STLS", 4, 0) == 4);
    assert(recv(args->fd, bytes, 4, MSG_WAITALL) == 4 && memcmp(bytes, "STLS", 4) == 0);
    SSL *ssl = SSL_new(args->context);
    assert(SSL_set_fd(ssl, args->fd));
    assert(SSL_accept(ssl) == 1);
    assert(SSL_version(ssl) == TLS1_3_VERSION);
    X509 *peer = SSL_get_peer_certificate(ssl);
    assert(peer && X509_cmp(peer, args->expected_client) == 0);
    X509_free(peer);
    static const char label[] = "adb-label";
    assert(SSL_export_keying_material(ssl, bytes, sizeof(bytes), label, sizeof(label), NULL, 0, 0));
    assert(SSL_write(ssl, bytes, sizeof(bytes)) == sizeof(bytes));
    assert(SSL_read(ssl, bytes, 4) == 4 && memcmp(bytes, "OPEN", 4) == 0);
    assert(SSL_write(ssl, "OKAY", 4) == 4);
    SSL_shutdown(ssl);
    SSL_free(ssl);
    close(args->fd);
    return NULL;
}

static void test_stls_and_exporter(void) {
    identity first = generate_identity(1), selected = generate_identity(2);
    SSL_CTX *server = SSL_CTX_new(TLS_method());
    assert(SSL_CTX_set_min_proto_version(server, TLS1_3_VERSION));
    assert(SSL_CTX_set_max_proto_version(server, TLS1_3_VERSION));
    assert(SSL_CTX_use_certificate(server, first.cert));
    assert(SSL_CTX_use_PrivateKey(server, first.key));
    SSL_CTX_set_verify(server, SSL_VERIFY_PEER | SSL_VERIFY_FAIL_IF_NO_PEER_CERT, accept_certificate);
    STACK_OF(X509_NAME) *issuers = sk_X509_NAME_new_null();
    X509_NAME *issuer = X509_NAME_new();
    assert(X509_NAME_add_entry_by_txt(issuer, "O", MBSTRING_ASC,
                                    (const unsigned char *) "AdbKey-0", -1, -1, 0));
    assert(X509_NAME_add_entry_by_txt(issuer, "CN", MBSTRING_ASC,
                                    (const unsigned char *) selected.fingerprint, -1, -1, 0));
    assert(sk_X509_NAME_push(issuers, issuer));
    SSL_CTX_set_client_CA_list(server, issuers);
    int sockets[2];
    assert(socketpair(AF_UNIX, SOCK_STREAM, 0, sockets) == 0);
    server_args args = {.fd = sockets[1], .context = server, .expected_client = selected.cert};
    pthread_t thread;
    assert(pthread_create(&thread, NULL, tls_server, &args) == 0);
    char error[512];
    kadb_io *client = kadb_io_adopt(sockets[0], error, sizeof(error));
    assert(client);
    uint8_t bytes[64], exported[64];
    assert(kadb_io_write(client, (const uint8_t *) "CNXN", 4, 1000, error, sizeof(error)) == 4);
    assert(kadb_io_read(client, bytes, 4, 1000, error, sizeof(error)) == 4 && memcmp(bytes, "STLS", 4) == 0);
    assert(kadb_io_write(client, (const uint8_t *) "STLS", 4, 1000, error, sizeof(error)) == 4);
    add_identity(client, &first);
    add_identity(client, &selected);
    if (!kadb_io_start_tls(client, 5000, error, sizeof(error))) {
        fprintf(stderr, "%s\n", error);
        abort();
    }
    assert(kadb_io_export_pairing_key(client, exported, sizeof(exported), error, sizeof(error)) == 1);
    int received = 0;
    while (received < 64) {
        int count = kadb_io_read(client, bytes + received, 64 - received, 1000, error, sizeof(error));
        assert(count > 0);
        received += count;
    }
    assert(memcmp(bytes, exported, sizeof(bytes)) == 0);
    assert(kadb_io_write(client, (const uint8_t *) "OPEN", 4, 1000, error, sizeof(error)) == 4);
    assert(kadb_io_read(client, bytes, 4, 1000, error, sizeof(error)) == 4 && memcmp(bytes, "OKAY", 4) == 0);
    assert(kadb_io_read(client, bytes, 4, 1000, error, sizeof(error)) == 0);
    kadb_io_close(client);
    assert(!kadb_io_is_open(client));
    kadb_io_free(client);
    pthread_join(thread, NULL);
    SSL_CTX_free(server);
    free_identity(&first);
    free_identity(&selected);
}

static void *blocked_reader(void *argument) {
    uint8_t byte;
    char error[512];
    assert(kadb_io_read(argument, &byte, 1, 0, error, sizeof(error)) == -1);
    assert(strstr(error, "closed"));
    return NULL;
}

static void test_timeout_and_close(void) {
    int sockets[2];
    assert(socketpair(AF_UNIX, SOCK_STREAM, 0, sockets) == 0);
    char error[512];
    kadb_io *client = kadb_io_adopt(sockets[0], error, sizeof(error));
    assert(client);
    uint8_t byte;
    assert(kadb_io_read(client, &byte, 1, 20, error, sizeof(error)) == -1);
    assert(strstr(error, "timed out"));
    pthread_t thread;
    assert(pthread_create(&thread, NULL, blocked_reader, client) == 0);
    usleep(20000);
    kadb_io_close(client);
    pthread_join(thread, NULL);
    kadb_io_free(client);
    close(sockets[1]);
}

static void test_tcp_connect(void) {
    int listener = socket(AF_INET, SOCK_STREAM, 0);
    assert(listener >= 0);
    struct sockaddr_in address = {.sin_family = AF_INET, .sin_addr.s_addr = htonl(INADDR_LOOPBACK)};
    assert(bind(listener, (struct sockaddr *) &address, sizeof(address)) == 0);
    assert(listen(listener, 1) == 0);
    socklen_t size = sizeof(address);
    assert(getsockname(listener, (struct sockaddr *) &address, &size) == 0);
    char error[512];
    kadb_io *client = kadb_io_connect("localhost", ntohs(address.sin_port), 1000, 1, 1, 10,
                                     error, sizeof(error));
    assert(client);
    int server = accept(listener, NULL, NULL);
    assert(server >= 0);
    assert(send(server, "CNXN", 4, 0) == 4);
    uint8_t bytes[4];
    assert(kadb_io_read(client, bytes, 4, INT64_MAX, error, sizeof(error)) == 4);
    assert(memcmp(bytes, "CNXN", 4) == 0);
    kadb_io_free(client);
    close(server);
    close(listener);
}

/* A blocked SSL_write has consumed internal state even when it returns no byte
 * count. Returning the socket to callers would permit an invalid new write or
 * duplicated application data. This is a positive product-health assertion:
 * it MUST fail against the unmodified 75678915 baseline. */
typedef struct {
    int fd;
    SSL_CTX *context;
    pthread_mutex_t lock;
    pthread_cond_t condition;
    int release;
} stalled_server_args;

static void *stalled_tls_server(void *argument) {
    stalled_server_args *args = argument;
    SSL *ssl = SSL_new(args->context);
    assert(SSL_set_fd(ssl, args->fd));
    assert(SSL_accept(ssl) == 1);
    pthread_mutex_lock(&args->lock);
    while (!args->release) pthread_cond_wait(&args->condition, &args->lock);
    pthread_mutex_unlock(&args->lock);
    SSL_free(ssl);
    close(args->fd);
    return NULL;
}

static void test_tls_write_timeout_invalidates_connection(void) {
    identity identity = generate_identity(3);
    SSL_CTX *server = SSL_CTX_new(TLS_method());
    assert(SSL_CTX_set_min_proto_version(server, TLS1_3_VERSION));
    assert(SSL_CTX_use_certificate(server, identity.cert));
    assert(SSL_CTX_use_PrivateKey(server, identity.key));
    int sockets[2];
    assert(socketpair(AF_UNIX, SOCK_STREAM, 0, sockets) == 0);
    int tiny_buffer = 1024;
    assert(setsockopt(sockets[0], SOL_SOCKET, SO_SNDBUF, &tiny_buffer, sizeof(tiny_buffer)) == 0);
    stalled_server_args args = {.fd = sockets[1], .context = server,
        .lock = PTHREAD_MUTEX_INITIALIZER, .condition = PTHREAD_COND_INITIALIZER};
    pthread_t thread;
    assert(pthread_create(&thread, NULL, stalled_tls_server, &args) == 0);
    char error[512] = {0};
    kadb_io *client = kadb_io_adopt(sockets[0], error, sizeof(error));
    assert(client);
    add_identity(client, &identity);
    assert(kadb_io_start_tls(client, 5000, error, sizeof(error)) == 1);
    const int length = 4 * 1024 * 1024;
    uint8_t *bytes = malloc(length);
    assert(bytes);
    memset(bytes, 0x5a, length);
    assert(kadb_io_write(client, bytes, length, 40, error, sizeof(error)) == -1);
    assert(strstr(error, "timed out"));
    /* The regression assertion. A successful negative reproducer is not a pass. */
    assert(!kadb_io_is_open(client));
    assert(kadb_io_write(client, (const uint8_t *) "NEW!", 4, 40, error, sizeof(error)) == -1);
    assert(strstr(error, "closed"));
    free(bytes);
    kadb_io_free(client);
    pthread_mutex_lock(&args.lock);
    args.release = 1;
    pthread_cond_signal(&args.condition);
    pthread_mutex_unlock(&args.lock);
    pthread_join(thread, NULL);
    pthread_cond_destroy(&args.condition);
    pthread_mutex_destroy(&args.lock);
    SSL_CTX_free(server);
    free_identity(&identity);
}

static void test_close_before_connect_is_terminal(void) {
    char error[512] = {0};
    kadb_io *io = kadb_io_create(error, sizeof(error));
    assert(io);
    assert(!kadb_io_is_open(io));
    kadb_io_close(io);
    kadb_io_close(io);
    assert(!kadb_io_connect_to(io, "localhost", 5555, 100, 0, 0, 0, error, sizeof(error)));
    assert(strstr(error, "closed"));
    assert(!kadb_io_is_open(io));
    kadb_io_free(io);
}

static void test_plain_write_error_has_no_sigpipe(void) {
    int sockets[2];
    assert(socketpair(AF_UNIX, SOCK_STREAM, 0, sockets) == 0);
    char error[512] = {0};
    kadb_io *io = kadb_io_adopt(sockets[0], error, sizeof(error));
    assert(io);
    close(sockets[1]);
    assert(kadb_io_write(io, (const uint8_t *) "closed", 6, 100, error, sizeof(error)) == -1);
    assert(!kadb_io_is_open(io));
    kadb_io_free(io);
}

static void test_failed_handshake_is_terminal(void) {
    int sockets[2];
    assert(socketpair(AF_UNIX, SOCK_STREAM, 0, sockets) == 0);
    char error[512] = {0};
    identity identity = generate_identity(4);
    kadb_io *io = kadb_io_adopt(sockets[0], error, sizeof(error));
    assert(io);
    add_identity(io, &identity);
    assert(!kadb_io_start_tls(io, 20, error, sizeof(error)));
    assert(strstr(error, "timed out"));
    assert(!kadb_io_is_open(io));
    uint8_t exported[64] = {0};
    assert(!kadb_io_export_pairing_key(io, exported, sizeof(exported), error, sizeof(error)));
    assert(!kadb_io_start_tls(io, 20, error, sizeof(error)));
    kadb_io_free(io);
    close(sockets[1]);
    free_identity(&identity);
}

static void test_tls_write_error_has_no_sigpipe(void) {
    identity identity = generate_identity(5);
    SSL_CTX *server = SSL_CTX_new(TLS_method());
    assert(SSL_CTX_set_min_proto_version(server, TLS1_3_VERSION));
    assert(SSL_CTX_use_certificate(server, identity.cert));
    assert(SSL_CTX_use_PrivateKey(server, identity.key));
    int sockets[2];
    assert(socketpair(AF_UNIX, SOCK_STREAM, 0, sockets) == 0);
    stalled_server_args args = {.fd = sockets[1], .context = server,
        .lock = PTHREAD_MUTEX_INITIALIZER, .condition = PTHREAD_COND_INITIALIZER};
    pthread_t thread;
    assert(pthread_create(&thread, NULL, stalled_tls_server, &args) == 0);
    char error[512] = {0};
    kadb_io *client = kadb_io_adopt(sockets[0], error, sizeof(error));
    assert(client);
    add_identity(client, &identity);
    assert(kadb_io_start_tls(client, 5000, error, sizeof(error)) == 1);
    pthread_mutex_lock(&args.lock);
    args.release = 1;
    pthread_cond_signal(&args.condition);
    pthread_mutex_unlock(&args.lock);
    pthread_join(thread, NULL);
    assert(kadb_io_write(client, (const uint8_t *) "closed", 6, 100, error, sizeof(error)) == -1);
    assert(!kadb_io_is_open(client));
    kadb_io_free(client);
    pthread_cond_destroy(&args.condition);
    pthread_mutex_destroy(&args.lock);
    SSL_CTX_free(server);
    free_identity(&identity);
}

typedef struct { kadb_io *io; int result; } handshake_args;

static void *blocked_handshake(void *argument) {
    handshake_args *args = argument;
    char error[512] = {0};
    args->result = kadb_io_start_tls(args->io, 0, error, sizeof(error));
    assert(!args->result);
    assert(strstr(error, "closed"));
    return NULL;
}

static void test_close_cancels_handshake(void) {
    int sockets[2];
    assert(socketpair(AF_UNIX, SOCK_STREAM, 0, sockets) == 0);
    char error[512] = {0};
    identity identity = generate_identity(6);
    kadb_io *io = kadb_io_adopt(sockets[0], error, sizeof(error));
    assert(io);
    assert(fcntl(sockets[0], F_GETFD) & FD_CLOEXEC);
    add_identity(io, &identity);
    handshake_args args = {.io = io, .result = -1};
    pthread_t worker;
    assert(pthread_create(&worker, NULL, blocked_handshake, &args) == 0);
    usleep(20000);
    kadb_io_close(io);
    assert(pthread_join(worker, NULL) == 0);
    assert(args.result == 0);
    kadb_io_free(io);
    close(sockets[1]);
    free_identity(&identity);
}

static void test_native_listener(void) {
    char error[512] = {0};
    int listener = kadb_create_listener(0, error, sizeof(error));
    assert(listener >= 0);
    assert(fcntl(listener, F_GETFD) & FD_CLOEXEC);
    struct sockaddr_storage address;
    socklen_t size = sizeof(address);
    assert(getsockname(listener, (struct sockaddr *) &address, &size) == 0);
    int port = ntohs(address.ss_family == AF_INET6 ? ((struct sockaddr_in6 *) &address)->sin6_port
                                                  : ((struct sockaddr_in *) &address)->sin_port);
    kadb_io *client = kadb_io_connect("127.0.0.1", port, 1000, 0, 0, 0, error, sizeof(error));
    assert(client);
    int accepted = accept(listener, NULL, NULL);
    assert(accepted >= 0);
    close(accepted);
    kadb_io_free(client);
    close(listener);
}

#ifdef __linux__
static int descriptor_count(void) {
    DIR *directory = opendir("/proc/self/fd");
    assert(directory);
    int count = 0;
    while (readdir(directory)) ++count;
    closedir(directory);
    return count;
}

static void test_closed_owners_retain_no_descriptors(void) {
    const int before = descriptor_count();
    kadb_io *owners[64];
    char error[512] = {0};
    for (int index = 0; index < 64; ++index) {
        int sockets[2];
        assert(socketpair(AF_UNIX, SOCK_STREAM, 0, sockets) == 0);
        owners[index] = kadb_io_adopt(sockets[0], error, sizeof(error));
        assert(owners[index]);
        close(sockets[1]);
        kadb_io_close(owners[index]);
        kadb_io_close(owners[index]);
    }
    /* Keeping every closed owner alive must not keep any socket/wakeup fd alive. */
    assert(descriptor_count() == before);
    for (int index = 0; index < 64; ++index) kadb_io_free(owners[index]);
    assert(descriptor_count() == before);
}
#endif

int main(void) {
    /* An implementation which leaks SIGPIPE must fail the process, not pass by
     * relying on a parent application's signal handler. */
    signal(SIGPIPE, SIG_DFL);
    test_stls_and_exporter();
    test_timeout_and_close();
    test_tcp_connect();
    test_tls_write_timeout_invalidates_connection();
    test_close_before_connect_is_terminal();
    test_plain_write_error_has_no_sigpipe();
    test_failed_handshake_is_terminal();
    test_tls_write_error_has_no_sigpipe();
    test_close_cancels_handshake();
    test_native_listener();
#ifdef __linux__
    test_closed_owners_retain_no_descriptors();
#endif
    puts("PASS: TCP connect, same-socket STLS/TLS 1.3, client identity selection, pairing exporter, I/O, EOF, timeout, concurrent close, TLS write failure invalidation, close-before-connect, handshake failure, per-socket SIGPIPE suppression, handshake cancellation, native listener, descriptor ownership");
    return 0;
}
