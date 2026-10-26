# Pinned Legacy SPAKE25519 source dependency

Repository: https://github.com/Flyfish233/spake2

Commit: `b837aba27bebc1050965fa124c2efa54b4e4544a`

`upstream/` contains **byte-for-byte unmodified** files from that commit.
`SHA256SUMS` records every included file. `verifyPinnedSources` checks both hashes
and the complete file inventory before compilation. This is a source-composed
fallback, not a published JitPack dependency and not a modification of the
SPAKE2 repository.

Only the Legacy protocol and its required Edwards25519 / SHA-512 primitives are
included. RFC 9382, P-256, JavaScript/Wasm targets, unrelated primitives, and the
SPAKE2 build files are not part of this dependency. No Kadb-specific mathematical
fork or copied platform-specific SPAKE implementation exists.

`build.gradle.kts` is Kadb-owned build adaptation: it uses the Kadb compiler/toolchain
and creates Android, Linux and Darwin variants (including macOS, absent from the
pinned upstream build). It does not modify the included algorithm sources and has
no publication plugin or upload task. Its target matrix is an integration choice,
not evidence that those targets have compiled or run; see the verification ledger.

The original code is **AGPL-3.0-only**, without a linking exception. The complete
license is retained in `upstream/LICENSE`. Kadb's existing Apache-2.0 notices remain
in force for those original files. See `docs/experiment/LICENSES.md` for combined
work obligations and boundaries; this experiment makes no formal release.
