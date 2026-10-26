# Forwarder lifecycle validation

## Red: unchanged upstream production

The JVM product jar from the confirmed M1 red build contains production sources at
`75678915fd4bdd52345edbb6bc4913ae3415a680`; `red/source-audit.txt` records the test-only
changes in that worktree. The new public-API loopback tests were committed as
`d1e3756` and compiled independently against that jar with Kotlin 2.4.20, then run
with JUnit 4.13.2 on JDK 25.0.3. This small CLI run avoided starting a second Gradle
build while the Linux Native toolchain was being initialized.

**Compiler exit 0; JUnit exit 1; four tests executed, four intended assertion failures.**
The failures separately establish that closing a forwarder waits for its pending
OPEN, waits for the shared initial CNXN handshake, leaves idle forwarding workers
blocked, and fails to reclaim a service when its OKAY arrives after forwarder close.
The tests close the whole Kadb only in fixture teardown to release the defective
baseline's workers. The behavior assertions require the shared transport to survive.

`red/manifest.json` records exact commands, classpaths and product-jar SHA-256.
`red/compile.log` and `red/junit.log` are unmodified process output.
`red/sandbox-denied.log` is an earlier environment-only failure: socket creation was
forbidden in the restricted sandbox. It is **not** defect-reproduction evidence.

The same source can run through the normal build with:

```sh
./gradlew :kadb:jvmTest :kadb:testAndroidHostTest --tests '*TcpForwarderLifecycleTest'
```

The initial CLI evidence is JVM-only. It establishes neither Android execution nor
Native execution; those need separate test results after the fix.

## First candidate validation: one fixture did not reach its subject

Production commit `28b319f` compiled for JVM and Android. All four new TCP
forwarder integration regressions and all four common protocol regressions passed
on both test targets, as did the public caller-interruption compatibility test.
The complete Android host suite executed **47 tests, zero failures/skips**.
The complete JVM suite executed **62 tests, one failure, zero skips**.

The failing assertion was the existing connector-cancellation fixture's
`entered.await(5 seconds)`, before its connector had been entered. The fixture
also generated a fresh RSA identity in that timed interval. This is recorded as
a fixture startup timing failure, not a successful product test or evidence of a
connection-close failure. The original log and XML are preserved in
`initial-candidate`. Identity preparation is moved before the worker/deadline;
the lifecycle deadline is not enlarged. The test is repeated and the complete
suite is rerun after this correction.

`harness-history/flattened-kmp-cli-compile.log` records an earlier unsuccessful
attempt to compile the entire multilevel KMP source hierarchy using a flat CLI
invocation. Its expect/actual compilation errors are harness errors. The normal
Gradle JVM and Android compilation above succeeded.

## Confirmed green: clean committed worktree

The final follow-up regression tree is `7682c0e` (production `28b319f`). It was
checked out into `/tmp/kadb-forwarder-verify-7682c0e` and built in the same execution
environment with `--no-build-cache -Pkotlin.incremental=false`. All 14 Gradle
actions executed; neither test task was skipped or restored from cache.

| Test target | Executed | Failures/errors/skips |
| --- | ---: | ---: |
| JVM | 63 | 0 / 0 / 0 |
| Android host | 48 | 0 / 0 / 0 |

Both targets executed the four TCP forwarding lifecycle tests and the five common
OPEN cancellation tests, including continued I/O on an already established
unrelated stream. The connector lifecycle class was then independently repeated
against the freshly compiled JVM classes using JUnit: **three tests, zero failures**.
Exact commands, classpaths, product SHA-256, raw process output and JUnit XML are
in `green/`.

A previous incremental build in the scratch worktree reported redeclarations of
unchanged common tests even though only one copy of each source was visible.
Deleted/renamed old iOS source files also reappeared there as untracked remnants.
The raw failed build is retained as `harness-history/scratch-incremental-redeclaration.log`.
No test task executed in that failed build; its old XML was not counted as new
results. The isolated clean checkout closed this validation gap without changing
the product implementation or broadening any timeout.

A separate agent reviewed the pending-OPEN cancellation/OKAY handoff, per-waiter
connection cancellation, generation ownership and old-job cleanup. It found no
additional correctness problem in those paths and confirmed the documented
unbounded shared-writer limitation. This review is not a substitute for the tests.

This green record is **JVM and Android host only**, before the later Apple facade
and NativeThrows removal commits. Kotlin/Native execution, Apple framework link,
Swift consumer behavior, simulator runs and real-device interoperability remain
separate integration evidence. The clean test tree still contains the earlier
NativeThrows alias experiment, subsequently rejected by Kotlin/Native and removed
without suppressing the diagnostic.
