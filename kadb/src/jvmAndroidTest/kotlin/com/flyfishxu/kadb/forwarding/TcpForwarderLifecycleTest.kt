package com.flyfishxu.kadb.forwarding

import com.flyfishxu.kadb.Kadb
import com.flyfishxu.kadb.cert.InMemoryPrivateKeyStore
import com.flyfishxu.kadb.cert.KadbCert
import java.io.DataInputStream
import java.net.InetAddress
import java.net.ServerSocket
import java.net.Socket
import java.net.SocketTimeoutException
import java.nio.ByteBuffer
import java.nio.ByteOrder
import java.util.concurrent.Executors
import java.util.concurrent.Future
import java.util.concurrent.TimeUnit.SECONDS
import java.util.concurrent.TimeoutException
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertFailsWith
import kotlin.test.assertNotNull
import kotlin.test.assertTrue

/** Loopback peer deliberately withholds replies; close must not require peer cooperation. */
class TcpForwarderLifecycleTest {
    @Test fun closeCancelsPendingOpenWithoutClosingTheSharedConnection(): Unit = Fixture().use { f ->
        val peer = f.acceptPeer()
        peer.connectReply()
        assertEquals("OPEN", peer.readFrame().command)

        val close = f.workers.submit { f.forwarder.close() }
        assertTrue(close.completesWithin(2), "Forwarder close must release its pending OPEN worker without an OKAY reply")
        assertEquals(-1, f.local.getInputStream().read(), "Forwarder close must close its accepted local socket")
        assertTrue(f.client.connectionCheck(), "Cancelling one forwarded OPEN must preserve the shared ADB connection")
    }

    @Test fun lateOkayIsClosedAndAnotherStreamCanUseTheSameConnection(): Unit = Fixture().use { f ->
        val peer = f.acceptPeer()
        peer.connectReply()
        val abandoned = peer.readFrame()
        assertEquals("OPEN", abandoned.command)

        // Give the defective baseline's five-second executor timeout time to return. This test
        // independently checks wire cleanup, rather than failing only on the close deadline.
        val close = f.workers.submit { f.forwarder.close() }
        assertTrue(close.completesWithin(7), "Forwarder close did not return")
        peer.send("OKAY", 41, abandoned.arg0)
        val reclaimed = runCatching { peer.readFrame() }.getOrNull()
        assertNotNull(reclaimed, "A late OKAY for a cancelled OPEN must receive CLSE")
        assertEquals("CLSE", reclaimed.command)
        assertEquals(abandoned.arg0, reclaimed.arg0)
        assertEquals(41, reclaimed.arg1)
        peer.send("CLSE", 41, abandoned.arg0)

        val next = f.workers.submit { f.client.open("shell:echo still-alive").close() }
        val open = peer.readFrame()
        assertEquals("OPEN", open.command)
        assertEquals("shell:echo still-alive\u0000", open.payload.decodeToString())
        peer.send("OKAY", 42, open.arg0)
        assertEquals("CLSE", peer.readFrame().command)
        next.get(3, SECONDS)
        assertTrue(f.client.connectionCheck())
        f.adbServer.soTimeout = 150
        assertFailsWith<SocketTimeoutException> { f.adbServer.accept().use { error("Unexpected replacement connection") } }
    }

    @Test fun closeDuringInitialHandshakeDetachesOnlyTheForwarderWaiter(): Unit = Fixture().use { f ->
        val peer = f.acceptPeer()
        val sharedWaiter = f.workers.submit<Boolean> { f.client.supportsFeature("shell_v2") }
        val close = f.workers.submit { f.forwarder.close() }
        assertTrue(close.completesWithin(2), "Forwarder close must not wait for a shared connection's CNXN handshake")
        assertEquals(-1, f.local.getInputStream().read())
        peer.connectReply()
        assertTrue(sharedWaiter.get(3, SECONDS), "Another caller must still receive the shared connection")
        assertTrue(f.client.connectionCheck())
        peer.socket.soTimeout = 150
        assertFailsWith<SocketTimeoutException> { peer.readFrame() }
    }

