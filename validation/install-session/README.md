# Install session write failure regression

`Kadb.installMultiple` creates a PackageInstaller session before reading each APK
for the write phase. At baseline `75678915fd4bdd52345edbb6bc4913ae3415a680`, an
exception in `streamInstallWrite` or `pushAndWrite` bypasses `finalizeSession`.
The already-created session receives neither commit nor abandon.

## Exact baseline reproduction

The four public API tests in `InstallSessionWireLifecycleTest` use a real loopback
ADB peer. The peer removes the local APK after receiving `install-create` and
before returning the session ID. This forces a deterministic filesystem exception
in the next phase. All four baseline runs observe the create command and then
transport EOF without an `install-abandon` command. The modes are `exec:cmd`,
`abb_exec:`, legacy `shell:pm`, and an injected abandon-failure scenario.

The test source alone was compiled with Kotlin 2.4.20 against the frozen baseline
JVM jar; the baseline production classes were not rebuilt or patched. Its SHA-256
is `70de6f6feec77f0453dcf3a87031aacc7fceb56270345ccb61221a02c22d23c5`.
`red/manifest.json` records exact commands, dependency paths, test source digest,
commit and exits. **JUnit executed 4 tests and failed all 4 expected wire
assertions, exiting 1. This confirms the defect; it is not a product-health pass.**

The initial run in `red/harness-history` had three valid defect assertions and one
inconclusive accept timeout because RSA identity generation occurred inside the
network time budget. The corrected test prepares identity before starting the
listener timeout. The initial timeout is not counted as defect evidence.

## Fix boundary and preservation

`runInstallWrites` owns only the APK write phase of an already-created session.
If that phase throws, it attempts `install-abandon` once and rethrows the identical
original exception. A cleanup failure is added as a suppressed exception unless
it is the original throwable itself. This includes cancellation exceptions.

Normal writes and the existing commit/error-string finalizer keep their previous
wire sequence. The fix does not retry a commit after an uncertain reply. It cannot
abandon a session whose creation reply never delivered an ID, or guarantee cleanup
when the device or transport is unreachable. Common tests cover successful writes,
original exception identity, cleanup suppression, self-suppression and cancellation.

## Focused repair verification

At fixed commit `1c79a3c`, Kotlin 2.4.20 compiled the changed `Kadb.kt` and
`InstallSession.kt`, unchanged common/JVM File compatibility sources, and the two
test classes as an overlay on the exact baseline jar. The CLI preserves the
`commonMain -> jvmAndroidMain -> jvmMain` fragment relationships and uses JVM
bytecode target 25 to match the frozen jar. No production source was transformed
for this run. The overlay appears first in the runtime classpath.

**JUnit executed all 9 tests, with 0 failures, exit 0 (12.879 seconds).** The same
four public API wire cases now observe the required abandon command. Five common
lifecycle cases verify the normal return path, exact original exception, suppressed
cleanup failure, self-suppression protection and cancellation cleanup.
`green-cli/manifest.json` records all source and output class hashes and exact
commands. Initial compiler-configuration errors are retained in its
`harness-history`; they are not runtime product failures.

This focused run proves the changed installation path over the old JVM runtime.
It is not a complete Gradle module build, Android device run or Native test. No
performance acceptance threshold was inferred from the recorded elapsed time.

## Remaining integrated validation

The exact-baseline red result above is complete. Full-module Android host and
Native validation of the fixed implementation must run on the integrated branch;
this document does not substitute test-source compilation for those target runs.
The normal Gradle suites pick up `InstallSessionLifecycleTest` from `commonTest`
and `InstallSessionWireLifecycleTest` from `androidHostTest`.
