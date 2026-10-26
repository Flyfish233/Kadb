# Platform scope of the Native-core experiment

The source targets below describe this branch's architecture. Executed evidence
is recorded per commit/job in [VALIDATION.md](experiment/VALIDATION.md); target
configuration, compilation, linkage, unit execution and device interoperability
are different claims.

| Target | Production transport/provider | mDNS | USB | Public file API |
| --- | --- | --- | --- | --- |
| Android, minSdk 23 | Android socket/TLS, JCA/Bouncy Castle; optional compatible Conscrypt for pairing | Android NSD | Android USB Host | Existing `File` overloads plus Okio |
| `iosArm64` | Shared POSIX/BoringSSL Native backend | Foundation Bonjour | Unavailable | Okio |
| `iosSimulatorArm64` | Same Native backend on simulator SDK | Foundation Bonjour | Unavailable | Okio |
| `macosArm64` | Same Native backend on macOS SDK | Foundation Bonjour | Unavailable | Okio |
| `macosX64` | Same Native backend on Intel macOS | Foundation Bonjour | Unavailable | Okio |
| `linuxX64` | POSIX/BoringSSL with a matching K/N libc/toolchain | Unavailable | Unavailable | Okio |
| Desktop JVM / Windows Native | Not supported in this experiment | — | — | — |

KGP 2.4.20 deprecates `macosX64` for removal in a future toolchain. This branch
pins its current toolchain and tests that target on an actual Intel runner; it
does not promise indefinite future compiler support. Deployment targets are
iOS 15 and macOS 12. `macosArm64Test` on an Intel host, or Apple tasks on Linux,
may be disabled by KGP and cannot count as executed tests.

## Shared logic and provider boundaries

`commonMain` owns ADB frames/checksums, connection and stream lifecycle, Shell
and shell-v2, Sync and installation orchestration, pairing state, exact protocol
labels, identity/store contracts and protocol models. The pinned shared Kotlin
Legacy SPAKE25519 module supplies the PAKE math. RFC 9382 is not substituted.

`androidMain` retains Android/JCA/Bouncy Castle behavior and the original File
bridges. `nativeMain` owns POSIX transport/TLS and Native crypto/identity adapters.
`appleMain` supplies Foundation locks, threads and logging; `linuxMain` supplies
pthread equivalents. Platform default names remain in their narrow source sets.
`kadb-mdns` shares registry and service-type parsing in common code, with only
system discovery in Android/Apple adapters.

Socket/TLS, secure entropy, AES/HKDF providers, certificates, filesystem safety
and USB are not forced into common code. Synchronous APIs remain synchronous.
Cancellation of suspend pairing closes the socket and waits for its blocking
worker before returning, preventing use-after-destroy of PAKE state.

## Native provider and identity

The C bridge uses BoringSSL at the exact revision and archive hash recorded in
`kadb/gradle/ios-native.gradle.kts` and retains its license under
`kadb/third_party/boringssl`. TLS upgrades the existing ADB socket, uses the ADB
certificate-selection convention and the exact NUL-terminated pairing exporter
label. See [Native provider evidence](verification/native/README.md).

The default identity store is process-local memory. Persistent identities use
the supplied store interface and explicit caller configuration. Native filesystem
storage is not a Keychain/Secure Enclave integration; OS-backed custom stores can
be supplied through that interface. Do not infer durable identity behavior from
a memory-store-only test.

## Compatibility and validation commands

Android AARs are compared with frozen Kotlin-public ABI and javap snapshots.
File default-argument bridges and public pairing signatures have dedicated
compatibility tests. iOS framework declarations are compared with the frozen
header; a separate Swift executable compiles, links and calls the produced
framework. Native protocol/pairing consumers do not access internal test friends.

```sh
./gradlew :kadb:testAndroidHostTest :kadb-mdns:testAndroidHostTest :kadb:bundleAndroidMainAar
./gradlew :kadb:linuxX64Test :validation-native-adbd:linkDebugExecutableLinuxX64
./gradlew :kadb:macosArm64Test :kadb:linkDebugFrameworkMacosArm64
./gradlew :kadb:macosX64Test :kadb:linkDebugFrameworkMacosX64
./gradlew :kadb:iosSimulatorArm64Test :kadb-mdns:iosSimulatorArm64Test -PiosSimulatorDevice=EXPLICIT_UDID
./gradlew :kadb:linkDebugFrameworkIosArm64
```

Run only commands matching the host. The CI summary requires nonempty executed
XML groups. Physical-device tests, real Bonjour browsing, Android USB behavior,
Windows, performance acceptance and an independent cryptographic audit require
separate evidence; none follows from `BUILD SUCCESSFUL`.
