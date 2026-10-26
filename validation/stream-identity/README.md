# ADB stream identity routing regression

## Reproduced production defect

The unchanged Android `classes.jar` was extracted from the actual AAR produced
by [CI run 40314095952](https://github.com/Flyfish233/Kadb/actions/runs/40314095952)
at `9a2ebbde700d36f7b0efcfc5002dea5c3e9634cf`. Its SHA-256 is
`4582c6be968a4531afa2c72cb58c45b88196096bb3b9e9213007a9edf31f9089`.
The Kotlin 2.4.20 CLI compiled only the new test, with the AAR on the classpath
and as a friend module. No production class was replaced in the red run.
This is an Android-bytecode host test, not an Android device or Native run.

Test source `211f867` executed **5 tests / 5 target assertion failures**, JUnit
exit **1**, after successful test compilation. The failures demonstrate:

- `OKAY(0, local)` can complete an OPEN with an invalid remote ID.
- WRTE from another remote ID is delivered to the established stream.
- OKAY from another remote ID supplies that stream's acknowledgement.
- CLSE from another remote ID closes that stream.
- WRTE before the first OKAY enters the pending stream's receive queue.

The fixture sends actual ADB frames through the shared reader and queue.
The CLSE test waits for a second OPEN/OKAY dispatch barrier and starts a reader
before supplying data; otherwise the old queue's intentional tail-data drain
can hide the closed state. The initial run at `9a83cf1` reproduced the other
four defects but did not establish the CLSE case. Its raw logs remain under
`red/harness-history`. The first CLI attempt selected JVM target 17 while the
AAR contains target-25 inline bytecode: compilation failed and no tests ran.
That harness error is retained separately and is not defect evidence.

These are routing/protocol validation defects within a connection, not proof of
an authentication bypass: a hostile authenticated adbd already controls its own
service data. The fix must bind the first nonzero remote ID, preserve late-OKAY
reclamation and normal queue draining, and retain AOSP's historical CLSE with
remote ID zero from this same transport. No checksum or receive-window policy
change is included in this correction.

## Reproduction entry point

The same test is in `commonTest` and therefore participates in Android Host,
Linux Native, macOS Native and iOS Simulator suites. Full-module CI must execute
those target suites before the focused CLI overlay can be called platform
validation. `red/manifest.json` records the exact byte hashes, tool commands,
classpath and exit codes for the captured pre-fix comparison.
