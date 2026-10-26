# Sources for the Android validation APK

The source-bundle scope now includes the Native runtime dependency set and the
specific `:validation-android-runtime` debug APK in this repository. This is a
bounded source inventory for an experimental consumer, not a claim about an
arbitrary Android application's Corresponding Source or a completed legal review.
The previous Native-only package and its hash remain evidence for their original
commit; they do not acquire Android coverage retroactively.

## Basis and fixed inputs

The consumer added by `2ab85febb3bf98338257d1d5aca0d9e49e552b19` was actually
assembled and passed D8. Its `debugRuntimeClasspath` contained **21 external
archives and two Android project classes JARs**. The original resolution report's
SHA-256 is `baf3c5ef8b0a51a7ca20e7061a4c65a71065ee6d68ad5589c108b11333b521d6`.
The source lock records external coordinates, filenames, byte lengths and
SHA-256 values from that report. The report's selected variants and provenance
are preserved in
[`android-source-provenance.json`](../../validation/source-bundle/android-source-provenance.json).
That provenance also identifies the original probe APK; it does not claim that
the probe APK was built from a later source-collector commit.

| Actual runtime dependency group | Source material included |
| --- | --- |
| Kotlin stdlib 2.4.20, coroutines JVM 1.11.0, Okio JVM 3.18.2 | Published JVM/common source classifiers and real POM/module metadata; the existing fixed complete upstream archives contain their JVM build context too. |
| Bouncy Castle `bcprov`, `bcpkix`, `bcutil` 1.86 | Three published source JARs, three POMs, and complete `bc-java` archive at `eacda831fbe15b272933e40841d8b0827b556fae` (`r1rv86`). The original BC license and source headers remain intact. |
| HiddenApiBypass 6.1 | Published source JAR/POM/module metadata and complete archive at `71aaad4ce558530b4788da67d0e3d9bb3596e9d3` (`v6.1`), including the Apache-2.0 license and build scripts. |
| Eleven AndroidX archives: annotation experimental/JVM, arch core common/runtime, collection, concurrent futures, core, DocumentFile, lifecycle common/runtime, versionedparcelable | Exact published source JARs, POMs, available module metadata and embedded notices. DocumentFile additionally has the fixed module subtree described below. |
| ListenableFuture 1.0, JetBrains annotations 23.0.0, JSpecify 1.0.0 | Exact published source JARs and metadata, with original license headers; ListenableFuture's parent POM is retained to preserve inherited publication information. |
| Metadata-only coordinates | Annotation/common and Okio/common owner metadata, coroutines/common metadata and the coroutines 1.11.0 BOM. A BOM is not misrepresented as a source JAR. |

There is **no Host Test Conscrypt artifact in the APK runtime graph**. The
independent host reference process and the Android platform TLS/ART implementation
are distinct from the APK's bundled dependencies. Atomicfu remains in the Native
source scope; it is not added to the Android binary inventory when absent from
that actual graph.

The combined lock contains **123 fetched inputs**: eight complete upstream
source archives, one DocumentFile module context, 42 published source JARs,
30 Gradle module files and 42 POM files. The exact Kadb commit is archived
separately, including the vendored Legacy SPAKE25519 sources, modifications,
Android consumer source, manifest, Gradle configuration and validation drivers.
The collector requires the consumer files to exist in the selected Git commit;
an uncommitted file in the working tree cannot satisfy this check.

### Published metadata has explicit limits

Thirty-two source classifiers are checked against the publisher's locked
Gradle module metadata. Ten dependencies have no published `.module`: BC's three
artifacts, arch core common/runtime, collection, concurrent futures,
versionedparcelable, ListenableFuture and JetBrains annotations. For those, the
collector verifies the actual POM identity (including Maven parent inheritance),
fixed source-JAR size/SHA-256, ZIP CRC and nonempty source-file inventory.
`metadata_verification: "pom-and-fixed-hash"` identifies this mode. A POM is not
treated as publisher-provided source-byte hash metadata, and no `.module` is
fabricated. The source files themselves, rather than POM URLs alone, are present.

The [official DocumentFile 1.1.0 release entry](https://developer.android.com/jetpack/androidx/releases/documentfile#1.1.0)
links to the change range ending at
`27495ca3d1fe4a1166bea16413ecf8cff5d85855`. The collected
[module subtree](https://android.googlesource.com/platform/frameworks/support/+archive/27495ca3d1fe4a1166bea16413ecf8cff5d85855/documentfile/documentfile.tar.gz)
is only 9,975 bytes, with SHA-256
`99f006d6ae091e5ef56c261f34c982a69cface6e2f46f4691c78b5cb2ced7963`.
All five `src/main/java` files match the published source JAR byte-for-byte; the
collector rechecks that match during creation. Its license is retained from the
published JAR's `META-INF/androidx/documentfile/documentfile/LICENSE.txt`.
This supplies the module build script and tests, not the AndroidX parent build
infrastructure. No release-to-commit mapping is guessed for other AndroidX
modules, and their larger build forest is not claimed to be included.

## CI integration

After APK assembly, export the **actual** Gradle runtime configuration:

```sh
./gradlew -I validation/android-runtime/runtime-classpath.init.gradle \
  :validation-android-runtime:recordRuntimeClasspath --no-configuration-cache

python3 scripts/source_bundle.py verify-android-runtime \
  --lock validation/source-bundle/dependencies.lock.json \
  --runtime-report validation/android-runtime/build/reports/debug-runtime-classpath.json \
  --output evidence/android-runtime-source-verification.json
```

The second command requires the complete external module set and resolved
component graph to match the lock. It rejects missing, unknown or duplicate
modules, changed published archive bytes and changed metadata-only components.
It reads every reported local artifact again and checks its size/hash, so a
stale report cannot hide a modified file. It also verifies the expected Android
project artifact set and current project-file hashes; those project hashes are
not pinned across Kadb commits. The result identifies both the source lock and
the runtime report by SHA-256. A failed check exits nonzero and produces no new
success result.

The source job creates and uploads the actual bundle for the same checkout.
The binary job then uses `record-binary-evidence.py` to associate the current
APK's bytes with that source artifact, exact Git commit and lock. The source
bundle manifest remains explicit when created without `--binary`: the manifest
is a source inventory, and the binary association is recorded separately.
The historical `native-source-bundle-` filename is retained; the manifest's
scope is `experimental-native-and-android-validation-runtime`.

## Coverage boundaries

Original third-party files and notices are retained. Source JARs without a
standalone license still contain their original headers and metadata; complete
Apache-2.0 text is also present in the Kadb archive and notices directory.
The BC full archive retains its own license; the vendored Legacy dependency
retains AGPL-3.0-only. This does not relicense Kadb's original Apache-2.0 source.

AndroidX's shared build infrastructure and complete build repositories for the
small Java annotation/ListenableFuture dependencies are outside this inventory.
Published Java/Kotlin source classifiers are also not a complete original Android
resource and manifest source tree; the resolved AndroidX AARs contain resource
inputs that these classifiers do not reproduce. DocumentFile's checked module
subtree adds the limited build context described above; it does not remove that
broader boundary.
The collected POMs and published source classifiers document that boundary;
their presence is not evidence that every dependency was rebuilt. The package
also omits general-purpose binary toolchains, Android SDK/system implementation,
arbitrary downstream additions and the complete installation/deployment
environment. It is not an offline Gradle cache, a bit-for-bit reproducibility
claim, a final source-availability policy or legal certification. It does not
publish an APK, package version or Release.
