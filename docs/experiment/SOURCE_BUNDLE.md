# Reproducible Native source-bundle entry point

The previous CI `git archive` supplied Kadb and vendored Legacy sources, but did
not supply all Native library source bytes. It must not be described as the
complete source package for a static framework that also incorporates BoringSSL,
the Kotlin runtime, coroutines, Okio and atomicfu.

`scripts/source_bundle.py` collects those sources and notices with fixed hashes.
It uses only Python 3.11+ and Git; it does not build a target, modify the SPAKE2
repository, upload a package, or publish a Release. A successful bundle result
is evidence of source collection and integrity, not legal certification or a
successful Native binary build.

## Fixed contents and provenance

| Component | Version / immutable revision | Source provided |
| --- | --- | --- |
| Kadb, its C/Cinterop shim and Legacy adaptation | Caller-specified Git commit | Exact `git archive`, including all tracked build scripts and retained licenses |
| Legacy SPAKE25519 | `b837aba27bebc1050965fa124c2efa54b4e4544a` | The actual six unmodified runtime sources and complete AGPL text already vendored in Kadb |
| BoringSSL | `5b83e5d1abf0ae0033ae52ab579d906b67633b2c` | Full 74,661,066-byte upstream archive; same SHA-256 gate as the Native build |
| Kotlin stdlib and Native runtime | 2.4.20 / `890ac1d94fdb80eb85f0eeb5be5e4352df987b2f` | Full repository source archive, including Native C/C++ runtime, plus published stdlib sources classifiers |
| Coroutines | 1.11.0 / `8564f65764d3d05893cec026c6e94250e2b23874` | Full source/build tree and common plus five Native source classifiers |
| Atomicfu | 0.32.1 / `1d625ed1f6e88173f2737c48afe86544e8738232` | Actual Native transitive dependency; full source/build tree and common plus five Native classifiers |
| Okio | 3.18.2 / `9403a094ac98d5a6ba8bad4ec3301399796fad67` | Full source/build tree and common plus five Native classifiers, including POSIX and Apple implementations |
| Breakpad | 2024.02.16 / `f80f2888031b0570783011476a5e862fb7d848a1` | Full source archive, retained for the dependency in Kotlin's macOS runtime build script |

`validation/source-bundle/dependencies.lock.json` fixes every URL, archive
revision, byte length and SHA-256. The source jars were actually downloaded and
checked against the published `.module` SHA-256 values, not inferred from a
release page. Each native artifact was inspected for real source entries. The
source-only jars do not contain complete standalone notices; the corresponding
full repository archives and extracted notices supply those additional files.

The Kotlin Native distribution's `kotlin-stdlib-native-sources.zip` and Maven
source jars were inspected: they do not include the C/C++ runtime. That is why
the full Kotlin source archive is included. It also contains the libbacktrace
and other vendored runtime source. Kotlin's runtime build declares the external
Breakpad tag for macOS; that source is supplied conservatively rather than
assuming dead-code removal excludes it from every consumer.

The Okio POM's SCM URL is `lysine-dev/okio`; its release tag is
`parent-3.18.2`. The old `square/okio` API route redirects there. Both the exact
resolved revision and upstream response are retained in
`validation/source-bundle/upstream-ref-resolution.json`. The resolution records
are provenance, not a claim that unsigned upstream tags are cryptographically
authenticated. Future execution downloads by immutable commit and fixed hash.

## CI integration

The collector supports a source package made in each binary job or a single
shared source artifact for the same CI run and exact commit. Neither arrangement
is a legal certification; both must provide the actual source bytes with clear
directions and equivalent copying access.

For a package made in a binary job, call after the corresponding Native binary
has been produced. Use the exact checkout commit and associate each binary with
a meaningful label. For example, on a macOS job:

```sh
python3 scripts/source_bundle.py create \
  --repo "$PWD" --ref "$GITHUB_SHA" \
  --output evidence/native-source \
  --cache "$RUNNER_TEMP/kadb-source-cache" \
  --boringssl-archive kadb/build/native/downloads/boringssl.tar.gz \
  --binary macosArm64/Kadb.framework/Kadb=kadb/build/bin/macosArm64/debugFramework/Kadb.framework/Kadb
```

For Linux, pass the linked executable or library path actually uploaded. Repeat
`--binary LABEL=PATH` for additional artifacts. If no binary is supplied, the
manifest explicitly records a source-only inventory with **no binary
association**; that mode is useful before linking but is not an assertion about
a particular binary. Hash association records the supplied artifact; it does not
prove by itself that the caller compiled it from the stated commit.

The output directory contains:

- `native-source-bundle-COMMIT.tar.gz`: source bytes, notices, assembly source and
  complete internal inventory.
- Its external `.sha256`, plus `source-bundle-manifest.json` and
  `source-bundle-result.json` for review without unpacking.
- `source-bundle-execution.jsonl`: actual download/cache verification events and
  failures, with timestamps. Existing execution evidence is never overwritten.

Upload the source package, checksum and manifest in the same artifact group as
the matching binaries, or use the shared-source arrangement below. A source
collection failure must block that binary upload from being labeled as
accompanied by its source; upload diagnostic logs separately. Keeping only the
dependency URLs or a Kadb-only archive is not the replacement. The collector is
independent of package publication; the experimental CI integration is described
below.

### One shared source artifact per run and commit

