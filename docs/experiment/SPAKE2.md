# Shared SPAKE25519 integration

## Fixed dependency and fallback

Runtime source is fixed to `Flyfish233/spake2@b837aba27bebc1050965fa124c2efa54b4e4544a`.
JitPack consumption failed: it supplied no usable `.module` or platform artifacts,
and its build log reports a missing `publishToMavenLocal` task. See
`validation/jitpack/README.md` and retained raw logs. We have not modified that
repository and do not claim Maven/JitPack integration.

Kadb composes a small standalone KMP module from six byte-for-byte upstream
Kotlin files plus the original license. `verifyPinnedSources` checks the complete
inventory and each SHA-256 before compilation. Build adaptation only supplies
Kadb's compiler/toolchain and Android/Linux/Darwin target matrix; no arithmetic
or upstream Legacy protocol source is edited. No RFC protocol implementation or
unneeded P-256 source is included.

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
