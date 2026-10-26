# USB connections

## Android USB Host

The Android target exposes `com.flyfishxu.kadb.usb.KadbUsb` for direct ADB over USB.
It uses Android's USB Host API, without a bundled adb executable or native USB library.
This experimental branch supports USB on Android only; the desktop JVM backend was removed.

The controlling Android device must support USB Host/OTG. Use a data-capable cable;
the target must expose an ADB interface and have USB debugging enabled.

Declare the optional feature in the application manifest:

```xml
<uses-feature android:name="android.hardware.usb.host" android:required="false" />
```

Enumerate and let the user choose a device:

```kotlin
val manager = context.getSystemService(UsbManager::class.java)
val devices = KadbUsb.devices(manager)
```

Use `UsbManager.requestPermission(device, pendingIntent)` if permission is missing.
Handle the result in the application and verify `manager.hasPermission(device)`.
This permission is separate from the target device's “Allow USB debugging” prompt.
Kadb does not display either prompt itself and does not use wireless pairing for USB.

After permission is granted, perform blocking operations on an I/O dispatcher:

```kotlin
withContext(Dispatchers.IO) {
    KadbUsb.create(context, device).use { kadb ->
        val response = kadb.shell("echo hello")
        check(response.exitCode == 0)
    }
}
```

`create` is lazy: the first command opens the interface and authenticates using the
existing `KadbCert` identity. Shell, sync, installation and TCP forwarding APIs are
the same as for a network connection. TCP keepalive options do not apply to USB.

Keep **one Kadb instance per physical USB device** and multiplex operations through
its independent ADB streams. Do not create separate clients for health probes,
installation progress or screen streaming. Close an operation's stream when it
ends; close Kadb only when the entire device session ends.

The transport cancels pending reads on close/detach. The application must bound
initial authorization waiting and close the pending Kadb when the user cancels;
`withTimeout` alone cannot interrupt blocking Kadb calls. Individual USB writes
have a bounded timeout. After unplug/replug, enumerate, select and check permission
again; USB bus addresses must not be persisted as device identity.

## Native scope and validation

There is no macOS/Linux/Windows Native USB provider in this experiment. Use a
TCP adbd endpoint for Native clients. The old desktop JVM API and hardware
smoke entry point remain recoverable from the frozen baseline commit, not as
unsupported source sets in the current build.

Host-side scripted USB channel tests exercise protocol behavior and error
handling. They do not establish Android USB permission flows, cable hot unplug,
physical device enumeration or OEM driver compatibility. Those need a physical
Android host/device setup and are listed separately in the verification ledger.