    @Test fun closeStopsBothIdleForwardingDirections(): Unit = Fixture().use { f ->
        val peer = f.acceptPeer()
        peer.connectReply()
        val open = peer.readFrame()
        assertEquals("OPEN", open.command)
        peer.send("OKAY", 51, open.arg0)
        // An upload and its ACK prove that the OPEN completed and the upload worker is running.
        f.local.getOutputStream().apply { write(7); flush() }
        val write = peer.readFrame()
        assertEquals("WRTE", write.command)
        assertEquals(7, write.payload.single().toInt())
        peer.send("OKAY", 51, open.arg0)

        val close = f.workers.submit { f.forwarder.close() }
        assertTrue(close.completesWithin(2), "Forwarder close must join its upload and download workers while both are idle")
        assertEquals(-1, f.local.getInputStream().read())
        val end = peer.readFrame()
        assertEquals("CLSE", end.command)
        assertEquals(open.arg0, end.arg0)
        assertEquals(51, end.arg1)
        assertTrue(f.client.connectionCheck())
    }

    private fun Future<*>.completesWithin(seconds: Long): Boolean = try {
        get(seconds, SECONDS)
        true
    } catch (_: TimeoutException) {
        false
    }

    private class Fixture : AutoCloseable {
        val workers = Executors.newFixedThreadPool(3)
        val adbServer = ServerSocket(0, 8, InetAddress.getLoopbackAddress()).apply { soTimeout = 5000 }
        val client: Kadb
        val forwarder: AutoCloseable
        val local: Socket
        private var peer: Peer? = null

        init {
            KadbCert.configure(InMemoryPrivateKeyStore())
            KadbCert.ensureReady()
            client = Kadb.create("127.0.0.1", adbServer.localPort, connectTimeout = 2000, socketTimeout = 0)
            val localPort = ServerSocket(0, 1, InetAddress.getLoopbackAddress()).use { it.localPort }
            forwarder = client.tcpForward(localPort, 5555)
            local = Socket("127.0.0.1", localPort).apply { soTimeout = 2000 }
        }

        fun acceptPeer(): Peer = Peer(adbServer.accept()).also {
            peer = it
            assertEquals("CNXN", it.readFrame().command)
        }

        override fun close() {
            // Also wakes the intentionally defective baseline's blocked OPEN/handshake worker.
            runCatching { client.close() }
            runCatching { local.close() }
            runCatching { peer?.socket?.close() }
            runCatching { forwarder.close() }
            adbServer.close()
            workers.shutdownNow()
            assertTrue(workers.awaitTermination(8, SECONDS), "Test fixture workers did not terminate")
        }
    }

    private class Peer(val socket: Socket) {
        init { socket.soTimeout = 2000 }
        private val input = DataInputStream(socket.getInputStream())

        fun connectReply() = send("CNXN", 0x01000001, 4096, "device::features=shell_v2;\u0000".encodeToByteArray())

        fun readFrame(): Frame {
            val header = ByteArray(24).also(input::readFully)
            val fields = ByteBuffer.wrap(header).order(ByteOrder.LITTLE_ENDIAN)
            val size = fields.getInt(12)
            check(size in 0..(1024 * 1024))
            return Frame(String(header, 0, 4, Charsets.US_ASCII), fields.getInt(4), fields.getInt(8),
                ByteArray(size).also(input::readFully))
        }

        fun send(command: String, arg0: Int, arg1: Int, payload: ByteArray = byteArrayOf()) {
            val commandId = ByteBuffer.wrap(command.encodeToByteArray()).order(ByteOrder.LITTLE_ENDIAN).int
            val header = ByteBuffer.allocate(24).order(ByteOrder.LITTLE_ENDIAN)
                .putInt(commandId).putInt(arg0).putInt(arg1).putInt(payload.size)
                .putInt(0).putInt(commandId.inv()).array()
            socket.getOutputStream().apply { write(header); write(payload); flush() }
        }
    }

    private data class Frame(val command: String, val arg0: Int, val arg1: Int, val payload: ByteArray)
}
