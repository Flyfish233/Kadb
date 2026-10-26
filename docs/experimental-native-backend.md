# Experimental POSIX and Darwin backend

This change starts from `75678915fd4bdd52345edbb6bc4913ae3415a680`, reuses its iOS
backend and keeps platform code out of common protocol logic.

- `nativeMain`: POSIX socket ownership, in-place TLS, BoringSSL identity/AEAD
  primitives, native file and Sync helpers, and TCP forwarding. These sources
  apply to the currently configured POSIX Native targets, not Windows.
- `appleMain`: Foundation reentrant locks, worker threads and logging; both iOS
  and macOS use this single Darwin implementation.
- `iosMain`: UIKit-based default device name only.
- `macosMain`: macOS default device name.
- `linuxMain`: pthread reentrant lock/condition and detached workers, Linux
  logging and host name.

The C adapter owns socket layout, IPv4/IPv6 listeners, SIGPIPE suppression,
nonblocking I/O, cancellation wakeups, TLS 1.3 and exporter plumbing. It is an
internal C ABI, not a new public Kadb API. BoringSSL's pinned source and license
remain documented in `kadb/third_party/boringssl`; no opaque prebuilts are shipped.
The adapter clears native TLS/key resources when the last active operation exits
a closed owner, without waiting for Kotlin's cleaner.

## Targets and evidence boundary

Configured core targets are `iosArm64`, `iosSimulatorArm64`, `macosArm64`,
`macosX64`, and `linuxX64`, in addition to Android and the temporary desktop JVM
baseline. Target configuration by itself does not establish support. Follow the
experiment's verification ledger and CI job results for compilation, linking,
execution and external-consumer evidence. The initial C backend evidence is in
[`verification/native/README.md`](verification/native/README.md).

The mDNS module shares Foundation Bonjour code via `appleMain`. Its original
`KadbMdnsIos` public class name is retained, including on macOS, to preserve the
iOS API. The Linux mDNS artifact currently offers common models and parsing only;
**there is no Linux discovery implementation**. No Native USB backend is provided.
These are explicit desktop feature gaps when assessing JVM removal.

The native CMake builder selects the iOS SDK for iOS, macOS SDK/architecture for
macOS and the host compiler for Linux. Apple archives request iOS 15 or macOS 12;
CI must inspect final framework deployment metadata before declaring older OS
compatibility. Linux system C++ toolchains introduce a libstdc++/glibc runtime
floor that must be assessed from the actual linked consumer. `mingwX64` is not
configured or claimed to work.

`getaddrinfo` remains a blocking system resolver. The already-published socket
owner can be closed before or during connect and can never reopen after close.
Poll waits are interruptible, but a coroutine canceled during DNS still waits for
the resolver worker to return. This limitation is not a bounded-cancellation claim.

## Test entry points

```sh
# Core Kotlin/Native tests execute on the matching host/architecture.
./gradlew :kadb:linuxX64Test
./gradlew :kadb:macosArm64Test
./gradlew :kadb:macosX64Test
./gradlew :kadb:iosSimulatorArm64Test -PiosSimulatorDevice=booted

# Device architecture compiles and links; this does not run on an iPhone.
./gradlew :kadb:linkDebugFrameworkIosArm64

# Host C transport regression and optional shim/harness sanitizers.
KADB_SANITIZE=1 scripts/test-native-c.sh /absolute/path/to/verified/boringssl
```

Native tests exercise real POSIX socket pairs, blocking-reader cancellation,
reentrant condition semantics and inherited identity/AEAD wire fixtures. Apple
session and forwarding tests are shared across iOS Simulator and macOS. The
existing opt-in physical device test still requires device configuration; a test
which returns without that configuration is not physical-device evidence.
