# External Native consumer → Android Emulator adbd

This entry point proves that a separately compiled Kotlin/Native program can
link Kadb and use its **public API** against Android's actual `adbd`. It does not
link test source sets or use Kadb internals. Linux x86-64 and both macOS
architectures have executable targets. The selected target must really link and
run; configuring it or observing a skipped Gradle task is insufficient.

The companion APK is a normal Android application module,
`:validation-android-fixture`, with package
`com.flyfishxu.kadb.validation.fixture`. It has no permissions, components,
executable application code, Kadb dependency, or publication task. Its disposable
debug signing key is generated under its own build directory. The signing key's
time-dependent certificate means APK bytes are not claimed to be identical
between clean builds; every run records the actual APK SHA-256.

## Required environment and build

Use Python 3.11+, the repository's JDK/Gradle/Android SDK versions, a rootable
**disposable** API 35+ Android Emulator, and acceleration appropriate to the host.
Google Play images do not allow `adb root`; choose an AOSP or Google APIs image.
On Linux, `emulator -accel-check` must establish usable KVM. The initial local
engineering container had no `/dev/kvm`; that is an environment limitation, not
an emulator test pass. Use the CI runner with KVM for actual execution.

Build from the repository root, after the Native backend targets are present:

```sh
./gradlew --no-daemon --max-workers=2 \
  :validation-native-adbd:linkDebugExecutableLinuxX64 \
  :validation-android-fixture:assembleDebug
```

The expected files are:

```text
validation/native-adbd/build/bin/linuxX64/debugExecutable/kadb-native-adbd.kexe
validation/android-fixture/build/outputs/apk/debug/validation-android-fixture-debug.apk
```

For a macOS host, select `linkDebugExecutableMacosArm64` or
`linkDebugExecutableMacosX64` and the corresponding `build/bin` directory.
Preserve the complete Gradle log and both binary artifacts. A link task must not
be `SKIPPED`. When using a cached binary, preserve its original build provenance
as well as the checksum of the file executed.

## Disposable emulator bootstrap

The driver takes an already booted, explicitly named `emulator-N` transport. It
does not select the first connected device. It also verifies
`ro.kernel.qemu=1` **before** rooting, changing adbd settings, writing test public
keys, or installing anything. Its default ADB server port is 5038, separate from
the usual user session on 5037. Every ADB device command includes both `-P` and
`-s`; the script never kills a global ADB server.

For example, on a dedicated Linux CI runner with an installed command-line SDK:

```sh
set -eu
test -r /dev/kvm
KADB_EMULATOR_WORK="$(mktemp -d)"
export ANDROID_USER_HOME="$KADB_EMULATOR_WORK/android-user"
export ANDROID_AVD_HOME="$KADB_EMULATOR_WORK/avd"
export ANDROID_ADB_SERVER_PORT=5038
mkdir -p "$ANDROID_USER_HOME" "$ANDROID_AVD_HOME"

"$ANDROID_HOME/cmdline-tools/latest/bin/sdkmanager" \
  'emulator' 'platform-tools' 'system-images;android-35;google_apis;x86_64'
printf 'no\n' | "$ANDROID_HOME/cmdline-tools/latest/bin/avdmanager" create avd \
  --name kadb_native_validation --package 'system-images;android-35;google_apis;x86_64'

"$ANDROID_HOME/platform-tools/adb" keygen "$KADB_EMULATOR_WORK/bootstrap-key"
export ADB_VENDOR_KEYS="$KADB_EMULATOR_WORK/bootstrap-key"
"$ANDROID_HOME/platform-tools/adb" -P 5038 start-server
"$ANDROID_HOME/emulator/emulator" -accel-check
"$ANDROID_HOME/emulator/emulator" -avd kadb_native_validation -port 5554 \
  -no-window -no-audio -no-snapshot -no-boot-anim -accel on -gpu swiftshader \
  > "$KADB_EMULATOR_WORK/emulator.log" 2>&1 &
KADB_EMULATOR_PID=$!
```

