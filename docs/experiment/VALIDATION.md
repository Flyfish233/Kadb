# Native-core experiment: validation ledger

## Boundary and provenance

- Write repository: `Flyfish233/Kadb` only.
- Experiment branch: `experiment/kmp-native-core`.
- Frozen implementation baseline: `75678915fd4bdd52345edbb6bc4913ae3415a680`
  (`flyfishxu/Kadb`, `feat/ios-support`, checked before work).
- Fork `main`, unchanged: `3d1c13e8df261cc4a2bb57b03aa8c392cb8386c3`.
- SPAKE2 reference, read-only: `b837aba27bebc1050965fa124c2efa54b4e4544a`.
- No upstream PR, main merge, release, or package publication is authorized.

`validation/baseline/source-manifest.json` freezes the baseline source and
configuration byte hashes. Source existence alone does not prove execution.

This ledger preserves chronological entries, including their original pending
states and failed experiments. Later sections supersede earlier status claims;
results belong only to the named source snapshot and job. Counts from different
snapshots must not be added together as one integrated run.

## Evidence levels

Record source, compilation, linkage, executed tests, simulator execution,
real-device execution, protocol interoperability, and security/performance
claims separately. A skipped test or missing XML report is not a pass.
In particular the baseline's opt-in real-device test returns normally without
device environment variables. The summary script excludes such suites from
executed coverage and never infers iPhone-to-adbd evidence.

Each defect regression must have (1) the test commit, (2) a baseline execution
with an assertion failure demonstrating the defect, and (3) the fix commit and
passing execution. Dependency/configuration errors do not establish a red test.

## M0: baseline freeze — initial entry

The baseline's committed versions are retained: Kotlin 2.4.20, Gradle 9.6.0,
AGP 9.4.0, JDK 25, coroutines 1.11.0, Okio 3.18.2, Bouncy Castle 1.86.
Artifact availability was checked before building. The initial local Gradle
attempt did not use the environment HTTP proxy and failed during plugin
resolution; it did not execute product tests. This is an environment failure.

The Android SDK now names API 37 as `platforms;android-37.0`; the obsolete
`platforms;android-37` package request did not install a platform. The SDK package
name correction does not change the library's requested compile SDK.

The baseline workflow checks out the exact frozen commit into a separate
directory. It retains raw Gradle logs, XML reports, ABI inventories and built
artifacts even when a later step fails. Test results will be recorded here
after the jobs have actually completed.

