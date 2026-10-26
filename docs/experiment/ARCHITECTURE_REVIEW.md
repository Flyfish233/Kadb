# Common and Native architecture review

## Scope and conclusion

This review starts from the complete experimental tree
`9a2ebbde700d36f7b0efcfc5002dea5c3e9634cf`, rather than the upstream iOS patch in
isolation. The frozen upstream comparison remains
`75678915fd4bdd52345edbb6bc4913ae3415a680`. Source review, the new routing
regression and recorded execution results have different scopes; none is an
independent security certification or a proof of all possible interleavings.

The architecture now has a useful shared boundary: protocol state, ownership
policy, pairing orchestration and forwarding sessions are Kotlin common code;
socket, TLS-provider, identity-provider, file-permission and operating-system
thread facilities remain platform implementations. Darwin and Linux reuse one
POSIX transport/identity boundary. The shared Legacy SPAKE25519 implementation
replaces both former platform mathematical cores. Keeping these boundaries is
more valuable than moving POSIX calls or provider objects into `commonMain`.

The review found a concrete remaining stream-routing defect and corrected it in
`02bdb55`: the queue previously matched only a local ID, permitting malformed
WRTE, OKAY and CLSE packets from a different remote stream to affect it. The
unchanged CI Android AAR reproduced five target assertion failures; the focused
corrected-queue overlay passed 22 routing/lifecycle/transfer tests. Full-module
and Native execution of that correction belongs to the subsequent integration
CI, not to the earlier `9a2ebbde` result. See
[the red/green record](../../validation/stream-identity/README.md).

## Shared responsibilities and necessary platform boundaries

Paths below are relative to the relevant module's `src/<sourceSet>/kotlin`.

| Concern | Shared implementation and owner | Required platform behavior |
| --- | --- | --- |
| ADB frames and connection | `core/AdbReader`, `AdbWriter`, `AdbConnection`, `Kadb`; frame bounds/magic, outgoing checksum, CNXN/AUTH/STLS negotiation, feature selection and one connection attempt | `TransportFactory`, `TransportChannel`, TLS upgrade, monotonic I/O deadlines and transport error mapping |
| Stream routing and flow | `queue/AdbMessageQueue`, `stream/AdbStream`; local ID allocation, OPEN handoff, peer binding, queued tail data, ACK interpretation and terminal stream ownership | Blocking reentrant lock/condition and one transport-reader worker; native descriptors never appear in the public stream API |
| Shell, Sync and installation | `shell/*`, `AdbSyncStream`, `Kadb`, `InstallSession`; wire framing, UTF-8 accumulation, feature selection, session abandonment and cleanup precedence | Host filesystem operations, path metadata and host-specific Sync policy; Android `File` compatibility overloads remain at the platform boundary |
| Pairing | `PairingConnectionCtx`, `PairingAuthCtx`, `PairingCrypto`; exact role bytes, TLS-exporter password binding, Legacy exchange, HKDF orchestration, PeerInfo authentication/type checks, nonce lifecycle | CSPRNG, TLS/exporter, HKDF and AES-GCM provider; cancellation closes the actual socket owner |
| Identity | `KadbCert`, policy/store interfaces, host-key selection, PEM and ADB public-key representation | RSA signing/key parsing/X.509 generation, secure system-file staging and optional platform storage; no claim of automatic Keychain/Keystore protection |
| TCP forwarding | `ForwardingSession`; one accepted socket, pending OPEN lifetime, upload/download pumps and completion tracking | Listener creation, accept wakeup, accepted-socket adaptation and platform thread creation |
| mDNS | Service models, service-type parsing, endpoint registry/filtering and `StateFlow` representation | Android NSD callbacks and Apple Bonjour/run-loop ownership; Linux currently has models/parsing only |

`nativeMain` in this experiment means the configured **POSIX** Native family,
not an implementation valid on every Kotlin/Native target. `appleMain` contains
Foundation locks, worker/autorelease-pool and logging adapters shared by iOS and
macOS. UIKit remains confined to the iOS device-name implementation. Linux uses
pthread locks/conditions and detached workers. Introducing Windows would require
an explicit socket/thread/storage implementation; merely adding `mingwX64()`
would produce a false support claim.

