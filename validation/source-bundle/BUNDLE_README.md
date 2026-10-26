# Experimental Native runtime source bundle

Kadb source commit: `@KADB_COMMIT@`.

This package supplies actual source bytes, original notices, build scripts and
checksums for the reviewed Native runtime dependency set. It is an engineering
source inventory, not a certification of complete legal compliance, a toolchain
image, or an Android/JVM dependency-source package.

## Contents

- `upstream/kadb-*.tar.gz`: the exact `git archive` of the stated Kadb commit,
  including its six source-pinned Legacy SPAKE25519 files, integration changes,
  Gradle wrapper/configuration, CMake/Cinterop sources, scripts and licenses.
- Six immutable upstream source archives: BoringSSL; Kotlin 2.4.20 (including
  Native C/C++ runtime, libbacktrace, standard-library sources and their build
  scripts); coroutines 1.11.0; atomicfu 0.32.1; Okio 3.18.2; and Breakpad, included
  conservatively because the pinned Kotlin macOS runtime build uses it.
- `maven/`: 20 published sources jars plus their 19 module metadata and 19 POM
  files. The library/common and five retained Native target variants are covered.
  Every sources jar was checked against its publisher's pinned module metadata.
- `notices/`: standalone license, copyright and notice files copied unchanged
  from the source archives. Original file headers and all remaining source text
  are retained inside those full archives. Apache-2.0's full text is also present
  in `notices/kadb/LICENSE`; the full AGPL text is in
  `notices/kadb/third-party/spake2/upstream/LICENSE`.
- `assembly/`: this bundler's source, fixed dependency lock, upstream tag-to-commit
  resolution evidence and this README template.
- `MANIFEST.json` and `SHA256SUMS`: the exact file inventory and hashes. The
  manifest identifies any compiled Native binaries supplied to the bundler by
  their labels and hashes. If none were supplied, it explicitly says source
  inventory only; the package does not then claim binary correspondence.

The Okio 3.18.2 POM identifies `lysine-dev/okio` as its SCM repository, and the
previous `square/okio` API route redirects there. The lock records the actual
repository and resolved `parent-3.18.2` commit; it does not silently substitute a
different Square revision. Atomicfu is included because coroutines' Native
metadata selects it transitively. The resolved version is 0.32.1, not the older
0.23.1 lower constraint also present in that metadata.

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

Extract `upstream/kadb-*.tar.gz` into a working directory and use its documented
Gradle tasks and Native backend build instructions. The original executable bits
and build scripts are retained by Git's archive. Reuse the included BoringSSL
archive at `kadb/build/native/downloads/boringssl.tar.gz`; the build verifies its
fixed checksum. The other full upstream archives provide the corresponding
library build scripts, alongside the exact published source classifiers.

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
Legacy source dependency is AGPL-3.0-only without a linking exception. Other
libraries retain their original, sometimes composite, notices. Providing this
package does not relicense all original Kadb files as AGPL or establish a final
license plan for an application that combines them.

AGPL section 1 describes Corresponding Source as the source and control scripts
needed to generate, install, run and modify the covered work, with specified
exceptions for System Libraries and unmodified general-purpose tools. This
package therefore includes actual linked-library sources and their build
scripts instead of treating URLs, version numbers or a Kadb-only archive as the
whole source delivery. Under the section 6(d) access method, provide the source
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
Those questions are not certified by this inventory. Android runtime libraries
such as Bouncy Castle, Conscrypt and DocumentFile are not covered by this Native
bundle; do not label it a complete Android or whole-application source package.

Primary texts: <https://www.gnu.org/licenses/agpl-3.0.html> (sections 1, 4–6, 13),
<https://www.apache.org/licenses/GPL-compatibility.html>. The complete relevant
license texts and upstream notices accompany the actual source archives.
