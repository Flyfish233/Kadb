# Native transport evidence

Baseline source: `75678915fd4bdd52345edbb6bc4913ae3415a680`.
BoringSSL: `5b83e5d1abf0ae0033ae52ab579d906b67633b2c`.
Verified archive SHA-256: `4117ae02de040d4469284673ed63a14e648af7c3974aa9e85bcef2975a9c9ea8`.
Local host: Linux x86_64, GCC 13.3.0, CMake 3.31.10. No Android or Apple device is involved.

## Red regression, before the implementation fix

`01-baseline-tls-write-failure.log` is a **failing health test**, not a success result.
The unchanged baseline C backend completes the earlier transport checks, then fails
`assert(!kadb_io_is_open(client))` after an intentionally stalled TLS 1.3 server
causes `SSL_write` to time out. CTest exits **8**, and the child aborts. A positive
health assertion proves the baseline incorrectly leaves the connection reusable.
The new test uses a real local TLS peer, a small send buffer and a 4 MiB write.

Reproduction (first download and verify the above source revision):

```sh
cmake -S kadb/src/nativeInterop -B build/native-c \
  -DBORINGSSL_SOURCE=/absolute/path/to/verified/boringssl \
  -DCMAKE_BUILD_TYPE=Release -DKADB_NATIVE_TESTS=ON
cmake --build build/native-c --target kadb_transport_test --parallel 4
ctest --test-dir build/native-c --output-on-failure
```

The harness compiles with `-UNDEBUG`, including Release builds, because its
assertions execute the operations under test. The CI must check CTest's exit
status and retain the output. Running within this task's syscall-intercepting
sandbox failed before the target assertion at the initial socket write; the
recorded result above was rerun with authorized local socket access. That earlier
environment failure is not used as defect evidence.

## Green regression and ownership checks

`02-fixed-native-c-and-sanitizers.log` is the complete output of
`scripts/test-native-c.sh` with `KADB_SANITIZE=1`, after the C transport fix.
CTest executes one harness containing explicit checks for TCP connect, same-socket
STLS and TLS 1.3, client identity selection, the exact NUL-terminated ADB exporter
label, I/O/EOF, terminal TLS write timeout, handshake failure, cancellation, listener
creation and repeated close. On Linux it additionally keeps 64 closed owners alive
and verifies `/proc/self/fd` returns to its original count before freeing owners.
The harness restores the default SIGPIPE disposition: plaintext and TLS writes to
closed peers must fail as errors without terminating the process.

The sanitizer run recompiles the transport shim and harness with GCC
`-fsanitize=address,undefined -Wall -Wextra -Werror` and leak detection enabled.
BoringSSL static archives are the verified Release build, **not** a fully
sanitizer-instrumented rebuild. Both executions exit zero. This is C/POSIX backend
evidence; it does not demonstrate Kotlin/Native linking, Swift consumption,
simulator operation, real Android pairing, or physical-device compatibility.

### Cancellation and ownership boundary

The native socket owner exists before connect. A cancellation pipe wakes blocked
polls even if shutdown cannot wake an unestablished socket. Socket descriptors are
not recycled until their last active I/O operation exits. At that point close
releases TLS state, imported private-key objects, sockets and cancellation pipes;
the language cleaner only reclaims the stable owner and mutex storage later.
Writes are serialized across BoringSSL retry loops. Any failed write makes the
connection terminal. Timeout addition is saturated rather than overflowing for
`Long.MAX_VALUE`.

`getaddrinfo` remains system-blocking. Cancellation makes the owner terminal and
prevents a returned address from being published, but does not interrupt the OS
resolver; the structured caller waits for that worker to exit. Numeric addresses
avoid this resolver latency. No bounded-DNS-cancellation claim is made.

## Linux compiler and sysroot boundary

K/N 2.4.20 uses the LLVM 21 essentials package and a GCC 8.3/glibc 2.19
sysroot. The first host-GCC13 archives passed C tests and were embedded by
Cinterop, but **actual K/N test linking failed** with unresolved
`__isoc23_strtoull` (`03-linux-host-archive-link-failure.log`). Source compilation
and KLIB creation therefore did not establish a consumable Linux backend.

A direct GCC 8.3 build then failed inside debug-location generation for BoringSSL
AVX Keccak (`04-linux-gcc8-debug-compiler-failure.log`). A `-g0` diagnostic trial
passed that point but failed BoringSSL's error-level enum bitfield diagnostic
(`05-linux-gcc8-enum-compiler-failure.log`). Neither attempt is a health-test pass.

The final builder uses the exact Clang 21/LLD and sysroot package versions from
K/N, downloaded from JetBrains with SHA-256 verification. URLs and checksums are
in `../../experimental-native-backend.md` and the Gradle build script. No crypto
compiler warning is suppressed. `06-linux-clang-c-transport.log` records a full
independent CMake build with these compiler/sysroot settings and execution of the
real transport harness: **1 executed, 0 failed, CTest exit 0**. This confirms the C
backend with that toolchain; subsequent K/N linking and execution are recorded
separately. The Gradle download/extraction task chain must also execute in CI;
this manual C build does not stand in for that task-chain validation.
