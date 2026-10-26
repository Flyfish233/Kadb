# Lifecycle regression evidence

The production baseline is exactly `75678915fd4bdd52345edbb6bc4913ae3415a680`.
The confirmed negative run executed **23 tests, with 14 failures and no skipped tests**.
This is evidence of baseline defects, **not a healthy product result**: Gradle exited 1.

`red-confirmed/results.json` identifies the original local test commits and every executed test.
M1 tests used source snapshot `648222c79f56571603e7568e9bfd5d423d8adb05`. The test-only
files from M2 `f53ee4b0a9c29d1b9082a5ba08aa142a23801d06` and M3
`32159c40cc155cac68877682de6960d935c51743` were copied into the baseline checkout; no
production fixes were copied. The added connector-timeout compatibility test in
`c7ca9e94c3679661cfa89ea07154d3fd49901167` was written after this confirmed negative run.
Integration commits may have different SHAs after cherry-picking; these IDs record the
original test-source snapshot, not a claim that each is a separate published CI run.

Command (Gradle 9.6.0, Kotlin 2.4.20, JDK 25.0.3, Linux x64):

```sh
./gradlew :kadb:jvmTest \
  --tests '*PairingCompatibilityTest' \
  --tests '*PairingCancellationTest' \
  --tests '*TlsFailureLifecycleTest' \
  --tests '*AdbWriterLifecycleTest' \
  --tests '*KadbConnectionAttemptCancellationTest' \
  --tests '*PairingAuthLifecycleTest' \
  --tests '*AdbWireGoldenTest' \
  --tests '*AdbShellEncodingTest' --console=plain
```

## Expected failing properties

- Two actual JDK TLS record tests: the plaintext was consumed by `SSLEngine.wrap`, but a
  failure after 0 or 5 transmitted ciphertext bytes left the transport reusable.
- Two blocked TLS handshake tests: cancelling `Kadb.pair` or closing its context did not
  stop the socket operation and finish the worker.
- Four independently encrypted PeerInfo responses were incorrectly accepted: server type
  0, unknown type 255, empty GUID, and a GUID without a terminating zero byte.
- Closing a pending ADB connection before its connector returned did not cancel the connector.
- Closing `AdbWriter` overlapped an in-flight write to the same Okio buffer.
- Three M2 authentication lifecycle tests and the M3 split-UTF-8 shell test also failed.

The wrong-code pairing case, wrong PeerInfo length, independent positive pairing/cipher
cases, and framing golden cases remained controls in the same run.

## Harness corrections retained

`harness-history/initial-junit-error.log` records a first run with a non-Unit expression-body
JUnit test method: those TLS cases did **not** execute and are not counted as TLS defect
proof. That run also exposed cleanup EOF masking the intended cancellation assertion.
Test commits `6e086955` and `648222c7` fix the return type and preserve explicit lifecycle
assertions. `stale-test-copy.log` records a subsequent compiler error from a stale untracked
copy after relocating the cancellation test into `jvmAndroidTest`; the byte-identical old
copy was removed before the confirmed run. No failed experiment was overwritten in Git.

Green validation is recorded separately after execution. Simulator, native linking, device
pairing, and production adbd interoperability are not established by this JVM negative run.

## M1 positive run

Production tree committed as `904aaa0d92c2f0e52f76a4e1cc13135d82798f59`:

| Task | Tests executed | Failures/errors | Skipped |
| --- | ---: | ---: | ---: |
| `:kadb:jvmTest` | 53 | 0 | 0 |
| `:kadb:testAndroidHostTest` | 38 | 0 | 0 |

Command: `./gradlew :kadb:jvmTest :kadb:testAndroidHostTest --console=plain`.
Gradle exited 0; the test tasks actually ran. `green/` contains their original XML reports,
raw Gradle output, and a separate machine-readable result summary. The full existing M1
checkout suite ran, not only filtered new regressions. This includes the previously fixed
concurrent-first-connect, close-during-handshake, no-OPEN-replay, reset/reconnect, stream,
USB fake-transport, identity, and File API compatibility tests.

The M2 auth-state and M3 split-UTF-8 production fixes/new tests were not yet integrated into
this M1 checkout; their aggregate positive result belongs to the integration ledger. The
M1 run must not be presented as proof that all M2/M3 defects were already fixed.

`green/companion-api-before.txt` and `green/companion-api-after.txt` compare public Java
bytecode declarations for `Kadb.Companion` against the exact baseline build. They are
identical, including the suspend `pair` method's lack of new checked exceptions. This is a
focused check for the Native-only annotation; it does not replace the repository-wide
API/ABI comparison.
