# Targeted review of the pinned Legacy SPAKE25519 integration

This is a source review performed during the Kadb experiment, not an independent
security audit, proof of constant-time execution, cryptographic certification,
or permission to release the combined library. The examined source is
`Flyfish233/spake2@b837aba27bebc1050965fa124c2efa54b4e4544a`, preserved byte for
byte in `third-party/spake2/upstream` and checked by its complete SHA-256
inventory. Kadb integration/lifecycle changes are separate from that immutable
source. No changes were made to the `spake2` repository.

## Source scope and timing behavior

The relevant source files are the pinned `LegacySpake25519.kt`, `Edwards25519.kt`,
`ModMath.kt`, and `Sha512.kt`, plus Kadb's `PairingCrypto`, `PairingAuthCtx`,
platform primitive adapters, and native C RNG/HKDF/AES boundary. All paths below
refer to functions in these exact files, not to a mutable upstream branch.

| Path | Source-level observation | Limit of the observation |
| --- | --- | --- |
| `ModMath.add`, `subtract`, `multiply` | Sixteen limbs, public loop bounds, arithmetic carry/borrow and mask selection; multiplication does not loop until a secret carry becomes zero. | Kotlin/ART/JIT/AOT lowering and CPU behavior were not audited. |
| `ModMath.reduce`, `pow` | Both alternatives are computed for every input bit, then selected by mask. Reduction's loop length depends on input length. | Production random/password hashes are fixed 64-byte values; a generic caller's variable input length is observable. |
| `Edwards25519.multiply` | Processes all 64 four-bit windows, performs four doublings each, and scans all 15 non-identity table entries. Scalar bits do not select a table index or loop bound in source. | Compiler-generated branches, array bounds checks, register spills, allocation/GC and cache effects remain unverified. |
| `hardenPasswordScalar`, `shiftThree` | Three fixed 32-byte hardening passes and one fixed 32-byte shift. Password-bit choices use masks. Kadb explicitly selects `HARDENED`. | This does not independently prove the protocol or the legacy hardening construction. |
| `Sha512.digest` | Eighty rounds per block; padding/copy branches depend on input length and block index, not message byte values. | Length is not hidden, and scalar `Long` intermediates cannot be explicitly erased. |

There **are data-dependent rejection branches**: `ModMath.inverse` rejects zero;
`fromBytes` rejects a non-canonical representative; point decoding checks the
denominator, square-root equation and, in strict mode, canonical sign. Legacy
point decoding uses peer-supplied public bytes; the other inverse check also
protects arithmetic invariants. These branches must not be described as an
unconditional constant-time guarantee. For the reviewed valid, fixed-length
scalar path, no explicit secret-indexed lookup or secret-dependent loop bound
was found. That narrower statement is all the source review establishes.

The same source is compiled on Android and Native, but the resulting machine
code and runtime differ. Native release/debug LLVM builds, Android ART/JIT/AOT,
and different CPU families need their own disassembly and statistical leakage
analysis before a constant-time claim. Timing a few complete pairings cannot
establish absence of a side channel.

## Secret ownership and erasure reachability

The legacy scalar representation is mutable `ByteArray`/`IntArray`, not immutable
`BigInteger`. The normal owned-state paths are explicit:

- `generateMessage` copies caller password input, transfers ownership of exactly
  64 CSPRNG bytes, and clears that password copy, random bytes and temporary
  points in `finally`.
- `deriveUnconfirmedKey` consumes the session. It clears retained scalar/hash/
  transcript state and temporary points and returns a distinct 64-byte
  **unconfirmed** key to its caller.
- `guarded` clears retained state after failure and poisons concurrent access;
  it clears a produced result if a concurrent caller invalidated that operation.
  `destroy` clears retained buffers. Kadb keeps this object owned by one pairing
  worker and does not race destruction against that worker.
- Kadb's HKDF step clears the 64-byte material and temporary 16-byte result after
  copying into its owned key. Destruction clears that key, outbound message and
  nonce state. Authentication/provider failure is terminal. Native AES temporary
  outputs and JVM outputs on tag failure are cleared before discarding them.

These are best-effort overwrites of reachable owned arrays, **not guaranteed
physical zeroization**. Specific remaining limitations include:

1. SHA-512 round locals (`a` through `h`, `t1`, `t2`) and arithmetic carry/nibble
   locals are scalar values. Runtime copies, spills, registers, optimized-away
   stores and garbage-collected copies cannot be reliably erased by `fill(0)`.
   Caller-owned password strings and provider-internal state have separate
   lifetimes. Public `Kadb.pair` takes an immutable `String`, so the caller's
   original pairing code cannot be erased by this implementation.
2. Some low-level allocation-failure paths cannot reach every temporary.
   `Edwards25519.encode` allocates inverse/coordinate/encoding arrays before its
   `try/finally`; failure during those earlier expressions can leave preceding
   arrays unreachable without an overwrite. `add`/`double` construct the four
   output coordinates inline; a later allocation failure can strand an earlier
   output coordinate. In `multiply`, a selected point is not in the outer table
   cleanup if an addition fails before its explicit destruction. `ModMath`
   allocation paths also lack a comprehensive exceptional-cleanup scope.
3. An allocation failure/OOM can itself prevent a managed runtime from reliably
   completing recovery. Ordinary invalid peer inputs are tested separately;
   there is no claim that fault-injected OOM, crash dumps or forensic heap
   inspection has been validated on ART or Darwin/Linux Native.

