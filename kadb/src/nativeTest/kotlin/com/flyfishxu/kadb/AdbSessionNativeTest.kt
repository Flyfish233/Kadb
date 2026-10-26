@file:OptIn(kotlinx.cinterop.ExperimentalForeignApi::class)

package com.flyfishxu.kadb

import com.flyfishxu.kadb.concurrent.startKadbThread
import com.flyfishxu.kadb.core.AdbProtocol
import com.flyfishxu.kadb.core.AdbReader
import com.flyfishxu.kadb.core.AdbWriter
import com.flyfishxu.kadb.nativebridge.kadb_create_listener
import com.flyfishxu.kadb.transport.PosixTransportChannel
import com.flyfishxu.kadb.transport.asOkioSink
import com.flyfishxu.kadb.transport.asOkioSource
import kotlinx.cinterop.*
import kotlinx.coroutines.CompletableDeferred
import kotlinx.coroutines.runBlocking
import kotlinx.coroutines.withTimeout
import okio.use
import platform.posix.*
import kotlin.test.*

class AdbSessionNativeTest {
    @Test fun commonShellRunsThroughNativeSocketAndClosesCleanly() = runBlocking {
        memScoped {
            val error = allocArray<ByteVar>(512)
            val listener = kadb_create_listener(0, error, 512.convert())
            assertTrue(listener >= 0, if (listener < 0) error.toKString() else "")
            val address = alloc<sockaddr_storage>()
            val length = alloc<socklen_tVar> { value = sizeOf<sockaddr_storage>().convert() }
            assertEquals(0, getsockname(listener, address.ptr.reinterpret(), length.ptr))
            val service = allocArray<ByteVar>(6)
            assertEquals(0, getnameinfo(address.ptr.reinterpret(), length.value,
                null, 0.convert(), service, 6.convert(), NI_NUMERICSERV))
            val port = service.toKString().toInt()
            val completed = CompletableDeferred<Unit>()
            val output = "你好 from Native\n".encodeToByteArray()
            startKadbThread("kadb-native-peer") {
                var failure: Throwable? = null
                try {
                    memScoped {
                        val ready = alloc<pollfd> { fd = listener; events = POLLIN.toShort() }
                        assertEquals(1, poll(ready.ptr, 1.convert(), 5000))
                    }
                    val fd = accept(listener, null, null)
                    check(fd >= 0)
                    PosixTransportChannel(fd).use { channel ->
                        val reader = AdbReader(channel.asOkioSource(3000))
                        val writer = AdbWriter(channel.asOkioSink(3000))
                        assertEquals(AdbProtocol.CMD_CNXN, reader.readMessage().command)
                        val banner = "device::features=\u0000".encodeToByteArray()
                        writer.write(AdbProtocol.CMD_CNXN, AdbProtocol.A_VERSION, 4096, banner, 0, banner.size)
                        val open = reader.readMessage()
                        assertEquals(AdbProtocol.CMD_OPEN, open.command)
                        assertEquals("shell:echo test\u0000", open.payload.decodeToString())
                        writer.writeOkay(7, open.arg0)
                        writer.writeWrite(7, open.arg0, output, 0, output.size)
                        assertEquals(AdbProtocol.CMD_OKAY, reader.readMessage().command)
                        writer.writeClose(7, open.arg0)
                        // A closed service does not itself end the shared ADB transport.
                        runCatching { reader.readMessage() }
                    }
                } catch (error: Throwable) {
                    failure = error
                } finally {
                    close(listener)
                }
                // Completion is published only after the peer's descriptors close.
                val terminal = failure
                if (terminal == null) completed.complete(Unit) else completed.completeExceptionally(terminal)
            }
            try {
                Kadb.create("127.0.0.1", port, connectTimeout = 3000, socketTimeout = 3000).use { client ->
                    assertEquals(output.decodeToString(), client.shell("echo test").output)
                    assertTrue(client.connectionCheck())
                }
            } finally {
                // poll and socket reads have bounded waits. Only the peer closes its
                // listener, and the test waits for cleanup even when the client fails.
                withTimeout(10000) { completed.await() }
            }
        }
    }
}
