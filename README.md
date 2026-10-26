# Kadb — experimental Native core

This is the `experiment/kmp-native-core` branch of **Flyfish233/Kadb**, based on
upstream iOS commit `75678915fd4bdd52345edbb6bc4913ae3415a680`. It is a source-only
architecture experiment. No release or Maven/JitPack version is published for
this branch. See the [verification ledger](docs/experiment/VALIDATION.md) for
actual executed coverage and [combination licensing](docs/experiment/LICENSES.md)
for the AGPL-3.0-only Legacy SPAKE25519 dependency.

Kadb is a Kotlin Multiplatform ADB client library for talking directly to `adbd`.

It is intended for apps and tools that need shell, sync, install, pairing, or port forwarding without embedding the full `adb` CLI or server stack.

## Overview

- Direct Kotlin API for `adbd`
- Android plus iOS, macOS and Linux Native targets; see [platform scope and evidence](docs/platform.md)
- Android USB; shared wireless pairing, shell, file transfer, install and TCP forwarding protocols
- AOSP-aligned host behavior where practical

## Powered by Kadb

Kadb powers [WearOS Toolbox](https://wearosbox.com/), an Android smartwatch toolbox
for connecting to watches, managing apps, and transferring files.
Both Kadb and WearOS Toolbox are developed by Flyfish Studio.

## Build from this source tree

This branch deliberately removes the production desktop `jvm()` targets and
publication/signing plugins. Android still uses its supported Kotlin/Android
runtime. Existing Maven Central coordinates refer to upstream releases and do
not contain this experiment.

Use project dependencies in this checkout, as the external Native validation
consumer does:

```kotlin
dependencies {
    implementation(project(":kadb"))
    // Optional on Android/Darwin only:
    implementation(project(":kadb-mdns"))
}
```

The build composes the hash-verified `:spake2-legacy` sources at a fixed commit.
JitPack could not supply consumable KMP metadata/variants; this is an explicit
[source-composition fallback](docs/experiment/SPAKE2.md), not a claimed JitPack
integration. Kotlin/Native uses a separately pinned BoringSSL provider for
socket TLS, X.509/RSA, OS randomness, HKDF and AES-GCM.

## Quick Start

Connect to an existing device transport:

```kotlin
Kadb.create("127.0.0.1", 5555).use { kadb ->
    val response = kadb.shell("echo hello")
    check(response.exitCode == 0)
    check(response.output == "hello\n")
}
```

Pair with a new Android 11+ device:

```kotlin
Kadb.pair("10.0.0.175", 37755, "643102")
```

Discover wireless debugging endpoints with the optional mDNS artifact:

```kotlin
val mdns = KadbMdnsAndroid(context)
mdns.start()
```

```kotlin
// Historical class name retained for iOS API compatibility; also available on macOS.
val mdns = KadbMdnsIos()
mdns.start()
```

Discovered endpoints can be passed to `Kadb.create(host, port)` or `Kadb.pair(host, port, code)`.

## API Overview

| Capability | API |
| --- | --- |
| Connect to `adbd` over TCP | `Kadb.create(...)` |
| USB discovery / connection | Platform-specific `KadbUsb.devices(...)`, `KadbUsb.create(...)` |
| Wireless pairing | `Kadb.pair(...)` |
| Shell | `shell(...)`, `openShell()`, `openPtyShellSession()` |
| File transfer | `push(...)`, `pull(...)`, `openSync()` |
| APK install | `install(...)`, `installMultiple(...)`, `uninstall(...)` |
| Port forwarding | `tcpForward(...)` |
| Transport reuse | `resetConnection()` |
| Optional mDNS discovery | `KadbMdnsAndroid`, `KadbMdnsIos` (Darwin) |

## Examples

Install an APK:

```kotlin
Kadb.create("127.0.0.1", 5555).use { kadb ->
    kadb.install(apkFile)
}
```

Push a file:

```kotlin
Kadb.create("127.0.0.1", 5555).use { kadb ->
    kadb.push(localFile, "/data/local/tmp/remote.txt")
}
```

Forward a TCP port:

```kotlin
Kadb.create("127.0.0.1", 5555).tcpForward(
    hostPort = 7001,
    targetPort = 7001
).use {
    // localhost:7001 now forwards to the device's port 7001
}
```

## Platform and Pairing Notes

- Android target support starts at `minSdk 23`
- Basic connect / shell / sync / install flows do not require the full `adb` binary
- Pairing has stricter requirements than ordinary client operations
- Android 6 to 8 usually need an appropriate custom Conscrypt provider for pairing.
- Native TLS and identity operations use the pinned C provider; SPAKE25519 math
  and pairing state are shared Kotlin.
- `java.io.File` overloads remain on Android. Native callers use Okio `Path`,
  `Source` and `Sink`.

## Scope and Limitations

- Kadb is a direct client library; transport brokering and adb server-style device tracking are out of scope.
- USB connections remain Android-only. Desktop Native USB is not implemented.
- Standalone desktop JVM, Windows Native and Linux mDNS discovery are not supported by
  this branch. The removed JVM backend's USB/JmDNS/Windows capabilities are
  documented in [the JVM exit decision](docs/experiment/JVM_EXIT.md).
- Simulator, reference-peer and emulator results do not establish physical
  iPhone-to-Android interoperability or a security/performance certification.

## Documentation

- [USB connections](docs/usb.md) — Android setup, permissions and connection lifecycle
- [Platform notes](docs/platform.md) — runtime requirements and pairing dependencies
- [mDNS discovery](docs/mdns.md) — discovering wireless debugging endpoints
- [Host identity](docs/kadbcert.md) — managing and persisting ADB credentials
- [Security policy](SECURITY.md) — reporting vulnerabilities privately

## Acknowledgements

- [Dadb](https://github.com/mobile-dev-inc/dadb)
- [libadb-android](https://github.com/MuntashirAkon/libadb-android)
- [spake2-java](https://github.com/Flyfish233/spake2-java)