The mDNS registry is intentionally not a second concurrency framework. Android
serializes its mutations under its adapter lock; Apple dispatches lifecycle and
Bonjour work through the main thread. `MutableStateFlow` does not make the
registry's mutable endpoint map independently thread-safe. Future backends must
preserve that single-owner/serialized-callback requirement.

## Resource ownership and state transitions

| Resource | Creation, handoff and terminal action | What the reviewed implementation establishes |
| --- | --- | --- |
| Shared Kadb connection | A `ConnectionAttempt` belongs to one generation. Publication requires matching generation and object identity. `close` permanently closes the client; `resetConnection` invalidates the generation and reconnects lazily. | A canceled/old attempt cannot resurrect the client or clear a newer attempt's owned socket/job. An uncertain OPEN is never replayed automatically. |
| Establishment worker | The ordinary first synchronous caller runs establishment on its own thread. A forwarder's first connection attempt uses a Kadb-owned worker so that its private wait can be canceled. | Closing one forwarder does not cancel a connection that another caller needs. Ordinary first-caller interruption and connector timeout exceptions retain their tested behavior. |
| Transport and frame buffers | The connection owns the transport. Okio source/sink adapters do not close it independently. STLS keeps the underlying TCP connection and replaces/adapts its framing owner. | Connection shutdown closes transport I/O before closing serialized writer buffers, waking blocked transport calls instead of waiting for buffer locks first. |
| Pending OPEN | The queue allocates a nonzero ID that is never reused on that connection. The pending record retains a received remote ID until the caller takes ownership or abandons it. | Cancellation before/after OKAY releases only that request. A late OKAY for an absent local stream sends CLSE outside the queue lock. The ID space is finite and exhaustion requests a connection reset. |
| Established stream | First valid OKAY binds the remote ID. Remote CLSE marks the stream closed while retaining already queued data; local close removes its queue and binding. | A fast OKAY/WRTE/CLSE service can return its tail data. The routing fix ignores mismatched IDs without closing unrelated streams. Historical CLSE with remote ID zero remains accepted on this same connection. |
| Forwarding session | The session owns the accepted local socket, a private cancellation Job and registered pump count. Listener adapters retain active sessions and wait for their completion on close. | The listener exiting is not mistaken for all workers exiting. Closing local I/O and canceling a pending OPEN releases tested waiters without closing the shared Kadb transport. |
| Pairing worker | The TLS owner exists before connect/handshake. `runClosingOnCancellation` closes it when canceled and structurally waits for the worker. The worker's `finally` destroys crypto state and temporary password/exporter material. | Cancellation does not race crypto destruction against a still-running worker. A successful suspend return is distinct from merely requesting socket closure. |
| Native C owner | A stable handle owns the socket, close-wakeup pipe, SSL/CTX and copied identity material. Active operations retain those resources. Close poisons the owner and wakes poll; last active exit releases its resources. | Explicit close does not defer socket/TLS/key release until Kotlin's cleaner. The cleaner ultimately reclaims the stable handle/mutex storage. C ownership tests, not Kotlin source shape alone, support this statement. |

The common locks preserve the existing blocking API. Network connect/read/write
and crypto work are not moved into the shared queue lock. `AdbWriter` serializes
a complete ADB frame, which is necessary to prevent bytes from concurrent
streams interleaving. The queue's late-OKAY close callback executes after its
lock is released. Platform forwarder callbacks remove completed sessions outside
the session lock. The Darwin and Linux condition adapters release all recursive
parent-lock depth while waiting and restore it afterward; their condition gate
prevents a signal between release and wait from being lost.

`AdbStream.source` and `sink` each contain mutable buffering and ACK state. The
review supports a reader and a writer coordinated by the connection; it does
not establish that several callers may concurrently read the same source or
write the same sink. Atomic close prevents repeated cleanup, not arbitrary
multi-writer safety. Callers must close the owning stream/session rather than
assuming that closing an individual adapter transfers transport ownership.

## Routing defect: exact scope of the correction

At `9a2ebbde`, dispatch used `arg1` alone and could also accept remote ID zero
for initial OKAY. `AdbStreamIdentityTest` sends encoded frames through the real
reader/queue and demonstrates invalid initial identity, wrong-peer data,
wrong-peer acknowledgement, wrong-peer close and data preceding establishment.
The corrected queue learns a peer once and checks it before dispatch. Its extra
map is protected by the existing queue lock and is removed on cancel, abandon
and stop; `ensureEmpty` now checks it as well.

