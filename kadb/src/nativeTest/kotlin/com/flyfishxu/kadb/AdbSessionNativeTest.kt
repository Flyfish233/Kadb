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
                    completed.complete(Unit)
                } catch (failure: Throwable) {
                    completed.completeExceptionally(failure)
                } finally {
                    close(listener)
                }
            }
            try {
                Kadb.create("127.0.0.1", port, connectTimeout = 3000, socketTimeout = 3000).use { client ->
                    assertEquals(output.decodeToString(), client.shell("echo test").output)
                    assertTrue(client.connectionCheck())
                }
                withTimeout(5000) { completed.await() }
            } finally {
                // The accepting worker owns close; only wake it here, avoiding fd reuse.
                if (!completed.isCompleted) shutdown(listener, SHUT_RDWR)
            }
        }
    }
}
