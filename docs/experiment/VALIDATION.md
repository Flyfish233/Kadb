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

## M0: baseline freeze (in progress)

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

## Initial findings, not yet fixed/verified

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

The next implementation removes production JVM targets/providers from all three
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
