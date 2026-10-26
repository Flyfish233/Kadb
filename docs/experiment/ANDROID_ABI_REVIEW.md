# Android raw bytecode difference classification

Reviewed the actual Android AAR inventory for CI run `40326629845`, job
`121585342777`, commit `35e002e721d8610dfd08d374fd41cbf666f16c35`, against the
frozen `75678915fd4bdd52345edbb6bc4913ae3415a680` Android inventory. The raw
`android-bytecode.diff` is 29,429 bytes. This is not an assertion of identical
JVM bytecode or compatibility for Java callers of Kotlin-internal classes.

The metadata-aware public Kotlin API inventories for Kadb and mDNS are each
byte-identical to their frozen baselines. The independent raw `javap` inventory
has 36 affected class blocks: 21 added, 4 removed, 9 with member changes, and 2
with ordering changes only. Method descriptors were compared as sets within
each class so declaration reordering was not counted as signature removal.

## Removed or replaced signatures

| Raw bytecode difference | Declaration at both frozen source revisions | Classification |
| --- | --- | --- |
| `core.AdbConnection.open(String)` becomes `open(String, Job)` plus the default bridge | `internal class AdbConnection` in `commonMain/.../core/AdbConnection.kt` | An actual binary change in an internal class. Public `Kadb.open(String)` remains unchanged. |
| `pair.PairingCrypto(byte[], byte[])` becomes the constructor accepting `EntropySource` plus its default bridge | Baseline `internal expect class PairingCrypto` in `PairingAuthCtx.kt`; current `internal class PairingCrypto` in `PairingCrypto.kt` | An actual binary change in an internal class used to replace the mathematical backend. |
| `queue.AdbMessageQueue(AdbReader, Function0)` gains a callback argument and a default bridge | `internal class AdbMessageQueue` | An actual binary change in an internal class. New OPEN/remote-ID ownership helpers are internal through the containing class. |
| `transport.PlainBlockingChannel.Companion.connect` and `connect$default` gain a continuation | `internal class PlainBlockingChannel`, with its companion | An actual binary change in an internal implementation. The public synchronous/async Kadb surface remains unchanged. |
| `stream.SyncPlatformKt.isWindowsHost()` and its file facade disappear | Baseline `internal expect fun isWindowsHost()` and `internal actual fun isWindowsHost()` | Internal helper removed as part of the desktop JVM target exit. |
| `TcpForwarder.State` and `PairingConnectionCtx.State` disappear | Both were `private enum class State` | Private implementation classes. Their raw class headers are package-private. |
| `PairingConnectionCtx.WhenMappings` disappears | Generated switch table for the removed private enum | The frozen Android AAR has `ACC_SYNTHETIC` on both the class and its mapping field, confirmed with `javap -v`. |

## Additions and ordering changes

The added `runInstallWrites`, `writeSystemPrivateKeyAtomically`,
`startKadbThread`, `runClosingOnCancellation`, and `securePairingRandomBytes`
functions are explicitly `internal` in the exact source commit. So are the
new `ForwardingSession`, `PairingNonceSequence`, and `PairingPrimitives`
classes. `Kadb.openCancellable` is an added internal, module-mangled method.

`Kadb.ConnectionAttempt`, `TcpForwarder.Listener`, and `PairingAuthCtx.State`
are private nested classes. `PairingConnectionCtx.startCancellable` belongs to
an internal class; `PeerInfo.isValidDeviceGuid` belongs to a private nested
class. The remaining added classes are compiler-generated coroutine,
function-reference, or SAM helper implementations. New `Kadb` connecting-job
accessors and `TlsNioChannel` handshake/read-record accessors were independently
confirmed as `ACC_SYNTHETIC` in the actual AAR.

`KadbIdentitySnapshot.toString()` and `ResolvedIdentity.toString()` moved in
the `javap` listing after explicit diagnostic-redaction overrides were added;
each class retains exactly the same descriptor set. Their behavior change is
intentional and is covered by the identity diagnostic-redaction tests.

## Result and scope

No removed or changed declaration in this diff was found to be an explicitly
public Kotlin API declaration or a separately authored public Java declaration.
The retained public surface is also covered by the metadata-aware ABI comparison,
the File-overload binary compatibility tests, and the Android APK compilation.

Kotlin `internal` classes are still JVM-public bytecode and can be used directly
by Java or reflection. Such consumers can encounter `NoSuchMethodError` or
missing internal classes for the five signature groups above. The evidence
therefore supports unchanged declared Kotlin public API and retained tested Java
entry points, not compatibility for every JVM-public implementation member.
ART runtime evidence is a separate emulator gate.

Source checks used `git grep`/`git show` at the two exact revisions. Metadata
visibility evidence is the pinned binary-compatibility-validator output in the
artifact; synthetic flags were read from the actual frozen/current Android AARs.
The [machine-readable descriptor differences](../../validation/integration/35e-reports/android-35e002e-bytecode-classification-input.json)
and [original bytecode diff](../../validation/integration/35e-reports/android-35e002e/evidence/android-bytecode.diff)
are preserved with the run evidence. No product build or source
mutation was performed during this review.
