# Native source collector evidence

This directory fixes the reviewed Native source inputs and retains the actual
collector validation. It does not certify a final application distribution's
license compliance or claim a Native binary was built in this check.

The input Kadb commit was `9a2ebbde700d36f7b0efcfc5002dea5c3e9634cf`. The collector
was run from this change's worktree; its exact bytes and template are included
in the generated package and hashed in `evidence/final-manifest.json`. The Kadb
archive remains the exact committed input, with no worktree changes substituted.

## Actual results

| Check | Observed result |
| --- | --- |
| Initial network collection | All 64 fixed dependencies obtained and SHA-256 verified; collector then failed on an incorrect assumption about the Native module's common owner identity |
| Corrected metadata validation | Requires the owning common module and its `available-at` backlink to the exact target; two focused regressions added |
| Integrity regression suite | 10 tests executed, 0 failures, exit 0; no network or Gradle needed |
| Complete offline runs 2 and 3 | Both exit 0 and the same SHA-256 `a88bab1eb6da9c1fc1d206d9f1d692d0e94753fd1b41b2bea3eabffa005193bf`; 142,216,881 bytes |
| Final run 4, after README clarified shared CI source artifacts | Exit 0; 142,217,510 bytes, SHA-256 `2e78c70b1c49ce729ca20f4d4e4cf07516b1cbb101565a4f17c2f12822d96ea8` |
| Independent final CLI `verify --sha256` | All 168 member hashes and the closed manifest/checksum inventory verified |

Run 4's hash intentionally differs: the package includes its README and assembly
template, and those texts changed after the two identical-input reproducibility
runs. The collector algorithm and pinned source bytes did not change. This
checks source-package reproducibility in the recorded Python 3.12.14 environment;
it does not assert that different compiler environments produce identical
Native binaries.

The final package contains 7 full source archives including Kadb, 20 published
source jars, 19 module metadata files, 19 POM files and 96 extracted notice files.
The complete Kotlin repository source contains 249 C/C++/header files under its
Native runtime tree; these are missing from the stdlib-only sources classifiers.
Full upstream archives retain all other source files and original headers too.

The first attempt's raw failure log is preserved under `evidence/harness-history/`.
It is a collector implementation defect, not evidence of a Kadb runtime defect.
The successful run logs, complete final inventory, results and test output are
retained alongside it. No skipped Gradle task is counted as test execution.

## Reproduce and use in CI

See [`docs/experiment/SOURCE_BUNDLE.md`](../../docs/experiment/SOURCE_BUNDLE.md)
for the portable entry point, fixed revisions, shared-source artifact workflow,
binary association and licensing boundaries. The large generated archive is
kept outside Git; the CI entry point obtains and verifies the actual bytes,
rather than providing only their locations.

The validation here used no `--binary`: all manifests explicitly report source
inventory only. A CI job must supply either the real binary hashes to the
collector or separate exact-commit build/hash evidence with clear directions to
the successfully uploaded source artifact. Source collection alone is not proof
that an arbitrary binary came from the recorded commit.
