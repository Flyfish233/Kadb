# mDNS Discovery

Kadb mDNS discovery is available as the optional `com.flyfishxu:kadb-mdns` artifact.

The module discovers ADB-related mDNS services only. It does not open ADB connections, perform pairing, or manage device authorization. Consumers decide how to use discovered endpoints with `Kadb.create(host, port)` or `Kadb.pair(host, port, code)`.

## Source dependency

This experimental branch does not publish packages. Use `project(":kadb-mdns")`
from this source tree. Discovery providers are available for Android and Darwin.
The Linux Native target exposes shared models and parsers only; Linux discovery
and the removed desktop JVM/JmDNS backend are unavailable.

## Service Types

The default configuration searches for:

- `_adb._tcp`
- `_adb-tls-connect._tcp`
- `_adb-tls-pairing._tcp`

`_adb._tcp` and `_adb-tls-connect._tcp` are exposed as connect endpoints. `_adb-tls-pairing._tcp` is exposed as pairing endpoints.

## Android

Android discovery requires an explicit `Context`:

```kotlin
val mdns = KadbMdnsAndroid(context)
mdns.start()
```

The Android implementation uses platform `NsdManager`, stores `context.applicationContext`, and supports API 23+. Android API 34 and newer use `NsdManager.ServiceInfoCallback`; older versions use `resolveService`.

## Darwin

```kotlin
val mdns = KadbMdnsIos() // historical public class name retained on iOS/macOS
mdns.start()
```

The Darwin adapter uses Foundation Bonjour and a running main run loop. iOS
applications must declare `NSLocalNetworkUsageDescription` and the required
`NSBonjourServices` entries in their Info.plist. Real multicast discovery and
permission prompts require separate network/device validation; common parser
and registry tests do not establish that coverage.

## Lifecycle

`KadbMdns` exposes a `StateFlow<MdnsDiscoveryState>`:

```kotlin
mdns.state.collect { state ->
    val target = state.connectDevices.firstOrNull()
    if (target != null) {
        // Kadb.create(target.host, target.port)
    }
}
```

Call `start()` to begin discovery. Call `stop()` or `close()` to stop listeners and clear state.

## Notes

- No default logging is emitted by the module.
- Discovery data is best-effort and network-dependent.
- The library trusts mDNS host/port data; connection failures should be handled by the caller.
- USB discovery remains out of scope.