This matches the relevant
[pinned AOSP packet-routing behavior](https://android.googlesource.com/platform/packages/modules/adb/+/1cf2f017d312f73b3dc53bda85ef2610e35a80e9/adb.cpp#558):
first OKAY establishes the peer, later packets must match it, and zero-ID CLSE
has an intentional historical compatibility exception. This is protocol
isolation inside one connection, not evidence that authentication was bypassed;
a hostile authenticated adbd already controls the data of its legitimate
services. The correction neither changes the SPAKE protocol nor adds a new
checksum or receive-credit policy.

Tests also cover cancellation before OPEN, cancellation after OKAY but before
handoff, late OKAY reclamation, another already-established stream surviving
cancellation, fast tail-data drain, idle transport EOF, local queue close, Sync
QUIT/CLSE cleanup and small-source transfer batching. Their passing results
narrow the regression risk; they do not enumerate every thread interleaving.

## Checksum compatibility: source audit and decision

A follow-up source audit resolves the earlier classification of missing receive
checksum validation. This is a compatibility choice, **not a demonstrated
security defect requiring a new reader rule**. The inspected AOSP files are
pinned to `platform/packages/modules/adb@1cf2f017d312f73b3dc53bda85ef2610e35a80e9`;
retrieved-file hashes and exact URLs are retained in
[the source manifest](../../validation/protocol-checksum/source-manifest.json).
This record is a source audit, not an additional interoperability test run.

The [version constants](https://android.googlesource.com/platform/packages/modules/adb/+/1cf2f017d312f73b3dc53bda85ef2610e35a80e9/adb.h#52)
identify `0x01000000` as the original protocol and `0x01000001` as the
December 2017 skip-checksum revision. The wire calculation is an unsigned-byte
additive sum, as implemented by
[`calculate_apacket_checksum`](https://android.googlesource.com/platform/packages/modules/adb/+/1cf2f017d312f73b3dc53bda85ef2610e35a80e9/adb.cpp#113),
not CRC32. The retained
[protocol document](https://android.googlesource.com/platform/packages/modules/adb/+/1cf2f017d312f73b3dc53bda85ef2610e35a80e9/docs/dev/protocol.md)
still labels the field `data_crc32` and describes version `0x01000000`; those
historical descriptions cannot establish current receive behavior by themselves.

In the pinned implementation,
[`send_packet`](https://android.googlesource.com/platform/packages/modules/adb/+/1cf2f017d312f73b3dc53bda85ef2610e35a80e9/transport.cpp#564)
sends the sum below the skip-checksum version and zero at or above it.
`FdConnection::Read` checks the payload cap, reads the payload and returns;
`atransport::HandleRead` calls `check_header`, which checks magic and the
negotiated length. These receive paths do not compare `data_check`, including
for negotiated legacy connections. The shared
[`APacketReader`](https://android.googlesource.com/platform/packages/modules/adb/+/1cf2f017d312f73b3dc53bda85ef2610e35a80e9/apacket_reader.cpp#34)
also assembles frames without such a comparison. Historical receive validation
is real: Android 8.1's pinned
[`remote_read`](https://android.googlesource.com/platform/system/core/+/f469ebae8604bc756259c7305f8cb7617ca18ddc/adb/transport_local.cpp#63)
called `check_data` after reading the payload. That older implementation is not
the current compatibility reference.

Handshake timing matters independently of that historical difference. AOSP
[initializes the transport version to the minimum](https://android.googlesource.com/platform/packages/modules/adb/+/1cf2f017d312f73b3dc53bda85ef2610e35a80e9/transport.h#283).
The daemon then [updates it on receiving the host CNXN, before requesting AUTH](https://android.googlesource.com/platform/packages/modules/adb/+/1cf2f017d312f73b3dc53bda85ef2610e35a80e9/adb.cpp#407).
Consequently, a modern peer can send zero-checksum AUTH before the host has
received the peer CNXN. Treating the host's initial version as a negotiated
legacy receive requirement would reject this valid handshake.

The decision is to retain Kadb's compatible receive behavior and its existing
version-aware writer. `AdbWireGoldenTest` already covers unsigned-byte outgoing
sums, modern zero checksums, magic/length rejection and truncated frames. A
receive checksum would only detect some accidental payload corruption: the sum
is unkeyed and easily recomputed, so it cannot authenticate a peer or its data.
Kadb checks frame length and magic; authenticated record integrity comes from
TLS when TLS is active. Plain TCP/USB and pre-TLS frames do not acquire that TLS
guarantee, and TLS does not establish that an authenticated peer behaves safely.

## Native and cryptographic boundary

The C shim has explicit responsibilities: descriptor/socket ABI, IPv4/IPv6,
SIGPIPE handling, nonblocking connect/read/write, close wakeups, TLS 1.3,
exporter bytes, RSA/X.509 and the platform primitive calls. BoringSSL is pinned
to `5b83e5d1abf0ae0033ae52ab579d906b67633b2c`, with archive SHA-256
`4117ae02de040d4469284673ed63a14e648af7c3974aa9e85bcef2975a9c9ea8`.
The Native build records its source and compiler/sysroot inputs; Cinterop lists
the embedded archives as inputs so a C change invalidates the KLIB.

The TLS write path serializes retry ownership and preserves the provider's
required buffer across WANT_WRITE retries. A timeout or partial write failure
makes the connection terminal rather than retrying an ADB frame with uncertain
wire progress. Source review and the C transport harness cover same-socket STLS,
TLS exporter bytes including the terminating NUL in the label, identity
selection, write failure, concurrent close, SIGPIPE and retained closed owners.
ASan/UBSan here instrument the shim/harness; they do not establish that the whole
BoringSSL build or Kotlin runtime has undergone sanitizer coverage. See
[Native verification](../verification/native/README.md).

SPAKE math and its protocol transcript are the pinned
`Flyfish233/spake2@b837aba27bebc1050965fa124c2efa54b4e4544a` Legacy implementation.
Kadb selects `HARDENED`; the RFC 9382 path is not substituted. AES-GCM, HKDF,
SecureRandom/RAND_bytes and TLS remain provider boundaries. The independent
Java/C references are validation dependencies, not a second production SPAKE
backend. The source-composition fallback is not a claim that JitPack published
consumable Native/Maven variants; the exact probe result is in [SPAKE2.md](SPAKE2.md).

The [targeted crypto review](LEGACY_CRYPTO_REVIEW.md) describes inherited nonce
semantics, point compatibility, best-effort erasure and source-level timing
observations. This architecture review makes no stronger claim: a valid SPAKE
calculation is not peer authentication until PeerInfo authentication and its
protocol constraints succeed; Kotlin array overwrites are not physical memory
zeroization; functional vectors are not a constant-time proof.

## Public API, exceptions and JVM exit

The existing `Kadb`, shell/Sync models, package names, synchronous entry points,
default arguments and Android `File` overloads remain the compatibility surface.
The concrete Android AAR ABI gate at `9a2ebbde` passed against the frozen public
inventory. Broader bytecode inventories and Native header comparison remain
separate checks: an internal refactor passing Kotlin source compilation does
not imply Java binary or Swift selector compatibility.

The internal cancellable OPEN does not add coroutine semantics to public
synchronous operations. The client never retries an uncertain OPEN. Explicit
close/reset during establishment reports transport cancellation; a connector's
ordinary `TimeoutCancellationException` is preserved when the client generation
has not been invalidated. Existing failure cleanup preserves the original
exception with secondary cleanup failures where the corresponding protocol
wrapper defines that behavior.

Kotlin/Native's Objective-C exception boundary requires deliberate API design.
Adding `@Throws` to existing synchronous methods changes their exported
selectors/Swift call shape; annotating common declarations can also change Java
checked-exception metadata. The additive `appleMain/KadbApple` adapter therefore
wraps high-level shell/file/install/reset/close operations and suspend pairing
with `@Throws(Exception::class)`, directly delegating to the existing client.
It does not expose a raw stream and pretend subsequent Swift I/O is protected.
Closing the adapter explicitly closes its supplied client. Fatal `Error`
classes are not declared as ordinary NSError failures. The original unannotated
Kadb Swift methods retain their original limitations; see
[the exception-boundary contract](../apple-exception-boundary.md) and
[JetBrains interop documentation](https://kotlinlang.org/docs/native-objc-interop.html#errors-and-exceptions).

The attempted optional `NativeThrows`/actual-typealias approach failed real
Native compilation and was removed, without suppression or rewriting the failed
history. An exported header is necessary but insufficient for consumer support:
the standalone Swift consumer must compile, link, run, receive a controlled
pairing failure and catch a real accepted-socket EOF from `KadbApple.shell`.

A read-only review of the M5 candidate `/tmp/kadb-m5` confirms a substantive
removal design: production `jvm()` targets and desktop JVM USB/JmDNS backends
are removed; Android retains the Java/ART crypto and transport implementation;
independent Java reference processes remain test tooling. This candidate was
not the `9a2ebbde` CI tree, so JVM-removal acceptance requires a new full-tree
run. Native TCP, TLS, shell, Sync, installation and forwarding are the desktop
replacement scope. Native USB and Linux discovery are explicit feature losses,
not advertised replacements. No Java/JVM artifact compatibility is promised for
the intentionally removed desktop target.

## Execution evidence at the reviewed checkpoint

The following rows refer to
[run 40314095952](https://github.com/Flyfish233/Kadb/actions/runs/40314095952),
checked at the completed job states. Later ledger entries supersede platform
status only with their own commit and execution evidence.

| Platform / gate | Observed evidence | Limit |
| --- | --- | --- |
| Android artifact and host | Job `121542218874` succeeded; actual Kadb/mDNS AARs, 92 Kadb Android Host tests and public ABI comparison passed. The same job also ran 81 temporary JVM Kadb and 12 JVM mDNS tests: 185 total, zero failures. | Host JVM execution is not Android instrumentation or ART/device execution. |
| Linux Native | Job `121542219187` succeeded; Cinterop, compile, executable link, 47 executed Native tests, external independent-Java pairing, C harness/sanitizers and independent SPAKE oracle all passed. | Test/reference peer is not adbd; tested host is not proof of the declared minimum glibc runtime. |
| macOS ARM64 | Job `121542219244` built/linked the framework and Native executable, executed its macOS suite and independent-Java pairing; report records 54 tests, zero failures. | The job failed at the standalone Swift consumer's external link, then correctly failed the missing-Simulator gate. |
| macOS x86_64 | Job `121542219335` passed Native build/execution and independent-Java pairing. | Its standalone Swift link also failed; deprecated K/N target status is a maintenance risk, not an excuse to call a skipped test passed. |
| iOS Simulator / device framework in this run | Required subsequent steps were skipped after the Swift failure. | Earlier baseline Simulator execution remains baseline evidence only. This run establishes neither current Simulator execution nor iPhone execution. |
| Real emulator adbd | Job `121544228916` provisioned the emulator, but its public Native consumer driver failed with `checks_executed: 0`. | No protocol/installation success can be inferred from emulator boot. The next run must retain the failure report and execute the checks. |
| Remote-ID correction | New test `211f867`: unchanged Android AAR 5/5 intended failures. Corrected production queue `02bdb55`: focused CLI overlay 22/22 passed. | The correction is newer than this CI run and needs integrated Android/Native validation. |

The Swift failure is a **link** failure, not a Swift API spelling failure. The
ARM64 runner reported Xcode 16.4; unresolved Foundation/CoreFoundation symbols
came from K/N platform cache objects. The K/N 2.4.20 distribution itself lists
`linkerOptimizationFlags.macos_{arm64,x64} = -dead_strip`, and Apple documents
[dead-code stripping as a standard linker setting](https://developer.apple.com/documentation/xcode/build-settings-reference).
Adding that ordinary static-link setting retains unresolved-symbol checking for
live code; it is not equivalent to dynamic lookup or a symbol stub. The
[official Kotlin compatibility table](https://kotlinlang.org/docs/multiplatform/multiplatform-compatibility-guide.html)
recommends Xcode 26.4 for KGP 2.4.20. The next consumer link/run must establish
whether standard dead stripping suffices or a matching SDK must be selected.
Neither remedy is recorded here as having run successfully.

## Remaining risks and precise limits

1. **Blocking DNS:** `getaddrinfo` cannot be interrupted by closing the socket
   owner. Native cancellation wakes poll/connect/read/write, but the structured
   helper still waits for a resolver already running. Numerical-loopback
   cancellation tests do not establish a bounded DNS deadline.
2. **Connection-wide writes:** `AdbStream.close` sends CLSE before removing its
   local listener. A writer already blocked indefinitely can delay both that
   cleanup and a forwarder's cancellation callback. Closing a single stream
   cannot safely abort a partial shared frame while promising all other streams
   survive. Default `socketTimeout == 0` remains unbounded; no universal bounded
   `forwarder.close()` claim is made. Android's blocking Socket output path also
   lacks a hard write timeout even when its timeout parameter is nonzero.
3. **Deadline scope:** Native and Java Okio adapters split transfers into chunks;
   per-call timeouts are not an end-to-end deadline for a large shell/Sync/install
   transaction. DNS, identity generation, lock acquisition and a sequence of
   chunk writes need separate accounting before a total-duration guarantee.
4. **Adversarial peer limits:** per-stream command queues have no
   aggregate-byte/credit admission bound against a peer that ignores ADB flow
   control. Remote-ID binding does not provide that resource bound. No resistance
   to an indefinitely flooding authenticated peer is asserted. Receive checksum
   behavior is documented separately above as compatibility with the inspected
   current AOSP implementation, rather than classified as a confirmed security
   defect; frame length/magic checks are not payload authentication.
5. **Physical worker completion:** pairing cancellation and forwarder pump
   completion have explicit waits. `Kadb.close()` does not join every reader or
   shared connection-establishment worker; it invalidates publication and closes
   owned I/O. Native detached threads and Java reader threads may finish later.
   Cleaner reclamation of an unreachable lock/handle is also distinct from
   explicit socket/secret release.
6. **Identity persistence:** Native system-store hardening is separately tested
   in the Native security follow-up (`f6a30e3`), including exclusive 0600 staging,
   symlink replacement, cleanup and close-on-exec. It was not part of this
   reviewed CI checkpoint. The common/custom-filesystem staging path was found
   to skip cleanup if staging itself throws, and its cleanup existence probe
   can mask the original error; that ordinary-I/O regression is assigned to the
   Native/storage follow-up. Custom filesystems cannot be promised POSIX
   permissions. `KadbCert` restoring its previous in-memory state after an error
   is not an atomic rollback of an already committed store write; no injected
   OOM/store transaction proof is claimed.
7. **Secret diagnostics and lifecycle:** the snapshot data-class diagnostic
   string contains secret-array representations at the reviewed checkpoint;
   the separately assigned redaction follow-up must retain component/copy/API
   compatibility and show synthetic-secret tests. Long-lived caller snapshots,
   immutable pairing-code strings and provider internals cannot be erased by
   closing a Kadb session. See the crypto review for finer erasure limits.
8. **Hardware and OS coverage:** no physical iPhone-to-adbd, Android USB hardware,
   Native USB, Windows Native, real-network Bonjour churn, suspend/resume or
   minimum-OS execution is established here. The explicit device entry point
   must fail when required configuration is missing, and its logs must identify
   the actual client platform rather than relabel a Simulator as an iPhone.

## Performance claims this evidence supports

The code batches small Sync source reads instead of flushing every read. The
transfer regression sends 128 KiB from a source limited to 111 bytes/read,
checks exact bytes and framing, and requires fewer than 25 ADB WRTE packets at
an 8192-byte negotiated payload. That demonstrates batching for this controlled
case. Reused adapter scratch buffers, one transport reader and serialized frame
writes are source observations, not throughput or memory measurements.

The design still allocates a payload array per received frame, several pairing
intermediates, per-stream buffers and platform workers. `ForwardingSession`
uses two blocking pumps per active connection. A large connection count can
therefore exhaust threads or accumulate queued data; no scalability envelope
has been measured. Native/Java pairing driver elapsed times are individual
functional observations, not p95 latency or comparative platform benchmarks.
There is no energy, thermal, constant-time, peak-RSS, long-duration leak or
performance acceptance claim. A meaningful later benchmark needs fixed device,
OS, build mode, payload/window settings, concurrent stream count and a retained
measurement harness.

## Integration gates after this review

The routing correction must run with the storage/redaction and M5 changes on
the full Android and retained Native target set. Preserve the ABI comparison,
actual report count gates, independent pairing, external Swift compile/link/run,
Simulator execution and actual-adbd checks. Each failure remains in history and
must be distinguished from a dependency, harness, compile or link failure.
Security and performance acceptance remain separate from a green build.

The combined distribution includes original Apache-2.0 code and pinned
AGPL-3.0-only SPAKE code; it is an experimental fork, not a blanket relicensing
of Kadb or a finished release/license plan. The corresponding-source bundle,
third-party notices and [license record](LICENSES.md) are part of the deliverable.
No Maven/Release publication or upstream PR follows from this review.
