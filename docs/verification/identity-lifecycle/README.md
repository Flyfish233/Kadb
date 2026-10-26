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

## Storage failure fixtures

The first fixture compile at source `d0c7e47` failed because Okio's JVM
`ForwardingSink` is not exposed in the resolved Native/common API. No storage
test executed in that attempt, so its preserved log is only fixture-compilation
failure evidence. The corrected fixture uses standard Kotlin `Sink` interface
delegation while retaining real underlying filesystem writes.

The corrected fixture at `9741ab13c7850443452e6c3fb02b0f7929f999ff` actually
compiles, links and runs **3 tests, all 3 failing, 0 skipped**. `storage-red`
retains the log, XML and executable hash. A partial OS write leaves a staging
file, a failed cleanup lookup replaces the atomic-move exception, and a failed
write never attempts staging deletion. Tests inject failures through a supplied
`ForwardingFileSystem`, so they exercise the common fallback even on Native;
the default Native SYSTEM secure writer is intentionally not used in these cases.
