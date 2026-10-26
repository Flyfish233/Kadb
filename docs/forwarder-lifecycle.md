# Forwarding sessions and cancelled OPEN

## Ownership

A platform TCP forwarder owns its listening socket and the set of accepted local
sockets. Each accepted socket now has one common `ForwardingSession`, which owns
its ADB open lifetime, upload worker and download worker. Closing the listener
first prevents new sessions; closing the captured sessions closes their local
sockets and cancels their private `Job` lifetimes. The listener then waits for its
accept loop and both workers of every captured session to finish. The private Job
is a cancellation signal, not a coroutine dispatcher or a shared connection job.

The JVM/Android and POSIX implementations retain their own socket/listen/accept
operations. The shared class performs the two data pumps, stream acquisition,
cleanup and worker completion tracking. No POSIX or JVM socket type is introduced
into commonMain.

## Connection waiting

The public `Kadb.open` API remains synchronous. An ordinary first caller still
performs `runBlocking` connection establishment on its calling thread, preserving
its interruption and connector-timeout exception behavior. Concurrent callers
share one connection attempt and wait on a common condition.

An internally cancellable forwarder which initiates connection establishment
uses a Kadb-owned worker. Cancelling this forwarder's lifetime wakes only its own
connection waiter. Other callers can still receive the original connection when
CNXN completes. Kadb close/reset cancels the connection's own job and closes its
pending transport, retaining the generation check which prevents resurrection.
If the forwarder was the only waiter, the pending connection still belongs to
Kadb; it ends on connection timeout/failure or Kadb close/reset. It is not counted
as a forwarder worker.

## Pending OPEN and late OKAY

The queue retains a pending OPEN's received remote ID until the caller transfers
ownership to `AdbStream` or abandons the request. Cancelling a pending OPEN removes
only that local queue and wakes its waiter. If OKAY was already received, the
caller sends CLSE using the retained remote ID. If OKAY arrives after removal,
the transport reader sends CLSE for the now unknown local stream. No OPEN is
replayed, and cancelling a stream does not invalidate the shared transport.

This matches the AOSP host's explicit handling of a client disconnect between
OPEN and OKAY:
[adb.cpp, fixed revision 1cf2f017](https://android.googlesource.com/platform/packages/modules/adb/+/1cf2f017d312f73b3dc53bda85ef2610e35a80e9/adb.cpp#590).

Local IDs are allocated monotonically and never reused within a connection.
Consequently a delayed reply cannot be mistaken for a later request, and there
is no unbounded collection of cancellation tombstones. Exhausting the nonzero
32-bit ID space rejects a new OPEN and asks the caller to reset the connection;
existing streams remain unaffected. The allocation and queue registration share
one lock.

A CLSE immediately following OKAY does not erase already queued output. The
handoff checks that the queue still exists, rather than requiring the remote
stream still be open. This preserves a fast shell/service's final output.

## Scope and limits

The tests distinguish waiting for a connection, waiting for OKAY, late-OKAY wire
cleanup, and closing the two established forwarding directions. Common protocol
tests execute the same state machine with a blocking byte-pipe fixture; socket
integration tests exercise the JVM/Android TCP implementations separately.

Cancellation cannot safely interrupt a partially transmitted frame on a shared
transport while promising the other streams survive. A write of OPEN, WRTE or
CLSE which is blocked in the transport is still governed by the configured I/O
timeout; with an explicitly unbounded timeout, shutdown may wait for that write.
Closing the whole shared Kadb to make a forwarding deadline appear successful is
not used. A failed or timed-out TLS write remains terminal under the M1 transport
fixes. This change does not claim bounded shutdown for an indefinitely blocked
transport write, or native socket verification from JVM-only results.

Raw baseline evidence, exact runner commands and separately recorded green
results are in [validation/forwarder](../validation/forwarder/README.md).
