package com.flyfishxu.kadb.stream

import com.flyfishxu.kadb.concurrent.BlockingLock
import com.flyfishxu.kadb.concurrent.withLock
import com.flyfishxu.kadb.core.AdbProtocol
import com.flyfishxu.kadb.core.AdbReader
import com.flyfishxu.kadb.core.AdbWriter
import com.flyfishxu.kadb.queue.AdbMessageQueue
import okio.Buffer
import okio.IOException
import okio.Sink
import okio.Source
import okio.Timeout
import kotlin.test.Test
import kotlin.test.assertContentEquals
import kotlin.test.assertEquals
import kotlin.test.assertFailsWith
import kotlin.test.assertSame
import kotlin.test.assertTrue

/** Exercises the real Sync/ADB stream and message queue with controlled transport failures. */
class AdbSyncCloseLifecycleTest {
    @Test fun quitWriteFailureStillRemovesTheStreamListener() {
        val original = IOException("QUIT write failed")
        Fixture(quitFailure = original).use { fixture ->
            assertSame(original, assertFailsWith<IOException> { fixture.sync.close() })
            fixture.queue.ensureEmpty()
            assertTrue(fixture.queue.isOpen, "Closing one Sync stream must not close the shared queue")
        }
    }

    @Test fun quitAndCloseFailuresKeepTheOriginalAndSuppressCleanup() {
        val original = IOException("QUIT write failed")
        val cleanup = IOException("CLSE write failed")
        Fixture(quitFailure = original, closeFailure = cleanup).use { fixture ->
            val observed = assertFailsWith<IOException> { fixture.sync.close() }
            assertSame(original, observed)
            assertEquals(listOf(cleanup), observed.suppressedExceptions)
            fixture.queue.ensureEmpty()
        }
    }

    @Test fun identicalQuitAndCloseFailureCannotCauseSelfSuppression() {
        val original = IOException("same failed transport")
        Fixture(quitFailure = original, closeFailure = original).use { fixture ->
            val observed = assertFailsWith<IOException> { fixture.sync.close() }
            assertSame(original, observed)
            assertTrue(observed.suppressedExceptions.isEmpty())
            fixture.queue.ensureEmpty()
        }
    }

    @Test fun successfulClosePreservesQuitThenClseWireSequence() {
        Fixture().use { fixture ->
            fixture.sync.close()
            fixture.queue.ensureEmpty()
            val bytes = Buffer().apply { fixture.writes.forEach(::write) }
            val reader = AdbReader(bytes)
            val quit = reader.readMessage()
            assertEquals(AdbProtocol.CMD_WRTE, quit.command)
            assertEquals(1, quit.arg0)
            assertEquals(10, quit.arg1)
            assertContentEquals(Buffer().writeUtf8("QUIT").writeIntLe(0).readByteArray(), quit.payload)
            val close = reader.readMessage()
            assertEquals(AdbProtocol.CMD_CLSE, close.command)
            assertEquals(1, close.arg0)
            assertEquals(10, close.arg1)
            assertEquals(0, close.payloadLength)
            assertTrue(bytes.exhausted())
            assertTrue(fixture.queue.isOpen)
        }
    }

    @Test fun clseFailureAfterSuccessfulQuitStillRemovesTheListener() {
        val cleanup = IOException("CLSE write failed")
        Fixture(closeFailure = cleanup).use { fixture ->
            val observed = assertFailsWith<IOException> { fixture.sync.close() }
            assertSame(cleanup, observed)
            assertTrue(observed.suppressedExceptions.isEmpty())
            fixture.queue.ensureEmpty()
        }
    }

    private class Fixture(
        quitFailure: IOException? = null,
        closeFailure: IOException? = null,
    ) : AutoCloseable {
        private val input = BlockingSource()
        val writes = mutableListOf<ByteArray>()
        val queue = AdbMessageQueue(AdbReader(input), closeTransport = input::cancel)
        private val output = object : Sink {
            override fun write(source: Buffer, byteCount: Long) {
                writes += source.readByteArray(byteCount)
                // A write may consume bytes before reporting failure. The close tests must
                // still release their local listener and preserve the first exception.
                when (writes.size) {
                    1 -> {
                        if (quitFailure != null) throw quitFailure
                        val reply = Buffer()
                        AdbWriter(reply).writeOkay(10, 1)
                        input.offer(reply.readByteArray())
                    }
                    2 -> if (closeFailure != null) throw closeFailure
                    else -> error("Unexpected extra transport write")
                }
            }
            override fun flush() = Unit
            override fun timeout() = Timeout.NONE
            override fun close() = Unit
        }
        private val stream = AdbStream(queue, AdbWriter(output), 4096, 1, 10)
        val sync = AdbSyncStream(stream)

        init { queue.startListening(1, remoteId = 10) }

        override fun close() {
            // Also clean up the defective baseline after its assertion has observed the leak.
            runCatching { stream.close() }
            queue.close()
            input.awaitReaderStopped()
        }
    }

    private class BlockingSource : Source {
        private val lock = BlockingLock()
        private val changed = lock.newCondition()
        private val bytes = Buffer()
        private var cancelled = false
        private var readerStopped = false

        fun offer(value: ByteArray) = lock.withLock {
            bytes.write(value)
            changed.signalAll()
        }

        override fun read(sink: Buffer, byteCount: Long): Long = lock.withLock {
            if (byteCount == 0L) return 0L
            while (!cancelled && bytes.size == 0L) changed.await()
            if (cancelled) -1L else bytes.read(sink, byteCount)
        }

        fun cancel() = lock.withLock {
            cancelled = true
            changed.signalAll()
        }

        override fun close() = lock.withLock {
            cancelled = true
            readerStopped = true
            changed.signalAll()
        }

        fun awaitReaderStopped() = lock.withLock {
            while (!readerStopped) changed.await()
        }

        override fun timeout() = Timeout.NONE
    }
}
