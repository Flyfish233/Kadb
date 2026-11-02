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

The environment gate passed in run `41447772316` on exact code
`01220570ce2fc17e819c318d99a57b87e1cf9d43`; its raw evidence is retained under
`runs/41447772316/`. The dedicated workflow now compiles only the Linux Native
authentication and real-pairing consumers and executes `ci/run_auth.py`.

The RSA stage enrolls A through a matching pending Android confirmation, then
requires independently verified signatures and CNXN on new A connections before
and after B's explicit framework/adbd denial. The TLS stage uses a separate fresh
A/B pair, real public `Kadb.pair`, accepted A, rejected B, accepted A again,
targeted removal and rejected revoked A. Authorized control C then proves the
same wireless listener remains healthy. No wrong-code or cross-platform matrix
is repeated.

`auth_observer.py` extends the existing M3 byte-transparent relay. RSA token and
signature are used in memory for independent public-key verification; reports
retain only hashes, lengths and results. TLS records are not decrypted. System
logs restricted to the actual adbd PID supply separate key-match and certificate
verification decisions. A failed consumer or ServerHello alone never satisfies
the identity rejection criteria.

Every actual `.kexe` is associated with the exact CI commit, fixed Maven binary
resolution, dependency source lock and complete corresponding-source artifact.
Installed official Android image files are independently hashed; shell access to
the platform adbd ELF is restricted on the user image and is not bypassed.

Current stage verdicts and execution references are in `verdict.json` and the
delivery document; environment success alone does not upgrade M4-A/M4-B.
