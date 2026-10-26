package com.flyfishxu.kadb.core

import com.flyfishxu.kadb.concurrent.BlockingLock
import com.flyfishxu.kadb.concurrent.startKadbThread
import com.flyfishxu.kadb.concurrent.withLock
import com.flyfishxu.kadb.queue.AdbMessageQueue
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.CompletableDeferred
import kotlinx.coroutines.Deferred
import kotlinx.coroutines.Job
import kotlinx.coroutines.runBlocking
import kotlinx.coroutines.withTimeout
import okio.Buffer
import okio.Closeable
import okio.IOException
import okio.Sink
import okio.Source
import okio.Timeout
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertFailsWith
import kotlin.test.assertFalse
import kotlin.test.assertNotEquals
import kotlin.test.assertTrue

/** Runs the same wire-state cancellation assertions on Android/JVM and Kotlin/Native. */
class AdbOpenCancellationTest {
    @Test fun cancelledOpenReclaimsLateOkayAndPreservesAnotherStream(): Unit = runBlocking {
        Fixture().use { f ->
            val lifetime = Job()
            val pending = worker { f.connection.open("tcp:5555", lifetime) }
            val request = worker { f.peerReader.readMessage() }.awaitBounded()
            assertEquals(AdbProtocol.CMD_OPEN, request.command)
            lifetime.cancel()
            assertFailsWith<CancellationException> { pending.awaitBounded() }
            assertTrue(f.connection.isOpen)

            f.peerWriter.writeOkay(41, request.arg0)
            val reclaim = worker { f.peerReader.readMessage() }.awaitBounded()
            assertEquals(AdbProtocol.CMD_CLSE, reclaim.command)
            assertEquals(request.arg0, reclaim.arg0)
            assertEquals(41, reclaim.arg1)

            val next = worker { f.connection.open("shell:still-alive") }
            val nextRequest = worker { f.peerReader.readMessage() }.awaitBounded()
            assertEquals(AdbProtocol.CMD_OPEN, nextRequest.command)
            assertNotEquals(request.arg0, nextRequest.arg0)
            f.peerWriter.writeOkay(42, nextRequest.arg0)
            next.awaitBounded().close()
            val closed = worker { f.peerReader.readMessage() }.awaitBounded()
            assertEquals(AdbProtocol.CMD_CLSE, closed.command)
            assertEquals(42, closed.arg1)
            f.connection.ensureEmpty()
        }
    }

    @Test fun cancellationBeforeOpenWritesNoRequest() {
        Fixture().use { f ->
            val lifetime = Job().also { it.cancel() }
            assertFailsWith<CancellationException> { f.connection.open("tcp:5555", lifetime) }
            assertEquals(0L, f.fromHost.size)
            f.connection.ensureEmpty()
        }
    }

    @Test fun cancellingOneOpenKeepsAnAlreadyEstablishedStreamUsable(): Unit = runBlocking {
        Fixture().use { f ->
            val existing = worker { f.connection.open("shell:live") }
            val established = worker { f.peerReader.readMessage() }.awaitBounded()
            f.peerWriter.writeOkay(81, established.arg0)
            val stream = existing.awaitBounded()
            val response = worker { stream.source.readUtf8() }

            val lifetime = Job()
            val abandoned = worker { f.connection.open("tcp:5555", lifetime) }
            val pending = worker { f.peerReader.readMessage() }.awaitBounded()
            assertNotEquals(established.arg0, pending.arg0)
            lifetime.cancel()
            assertFailsWith<CancellationException> { abandoned.awaitBounded() }

            f.peerWriter.writeWrite(81, established.arg0, "alive".encodeToByteArray(), 0, 5)
            f.peerWriter.writeClose(81, established.arg0)
            assertEquals("alive", response.awaitBounded())
            assertTrue(f.connection.isOpen)
            f.connection.ensureEmpty()
        }
    }

    @Test fun queuedOkayRetainsItsRemoteIdUntilTheOpenOwnerCleansUp(): Unit = runBlocking {
        val pipe = BytePipe()
        val queue = AdbMessageQueue(AdbReader(pipe.source)) { pipe.close() }
        try {
            val local = queue.startOpening()
            AdbWriter(pipe.sink).writeOkay(61, local)
            val okay = worker { queue.take(local, AdbProtocol.CMD_OKAY) }.awaitBounded()
            assertEquals(61, okay.arg0)
            // Cancel precisely after the reader supplied OKAY and before ownership transfers.
            queue.cancelOpening(local)
            assertFalse(queue.finishOpening(local))
            assertEquals(61, queue.abandonOpening(local))
            queue.ensureEmpty()
        } finally {
            queue.close()
        }
    }

    @Test fun remoteCloseFollowingOkayDoesNotDiscardAlreadyQueuedData(): Unit = runBlocking {
        Fixture().use { f ->
            val pending = worker { f.connection.open("shell:quick") }
            val request = worker { f.peerReader.readMessage() }.awaitBounded()
            f.peerWriter.writeOkay(71, request.arg0)
            f.peerWriter.writeWrite(71, request.arg0, "ok".encodeToByteArray(), 0, 2)
            f.peerWriter.writeClose(71, request.arg0)
            val stream = pending.awaitBounded()
            assertEquals("ok", worker { stream.source.readUtf8() }.awaitBounded())
            f.connection.ensureEmpty()
        }
    }

    private fun <T> worker(block: () -> T): Deferred<T> {
        val result = CompletableDeferred<T>()
        startKadbThread("kadb-open-test") {
            try {
                result.complete(block())
            } catch (failure: Throwable) {
                result.completeExceptionally(failure)
            }
        }
        return result
    }

    private suspend fun <T> Deferred<T>.awaitBounded(): T = withTimeout(5000) { await() }

    private class Fixture : AutoCloseable {
        private val toHost = BytePipe()
        val fromHost = BytePipe()
        val peerReader = AdbReader(fromHost.source)
        val peerWriter = AdbWriter(toHost.sink)
        val connection = AdbConnection(AdbReader(toHost.source), AdbWriter(fromHost.sink),
            object : Closeable { override fun close() { toHost.close(); fromHost.close() } },
            emptySet(), AdbProtocol.A_VERSION, 4096)

        override fun close() = connection.close()
    }

    /** Test-only blocking duplex building block; platform transports are tested separately. */
    private class BytePipe : AutoCloseable {
        private val lock = BlockingLock()
        private val changed = lock.newCondition()
        private val bytes = Buffer()
        private var closed = false
        val size: Long get() = lock.withLock { bytes.size }
        val source = object : Source {
            override fun read(sink: Buffer, byteCount: Long): Long = lock.withLock {
                require(byteCount >= 0)
                if (byteCount == 0L) return 0L
                while (bytes.size == 0L && !closed) changed.await()
                if (bytes.size == 0L) -1L else bytes.read(sink, byteCount)
            }
            override fun close() = this@BytePipe.close()
            override fun timeout() = Timeout.NONE
        }
        val sink = object : Sink {
            override fun write(source: Buffer, byteCount: Long) = lock.withLock {
                if (closed) throw IOException("Test pipe closed")
                bytes.write(source, byteCount)
                changed.signalAll()
            }
            override fun flush() = Unit
            override fun close() = this@BytePipe.close()
            override fun timeout() = Timeout.NONE
        }
        override fun close() = lock.withLock {
            closed = true
            changed.signalAll()
        }
    }
}
