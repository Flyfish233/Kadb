@file:OptIn(kotlinx.cinterop.ExperimentalForeignApi::class)

package com.flyfishxu.kadb.transport

import com.flyfishxu.kadb.concurrent.startKadbThread
import kotlinx.cinterop.*
import kotlinx.coroutines.CompletableDeferred
import kotlinx.coroutines.runBlocking
import kotlinx.coroutines.withTimeout
import okio.IOException
import platform.posix.*
import kotlin.test.*

class PosixTransportLifecycleTest {
    @Test fun plaintextRoundTripAndRepeatedClose() = memScoped {
        val descriptors = allocArray<IntVar>(2)
        assertEquals(0, socketpair(AF_UNIX, SOCK_STREAM, 0, descriptors))
        val first = PosixTransportChannel(descriptors[0])
        val second = PosixTransportChannel(descriptors[1])
        try {
            val request = "CNXN".encodeToByteArray()
            first.write(request, 0, request.size, 1000)
            val actual = ByteArray(4)
            assertEquals(4, second.read(actual, 0, actual.size, 1000))
            assertContentEquals(request, actual)
            second.write(actual, 0, actual.size, 1000)
            assertEquals(4, first.read(actual, 0, actual.size, 1000))
            assertContentEquals(request, actual)
            first.close()
            first.close()
            assertFalse(first.isOpen)
            assertFailsWith<IOException> { first.write(request, 0, request.size, 1000) }
        } finally {
            first.close()
            second.close()
        }
    }

    @Test fun closeWakesBlockingReadAndWorkerTerminates() = runBlocking {
        memScoped {
            val descriptors = allocArray<IntVar>(2)
            assertEquals(0, socketpair(AF_UNIX, SOCK_STREAM, 0, descriptors))
            val channel = PosixTransportChannel(descriptors[0])
            val entered = CompletableDeferred<Unit>()
            val result = CompletableDeferred<Throwable?>()
            try {
                startKadbThread("kadb-close-test") {
                    entered.complete(Unit)
                    val failure = try {
                        channel.read(ByteArray(1), 0, 1, 0)
                        null
                    } catch (failure: Throwable) {
                        failure
                    }
                    result.complete(failure)
                }
                withTimeout(5000) { entered.await() }
                channel.close()
                val failure = withTimeout(5000) { result.await() }
                assertIs<IOException>(failure)
                assertFalse(channel.isOpen)
            } finally {
                channel.close()
                close(descriptors[1])
            }
        }
    }

    @Test fun failedWriteIsTerminal() = memScoped {
        val descriptors = allocArray<IntVar>(2)
        assertEquals(0, socketpair(AF_UNIX, SOCK_STREAM, 0, descriptors))
        val channel = PosixTransportChannel(descriptors[0])
        close(descriptors[1])
        try {
            assertFailsWith<IOException> { channel.write(ByteArray(16), 0, 16, 1000) }
            assertFalse(channel.isOpen)
            assertFailsWith<IOException> { channel.write(ByteArray(1), 0, 1, 1000) }
        } finally {
            channel.close()
        }
    }
}
