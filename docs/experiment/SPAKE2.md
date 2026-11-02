# Shared SPAKE25519 integration

## Fixed Maven dependency

The production entry is the KMP root coordinate
`io.github.flyfish233:spake2-legacy:0.1.0-dev.59105290820b`. Its published metadata
selects the platform variant and transitively resolves `spake2-primitives` at
the same version. The immutable producer source is
`Flyfish233/spake2@59105290820bcbfd4e0336a2e7713006a461527f`.

The candidate is the complete Maven directory from Actions run `40388080222`,
artifact `12682137388`. A byte-preserving recovery archive and original artifact
identity are retained under `validation/maven-candidate/`. It is a fixed
experimental candidate, with no formal Maven or Release publication performed.
The exclusive `spake2Repository` prevents an unrelated Maven Local or network
repository from silently supplying this group. The production embedded project
entry has been removed. The Java BoringSSL oracle remains a test dependency.

`verifySpake2MavenResolution` records actual external components, artifacts,
variants and attributes. The source collector independently checks those bytes
against the fixed Maven inventory, original source revision, full source ZIPs
and license companions; see [SOURCE_BUNDLE.md](SOURCE_BUNDLE.md).
Primitives contains its published internal implementation, including P-256;
Kadb continues to invoke only the Legacy public API. Neither production source
sets nor dependency substitution rebuild SPAKE2 from source.

The earlier JitPack failure and six-file source composition belong to Kadb
baseline `49a88b14e9b731e4c086c920eb74664450c79d9f` and upstream `b837aba27...`.
Their logs remain historical evidence in `validation/jitpack/`; they do not
describe the Maven candidate now selected by this branch.

## Production boundary

`PairingCrypto` is a commonMain class. It always selects `LegacySpake25519`,
`Role.ALICE`, and explicit `LegacyPasswordScalarMode.HARDENED`. There is no runtime
negotiation, RFC9382 substitution, pre-hardening fallback or platform SPAKE core.
The obsolete production `spake2-java` dependency and C SPAKE wrapper are removed.
The old Java implementation exists only in validation as an independent peer.

Platform code supplies only operating-system randomness, HKDF-SHA256 and
AES-128-GCM. Android uses `SecureRandom`; Native uses pinned BoringSSL's
`RAND_bytes`, with an error path and no weak/deterministic fallback. This keeps
entropy ownership clear: each request returns a fresh array and the Legacy
library overwrites that transferred entropy buffer. These plumbing tests do not
certify entropy quality or compiled constant-time behavior.

The ADB contract remains: NUL-terminated client/server names, the caller-provided
pairing code concatenated with the exact TLS exporter output, a 32-byte SPAKE
message, 64-byte **unconfirmed** result, HKDF-SHA256 with empty salt and the exact
ADB info string, then AES-128-GCM PeerInfo authentication. AES nonces are independent
send/receive 64-bit little-endian counters followed by four zero bytes. Protocol
PeerInfo validation is required after successful AEAD decryption.

## Lifecycle correction

The old authentication context allowed encryption before key agreement using its
initial all-zero key array, did not consume itself after failed peer processing,
and retained its owned outbound message after destruction. The first three
`PairingAuthLifecycleTest` cases are committed before the fix; their actual red
run is a separate entry in the verification ledger.

The new state machine is one-way: message generated → cipher ready → destroyed.
Key agreement may run once. Invalid peer input, repeated initialization, failed
authentication and exhausted nonce space are terminal. No counter wraps, and
teardown clears the key, owned message, counters and Legacy state. The context
is worker-owned; cancellation closes the transport, while the worker's `finally`
block owns cryptographic destruction after I/O unwinds.

## Evidence interpretation

- `validation/spake2/oracle-reexecution.json` records this experiment's fresh
  BoringSSL C reference run: seven exchanges / fourteen endpoints plus four peer
  cases, with the fixture and executed backend revisions kept distinct.
- `PairingSpakeVectorTest` runs five independent pinned C-oracle exchanges through
  the production wrapper, including ADB identities and high scalar-bit boundaries.
- Existing JCA-generated HKDF/AES-GCM vectors remain common tests.
- `PairingSpakeCompatibilityTest` checks shared Legacy Bob / cipher integration,
  wrong passwords and separate nonce counters. It is not an independent math oracle.
- The historical Java/BoringSSL-derived peer checks the complete TLS exporter and
  pairing wire flow where executed by the validation target.
- `PairingAuthLifecycleTest` protects initialization, terminal failure, cleanup,
  reinitialization and nonce exhaustion. Source presence is not execution evidence.

Only recorded job/test reports establish results on each platform. Pure-Kotlin
sharing alone does not establish production cryptographic security or timing
properties. The dependency's previous tests are provenance, not a substitute
for this consumer's executed tests.
