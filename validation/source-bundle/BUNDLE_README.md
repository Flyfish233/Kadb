# Experimental Native and Android validation runtime source bundle

Kadb source commit: `@KADB_COMMIT@`.

This package supplies actual source bytes, original notices, build scripts and
checksums for the reviewed Native runtime dependency set and this repository's
`validation-android-runtime` debug APK. It is an engineering
source inventory, not a certification of complete legal compliance, a toolchain
image, or a source package for arbitrary downstream Android applications.

## Contents

- `upstream/kadb-*.tar.gz`: the exact `git archive` of the stated Kadb commit,
  including the fixed Maven candidate recovery archive/manifest, integration changes,
  Gradle wrapper/configuration, CMake/Cinterop sources, Android consumer Java,
  manifest/build scripts, validation drivers and licenses. Creation fails when
  the exact selected commit lacks the consumer's required source files.
- Eight immutable upstream source archives: BoringSSL; Kotlin 2.4.20 (including
  Native C/C++ runtime, libbacktrace, standard-library sources and their build
  scripts); coroutines 1.11.0; atomicfu 0.32.1; Okio 3.18.2; and Breakpad, included
  conservatively because the pinned Kotlin macOS runtime build uses it; Bouncy
  Castle 1.86; and HiddenApiBypass 6.1.
- A fixed DocumentFile 1.1.0 module subtree with its build script, tests and all
  five runtime Java files, checked byte-for-byte against the published sources.
  Its 19 readable files are retained in the exact Kadb commit and checked against
  upstream Git blob IDs and per-file SHA-256 before a fixed plain USTAR is
  assembled and checked by its whole-archive hash. This avoids Gitiles archives'
  varying request-time tar metadata. Of 213 fixed dependency inputs, 122 retain
  their previous upstream download sources, 90 are copied from the verified
  Maven candidate and this one is assembled from committed files.
  This small subtree does not include the AndroidX parent build system.
- `maven/`: 64 published source JARs, 52 Gradle module metadata files, 64 POMs,
  22 SPAKE2 license/documentation companions and two full SPAKE2 source/build
  distribution ZIPs. Legacy and Primitives use the fixed version
  `0.1.0-dev.59105290820b`, source
  `59105290820bcbfd4e0336a2e7713006a461527f`, and original GitHub candidate
  artifact `12682137388` from run `40388080222`. Full ZIPs contain all producer
  modules, tests/reference tools, wrapper/build files, dependency lock and
  original notices; individual source JARs do not replace those archives.
  The source lock fixes all 22 production-related SPAKE2 publications and 124
  Maven files. The remaining Native/common and Android source classifiers keep
  their earlier coverage. Fifty-four source JARs are checked against locked
  Gradle metadata; ten older modules without `.module` use verified POM identity
  and fixed source size/hash/inventory. No module metadata is invented.
  Metadata-only owners, the coroutines BOM and ListenableFuture's parent POM are
  retained. See `MANIFEST.json` for exact paths, candidate identity and coordinates.
- `notices/`: standalone license, copyright and notice files copied unchanged
  from the source archives and published source jars. Original file headers and
  all remaining source text are retained in the original archives. Some older
  AndroidX source jars only contain license headers and license URLs in their
  POMs; their contents are preserved unchanged. Apache-2.0's full text is present
  in `notices/kadb/LICENSE`; the full AGPL text is retained as `LICENSE` in
  both SPAKE2 source-distribution ZIPs and every license companion, with byte
  copies under the corresponding `notices/maven/io/github/flyfish233/` paths.
- `assembly/`: this bundler's source, fixed dependency lock, upstream tag-to-commit
  resolution evidence, Android runtime/source provenance and this README template.
- `MANIFEST.json` and `SHA256SUMS`: the exact file inventory and hashes. The
  manifest identifies any compiled Native binaries supplied to the bundler by
  their labels and hashes. If none were supplied, it explicitly says source
  inventory only; the package does not then claim binary correspondence.

The historical `native-source-bundle-` file/prefix is retained for existing
automation. Its manifest's explicit scope, rather than the filename, identifies
the additional Android validation consumer coverage.

The Okio 3.18.2 POM identifies `lysine-dev/okio` as its SCM repository, and the
previous `square/okio` API route redirects there. The lock records the actual
repository and resolved `parent-3.18.2` commit; it does not silently substitute a
different Square revision. Atomicfu is included because coroutines' Native
metadata selects it transitively. The resolved version is 0.32.1, not the older
0.23.1 lower constraint also present in that metadata.

The Android runtime lock retains the original consumer's 21 external archives,
including DocumentFile's AndroidX transitives, ListenableFuture, JetBrains
annotations and JSpecify, then replaces the embedded SPAKE2 project with two
fixed candidate AARs. The expected migrated graph has 23 external archives and
one Kadb project artifact; it requires a fresh runtime report before binary
acceptance. The baseline report is labeled separately and contains no Host Test
Conscrypt binary. The CI
`verify-android-runtime` command compares the complete resolved module set,
metadata-only components and actual external archive hashes with this lock. It
also rehashes the current project classes JARs without fixing their hashes across
Kadb commits. `record-binary-evidence.py` separately binds the resulting APK,
source package, lock and Git commit within the same CI run.