Keep the SDK system-image and emulator `source.properties`, their
`package.xml`, emulator startup/version logs, and Android build fingerprint with
CI artifacts. SDK package names alone do not pin their mutable revisions. The
commands above are a bootstrap recipe, not a claim that an image was downloaded
or that a boot succeeded. The driver waits at most 120 seconds for boot and fails
if the selected bootstrap transport is not authorized or rootable. It does not
work around authorization by setting `ro.adb.secure=0`.

Version metadata uses `emulator -no-window -no-audio -version`, matching the
headless engine selected for startup. The `9a2ebbd` CI artifact recorded emulator
37.2.12 starting headlessly, but a plain `-version` selected the GUI engine and
failed to load `libpulse.so.0` before any product checks ran. The
[launcher source](https://android.googlesource.com/platform/external/qemu/+/c6efd5a2babeb3c0bbfdeadf4b7d95949b55c32d/android/emulator/main-emulator.cpp)
shows that `-version` and headless selection are separate flags. The argument
fix is infrastructure only; a subsequent real CI run must establish execution
of the fifteen checks.

Execute the validation from the repository root:

```sh
python3 validation/native-adbd/run_emulator.py \
  --serial emulator-5554 --adb-server-port 5038 \
  --adb "$ANDROID_HOME/platform-tools/adb" \
  --aapt2 "$ANDROID_HOME/build-tools/37.0.0/aapt2" \
  --emulator "$ANDROID_HOME/emulator/emulator" \
  --consumer validation/native-adbd/build/bin/linuxX64/debugExecutable/kadb-native-adbd.kexe \
  --apk validation/android-fixture/build/outputs/apk/debug/validation-android-fixture-debug.apk \
  --output build/validation/native-adbd-emulator
```

The output directory must be new. Preserve `report.json` and `commands.jsonl`
even when the process exits nonzero. After preserving emulator logs, stop only
the instance created by this job, for example `adb -P 5038 -s emulator-5554 emu
kill`, then wait for its recorded process. Remove the job's disposable AVD and
bootstrap key directory. CI should implement this cleanup in its final step
even when the build or consumer fails.

## What is actually exercised

The consumer always requires all fifteen checks; it has no missing-environment
skip branch. Missing arguments exit nonzero. The Python driver rejects scripts
in place of an ELF/Mach-O binary, checks the APK's exact package and absence of
permissions with `aapt2`, requires a successful consumer exit, the exact check
list, and at least three observed TCP connections.

| Check | Assertion |
| --- | --- |
| `identity_import` | Import an ephemeral RSA private key through public `KadbCert`; wipe the buffers owned by the consumer. |
| `feature_negotiation` | Real peer advertises shell_v2, stat_v2, ls_v2, sendrecv_v2, and cmd. |
| `shell_v2` | Exact stdout/stderr separation and exit status 7. |
| `sync_transfer` | 1 MiB + 13 bytes with zero/high-bit data survive push/pull byte for byte. |
| `sync_stat` | Regular-file type, size, fixed second-granularity mtime, and device mode 0666 for a requested 0600 under the stated AOSP permission-policy assumption. |
| `sync_shell_metadata` | Android's `sha256sum` and `stat` independently confirm Sync content/metadata. |
| `sync_directory` | list_v2 yields the exact named file and size. |
| `sync_symlink` | lstat sees a symlink; stat follows it; pull through it returns exact content. |
| `sync_empty_file` | Zero-length Sync push/pull/stat. |
| `install` | Public install API streams the real fixture APK; Package Manager reports it installed. |
| `uninstall` | Public uninstall API removes that package. |
| `reconnect_1`, `reconnect_2` | reset discards the transport; the next shell opens a working new connection. |
| `cleanup` | Remove only this run's uniquely named files and directory. |
| `close_terminal` | Repeated close is safe; a closed client rejects another command with IOException. |

The permission request remains **0600**. The pinned AOSP daemon's
[`send_impl`](https://android.googlesource.com/platform/packages/modules/adb/+/1cf2f017d312f73b3dc53bda85ef2610e35a80e9/daemon/file_sync_service.cpp#532)
copies owner permission bits to group and other, producing **0666** for this
regular-file request. Its platform `adbd_fs_config` hook can then override the
mode, depending on the device image, process UID and path policy. This fixture
uses a uniquely named file under `/data/local/tmp`; 0666 is the reference
expectation for that test environment, not a guarantee for every Android device.

The consumer prints and records requested mode, observed mode, reference mode,
the actual remote path and the pinned source URL separately. A different observed
mode records `mismatch_requires_triage` and stops this validation with a failure;
that result alone does not establish a Kadb protocol defect. Investigate the
device's `fs_config` policy and the transmitted mode before attributing it to Kadb.
The independent Android `stat` check still verifies the same expected metadata.
The [scoped Sync source review](../../docs/experiment/SYNC_REVIEW.md) records the
source hashes and the unchanged timestamp/symlink behavior.

The driver independently checks package and directory removal through official
ADB. It also attempts cleanup after a consumer failure, restores the original
public-key authorization list and adbd TCP setting, and restores adbd's initial
root/non-root state. Cleanup failures make the overall run fail. Only the new
test public key reaches Android; private keys stay in an automatically removed
host temporary directory and are not included in reports.

## AUTH, TLS, and evidence boundaries

The endpoint is a real emulator `adbd` TCP listener reached through official ADB
forwarding. Kadb's ADB protocol bytes pass through a loopback relay unchanged;
the relay records only header command, arguments, length, direction, and counts.
It never records payloads, shell contents, signatures, private keys, or TLS data.
`STLS` ends plaintext observation for that direction.

When `ro.adb.secure=1`, a fresh, not-yet-authorized key is first used for a bounded
negative connection probe. That probe's product exit must be nonzero, an actual
AUTH token/signature exchange must be observed, and no peer CNXN may follow for
the report to count an unauthorized rejection. It is labeled
`expected_rejection_probe` with `product_health_test=false`. It is never counted
as one of the fifteen positive product checks. The driver then installs only
the ephemeral public key, reloads adbd, and runs the full consumer.

Some rootable emulator images disable AUTH. Such a run can establish real ADB
protocol interoperability but **cannot establish RSA authentication**. The
report separately records the image property, actual AUTH frame evidence,
positive authentication, and the negative probe result. Use `--require-auth`
to fail unless both positive RSA authentication on all three connections and
unauthorized-key rejection are observed. No downgrade or authentication-disable
option exists in this driver.

An observed STLS exchange is reported separately. This scenario does not itself
validate wireless pairing, the TLS exporter/PeerInfo binding, a physical iPhone
or Android phone, network discovery, security certification, or performance.
Those have separate tests and evidence. A passing loopback/emulator run must not
be described as a phone-to-phone result.

## Driver self-checks and evidence status

```sh
python3 -m unittest discover -s validation/native-adbd -p 'test_*.py' -v
python3 -m py_compile validation/native-adbd/adb_observer.py validation/native-adbd/run_emulator.py
```

The observer tests cover fragmented/coalesced headers, payload bytes that look
like AUTH headers, transition to opaque TLS, invalid magic, and byte-preserving
large-payload/half-close relay behavior. These are validation-infrastructure
tests; passing them does not count as a Kadb-to-adbd run. At the initial commit
of this entry point, Android APK and Native linking/runtime execution remain
pending the CI/toolchain test slot. Record actual results in the experiment
verification ledger without changing this statement into a fabricated pass.

Primary references:

- [Android Emulator command-line options](https://developer.android.com/studio/run/emulator-commandline)
- [Emulator acceleration and graphics modes](https://developer.android.com/studio/run/emulator-acceleration)
- [Official ADB command reference](https://android.googlesource.com/platform/packages/modules/adb/+/1cf2f017d312f73b3dc53bda85ef2610e35a80e9/docs/user/adb.1.md)
- [AOSP daemon authentication](https://android.googlesource.com/platform/packages/modules/adb/+/1cf2f017d312f73b3dc53bda85ef2610e35a80e9/daemon/auth.cpp)
- [AOSP Android 15 authorization-store behavior](https://android.googlesource.com/platform/frameworks/base/+/refs/heads/android15-release/services/core/java/com/android/server/adb/AdbDebuggingManager.java)
