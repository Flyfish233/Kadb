package com.flyfishxu.kadb

import com.flyfishxu.kadb.cert.InMemoryPrivateKeyStore
import com.flyfishxu.kadb.cert.KadbCert
import com.flyfishxu.kadb.core.AdbProtocol
import java.io.DataInputStream
import java.io.EOFException
import java.io.IOException
import java.net.InetAddress
import java.net.ServerSocket
import java.net.Socket
import java.nio.ByteBuffer
import java.nio.ByteOrder
import java.nio.file.Files
import java.util.concurrent.Executors
import java.util.concurrent.TimeUnit
import okio.Path.Companion.toOkioPath
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertFailsWith
import kotlin.test.assertFalse
import kotlin.test.assertTrue

/** A real ADB loopback peer removes an APK only after install-create has executed. */
class InstallSessionWireLifecycleTest {
    @Test fun execCmdWriteFailureAbandonsTheCreatedSession() = exercise("cmd", "exec:cmd", false)
    @Test fun abbExecWriteFailureAbandonsTheCreatedSession() = exercise("abb_exec,cmd", "abb_exec:", false)
    @Test fun legacyPushWriteFailureAbandonsTheCreatedSession() = exercise("", "shell:", false)
    @Test fun abandonFailureDoesNotReplaceTheOriginalFileFailure() = exercise("cmd", "exec:cmd", true)

    private fun exercise(features: String, servicePrefix: String, failAbandon: Boolean) {
        val directory = Files.createTempDirectory("kadb-install-session-")
        val apk = directory.resolve("base.apk")
        Files.write(apk, ByteArray(16))
        KadbCert.configure(InMemoryPrivateKeyStore())
        val executor = Executors.newSingleThreadExecutor()
        try {
            // Generate the test identity before starting the peer's accept timeout.
            KadbCert.ensureReady()
            ServerSocket(0, 1, InetAddress.getLoopbackAddress()).use { listener ->
                listener.soTimeout = 10000
                val peer = executor.submit<List<String>> {
                    val services = mutableListOf<String>()
                    listener.accept().use { socket ->
                        socket.soTimeout = 10000
                        assertEquals(AdbProtocol.CMD_CNXN, socket.readPacket().command)
                        socket.writePacket(AdbProtocol.CMD_CNXN, AdbProtocol.A_VERSION, 4096,
                            "device::features=$features;\u0000".encodeToByteArray())
                        val create = socket.readOpen()
                        services += create.payload.decodeToString().removeSuffix("\u0000")
                        assertTrue(services.last().startsWith(servicePrefix))
                        assertTrue(services.last().contains("install-create"))
                        // Metadata was already read to size install-create. This forces a
                        // deterministic local I/O failure in the subsequent APK write phase.
                        Files.delete(apk)
                        socket.respond(create, 7, "Success: created install session [42]\n")
                        val abandon = try { socket.readOpen() } catch (_: EOFException) { null }
                        if (abandon != null) {
                            services += abandon.payload.decodeToString().removeSuffix("\u0000")
                            assertTrue(services.last().startsWith(servicePrefix))
                            assertTrue(services.last().contains("install-abandon"))
                            assertTrue(services.last().contains("42"))
                            socket.respond(abandon, 8, if (failAbandon) "Failure [injected cleanup failure]\n" else "Success\n")
                            // Keep transport EOF distinct from the command stream's CLSE.
                            try { socket.readPacket() } catch (_: EOFException) { }
                        }
                    }
                    services
                }
                val client = Kadb.create("127.0.0.1", listener.localPort, connectTimeout = 10000, socketTimeout = 10000)
                val failure = try {
                    assertFailsWith<IOException> { client.installMultiple(listOf(apk.toOkioPath())) }
                } finally {
                    client.close()
                }
                val services = peer.get(15, TimeUnit.SECONDS)
                assertEquals(2, services.size, "A created session must receive install-abandon after local APK I/O fails")
                assertFalse(services.any { it.contains("install-commit") })
                if (failAbandon) {
                    assertEquals(1, failure.suppressedExceptions.size)
                    assertTrue(failure.suppressedExceptions.single().message.orEmpty().contains("injected cleanup failure"))
                } else {
                    assertTrue(failure.suppressedExceptions.isEmpty())
                }
            }
        } finally {
            executor.shutdownNow()
            assertTrue(executor.awaitTermination(5, TimeUnit.SECONDS), "ADB peer worker did not terminate")
            Files.deleteIfExists(apk)
            Files.deleteIfExists(directory)
            KadbCert.clear()
        }
    }

    private data class Packet(val command: Int, val arg0: Int, val arg1: Int, val payload: ByteArray)

    private fun Socket.readPacket(): Packet {
        val input = DataInputStream(getInputStream())
        val header = ByteBuffer.wrap(ByteArray(24).also(input::readFully)).order(ByteOrder.LITTLE_ENDIAN)
        val command = header.int
        val arg0 = header.int
        val arg1 = header.int
        val size = header.int
        require(size in 0..1024 * 1024)
        header.int // checksum; protocol version 0x01000001 does not require it.
        assertEquals(command.inv(), header.int)
        return Packet(command, arg0, arg1, ByteArray(size).also(input::readFully))
    }

    private fun Socket.readOpen(): Packet {
        while (true) {
            val packet = readPacket()
            if (packet.command == AdbProtocol.CMD_OPEN) return packet
            assertTrue(packet.command == AdbProtocol.CMD_CLSE || packet.command == AdbProtocol.CMD_OKAY)
        }
    }

    private fun Socket.respond(open: Packet, remoteId: Int, response: String) {
        writePacket(AdbProtocol.CMD_OKAY, remoteId, open.arg0)
        writePacket(AdbProtocol.CMD_WRTE, remoteId, open.arg0, response.encodeToByteArray())
        val acknowledged = readPacket()
        assertEquals(AdbProtocol.CMD_OKAY, acknowledged.command)
        assertEquals(open.arg0, acknowledged.arg0)
        assertEquals(remoteId, acknowledged.arg1)
        writePacket(AdbProtocol.CMD_CLSE, remoteId, open.arg0)
    }

    private fun Socket.writePacket(command: Int, arg0: Int, arg1: Int, payload: ByteArray = ByteArray(0)) {
        val header = ByteBuffer.allocate(24).order(ByteOrder.LITTLE_ENDIAN)
            .putInt(command).putInt(arg0).putInt(arg1).putInt(payload.size)
            .putInt(0).putInt(command.inv()).array()
        getOutputStream().apply { write(header); write(payload); flush() }
    }
}
