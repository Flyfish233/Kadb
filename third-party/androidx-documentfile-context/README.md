# Fixed DocumentFile source context

This directory retains the complete, small `documentfile/documentfile` subtree
from AndroidX commit `27495ca3d1fe4a1166bea16413ecf8cff5d85855`. It supplies source
and build context for the experimental source bundle; it is **not** added to
Kadb's production Gradle target graph. Android still consumes the published
`androidx.documentfile:documentfile:1.1.0` dependency.

- Repository: <https://android.googlesource.com/platform/frameworks/support>
- Subtree Git object: `70d1f5c4e38eb73cbc08b4d1f1d09f547ad39589`.
- `upstream/`: all 19 original files, unchanged, including six Java files
  (five runtime files and one Android test), APIs and module build configuration.
- `SOURCE_FILES.json`: each file's SHA-256, byte count and Git blob ID, plus the
  13 Gitiles directory-tree responses used to verify complete subtree membership.
- `LICENSE`: original Apache-2.0 text from the published source JAR's
  `META-INF/androidx/documentfile/documentfile/LICENSE.txt`. The upstream source
  files retain their own copyright/license headers.

The official [1.1.0 release entry](https://developer.android.com/jetpack/androidx/releases/documentfile#1.1.0)
links to the change range ending at the stated commit. All five runtime Java
files were also compared byte-for-byte with the published 1.1.0 source JAR.

## Why the tree is retained here

The fixed Gitiles `+archive/...tar.gz` URL does not give stable archive bytes:
repeated HTTP 200 responses contain identical source files but fresh tar/PAX
member timestamps. The first download happened to produce a 9,975-byte archive;
later downloads differ in compressed size and SHA-256. The original strict CI
gate correctly rejected this difference rather than disabling its check.

The collector reads these files from the exact selected **Git commit**, checks
both per-file SHA-256 and upstream Git blob ID, and creates a plain USTAR with
explicit zero timestamps and fixed permissions/owners. It then checks a fixed
whole-archive size and SHA-256. It never redownloads or silently accepts changed
Gitiles archive bytes. Source bundle verification still rechecks the five runtime
files against the published source JAR.

The original transport diagnosis is recorded in
[`gitiles-context-diagnosis.json`](../../validation/source-bundle/gitiles-context-diagnosis.json).
This directory does not include AndroidX's parent build infrastructure or claim
a complete resource/manifest source tree for all AndroidX dependencies.