## Verify and rebuild

Verify the outer package before extracting it, using the assembly script from a
trusted Kadb checkout and the outer SHA-256 supplied beside the package:

```sh
python3 scripts/source_bundle.py verify native-source-bundle-COMMIT.tar.gz --sha256 EXPECTED_SHA256
```

The verifier reads every member without extracting paths. After extraction,
`assembly/source_bundle.py verify` can perform the same integrity check. A hash
establishes byte integrity relative to a trusted expected value; it is not a
signature or proof of authorship.

Extract `upstream/kadb-*.tar.gz` into a working directory, run
`python3 scripts/prepare_spake2_candidate.py` to recover the fixed Maven repository,
and use its documented Gradle tasks and Native backend build instructions.
The Maven group resolves exclusively from that repository. A report generated by
`:kadb:verifySpake2MavenResolution` records the actual selected binaries/variants;
`source_bundle.py verify-spake2-maven` rechecks their bytes, version and source
identity. `MANIFEST.json` labels resolution as `NOT VERIFIED` when source
collection was run without an actual resolution report. The original executable bits
and build scripts are retained by Git's archive. Reuse the included BoringSSL
archive at `kadb/build/native/downloads/boringssl.tar.gz`; the build verifies its
fixed checksum. The full upstream archives provide their library build scripts,
alongside the exact published source classifiers. AndroidX's parent build
infrastructure and the full build repositories for the small Java
annotation/ListenableFuture dependencies are not included. Their published
Java/Kotlin classifiers do not supply the complete original Android resource
and manifest source trees either. Sources and POMs are retained; do not interpret
this bounded inventory as a clean rebuild of every dependency.

This is not an offline Gradle dependency cache. Building still requires the
documented unmodified general-purpose tools: JDK, Gradle, Kotlin compiler/Native
distribution, CMake, a C/C++ toolchain and the appropriate platform SDK. This
bundle does not download their large binary distributions. The Kotlin source
archive contains additional compiler source as delivered by upstream, because
it also contains the required Native runtime and standard-library build tree.
The presence of these sources does not assert that all upstream tools or tests
were rebuilt or that the final binary is bit-for-bit reproducible.

## License and distribution boundaries

The original Kadb source remains under its existing Apache-2.0 notices. The
Legacy and Primitives Maven dependencies are AGPL-3.0-only without a linking exception. Other
libraries retain their original, sometimes composite, notices. Providing this
package does not relicense all original Kadb files as AGPL or establish a final
license plan for an application that combines them.

AGPL section 1 describes Corresponding Source as the source and control scripts
needed to generate, install, run and modify the covered work, with specified
exceptions for System Libraries and unmodified general-purpose tools. This
package includes actual Native library build trees and the Android validation
dependencies' published sources, with the remaining build-context boundaries
stated above. URLs, version numbers or a Kadb-only archive are not treated as
the whole source delivery. Under the section 6(d) access method, provide the source
alongside the binary with equivalent copying access, clear directions and
appropriate availability. The word “experimental” does not remove those duties.

Provide this actual package and its hash/manifest with the corresponding CI
binaries. A single source artifact for the same CI run and exact Kadb commit is
also supported: every binary artifact must contain clear `SOURCE_LOCATION.txt`
directions to that source artifact, with equivalent copying access and an
appropriate retention policy. The source package must have been uploaded
successfully; a location or hash alone is not source delivery. In this arrangement
the source-only manifest intentionally does not claim binary association. Each
binary job must retain its checkout commit, source lock/package hashes, actual
binary hashes and build/test evidence to establish the association separately.

A source-generation, checksum or source-upload failure must prevent a binary
from being presented as having its matching source package; keep failure logs.
Do not rely on an expiring unrelated CI artifact as a final source-availability
policy. No package repository, Release or application distribution is created
by this script.

The system C/C++ runtimes, OS libraries/frameworks and SDK implementation are
outside this package's dependency-source scope. Whether each such component
qualifies for the AGPL System Library exception requires review for the actual
distributed binary and environment; static versus dynamic linkage alone does
not settle that classification. The Native framework/application boundary,
downstream additions, possible User Product Installation Information and AGPL
section 13 network duties also depend on the actual distribution/deployment.
Those questions are not certified by this inventory. Bouncy Castle,
HiddenApiBypass and DocumentFile are included for this specific Android APK.
The Android platform's TLS/ART/system implementation and the independent host
reference process are not linked libraries inside that APK. This does not cover
an arbitrary Android application, its other dependencies or its complete
installation/deployment environment.

Primary texts: <https://www.gnu.org/licenses/agpl-3.0.html> (sections 1, 4–6, 13),
<https://www.apache.org/licenses/GPL-compatibility.html>. The complete relevant
license texts and upstream notices accompany the actual source archives.
