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

The fix explicitly formats only the object type, public fingerprint and
certificate expiry. It preserves data-class constructors, properties, generated
`componentN`/`copy`, equality and hashing. `toString()` remains the same method
signature, but its diagnostic text deliberately stops exposing private-key and
certificate bytes. No crypto provider or caller-supplied key-pair diagnostic is
invoked while formatting an identity.

At source `04a63fd10e44ea64c422f7c5e7f607a7caa3c4de`, the full local Linux
Native suite executes **21 tests, 0 failures, 0 skipped**, including both
diagnostic regressions. `diagnostics-green` preserves the Gradle log, all XML and
executable hash. Android ABI comparison and integrated-platform runs remain
separate evidence; this result does not substitute for them.
