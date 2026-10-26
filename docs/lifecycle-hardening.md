# Lifecycle hardening (M1)

The experimental changes start from the iOS baseline
`75678915fd4bdd52345edbb6bc4913ae3415a680`. Defect reproductions were committed before
production fixes. The confirmed negative results are in `validation/m1/red-confirmed`;
positive execution results are recorded separately, after the corresponding tasks finish.

## Ownership and cancellation

`runClosingOnCancellation` adapts blocking I/O into structured coroutines. Its resource is
owned before scheduling the worker. Cancellation closes that resource to interrupt I/O,
while `coroutineScope` waits for the worker to exit. An atomically started child guarantees
that scheduling cancellation cannot strand the operation. The helper also closes the
resource if cancellation wins while the scope is returning a result. Successful operations
transfer the still-open resource to the caller.

The pairing worker alone creates, uses, and destroys its cryptographic context. Concurrent
`PairingConnectionCtx.close()` only invalidates the context and closes transport I/O while
that worker is active. Its finally block erases the password and destroys the auth state.
The temporary TLS-exporter material and session-bound password are erased immediately after
initializing the authentication context. The public `pair` entry also clears its password
array if construction or identity loading fails. The caller's immutable String cannot be
erased by this API.

The JVM/Android pairing transport registers its raw socket before connect and its TLS socket
before handshake. Close is terminal and idempotent. Raw TCP is closed before the TLS wrapper
so cleanup does not wait for a peer to receive a TLS close notification. No racing start may
publish a new live socket after close.

Name resolution is a platform blocking operation. Closing the socket cannot reliably abort
an in-progress system resolver call; structured cancellation waits for that worker rather
than hiding it as an orphan. CPU-only cryptographic work similarly retains its state until
its worker has stopped using it.

## Failed writes are terminal

An `SSLEngine.wrap` call may consume plaintext and advance TLS record state before any bytes
reach TCP. After a write timeout or partial delivery, replacing that record or retrying the
consumed plaintext would be unsafe. `TlsNioChannel` now closes and permanently invalidates
the underlying transport on write failure. Handshake and read failures also invalidate the
channel. Further I/O checks the terminal state, including writes whose supplied buffer is
already empty. Cleanup is atomic and idempotent, and the original failure is propagated.

The regression peer completes a real JDK TLS 1.3 handshake, then injects TCP failure after
0 or 5 bytes of an application record. The test verifies actual plaintext consumption,
transport invalidation, absence of later writes, and idempotent cleanup. It does not infer
correctness from a mock cipher.

`AdbWriter.close()` now takes the same reentrant lock as writes. `AdbConnection` already
closes the transport first, which unblocks an in-flight write before buffered cleanup waits
for its lock. This avoids concurrently flushing or mutating the same Okio buffer.

## Connection attempts and exception compatibility

Kadb records the active connection coroutine before the connector can return a transport.
Close/reset can therefore cancel a pending attempt even before `connectingTransport` exists.
Android's blocking connect runs through the same close-on-cancellation helper. Existing
connector timeout exceptions remain unchanged when no close/reset invalidated the attempt;
explicit lifecycle cancellation reports an IOException to the synchronous caller.

This concerns connection creation. Cancelling one forwarded pending OPEN on an already
shared ADB connection is a separate stream-lifecycle issue; these changes do not claim that
closing a forwarder's listener joins every forwarding worker.

## Authenticated PeerInfo validation

Successful AEAD decryption is followed by exact 8192-byte PeerInfo validation. A client
accepts only `ADB_DEVICE_GUID` (type 1), with a nonempty, NUL-terminated GUID in the 8191-byte
data field. GUIDs remain opaque strings: no UUID syntax or zero-padding requirement is
invented. Wrong password, wrong length, client-key type, unknown type, empty GUID, and missing
terminator have independent loopback cases.

The host-side AOSP type check is in
[adb_wifi.cpp at the pinned AOSP revision](https://android.googlesource.com/platform/packages/modules/adb/+/1cf2f017d312f73b3dc53bda85ef2610e35a80e9/client/adb_wifi.cpp#243).
The size and type representation are defined by the
[pinned pairing_connection.h](https://android.googlesource.com/platform/packages/modules/adb/+/1cf2f017d312f73b3dc53bda85ef2610e35a80e9/pairing_connection/include/adb/pairing/pairing_connection.h#50).
The independent peer still verifies the TLS exporter label including its trailing NUL,
64-byte exporter length, ADB password binding, frame byte order, HKDF, and AES-GCM counters.

## Native error export and validation boundaries

The internal optional `NativeThrows` annotation maps to `kotlin.Throws` only for Native.
`pair` declares cancellation, I/O, identity-store and argument failures for NSError export.
It does not add checked IOException declarations to the existing Java API. Kotlin/Native
compilation, generated Swift declarations, and a linked Swift failure consumer must be
validated on the native CI path; JVM compilation alone is not that evidence.

The portable helper tests hold worker cleanup behind a condition and prove that cancellation
cannot complete the caller while the worker still owns its state. JVM and Android Host
regressions exercise TLS write poisoning, handshake cancellation, pending connection
cancellation, writer close races, and preserved timeout semantics. Platform-native execution,
real iPhone-to-adbd pairing, and broader forwarding worker ownership require their own records.

Coroutine behavior used here is documented in the official
[coroutineScope](https://kotlinlang.org/api/kotlinx.coroutines/kotlinx-coroutines-core/kotlinx.coroutines/coroutine-scope.html),
[ATOMIC start](https://kotlinlang.org/api/kotlinx.coroutines/kotlinx-coroutines-core/kotlinx.coroutines/-coroutine-start/-a-t-o-m-i-c/),
and [suspendCancellableCoroutine](https://kotlinlang.org/api/kotlinx.coroutines/kotlinx-coroutines-core/kotlinx.coroutines/suspend-cancellable-coroutine.html)
contracts. No unstructured background scope is introduced.
