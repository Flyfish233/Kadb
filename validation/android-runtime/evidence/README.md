# Local Android consumer evidence — 2026-10-26

The production tree was `b17f418dd12c9a7dcc25021860266ebe24dc8039`, including
the Android source-set migration fix. The local cherry-pick was
`41cc7ab760baf9ea12407415050e97959d2aebd1`; both have tree
`e36acd1fcca8d07a8d00b2616a44835dbfe42abc`. The consumer's exact source is
`2ab85febb3bf98338257d1d5aca0d9e49e552b19`. Its input files are hashed in
`source-input-manifest.json`. No production source changed in the consumer commit.

## What actually passed

- Android Host Test XML records **107 executed, 0 failed, 0 skipped**: Kadb 102,
  mDNS 5. Both required test groups were present. Raw XML is under `junit/`.
- The actual `kadb.aar` and `kadb-mdns.aar` were built. The pinned Kotlin ABI
  capture tool produced public API inventories that are both byte-for-byte
  equal to their frozen Android baselines; both strict diff exits
  were zero. The captured APIs and empty diff files are retained.
- `:validation-android-runtime:assembleDebug` produced a real APK after D8 and
  packaging. The final successful build executed 47 tasks with another 37
  up-to-date tasks; it did not rely on a skipped APK/D8 task as fresh evidence.
  Earlier D8 work in the first build is preserved in that build's raw log.
- The APK contains **6 DEX files and 11,751 class definitions**, including the
  Instrumentation, Kadb, KadbCert and shared Legacy SPAKE25519 classes. No host
  Conscrypt provider or historical Java SPAKE oracle is packaged. The inspector
  reads DEX class-definition tables, not class-name strings.
- Actual AAPT output confirms the expected self-instrumentation component,
  package, debuggable flag and sole `INTERNET` permission. APK signature
  verification succeeds for v1 and v2. The complete verifier output, including
  its META-INF warnings, is retained; this is a disposable debug APK.
- The actual APK runtime configuration contains **21 external artifacts and
  2 project class JARs**. The inventory retains coordinates, selected variants,
  attributes, original archive paths, sizes and hashes. It is distinct from
  Host Test and independent Java peer dependencies.
- Seven host tests of the negative report/DEX gates passed. The extracted
  reference-classpath helper verified all seven pinned peer dependency hashes
  and hashed its two compiled classes. These are infrastructure checks.

APK SHA-256:
`4538e33e848955a99b1bb012beab0da37d961574eeb5c6d86517272dee57dc5a`
(5,582,037 bytes). The exact APK remains a build artifact, not a Git blob or a
published package. Fresh signing keys make independently built APK bytes differ.

## Failures retained and corrected

1. The first real APK build failed on the three Bouncy Castle JARs' duplicate
   `META-INF/LICENSE.md` resource. The app packaging rule now merges all three
   notices, rather than dropping them. `apk-bc-notices.json` verifies all three
   original 1,171-byte notices are retained in the 3,513-byte APK resource.
   Conflicting Java 9 OSGi bundle manifests are excluded only from the APK;
   original dependency/source archives retain them. The 107 Host Tests had
   already executed in this failed build and are reported independently.
2. The second invocation failed in the new provenance exporter because an
   unqualified artifact view cannot choose among AGP's several project
   artifact types. External original archives and the explicit Android project
   class-JAR view are now selected separately. The third build executed that
   exporter and the APK/AAR tasks successfully.
3. One ABI-tool invocation initially used `kadb-android.aar`, while AGP's actual
   output is `kadb.aar`. It failed before capturing any API. The invocation log
   is retained; both later captures read the actual AARs and both diffs passed.

The Gradle commands, heap/worker settings, logs and final exits are recorded in
`build-command-attempt-*.json`, `build-attempt-*.txt` and `result.json`. Post-build
commands are in `post-build-commands.json`. The toolchain was JDK 25.0.5+8,
Gradle 9.6.0, AGP 9.4.0, Kotlin 2.4.20, Android platform/build-tools 37.

## Scope not established here

**No Android Emulator Instrumentation or ART pairing session was executed in
this local evidence set.** Its counts for Android platform TLS exporter,
real-adbd pairing and physical devices are zero. The mandatory emulator driver
must still execute all nine public-API checks and receive the independent peer's
two-session confirmation. This evidence is also not coverage of Android
Keystore, every Android API level, all public API behavior, independent security
auditing or performance acceptance. The runtime scenario explicitly requires
API 29 or later even though the APK is packaged with minSdk 23.

The runtime dependency inventory identifies corresponding-source inputs; it is
not itself a complete source bundle or a legal certification. The source-bundle
work is recorded separately and must use the actual resolved runtime closure.
