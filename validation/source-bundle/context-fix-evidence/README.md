# Stable DocumentFile source context: executed verification

Implementation source: `4c5febe1be6a761e2119e02ac9013472f72681af`.
The original `da03de0` CI failure belongs to the main validation ledger and its
retained CI log. This record covers the bounded source-fetch repair and its
actual local verification; it does not replace or reinterpret that failure.

## Diagnosis

Two fresh requests to the same fixed Gitiles archive URL returned HTTP 200 and
valid `application/x-gzip` archives, of **9,970 and 9,945 bytes**. The earlier
locked response was 9,975 bytes. All **19 file paths, lengths and SHA-256 values
match** across the three archives. Their tar/PAX member modification times
vary with request time, and both the uncompressed tar hashes and compressed
archive hashes therefore differ. The response gzip headers themselves contain
zero mtime; this is not fixed merely by zeroing a gzip header.

`http-response-0.tar.gz` and `http-response-1.tar.gz` retain the two unmodified
responses. Their hashes and the source/metadata comparison are recorded in
[`gitiles-context-diagnosis.json`](../gitiles-context-diagnosis.json).
The failed CI downloader discarded its partial response; this diagnosis does
not claim to have reconstructed that particular body. It proves that successful
requests to the supposedly fixed archive URL are not byte-stable.

## Repair and positive evidence

The complete module subtree is retained as **19 readable original files**,
totaling 50,645 bytes, under `third-party/androidx-documentfile-context/upstream`.
Thirteen fixed Gitiles directory trees establish the file membership and blob
identities. The locally committed subtree's actual Git tree is
`70d1f5c4e38eb73cbc08b4d1f1d09f547ad39589`, identical to the upstream module tree.
Its original headers and published Apache-2.0 license are preserved.

The collector reads the selected Git commit's files, verifies every file's size,
SHA-256 and Git blob ID, then creates an uncompressed USTAR with explicit fixed
headers. The resulting context is **71,680 bytes**, SHA-256:

```text
3b60454ef61425219931a5b664d3e6b7c75bf680350da1025afd1f88ba8f23c4
```

The whole-archive hash gate remains mandatory. The five runtime Java files are
also compared against the fixed published DocumentFile source JAR during bundle
creation. All prior module contents remain present; there is no network fallback
that accepts a different archive or a partial source tree.

| Check | Observed result |
| --- | --- |
| Collector integrity tests | **27 executed, 0 failed**; the previous 23 plus committed-file/metadata stability, source/blob tampering, missing-commit content and whole-archive hash controls. |
| Actual committed context assembly | Exact tree `4c5febe` produces the locked 71,680-byte archive and hash above. |
| Older commit missing the context | `5a7ca39` is correctly rejected even while the current working tree has valid files; this is a negative collector control, not product-health evidence. |
| Complete `create --offline` | Exit **0**, `verified`; **122** downloaded inputs verified from cache, plus **one** context assembled from committed source. |
| Independent `verify --sha256` invocation | Exit **0**, all **240 bundle members** verified. |
| Actual Android dependency inventory | **21 external + two project** artifacts re-read and hashed successfully against the new source lock. |

The full candidate package is
`native-source-bundle-4c5febe1be6a761e2119e02ac9013472f72681af.tar.gz`:

```text
bytes: 183122010
sha256: e0e600e278e17196e778fd7cc7788e46ec99ee79fbdf642752fb82387c1ac31d
source lock sha256: 87820248096bd110de6337071bb478405581b5248a88f4af31e685fabc0a1943
```

This large package is generated outside Git. Its unmodified result, manifest,
commands, exit codes and logs are retained here. It has **zero embedded binary
associations** and remains a source inventory. These hashes correspond only to
`4c5febe`, not the later integrated CI checkout. CI must create/upload its own
exact-commit package and separately associate its actual APK and Native binaries.
The earlier `5a7ca39` package evidence is unchanged.

This repairs archive reproducibility and source availability. It does not add
AndroidX's parent build infrastructure, remove the documented resource/manifest
source-tree limitations, establish dependency rebuild equivalence or certify
legal compliance. No product build or device test is claimed by this record.
