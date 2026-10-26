# Independent Java pairing reference after the production JVM target exits

`:validation-pairing-peer` is a test process with **no Kadb dependency**, no
Kotlin plugin, no publication plugin, and no consumable or produced JAR. Its
compiled Java classes run the independent reference against an external Native
consumer. This does not restore a desktop JVM production target.

The original Kotlin `IosPairingPeer` at Kadb baseline
`75678915fd4bdd52345edbb6bc4913ae3415a680` depended on Kadb JVM's internal identity
and public-key code. The Java adaptation here creates its own JCA/BC TLS identity
and independently encodes AOSP's 524-byte RSA public-key representation. It uses
the original Java SPAKE implementation, Conscrypt TLS exporter, JCA HKDF and
AES-GCM, and bounded, big-endian pairing framing. No SPAKE mathematics are copied
into Kadb or this peer.

## Reference provenance and licenses

The independent SPAKE artifact is
`com.github.Flyfish233:spake2-java:1.1.1`. The tag was read-only resolved to
[`809ad7aa731f475c07763b1ad2c165ae192dfb5f`](https://github.com/Flyfish233/spake2-java/tree/809ad7aa731f475c07763b1ad2c165ae192dfb5f).
Its retrieved POM declares GNU GPL v3. The exact JAR SHA-256 is
`077e52ff5594401cdbfca66f9b4d315676e01dff98eaa8ef302fa748ac508028`; the full GPL
text is retained at [the reference fixture license](../spake2/GPL-3.0-fixture-license.txt).
The library's curve core is the separate `cafe.cryptography` Elisabeth
implementation, not the new Kotlin SPAKE core used by production Kadb.

`SHA256SUMS` also fixes both Elisabeth runtime JARs, Conscrypt 2.7.0, and
Bouncy Castle 1.86's three JARs. `verifyReferenceClasspath` checks the entire
seven-artifact inventory and every checksum before compilation or execution.
A mutable remote tag cannot silently replace this oracle. Existing third-party
license/notice files remain inside the original dependency artifacts. Preserve
those artifacts' notices and supply their corresponding source if distributing
a combined validation binary under applicable license terms. This test-only
GPL reference is separate from production Kadb's AGPL source dependency and
does not relabel original Apache-2.0 Kadb source files. See
[the experiment license record](../../docs/experiment/LICENSES.md).

The test server intentionally trusts a presented client TLS certificate, then
checks that the authenticated PeerInfo public key and name match that exact
certificate. That is a bounded loopback interoperability fixture, not a server
trust policy for a deployed application.

## Build and mandatory execution

Build both programs before starting the bounded driver:

```sh
./gradlew --no-daemon --max-workers=2 \
  :validation-pairing-peer:writePeerClasspath \
  :validation-native-adbd:linkPairingDebugExecutableLinuxX64

python3 validation/pairing-peer/run_interop.py \
  --java "$JAVA_HOME/bin/java" \
  --classpath-file validation/pairing-peer/build/reference-classpath.txt \
  --consumer validation/native-adbd/build/bin/linuxX64/pairingDebugExecutable/kadb-native-pairing.kexe \
  --output build/validation/native-pairing-linux
```

For macOS, use `linkPairingDebugExecutableMacosArm64` or
`linkPairingDebugExecutableMacosX64` and the matching output directory. For an
actually booted iOS Simulator, use
`linkPairingDebugExecutableIosSimulatorArm64` and pass its explicit UDID:

```sh
python3 validation/pairing-peer/run_interop.py \
  --java "$JAVA_HOME/bin/java" \
  --classpath-file validation/pairing-peer/build/reference-classpath.txt \
  --consumer validation/native-adbd/build/bin/iosSimulatorArm64/pairingDebugExecutable/kadb-native-pairing.kexe \
  --simulator-udid "$KADB_SIMULATOR_UDID" \
  --output build/validation/native-pairing-ios-simulator
```

The driver checks the UDID in `simctl`'s booted-device inventory and invokes
`xcrun simctl spawn` for that specific device. Missing configuration, invalid
artifacts, process timeouts, absent result records, or incomplete session counts
exit nonzero. Both program exit codes and both final records must agree:

- The Native program must complete exactly two checks through public
  `Kadb.pair`: a successful `123456` session and rejection of `654321`.
- The independent peer must complete exactly two TLS 1.3 sessions, verify the
  successful PeerInfo key/name/zero padding, and detect an invalid AES-GCM tag
  with the wrong pairing code.

The Native wrong-code error alone is insufficient: a transport failure must not
be confused with rejection of the correct cryptographic exchange. Requiring the
peer's AES-GCM result supplies that distinction. The peer also checks the exact
SPAKE message length, ADB NUL-terminated role identities and exporter label,
64-byte exporter, HKDF context, 128-bit AES key, 96-bit nonce zero for the initial
record, PeerInfo size/type, and network-order frame lengths.

Save `report.json`, `java-peer.log`, `native-consumer.log`, the linked Native
binary, and the Gradle build log. The report includes exact oracle JAR and class
hashes, Native binary SHA-256, actual command lines, runtime version, session
counts, and elapsed Native time. Timing is diagnostic data only; no performance
acceptance threshold or constant-time guarantee is inferred.

`iosInteropPeer` remains the Java module's manual server task. Its ready file is
created atomically and a completed run exits only after both sessions. The root
Kadb task may delegate to `:validation-pairing-peer:iosInteropPeer` to keep that
developer entry point. The old internal-API iOS test is explicitly `@Ignore` and
retained as baseline reference; it can no longer appear as a successful test
when no peer was configured. Only the mandatory external run counts as new
Native pairing evidence.

## Android Host regression migration

The following tests now compile against the retained Android production
variant, with old Java SPAKE and Conscrypt dependencies only in
`androidHostTest`. Host tests execute in a JVM; that describes the test runtime,
not a supported desktop production library.

| Test | M5 location / scope |
| --- | --- |
| `PairingCompatibilityTest` | `androidHostTest`: real TLS, independent Java Bob/JCA peer, NUL/session binding, wrong-code/replay and M1 authenticated-malformed PeerInfo cases. |
| `IdentityCompatibilityTest` | `androidHostTest`: X.509 round trip, fingerprint and exact ADB RSA signature. |
| `KadbFileBinaryCompatibilityTest` | `androidHostTest`: old File descriptor resolution/default masks, symlink metadata and checked exceptions. Mode-read instrumentation covers Android's pre-26 File branch as selected by the host SDK stub. |
| `TlsFailureLifecycleTest` | Existing `jvmAndroidTest`, included by `androidHostTest`: consumed plaintext/partial TLS record failure is terminal and cannot emit another record. |
| Pairing/connection/writer lifecycle and queue/USB packet tests | Existing `jvmAndroidTest`, included by `androidHostTest`; keep their M1 tests and implementations unchanged during the target removal. |
| `TcpKeepAliveTest` for `AsynchronousSocketChannel` | Belongs to the removed desktop JVM NIO backend. Do not claim it tests Android's `ParcelFileDescriptor`/`Os` behavior. Native kernel keepalive and Android device behavior have separate coverage requirements. |
| Desktop USB hardware/smoke tests | Belong to the intentionally removed desktop JVM USB backend. Keep the history and record loss of this capability; do not call these Android USB tests. |

The production build's M5 integration must retain the common/shared test source
relationship, add `libs.spake2` and `libs.conscrypt.java` to Android Host tests,
and remove the old JavaExec classpath dependency on `jvmTestClasses`. Do not
copy the SPAKE reference into any production configuration. Keep host-test XML
and verify the migrated classes actually executed, including the M1 additions
when cherry-picking this rename onto M1.

## Initial validation status

The Java source was compiled locally with JDK 25, `-Xlint:all -Werror`, against
all seven checksum-verified reference artifacts: exit 0. The Python driver
passed bytecode compilation. The Gradle integration, Android Host test execution,
Native link, simulator launch, and actual dual-process pairing still need their
own executed evidence; this document does not turn source/Java compilation into
an interoperability pass.
