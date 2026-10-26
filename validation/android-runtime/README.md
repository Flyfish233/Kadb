# Android APK / ART public-API validation

This is a separate self-instrumenting Android APK that consumes the production
`:kadb` Android variant. It leaves `validation/android-fixture` unchanged: that
other APK remains a permission-free install/uninstall payload for Native-to-adbd
tests. This APK requests only `INTERNET` and has no Activity or AndroidX test
runner. Its Java `android.app.Instrumentation` calls the public Kotlin/Java API,
including the suspending `Kadb.pair` through the public coroutine entry points.

Building the Android library or running Host Tests does not exercise D8, ART,
the Android TLS provider or Android hidden-API access. This entry point adds those
separate gates. An APK build/DEX inventory alone still does not count as runtime
execution; only the mandatory emulator driver can produce that result.

## Build and inspect the actual APK

```sh
./gradlew :validation-android-runtime:assembleDebug \
  :validation-pairing-peer:writePeerClasspath --no-build-cache --console=plain
python3 validation/android-runtime/inspect_apk.py \
  validation/android-runtime/build/outputs/apk/debug/validation-android-runtime-debug.apk \
  --output evidence/android-runtime-apk.json
```

The inspector walks real DEX `class_defs`, not arbitrary class-name strings. It
requires the Instrumentation, public Kadb and KadbCert classes, and the shared
Legacy SPAKE25519 class. It rejects the host-only Conscrypt provider and old Java
SPAKE oracle in the APK. Its output records APK/DEX hashes and class counts.
Preserve the actual Gradle log, APK and inventory; require the D8/package tasks
to execute, rather than inferring success from an unrelated task's build status.

The debug signing key is generated only in this module's build directory. Its
time-dependent certificate means APK bytes are not claimed reproducible between
fresh builds; the exact executed APK is always hashed.

The three Bouncy Castle runtime JARs contain the same `META-INF/LICENSE.md` path.
This consumer merges all copies into the APK instead of dropping notices.
It excludes only their conflicting Java 9 OSGi bundle manifests, which describe
the separate Java bundles rather than this Android APK; their original contents
remain in the dependency archives and corresponding-source inventory.

After building, export the **resolved APK runtime** artifacts, including exact
coordinates, variants, original local paths and SHA-256 values:

```sh
./gradlew -I validation/android-runtime/runtime-classpath.init.gradle \
  :validation-android-runtime:recordRuntimeClasspath --no-configuration-cache
```

Preserve `validation/android-runtime/build/reports/debug-runtime-classpath.json`.
This is intentionally separate from the Host Test and Java reference peer
classpaths. It identifies the runtime dependencies for the corresponding-source
collector; a dependency/hash report by itself is not a source bundle.

## Execute on an explicitly selected disposable emulator

Use the already booted API 35 Google APIs emulator from the Native validation
workflow. No root operation or authentication change is needed for this APK.
The driver verifies the exact `emulator-N` serial, separate ADB server port and
`ro.kernel.qemu=1` before installing. Instrumentation additionally requires
emulator hardware and the Android runtime. The APK has minSdk 23 for packaging,
but this TLS 1.3 scenario deliberately requires runtime API 29 or newer; it is
not evidence for execution on every supported Android API level.

Build `:validation-pairing-peer:writePeerClasspath` on the **same host** that
runs the driver. The classpath file contains machine-local paths and must not be
copied unchanged from another CI runner.

```sh
python3 validation/android-runtime/run_android_runtime.py \
  --serial emulator-5554 --adb-server-port 5038 \
  --adb "$ANDROID_HOME/platform-tools/adb" \
  --aapt2 "$ANDROID_HOME/build-tools/37.0.0/aapt2" \
  --java "$JAVA_HOME/bin/java" \
  --classpath-file validation/pairing-peer/build/reference-classpath.txt \
  --apk validation/android-runtime/build/outputs/apk/debug/validation-android-runtime-debug.apk \
  --output evidence/android-runtime
```

