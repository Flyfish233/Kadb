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

## Initial findings, not yet fixed/verified

- Shared protocol logic already exists in this iOS baseline; relocation alone
  is not a goal.
- TLS partial writes and pairing cancellation require fail-closed lifecycle
  tests on the Java and Native providers.
- Authenticated PeerInfo still requires type and payload validation.
- The selected SPAKE2 source has no Maven publishing tasks or macOS targets.
  JitPack consumption must be tested independently from its build status.

## Coverage not yet established

No real iPhone/Android hardware, end-to-end adbd pairing, performance budget,
Android device/USB execution, Windows Native or independent security audit is
claimed by this initial ledger. Later entries must link specific commits and
job results rather than silently replacing this history.
