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
macOS and pinned LLVM 21 and GCC 8.3/glibc 2.19 sysroot packages matching Kotlin/Native for Linux. Apple archives request iOS 15 or macOS 12;
CI must inspect final framework deployment metadata before declaring older OS
compatibility. The Linux toolchain archive comes from JetBrains and is verified before use:
`https://download.jetbrains.com/kotlin/native/x86_64-unknown-linux-gnu-gcc-8.3.0-glibc-2.19-kernel-4.9-2.tar.gz`,
SHA-256 `a048397d50fb5a2bd6cc0f89d5a30e0b8ff0373ebff9c1d78ce1f1fb7f185a50`.
Clang and LLD come from
`https://download.jetbrains.com/kotlin/native/resources/llvm/21-x86_64-linux/llvm-21-x86_64-linux-essentials-116.tar.gz`,
SHA-256 `0b1f290214dd7ec20e2506210967e0ebd735cdefc3a3b4485bbccb439fa78e5b`.
Both packages match the dependencies named by the pinned K/N 2.4.20 distribution.
A host-GCC13 trial imported `__isoc23_strtoull` and actually failed K/N linking.
Compiling current BoringSSL with GCC 8.3 then encountered a debug-generation
internal compiler error and an enum bitfield diagnostic. Those failed experiments
remain in the verification logs. The final C build uses Clang 21 with that GCC
package's headers, sysroot and libraries; BoringSSL warnings remain errors.
The actual linked consumer still determines the runtime floor; no claim of
running on glibc 2.19 is made without that environment. `mingwX64` is not
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
inherited Android-device smoke test is excluded from default source sets. It is
added only with `-PenableIosDeviceSmoke=true`, and then missing any required
`KADB_DEVICE_*` / pairing parameters is an error. For example, on a configured
macOS test host:

```sh
./gradlew :kadb:iosSimulatorArm64Test -PiosSimulatorDevice=booted \
  -PenableIosDeviceSmoke=true --tests com.flyfishxu.kadb.RealDeviceSmokeTest
```

This opt-in contacts only the configured Android device and removes the unique
remote temporary file it created. **An iOS Simulator client talking to a physical
Android device is still not an iPhone run.** A true iPhone-to-adbd claim requires
an actual device test host and separately recorded device evidence.
