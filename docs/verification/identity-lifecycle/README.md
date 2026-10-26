# Identity diagnostics and storage failure evidence

## Secret-free diagnostic output

The focused regression at `077b3f34aa9b14a4869ac48fe17f952e992bf28c` compiled, linked and ran
two Linux Native tests. Both fail because generated data-class `toString()` output
includes the private-key field. `diagnostics-red` contains the complete Gradle
log, test XML and executable hash. This is **2 executed, 2 failed, 0 skipped**,
not a successful product test. Failure messages are constant and never render
the identity; only synthetic secret material is used in the aggregate under test.

The local runs reuse independently compiled, pinned Clang/BoringSSL C archives
and explicitly exclude `buildNativeLinuxX64`. Cinterop/Kotlin compilation,
executable linking and Native test execution remain real; complete C task-chain
validation and other platforms are recorded in integration CI. Local source
snapshots contain the original M1 and Native changes but not the later combined
SPAKE2/JVM-exit/M6 branch.
