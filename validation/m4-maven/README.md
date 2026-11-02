# M4 enforced identity authentication

Scope: real RSA AUTH and real wireless TLS identity rejection on an isolated,
disposable Android emulator. M1/M2/M3 evidence is retained unchanged. No physical
device is selected; no cryptographic production code or fixed Maven candidate is
changed.

Initial target: official SDK `system-images;android-35;google_apis_playstore;x86_64`,
fresh Google Play `user` image. A freshly generated bootstrap control key C is
provided through the emulator's normal host-key provisioning. Test identities A
and B are generated independently and are never bootstrap keys.

`ci/probe_environment.py` requires `ro.adb.secure=1`, a real 20-byte AUTH token
on a fresh connection, shell UID 2000, MANAGE_DEBUGGING permission and the actual
API 35 system Binder interface. These establish an executable environment only;
they do not constitute M4-A or M4-B PASS.

Normal authorization and pairing use the Android system service behind Settings,
with public authorization state read via `dumpsys adb`. The framework itself
checks that a key approved by `allowDebugging` matches the pending confirmation.
There is no direct authorization-file write, root request, image patch or auth
property override in M4.

Primary source references:

- [Goldfish bootstrap key provisioning](https://android.googlesource.com/device/generic/goldfish/+/79766c4d6eb22852aea508c587d1f130892f2c18/init.ranchu.adb.setup.sh)
- [Android 15 IAdbManager](https://android.googlesource.com/platform/frameworks/base/+/refs/heads/android15-release/core/java/android/debug/IAdbManager.aidl)
- [Android 15 AdbService permissions](https://android.googlesource.com/platform/frameworks/base/+/refs/heads/android15-release/services/core/java/com/android/server/adb/AdbService.java)
- [Android 15 AdbDebuggingManager authorization and revocation](https://android.googlesource.com/platform/frameworks/base/+/refs/heads/android15-release/services/core/java/com/android/server/adb/AdbDebuggingManager.java)
- [Android 15 shell permissions](https://android.googlesource.com/platform/frameworks/base/+/refs/heads/android15-release/packages/Shell/AndroidManifest.xml)

The dedicated workflow is initially an environment probe; actual Native M4
acceptance is added once the environment gate executes. Until then M4-A and
M4-B remain NOT VERIFIED.