The workflow committed at `696a85f22f25407f92754361b18ae6fd0c2cdba7`
implements this arrangement. Its dedicated source job in
[run 40318831760](https://github.com/Flyfish233/Kadb/actions/runs/40318831760)
actually collected and verified the package, then uploaded
[artifact 12647837176](https://github.com/Flyfish233/Kadb/actions/runs/40318831760/artifacts/12647837176).
The internal source package is 142,303,048 bytes, with SHA-256
`707f257633c57ac115ee6ac6d63b24d02f4f18456ea5d6723ee8cac813ee6485`.
The outer GitHub artifact ZIP has its own distinct digest. These values belong
only to that exact commit; earlier local reproducibility runs used `9a2ebbde`.

Android, Linux Native and Darwin jobs require the source job to succeed. They
record actual binary hashes, the exact commit and source-lock hash in a separate
`binary-source-association.json`, plus `SOURCE_LOCATION.txt`. Source and binary
artifacts use the same configured 90-day retention. This engineering provenance
does not turn a failed build into a pass: the platform results remain separate
entries in the verification ledger. The retention period is not a final source
availability policy or a certification of all Android/downstream dependencies.

A dedicated source job can run `create --ref "$GITHUB_SHA"` without `--binary`
and upload the actual package as `corresponding-source-FULL_COMMIT_SHA`. Have it
expose the successful upload's artifact URL, package SHA-256 and source-lock
SHA-256 as job outputs. This avoids uploading the same 136 MiB library sources
from every Native matrix job; it does not replace the source with pointers.

Every binary artifact must include `SOURCE_LOCATION.txt` identifying that exact
source artifact, the run URL, full checkout commit and package SHA-256. Its job
evidence must separately record `git rev-parse HEAD == GITHUB_SHA`, source-lock
SHA-256, the name/length/SHA-256 of each actual binary, and the build/test commands
and results. That evidence carries the binary association: the source-only
manifest continues to say **no binary association**, rather than pretending a
source job inspected files it never received. Bind the location to the artifact
URL returned by the successful upload, not a guessed artifact ID or a mutable
branch URL.

Gate Native binary uploads on the source job's success. Give the actual source
artifact equivalent copying access and availability for the associated binaries,
and use the same explicit retention policy. A hash, location text or successful
source build without a successful source upload does not satisfy this workflow.
A final job downloading all Native outputs merely to repeat their hashes is
optional; the existing per-job build/hash evidence supplies the simpler
engineering association. The bundler does not independently authenticate that
job evidence or decide a final distribution's section-6 compliance.

Archives are already compressed; artifact upload can use compression level 0.
The fixed source cache is independent of host architecture and can be keyed by
the lock-file SHA-256 to avoid repeated downloads. Every cache read still checks
the hash. The source download total is about 136 MiB, chiefly BoringSSL and the
Kotlin source repository; no compiler binary distribution is downloaded.

## Reproducibility and failure handling

Given the same Kadb commit, lock/assembly files and labeled binary bytes, the
archive has deterministic file order, normalized ownership/modes, commit-based
tar timestamps and zero gzip timestamps. Wall-clock execution data and local
paths stay outside the package. The same inputs can therefore be collected
again using `--offline` and a populated cache. This concerns the source bundle;
it does not claim bit-for-bit Native compiler output reproducibility.

The collector refuses changed project library versions, a mismatched BoringSSL
pin/hash, a changed Legacy revision, missing required source files, mismatched
publisher source metadata, invalid archives, and corrupt cached/downloaded
bytes. Transient network failures have bounded retries; an integrity failure is
not silently replaced or accepted. It retains full source archives and copies
standalone notices byte for byte, including original file headers inside the
archives. The verifier checks all member hashes without extracting archive paths.

```sh
python3 scripts/source_bundle.py verify \
  evidence/native-source/native-source-bundle-COMMIT.tar.gz \
  --sha256 EXPECTED_SHA256
python3 -m unittest discover -s validation/source-bundle -p 'test_*.py' -v
```

## Source obligations and remaining boundaries

The engineering decision follows the AGPL text's definition of Corresponding
Source in section 1: needed source and build/install/run control scripts,
subject to the stated System Library and unmodified general-purpose-tool
exceptions. Sections 4–6 also address notices and conveying combined/source or
object-code works. Section 6(d)'s access method requires equivalent access to
the source alongside the offered binary, with clear directions and appropriate
availability. A transient CI artifact is not a final source-retention policy.
The original Kadb Apache notices and the Legacy AGPL license remain in force;
the collection does not assert that all preexisting source was relicensed.

The bundle deliberately includes the directly used Native library sources and
their build trees. The JDK, Gradle/Kotlin compiler distributions, CMake, LLVM/GCC
toolchains and Apple/Android SDK binary distributions are not downloaded or
bundled. Use of unmodified general-purpose build tools is a different question
from the runtime-library source coverage. System C/C++ runtimes and OS libraries
or frameworks require binary/environment-specific System Library analysis;
the presence of a dynamic `libstdc++` entry alone does not prove that no runtime
code was copied statically. This tool does not certify those legal conclusions.

It also does not cover all Android/JVM external dependencies, third-party code
added by a downstream app, platform signing/installation information for a
User Product, or a deployment's section 13 obligations. Full upstream archives
include build scripts, but all upstream compiler/tools/tests have not been
rebuilt; this is not an offline distribution of every build tool. A final
binary/application distribution needs its own inventory and review. No Maven
publication, formal JitPack release or GitHub Release is authorized or performed.

Primary sources, read for this review:

- [GNU AGPL-3.0](https://www.gnu.org/licenses/agpl-3.0.html), sections 1, 4–6 and
  13; the full text is already retained with the Legacy source.
- [Apache Software Foundation GPL compatibility explanation](https://www.apache.org/licenses/GPL-compatibility.html).
- The fixed source archives, published POMs and `.module` files listed in the
  lock, including Kotlin's `kotlin-native/runtime/build.gradle.kts` and
  `kotlin-native/Interop/Runtime/build.gradle.kts`.