The output directory must be new. The driver refuses to replace an already
installed runtime fixture. It starts the existing independent `IosPairingPeer`
Java process, without changing or copying its protocol. Its listener remains on
host `127.0.0.1`; the APK reaches it using Android Emulator's documented
`10.0.2.2` host-loopback alias. The peer's seven dependency hashes and compiled
classes are checked by the same helper used by the Native interop driver.

The driver invokes the system runner with explicit `peer_host`, `peer_port` and
`run_id` Instrumentation arguments. Missing arguments are failures, never skips.
Each pairing call has a 20-second coroutine timeout; the host additionally
bounds readiness, Instrumentation and peer exit. The APK uses app-private storage
under a unique run directory and cleans it; the driver force-stops and uninstalls
only this initially absent fixture after success or failure. Cleanup failure
keeps the overall result failed.

## Required checks and result gate

All nine checks must appear in this exact order:

1. `identity_generate`: real 2048-bit RSA and self-signed X.509 generation, expiry
   metadata and Android certificate verification.
2. `identity_export_copy_isolation`: modifying an exported private-key buffer
   does not change the identity retained by Kadb.
3. `identity_import_certificate`: a valid exported key/certificate pair retains
   the same certificate and fingerprint on import.
4. `identity_file_persistence`: a fresh public `OkioFilePrivateKeyStore` instance
   reloads the same private key and RSA public identity from app-private storage;
   completed writes leave no staging files. A regenerated certificate's
   fingerprint is deliberately not assumed stable across reloads.
5. `identity_diagnostic_redaction`: public snapshot diagnostics omit PEM fields.
6. `identity_parse_failure_retains_state`: invalid PEM produces the public typed
   exception and retains the prior ready identity.
7. `pairing_positive`: public `Kadb.pair` completes against the independent Java
   Legacy peer, including TLS exporter binding and authenticated PeerInfo.
8. `pairing_wrong_code`: the second session fails in the client, and the separate
   peer must independently confirm AEAD authentication failure.
9. `identity_clear`: the public clear operation removes the persisted key and
   subsequent private-key export is absent.

The app reports SDK/fingerprint, hardware, process UID/PID, VM identity and the
default TLS provider. No test Conscrypt is bundled: this scenario must exercise
Android's actual provider/exporter path. Private-key buffers owned by the app
are wiped after the checks; this is not a proof of erasure of all VM/provider
copies or an independent security audit.

The host requires **all** of: successful ADB command; exactly one structured
Instrumentation report; `INSTRUMENTATION_CODE: -1` (`RESULT_OK`); the exact nine
checks; Android runtime/provider metadata; successful independent peer exit;
and peer confirmation of one positive and one wrong-code session. `am instrument`
can otherwise return a successful shell exit despite failed tests, so shell exit
alone is never accepted. Save `commands.jsonl`, `instrumentation.log`,
`java-peer.log` and `report.json` on both success and failure.

The resulting scope is **Android Emulator ART → independent Java pairing peer**.
It is not a real phone, real-adbd pairing, Android Keystore coverage, whole-API
coverage, security certification, performance acceptance or a Native test result.
The separate Native-to-adbd driver still owns Shell/Sync/install/reconnect checks.

## Small host checks

```sh
python3 -B -m unittest discover -s validation/android-runtime -p 'test_*.py' -v
```

These negative gates check incomplete/duplicate instrumentation reports,
misleading process exits, wrong runtime/provider metadata, and DEX class-name
strings without definitions. They are validation-infrastructure tests, not ART
execution. Record actual APK build and emulator results separately in the ledger.

Primary references:

- [Android Instrumentation API](https://developer.android.com/reference/android/app/Instrumentation).
- [Self-instrumenting tests](https://source.android.com/docs/core/tests/development/instr-self-e2e).
- [Android Emulator network address space](https://developer.android.com/studio/run/emulator-networking#networkaddresses).
- [DEX format](https://source.android.com/docs/core/runtime/dex-format).