First CI attempt: [run 40305077881](https://github.com/Flyfish233/Kadb/actions/runs/40305077881)
at `1b17e16efb91d0b9c79a900466c92797af7c5abc` failed in Android SDK setup:
the setup action's default requested the retired `tools` package. No product
tests ran; the report gate correctly failed on zero executed tests. The next
commit pins command-line tools build 16111833 and requests only platform-tools.

Second CI attempt: [run 40305359479](https://github.com/Flyfish233/Kadb/actions/runs/40305359479)
at `363de77e7c4de625876fdb360d3e61de104bce9f` executed **78 tests, zero
failures**: Kadb JVM 38, Android Host 28, mDNS JVM 12. The JVM bytecode inventory
contains 2,573 lines. The artifact SHA-256 is
`b0eb9fc36d497276ddff6ee398676e861145c67d496d4e887d8ec331139a84e5`;
the downloaded ZIP was verified before extracting the committed inventory and
summary. The corresponding local JVM/mDNS run executed 50 tests with zero
failures. Android Host tests exercise the host runtime, not an Android device.
Darwin and full Android ABI inventory are separate subsequent jobs.

## Initial findings at the frozen baseline

- Shared protocol logic already exists in this iOS baseline; relocation alone
  is not a goal.
- TLS partial writes and pairing cancellation require fail-closed lifecycle
  tests on the Java and Native providers.
- Authenticated PeerInfo still requires type and payload validation.
- The selected SPAKE2 source has no Maven publishing tasks or macOS targets.
  JitPack consumption must be tested independently from its build status.

## M1/M2/M3: first regression execution

The first added-test run on unchanged `75678915` product sources executed 22
cases and reported 13 failures. This count is **not** a healthy product-test
result. The actual assertion failures establish missing authenticated PeerInfo
validation, pre-agreement pairing encryption, context disposal, a writer/close
race, pending-connect cancellation, and UTF-8 corruption when a character spans
shell-v2 packets. The full original test source commits are retained in the
experiment history before production fixes.

Two harness problems were identified in that first run: the TLS write tests had
JUnit non-void method signatures and therefore did not execute; pairing
cancellation cleanup could mask the intended assertion with a handshake error.
Those results do not establish the corresponding regressions. Corrected tests
and a repeated pre-fix run are required before calling those defects reproduced.

## Coverage not yet established

No real iPhone/Android hardware, end-to-end adbd pairing, performance budget,
Android device/USB execution, Windows Native or independent security audit is
claimed by this initial ledger. Later entries must link specific commits and
job results rather than silently replacing this history.

## M0: ABI instrumentation correction

[Run 40306578218](https://github.com/Flyfish233/Kadb/actions/runs/40306578218)
again executed the 78 JVM/Android tests successfully, but the aggregate KGP
`updateKotlinAbi` task then failed on Linux: there was no existing iOS reference
from which to infer an unsupported target dump. This is an inventory setup
failure, not a failed product test. The next inventory reads the actual Android
AAR with JetBrains binary-compatibility-validator 0.18.2 and matching Kotlin
metadata 2.4.20. Its tools are checksum-pinned. It captures Kotlin-public ABI
and the broader javap inventory separately, without inferring an Apple result
on Linux. The standalone helper was first executed on the frozen JVM JAR and
produced 399 public-ABI lines. Apple frameworks remain a separate native gate.

## M1/M2/M3: confirmed pre-fix regression execution

After correcting the test harness at `e33d5d618642a4cf295290f81b2bdd018506b51b`,
unchanged baseline product sources executed **23 cases / 14 assertion failures /
zero skipped**. Both TLS tests now reached the unsafe-retry assertion; both
pairing-cancellation tests reached the worker-exit assertion. Four authenticated
PeerInfo payloads violated their expected constraints. The remaining failures
cover pending-connect cancellation, writer/close concurrency, three pairing
context lifecycle cases and split UTF-8 decoding. Raw evidence is preserved
separately from the earlier invalid harness attempts. These are defect
reproductions, not product-health passes; green evidence must follow the fixes.

## M0: Android artifact and Kotlin-public ABI snapshot executed

[Run 40308159247](https://github.com/Flyfish233/Kadb/actions/runs/40308159247)
at `10f64ba657c1043ec3455a329e311fff83d830a0` completed successfully:
all 78 baseline tests ran and both actual Android AARs were built. The
Kadb/mDNS Android Kotlin-public inventories and the broader Kadb bytecode
inventory are committed under `validation/baseline`. Artifact SHA-256:
`285efb0ef0c7a9bbc636b56ec8ff03c116b0e007cecf25338a60b105e5d3987a`.
Its explicitly skipped Darwin replay is not a Darwin pass.

## M1: first fixed implementation execution

The M1 implementation is `bf9695a88864355797dbf3f71bfb9c93d2a25b1a`.
Its local source-stage execution (recorded original source hash `904aaa0`) ran
**53 JVM and 38 Android Host tests, all passing with zero skipped**. Complete
XML, logs, manifest and the unchanged public `Kadb.Companion` Java declarations
are in `validation/m1/green`. This closes the M1-only red/green comparison; the
new shared SPAKE implementation, shell fix and platform integration still
require their own full current-tree runs.

The C regression was committed before its fix: `13d3d5affe7211cc99861a0e5d6e044a984f397c`
then `69aa47f60604a610066fcb26569900c05b713eb4`. POSIX target expansion is
`8e3fc41286ba531aa0a6d12118fe90c2c48dc3c0`. These checkpoints distinguish real
C TLS execution from pending Kotlin/Native compilation and external linkage.

## M0: actual iOS simulator baseline and framework linkage

The Darwin job `121517061889` in
[run 40306578218](https://github.com/Flyfish233/Kadb/actions/runs/40306578218)
**succeeded**, independently of the failed Linux ABI-instrumentation job in
that run. All 33 Gradle tasks executed, including Cinterop, device/simulator
framework links and simulator test binaries. The raw artifact SHA-256 is
`e4b4d84aaf4d2151eef95cb69c2cd213846b69aca92fda3d339c30362e2c56fb`.

An audit corrected the summary from 16 to **15 actually exercised cases**:
`JvmPairingInteropTest` silently returns when its peer environment is absent.
It must be excluded along with the explicit real-device opt-in suite. The raw
original summary is retained, with a corrected summary and the reason alongside
it. No JVM-peer pairing or physical device coverage is inferred from that run.

## First integrated CI configuration failure

[Run 40309464206](https://github.com/Flyfish233/Kadb/actions/runs/40309464206)
at `fc6e84c2051bede4dd37e77d54281149585e8cb8` failed during Gradle configuration:
the source-composition adapter used target-level `jvmToolchain(25)`, prohibited
by KGP 2.4.20. No current integrated product tests ran. The next change moves
that toolchain declaration to extension scope, and adds mandatory external
pairing consumers before attempting standalone JVM removal.

A local configuration-only check then caught a second adapter issue before a
CI rerun: the `InternalSpake2Api` opt-in was set only on `commonMain`, violating
KGP's dependent-source-set consistency rule. It now applies to every source
set. The original configuration-failure log is retained under
`validation/integration`; a `help` task is only a build-configuration check.

The next configuration check caught Gradle 9.6's locked configuration roles in
the Java-only reference harness. The harness now clears outgoing archives and
keeps its JAR task disabled instead of mutating the Java plugin's locked role.
It is a separate validation process, never a Kadb runtime dependency.

A separate configuration-cache execution check reached both checksum tasks but
failed to serialize their captured Gradle script objects. They now use explicit
task classes and typed file properties. The fix is validated with configuration
cache enabled; disabling the checks or silently changing the upstream hashes is
not a workaround. Raw pre-fix output is kept in `validation/integration`.

## Integrated Android execution and Native compiler blocker

[Run 40311473755](https://github.com/Flyfish233/Kadb/actions/runs/40311473755)
at `d298c5c763008258433695f1b268848b80c1bff1` produced actual reports for
**68 Android Host, 61 JVM and 12 mDNS JVM tests: 141 passed, zero skipped**.
The job nevertheless failed while storing the configuration cache. Its subsequent
CI ABI step did not run. The actual AARs were recovered from artifact
`12644328214`, SHA-256
`94889e2cf551641c75dff1969f5e7c188a0bf39fb784df99eee99fbf8bc9674d`;
a separate local comparison of those AARs against the frozen Android
Kotlin-public inventories found no differences.

Linux and Apple arm64 compilation then exposed a real M1 implementation error:
KGP 2.4.20 rejects an `actual typealias` to the compiler-sensitive `kotlin.Throws`
annotation. The unsupported alias is removed, rather than suppressing the
diagnostic. Original Kadb Java and Objective-C declarations remain unchanged.
An additive Apple-only `KadbApple` adapter declares `@Throws` directly for Swift
callers, including the suspending pairing boundary. Existing legacy Swift
entry points retain their original exception limitations; see
`docs/apple-exception-boundary.md`.

The Intel macOS job additionally encountered a native archive DNS/connect
failure. Downloads now retry transient I/O/HTTP failures at most three times;
hash mismatches and permanent HTTP failures still fail immediately. No TLS or
checksum validation is relaxed. These failed jobs establish no Native runtime,
simulator, external pairing or emulator result.

The checksum-task repair executed all four selected tasks with configuration
cache enabled and successfully stored its entry. Raw output is retained as
`validation/integration/05-checksum-tasks-configuration-cache-fixed.log`.
This focused build check does not replace the next full integrated run.

## Native replacement gate before the JVM exit attempt

[Run 40314095952](https://github.com/Flyfish233/Kadb/actions/runs/40314095952)
at `9a2ebbde700d36f7b0efcfc5002dea5c3e9634cf` establishes these distinct facts:

| Job / scope | Actual result |
| --- | --- |
| Android + temporary desktop reference | **92 Android Host + 81 JVM + 12 mDNS JVM** tests pass, zero skipped; actual AARs built; both Android Kotlin-public ABI diffs are empty |
| Linux Native | Full Gradle C downloads/build, Cinterop and native links execute; **47 Kotlin/Native tests pass**; external public-API consumer links |
| Independent Linux pairing | Two actual TLS 1.3/Legacy sessions complete: one successful code and one rejected wrong code; exporter and authenticated PeerInfo are exercised |
| Linux provider/reference checks | Real C transport harness and bridge sanitizers pass; pinned BoringSSL oracle reexecutes; Python observer tests run |
| macOS arm64 | **49 Kadb + 5 mDNS tests pass**; framework and public-API Native consumers link; independent positive/negative pairing completes |
| macOS x64 | Native build/tests/framework and independent pairing steps succeed; subsequent Swift link fails |
| External Swift | Source/API calls compile, but final link fails on unused cached Foundation/CoreFoundation wrappers absent from Xcode 16.4; no Swift runtime pass |
| Current iOS Simulator | Not executed after that Swift failure; the earlier frozen baseline simulator result is separate |
| Android Emulator adbd | Emulator starts, but the driver stops at `emulator -version` because the host lacks `libpulse.so.0`; **zero product checks** |

The overall run is **failed**, despite the successful Android and Linux jobs.
Recovered reports and artifact checksums are indexed in
`validation/integration/9a2-results.json`. These are actual Native replacement
capabilities sufficient to start the permitted JVM exit experiment, not a claim
of complete desktop feature parity or completion of the remaining gates.

## M5: actual standalone JVM target removal

Commit `0411b29e2cd27a6525068a368b2fb8b177157a5c` removes production JVM targets/providers from all three
modules, moves the retained Android backends without renaming facade-producing
files, and moves shared host regressions into Android Host tests. Desktop USB,
JmDNS and Windows JVM availability are explicitly lost; Android retains its File
overloads and platform support. The Java-only independent peer remains test
infrastructure without a Kadb runtime dependency.

An isolated preparation tree actually executes all three target-scope tasks
with configuration cache enabled. Each reports Android, the five Native targets
and common metadata, with no desktop JVM target. The raw log is
`validation/integration/m5/target-scope-configuration.log`; this is a configuration
gate only. The complete retained targets and Android ABI must pass again after
integration. Publishing/signing plugins are removed from this experiment.

For the next Darwin run, the runner changes to macOS 26 on both architectures and
explicit Xcode **26.4.1**, within the SDK family named by K/N 2.4.20 and its
[official compatibility table](https://kotlinlang.org/docs/multiplatform/multiplatform-compatibility-guide.html).
The external Swift link enables standard dead-code stripping, also listed in
the pinned compiler's `konan.properties`, and records its actual imports/link map.
There are no fabricated symbols or undefined-symbol exemptions. Framework
deployment stamps are checked separately from runtime OS claims. Independent
iOS steps can still execute if a Swift consumer check fails. The emulator host
installs and records the missing system runtime libraries before retrying.

## M5/M6: post-removal execution and Android migration repair

[Run 40318831760](https://github.com/Flyfish233/Kadb/actions/runs/40318831760)
at `696a85f22f25407f92754361b18ae6fd0c2cdba7` is **failed overall**. It is
the first full retained-target run after production JVM removal. The executed
Native results are distinct from its Android compiler failure:

| Job / scope | Actually observed |
| --- | --- |
| Source package | 10 collector integrity tests pass; actual pinned sources collected, verified and uploaded as artifact `12647837176`; per-binary jobs record its real URL and hashes |
| Linux Native | **63 Kadb + 5 mDNS tests pass**, zero failed/skipped; complete C task chain, Cinterop, external Native links, two independent TLS/Legacy sessions, C transport/bridge sanitizers, 18 BoringSSL oracle comparisons and five observer tests pass |
| macOS x86_64 | **65 Kadb + 5 mDNS tests pass**, zero failed/skipped; external Native pairing, framework linking, external Swift compile/link/run and deployment-metadata inspection pass |
| macOS arm64 | **65 Kadb + 5 mDNS tests pass**; independent pairing, framework, Swift compile/link/run and deployment metadata pass |
| iOS Simulator arm64 | **65 Kadb + 5 mDNS tests actually execute and pass** on the iOS **26.5** iPhone Air Simulator; mandatory external pairing executes both successful-code and wrong-code sessions |
| iOS device build | `iosArm64` framework compiles and links; this is not physical-iPhone execution |
| Exported Apple API | All **921** parsed baseline declarations retained; **0** removed/changed, **22** additions for the Apple adapter and companion |
| Android | Five mDNS Host tests execute successfully; Kadb production compilation fails before its Host tests, APK or ABI gate |
| Emulator adbd | Skipped because Android prerequisite failed; **zero** product checks in this run |

The ARM Darwin job has one explicitly ignored old optional
`JvmPairingInteropTest`; it contributes **zero** to the 140 executed cases.
Its replacement mandatory external Simulator driver passed both actual TLS
sessions. No skipped optional case is represented as a pass.

Both macOS Swift consumers recorded a received CNXN frame followed by an
NSError/Kotlin IOException and a joined peer worker. SDKs were 26.4 under
Xcode 26.4.1; the observed Simulator runtime was separately 26.5. Actual framework
records identify macOS 12 / iOS 15 deployment minima, without establishing
execution on those oldest systems. The historical `simulator.json` recorded its
pre-boot `Shutdown` state; boot logs, executed reports and the spawned consumer
establish the runtime result. The next harness refreshes that metadata after boot.

The Android failure is a migration bug: two former intermediate JVM/Android
`expect` declarations moved into `androidMain` alongside their `actual`
implementations. Repair `b17f418dd12c9a7dcc25021860266ebe24dc8039` removes
only those obsolete dispatch declarations/modifiers, preserving the public
`readMode(File)` signature and generated-facade filename. It requires a new
Android compile, Host test and ABI result. The original failure log is preserved
under `validation/integration/m5/android-source-set-failure`.

Artifact IDs/digests, source-package identity, per-job limits and the corrected
executed counts are in [`696-results.json`](../../validation/integration/696-results.json).
Downloaded Linux and both Darwin reports are retained under
`validation/integration/696-reports` without altering their contents.

The integrated lineage is explicit: Native secure persistence `0b79d56`, actual
JVM removal `0411b29`, remote-ID/diagnostic fixes `e14be4e`, and common storage
cleanup `696a85f`. Earlier local evidence still belongs to its original source
snapshots: `02bdb55` routing overlay 22/22, `04a63fd` Native 21/21 and `6e2f381`
Native 24/24 plus Android Host 36/36. This full CI run does not relabel those
isolated source snapshots as the current checkout.

## Android migration repair: actual local consumer and API evidence

Commit `f109e804ec0dfbf114f597ec1dacfe7ab0d1d163` integrates the Android
consumer and its actual isolated-build evidence. The production source tree is
identical to `b17f418dd12c9a7dcc25021860266ebe24dc8039`. All **102 Kadb + 5
mDNS Android Host tests execute and pass**, with zero skipped tests, and both
actual AAR Kotlin-public API inventories exactly match the frozen baseline.
The 5,582,037-byte debug APK passes D8, signature verification and a real DEX
class-definition inventory. It includes the shared Legacy implementation and
excludes the test-only Java SPAKE/Conscrypt peer.

The record preserves the initial BC notice-packaging collision and incorrect
Gradle artifact-view attempt before the successful build. The APK's actual
runtime inventory contains 21 external archives and two project artifacts.
These are build/Host/API results, **not ART, Android TLS exporter or real-adbd
execution**. See [the original logs and exact source/artifact identities](../../validation/android-runtime/evidence/README.md).

## Android runtime CI entry: source acquisition failure

[Run 40324927894](https://github.com/Flyfish233/Kadb/actions/runs/40324927894)
at `da03de02848bc4509c7d88cabc56fe2764d3e654` fails before any product build.
The source job `121579069748` executes all **23 integrity tests successfully**,
then rejects the DocumentFile fixed-commit subtree download because its response
exceeds the locked 9,975-byte length. The source package is not uploaded; all
Android, Linux, Darwin and emulator jobs are correctly skipped. **Zero product
tests execute in this run**. This is a source-acquisition failure, not an ART
or Native result.

The diagnostic artifact is `12649694165`, SHA-256
`29975085ac4d79eddef0296604881440ab09678bd7b9f3f49eb0598e229cea58`.
The full job log and explicit failed scope are retained in
`validation/integration/da03-source-failure`. The next repair must establish a
reproducible source acquisition without weakening the integrity check.

## Stable source content and integrated platform evidence at `35e002e`

`35e002e721d8610dfd08d374fd41cbf666f16c35` fixes the source acquisition
by pinning the exact 19-file AndroidX DocumentFile Git subtree, including blob
identities, lengths and SHA-256 values. Two successful Gitiles responses for the
same commit contain identical files but different request-time tar/PAX metadata.
The reproducible USTAR is 71,680 bytes with SHA-256
`3b60454ef61425219931a5b664d3e6b7c75bf680350da1025afd1f88ba8f23c4`.
The original responses and the separate local `4c5febe` source-package proof
are retained in `validation/source-bundle/context-fix-evidence`; that local
package is not relabeled as the integrated CI package.

[Run 40326629845](https://github.com/Flyfish233/Kadb/actions/runs/40326629845)
has five completed successful jobs. The downloaded ZIP hashes were independently
checked; selected unmodified reports are in
[`validation/integration/35e-reports`](../../validation/integration/35e-reports).

| Completed job | Actual evidence |
| --- | --- |
| Source package | 27 integrity tests; actual 183,189,268-byte package, SHA-256 `93f1881bcd2f9c2ee7be834651af4bf8367d2559f8a3e5647a583fe412aa4d6e`; downloaded and independently verified all 240 members |
| Android | 102 Kadb + 5 mDNS Host tests, zero failures/skips; real AAR/APK build and signature/DEX/source-inventory checks; both Kotlin-public API differences empty |
| Linux | 63 Kadb + 5 mDNS tests, zero failures/skips; actual linked consumers, two independent TLS/Legacy peer sessions, C regressions/sanitizers and 18 oracle comparisons |
| Intel macOS | 65 Kadb + 5 mDNS tests, zero failures/skips; actual Native pairing, Swift compile/link/run and framework metadata |
| ARM macOS + iOS Simulator | 70 macOS + 70 Simulator tests actually execute; the old optional Simulator peer case is ignored and excluded; mandatory external peer sessions pass on each runtime; Swift executes; device and Simulator frameworks link |
| Apple API | 921 baseline declarations retained, zero removed/changed and 22 additions; refreshed iPhone Air / iOS 26.5 metadata records `Booted` |

The broader Android bytecode inventory has 36 affected class blocks, including
five groups of binary changes to Kotlin-internal declarations compiled as
JVM-public. Java/reflection callers relying on those internals can break. The
complete classification and intended public API boundary are in
[ANDROID_ABI_REVIEW.md](ANDROID_ABI_REVIEW.md).

The emulator job's Native and ART drivers both return failure and their console
summaries report zero completed checks. Those summaries alone do not establish
whether a consumer started. The subsequent unbounded `adb logcat` command blocks
cleanup and upload. After the other five jobs completed, ordinary cancellation
was requested through GitHub; the request acknowledgement is retained. At this
checkpoint the raw emulator reports are still unavailable, and no adbd or ART
success is claimed. The next harness bounds diagnostics and cleanup, allows
ordinary cancellation of test steps, and prints existing failure fields in both
driver summaries. It leaves protocol/provider behavior and pass gates unchanged.
