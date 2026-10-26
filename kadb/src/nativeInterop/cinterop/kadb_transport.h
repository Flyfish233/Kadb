#ifndef KADB_TRANSPORT_H
#define KADB_TRANSPORT_H

#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

typedef struct kadb_io kadb_io;

/* Create a closeable owner before connecting; close is terminal even before start.
 * getaddrinfo itself is system-blocking: cancellation prevents publication but
 * cannot interrupt the resolver, and the caller must wait for it to return. */
kadb_io *kadb_io_create(char *error, size_t error_size);
int kadb_io_connect_to(kadb_io *io, const char *host, int port, int64_t timeout_ms,
                      int keepalive_idle, int keepalive_interval, int keepalive_count,
                      char *error, size_t error_size);
/* Returns an owned nonblocking dual-stack listener (IPv4 fallback), or -1. */
int kadb_create_listener(int port, char *error, size_t error_size);
/* Timeouts are milliseconds; zero means no timeout, matching the JVM transport. */
kadb_io *kadb_io_connect(const char *host, int port, int64_t timeout_ms,
                         int keepalive_idle, int keepalive_interval, int keepalive_count,
                         char *error, size_t error_size);
/* Takes ownership of fd, including on failure. */
kadb_io *kadb_io_adopt(int fd, char *error, size_t error_size);
int kadb_io_is_open(kadb_io *io);
void kadb_io_close(kadb_io *io);
/* Call after all users have released their reference to io. */
void kadb_io_free(kadb_io *io);
/* Returns a byte count, zero for EOF, or -1 with error populated. */
int kadb_io_read(kadb_io *io, uint8_t *bytes, int size, int64_t timeout_ms,
                 char *error, size_t error_size);
int kadb_io_write(kadb_io *io, const uint8_t *bytes, int size, int64_t timeout_ms,
                  char *error, size_t error_size);
int kadb_io_add_identity(kadb_io *io, const uint8_t *key_pem, size_t key_size,
                         const uint8_t *cert_pem, size_t cert_size,
                         const char *fingerprint_hex, char *error, size_t error_size);
int kadb_io_start_tls(kadb_io *io, int64_t timeout_ms, char *error, size_t error_size);
int kadb_io_export_pairing_key(kadb_io *io, uint8_t *output, size_t output_size,
                              char *error, size_t error_size);

#ifdef __cplusplus
}
#endif
#endif
