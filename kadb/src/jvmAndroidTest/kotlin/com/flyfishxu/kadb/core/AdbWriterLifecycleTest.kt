package com.flyfishxu.kadb.core

import java.util.concurrent.CountDownLatch
import java.util.concurrent.Executors
import java.util.concurrent.TimeUnit
import java.util.concurrent.atomic.AtomicBoolean
import java.util.concurrent.atomic.AtomicInteger
import okio.Buffer
import okio.IOException
import okio.Sink
import okio.Timeout
import kotlin.test.Test
import kotlin.test.assertFalse
import kotlin.test.assertNull
import kotlin.test.assertTrue

class AdbWriterLifecycleTest {
    @Test fun closeCannotFlushTheSameBufferWhileAWriteIsInFlight() {
        val inWrite = AtomicInteger()
        val overlappingAccess = AtomicBoolean()
        val entered = CountDownLatch(1)
        val overlap = CountDownLatch(1)
        val release = CountDownLatch(1)
        val closeStarted = CountDownLatch(1)
        val writer = AdbWriter(object : Sink {
            override fun write(source: Buffer, byteCount: Long) {
                if (inWrite.incrementAndGet() != 1) {
                    inWrite.decrementAndGet()
                    overlappingAccess.set(true)
                    overlap.countDown()
                    throw IOException("Concurrent access to buffered write")
                }
                try {
                    entered.countDown()
                    assertTrue(release.await(5, TimeUnit.SECONDS))
                    source.skip(byteCount)
                } finally {
                    inWrite.decrementAndGet()
                }
            }
            override fun close() {
                if (inWrite.get() != 0) overlappingAccess.set(true)
            }
            override fun flush() = Unit
            override fun timeout() = Timeout.NONE
        })
        val executor = Executors.newFixedThreadPool(2)
        try {
            val write = executor.submit<Throwable?> {
                runCatching { writer.writeConnect("host::features=;\u0000".encodeToByteArray()) }.exceptionOrNull()
            }
            assertTrue(entered.await(5, TimeUnit.SECONDS))
            val close = executor.submit<Throwable?> {
                closeStarted.countDown()
                runCatching { writer.close() }.exceptionOrNull()
            }
            assertTrue(closeStarted.await(5, TimeUnit.SECONDS))
            // On the baseline close() re-enters Sink.write while the first flush is held here.
            overlap.await(2, TimeUnit.SECONDS)
            release.countDown()
            assertNull(write.get(5, TimeUnit.SECONDS))
            assertNull(close.get(5, TimeUnit.SECONDS))
            assertFalse(overlappingAccess.get(), "Close must not concurrently flush/mutate the writer's buffer")
        } finally {
            release.countDown()
            executor.shutdownNow()
            assertTrue(executor.awaitTermination(5, TimeUnit.SECONDS))
            writer.close()
        }
    }
}
