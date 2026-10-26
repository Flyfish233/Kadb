# Android source-scope validation evidence

Source collector candidate: `5a7ca3928cb4f09c86ff8efada68c859b5f33e49`.
Executed locally on Linux with Python 3.12.14 on 2026-10-26. This is collector
and source-inventory evidence, not an Android device test or a Kadb protocol
health result. No Gradle process was started for these checks.

| Check | Actual result |
| --- | --- |
| Original collector integrity regressions plus Android/metadata controls | **23 tests executed, 0 failures**; raw `integrity-tests-final.log`. |
| Actual runtime archives against the source lock | **21 external archives and two current project JARs** re-read and hashed; exact set/size/hash matched. |
| Source scope applied to the older `b17f418` commit without consumer code | **Expected rejection** at the missing committed Android build file, recorded separately; this is a negative collector-boundary control. |
| `create --offline` at exact candidate commit | Exit **0**, status `verified`; all **123 fixed external inputs** consumed from the already downloaded verified cache. |
| Separate `verify --sha256` command against generated package | Exit **0**, all **239 bundle members** checked against manifest/checksum inventory. |
| DocumentFile module context | All **five published runtime Java files** matched byte-for-byte; six source files in the subtree include its separate Android test. |

The generated package was
`native-source-bundle-5a7ca3928cb4f09c86ff8efada68c859b5f33e49.tar.gz`:

- Bytes: `183063960`.
- SHA-256: `dafd92f795ba51b6ab08edffcaebcdf475d538e3332eb4bb4200912f92213649`.
- Source-lock SHA-256: `50f31392b7a88ef1fefa1f009ea4b9201c1c571814ba990392238265d225bfe0`.
- Complete source archives: nine including Kadb; eight third-party archives.
- Additional module contexts: one, DocumentFile.
- Published source JARs: 42.
- Binary associations inside this package: **0**. Its manifest explicitly records
  a source inventory; actual CI APK/source association is a separate gate.

The large generated package is not committed to Git. CI regenerates and uploads
the actual package for its own checkout commit. A different integrated commit
produces a different package and must use its own hash; this candidate's hash
must not be relabeled as final CI output. `source-bundle-manifest.json` and
`source-bundle-result.json` are the candidate's unmodified outputs.

`origin-debug-runtime-classpath.json` is the unmodified actual Gradle report from
the Android consumer build introduced by
`2ab85febb3bf98338257d1d5aca0d9e49e552b19`. Its SHA-256 is
`baf3c5ef8b0a51a7ca20e7061a4c65a71065ee6d68ad5589c108b11333b521d6`.
Absolute file paths refer to that original build environment. The runtime
verifier actually re-read those files before recording this result. It did not
recompile the APK from the source-collector candidate commit. Current CI must
export its own runtime report and verify its actual current files again.

The integrity tests cover missing/unknown/duplicate runtime modules, a replaced
binary at the same coordinate, stale file hashes, metadata graph/project-set
drift, missing source mappings/POMs, POM identity and inheritance, rejection of
POM-only evidence falsely labeled as Gradle metadata, and checking consumer
files in the exact Git commit rather than the working tree. The original cache,
archive traversal, source-content, metadata backlink and package-integrity
regressions remain in the same run.

`aar-context-observation.json` records actual Android resource/manifest entries
in the resolved AARs. The Java/Kotlin source classifiers are not represented as
a complete original resource/build tree. See
[`ANDROID_SOURCE_COVERAGE.md`](../../../docs/experiment/ANDROID_SOURCE_COVERAGE.md)
for fixed origins, notices and remaining scope boundaries.

Reproduce from the candidate checkout, using a new output directory:

```sh
python3 -m unittest discover -s validation/source-bundle -v
python3 scripts/source_bundle.py create --repo . \
  --ref 5a7ca3928cb4f09c86ff8efada68c859b5f33e49 \
  --cache /path/to/source-cache --output /path/to/new-output
python3 scripts/source_bundle.py verify /path/to/new-output/native-source-bundle-COMMIT.tar.gz \
  --sha256 EXPECTED_PACKAGE_SHA256
```

Add `--offline` only after the fixed inputs are cached. The exact local command
arguments, raw outputs and process exit codes are retained alongside this file.
No source fetch, checksum verification or package creation is treated as a
legal certification or evidence that every upstream dependency was rebuilt.