These are residual erasure limitations, not silently patched mathematical
source. A future change to the library would require separate authorization,
a new immutable source version and its own cryptographic/compatibility review.

## Peer-point semantics and key confirmation

The Legacy protocol intentionally does not apply RFC 9382 point rules.
`decodeLegacy` reduces a non-canonical `y` representative and accepts the old
sign encoding for `x=0`; `deriveUnconfirmedKey` does not call `isSmallOrder` or
`isPrimeOrder` and deliberately allows identity/low-order results after
unmasking. Those helper functions exist in the curve implementation but are not
part of the Legacy path. Rejecting additional points locally would change the
pinned BoringSSL-compatible behavior.

The retained independent C fixture demonstrates why an informal "invalid
encoding" label is insufficient. Its `invalid-encoding-all-ff`, corrupted-point
and identity-after-unmasking cases produce **accepted, unconfirmed** 64-byte
keys; the 31-byte message is rejected. The committed C reexecution matched all
four cases byte for byte. `PairingSpakeVectorTest` now replays those same expected
results through the Kadb shared adapter, in addition to its five message/key
vectors. No expected result is generated by the Kotlin implementation under
test. These added Kotlin checks require actual CI execution before they count
as passing evidence.

Successful point processing establishes no authenticated peer. The enclosing
ADB protocol must retain the exact NUL-terminated role identities, TLS exporter
password binding, transcript hashing, HKDF context and AES-GCM PeerInfo
authentication. M1 additionally validates the authenticated PeerInfo's server
type, length and terminated, nonempty device GUID. A valid tag does not allow
a client public-key record to masquerade as the expected server identity.

No fallback to `PRE_HARDENING_UNSAFE`, RFC 9382, a different curve, or unbound
password material is enabled. The unsafe enum remains present only because the
pinned upstream file is preserved unchanged; Kadb's adapter selects only
`HARDENED` and creates no generic public SPAKE API.

## Nonces and inherited protocol constraints

Kadb encodes the unsigned 64-bit per-direction counter little-endian in the
first eight bytes of a 12-byte nonce, followed by four zeros. The last value
`2^64−1` can be returned once; the next request fails and destroys the pairing
context instead of wrapping. Separate tests cover the high-bit boundary and
exhaustion. Failed authentication or initialization cannot reset a live key
to nonce zero or cause another record to be accepted on that context.

The existing ADB exchange uses the same HKDF result in both directions and
independent counters that each start at zero. This is an inherited protocol
constraint, not directional nonce/key separation introduced by this refactor.
The AOSP [AES-GCM implementation](https://android.googlesource.com/platform/packages/modules/adb/+/44dfb0a1467aa9afe95d15913ae06879f38d1e6a/pairing_auth/aes_128_gcm.cpp)
and [counter initialization change](https://android.googlesource.com/platform/system/core/+/79f3d26b25e731890266f0223fe3453a315a5acb%5E2..79f3d26b25e731890266f0223fe3453a315a5acb/)
are the primary protocol evidence. Changing nonce direction bits or separate
HKDF labels unilaterally would break existing adbd interoperability.

For general AES-GCM use, IV uniqueness applies across encryption invocations
under a key; [NIST SP 800-38D section 8](https://nvlpubs.nist.gov/nistpubs/Legacy/SP/nistspecialpublication800-38d.pdf)
explains the forgery risks of reuse. Therefore this internal ADB key-confirmation
wrapper is **not a general-purpose AEAD construction**, and its counter overflow
protection is not a standalone security proof. The impact of the inherited
two-direction nonce behavior within the TLS-exporter-bound ADB exchange needs
a protocol threat-model review. This experiment neither asserts an exploitable
ADB vulnerability from that observation alone nor certifies the construction.
The production exchange sends one PeerInfo in each direction; the mathematical
counter range is not a promise that `2^64` records per key are safe or supported.

## Entropy, backend boundaries, and executable evidence

Production entropy is supplied by `SecureRandom` on Android and BoringSSL's
`RAND_bytes` through the C boundary on Native. There is no `kotlin.random.Random`
fallback in the SPAKE path. The provider must return newly owned bytes and fail
closed. Added injected-source tests check that wrong-length/throwing entropy
cannot generate a message, clear transferred malformed bytes and cannot retry
a poisoned session. The real-provider smoke test checks owned buffers and
different results; it does **not** certify entropy quality or all provider
failure modes.

The evidence already recorded at the time of this source review is the immutable
source inventory and the independent BoringSSL C oracle's 18 endpoint/input
results, reported in [oracle-reexecution.json](../../validation/spake2/oracle-reexecution.json).
The reference source commit used for that reexecution is
`5b83e5d1abf0ae0033ae52ab579d906b67633b2c`; the historical fixture originated with
`9e04aed2d1652441d2c84e85ed21acc05e053260`. They are not mislabeled as the same
reference build.

Kotlin target compilation, executed vector/lifecycle tests and the mandatory
Native/Java TLS pairing driver each have separate ledger entries. The driver
records elapsed milliseconds, build/runtime identifiers and both session
results; no local Native pairing time is invented here while its build/test
slot is pending. A few functional runs are not a statistical timing study,
performance acceptance, a real-adbd pairing test, or physical-device evidence.
