package com.flyfishxu.kadb.queue

import com.flyfishxu.kadb.concurrent.BlockingLock
import com.flyfishxu.kadb.concurrent.startKadbThread
import com.flyfishxu.kadb.concurrent.withLock
import com.flyfishxu.kadb.core.AdbMessage
import com.flyfishxu.kadb.core.AdbProtocol
import com.flyfishxu.kadb.core.AdbReader
import com.flyfishxu.kadb.core.AdbWriter
import com.flyfishxu.kadb.exception.AdbStreamClosed
import kotlinx.coroutines.CompletableDeferred
import kotlinx.coroutines.Deferred
import kotlinx.coroutines.runBlocking
import kotlinx.coroutines.withTimeout
import kotlinx.coroutines.withTimeoutOrNull
import okio.Buffer
import okio.IOException
import okio.Sink
import okio.Source
import okio.Timeout
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertFailsWith
import kotlin.test.assertTrue

/** Actual encoded frames exercise the shared queue on Android and Native. */
class AdbStreamIdentityTest {
    @Test fun zeroRemoteIdCannotEstablishAnOpen(): Unit = runBlocking {
        Fixture().use { f ->
            val local = f.queue.startOpening()
            f.writer.writeOkay(0, local)
            f.writer.writeOkay(41, local)
            assertEquals(41, f.take(local, AdbProtocol.CMD_OKAY).arg0,
                "OKAY with remote ID zero must not complete OPEN")
        }
    }

    @Test fun wrongRemoteIdCannotSupplyStreamData(): Unit = runBlocking {
        Fixture().use { f ->
            val local = f.open()
            f.write(43, local, "wrong")
            f.write(41, local, "right")
            assertEquals("right", f.take(local, AdbProtocol.CMD_WRTE).payload.decodeToString(),
                "WRTE from a different remote stream must be ignored")
        }
    }

    @Test fun wrongRemoteIdCannotSupplyAcknowledgement(): Unit = runBlocking {
        Fixture().use { f ->
            val local = f.open()
            f.writer.writeOkay(43, local)
            f.writer.writeOkay(41, local)
            assertEquals(41, f.take(local, AdbProtocol.CMD_OKAY).arg0,
                "An established stream must retain its first remote ID")
        }
    }

    @Test fun wrongRemoteCloseIsIgnoredButLegacyZeroCloseStillWorks(): Unit = runBlocking {
        Fixture().use { f ->
            val local = f.open()
            f.writer.writeClose(43, local)
            // A second OPEN/OKAY is a reader-dispatch barrier after the malformed CLSE.
            // Do not queue WRTE yet: the old queue returns queued data even after closing a stream.
            f.open()
            val reading = f.startTake(local, AdbProtocol.CMD_WRTE)
            val premature = withTimeoutOrNull(250) { runCatching { reading.await() } }
            assertEquals(null, premature,
                "CLSE from a different remote stream must leave this reader waiting")
            f.write(41, local, "alive")
            assertEquals("alive", withTimeout(5000) { reading.await() }.payload.decodeToString())
            // AOSP accepts CLSE(0, local) from the same transport for historical adbd versions.
            f.writer.writeClose(0, local)
            assertFailsWith<AdbStreamClosed> { f.take(local, AdbProtocol.CMD_WRTE) }
            assertTrue(f.queue.isOpen, "A stream close must preserve the connection")
        }
    }

    @Test fun dataBeforeFirstOkayCannotEnterTheStream(): Unit = runBlocking {
        Fixture().use { f ->
            val local = f.queue.startOpening()
            f.write(41, local, "early")
            f.writer.writeOkay(41, local)
            f.write(41, local, "ready")
            assertEquals(41, f.take(local, AdbProtocol.CMD_OKAY).arg0)
            assertTrue(f.queue.finishOpening(local))
            assertEquals("ready", f.take(local, AdbProtocol.CMD_WRTE).payload.decodeToString(),
                "WRTE must follow the OPEN/OKAY remote identity binding")
        }
    }

    private class Fixture : AutoCloseable {
        private val lock = BlockingLock()
        private val changed = lock.newCondition()
        private val bytes = Buffer()
        private var closed = false
        private val source = object : Source {
            override fun read(sink: Buffer, byteCount: Long): Long = lock.withLock {
                require(byteCount >= 0)
                if (byteCount == 0L) return 0L
                while (bytes.size == 0L && !closed) changed.await()
                if (bytes.size == 0L) -1L else bytes.read(sink, byteCount)
            }
            override fun timeout() = Timeout.NONE
            override fun close() = closePipe()
        }
        private val sink = object : Sink {
            override fun write(source: Buffer, byteCount: Long) = lock.withLock {
                if (closed) throw IOException("Test pipe closed")
                bytes.write(source, byteCount)
                changed.signalAll()
            }
            override fun flush() = Unit
            override fun timeout() = Timeout.NONE
            override fun close() = closePipe()
        }
        val writer = AdbWriter(sink)
        val queue = AdbMessageQueue(AdbReader(source)) { closePipe() }

        suspend fun open(): Int {
            val local = queue.startOpening()
            writer.writeOkay(41, local)
            assertEquals(41, take(local, AdbProtocol.CMD_OKAY).arg0)
            assertTrue(queue.finishOpening(local))
            return local
        }

        fun write(remote: Int, local: Int, value: String) {
            val payload = value.encodeToByteArray()
            writer.writeWrite(remote, local, payload, 0, payload.size)
        }

        suspend fun take(local: Int, command: Int): AdbMessage =
            withTimeout(5000) { startTake(local, command).await() }

        suspend fun startTake(local: Int, command: Int): Deferred<AdbMessage> {
            val result = CompletableDeferred<AdbMessage>()
            val entered = CompletableDeferred<Unit>()
            startKadbThread("kadb-stream-id-test") {
                entered.complete(Unit)
                try { result.complete(queue.take(local, command)) }
                catch (error: Throwable) { result.completeExceptionally(error) }
            }
            withTimeout(5000) { entered.await() }
            return result
        }

        override fun close() = queue.close()
        private fun closePipe() = lock.withLock {
            closed = true
            changed.signalAll()
        }
    }
}
