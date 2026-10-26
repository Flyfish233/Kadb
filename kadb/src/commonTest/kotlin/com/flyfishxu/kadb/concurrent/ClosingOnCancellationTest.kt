package com.flyfishxu.kadb.concurrent

import kotlinx.coroutines.CompletableDeferred
import kotlinx.coroutines.cancelAndJoin
import kotlinx.coroutines.launch
import kotlinx.coroutines.runBlocking
import kotlinx.coroutines.withTimeout
import okio.IOException
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertFailsWith
import kotlin.test.assertFalse
import kotlin.test.assertTrue

class ClosingOnCancellationTest {
    @Test fun cancellationClosesIoButWaitsForWorkerOwnedCleanup() = runBlocking {
        val entered = CompletableDeferred<Unit>()
        val cleanupStarted = CompletableDeferred<Unit>()
        val lock = BlockingLock()
        val condition = lock.newCondition()
        var closed = false
        var allowCleanup = false
        var cleanupFinished = false
        val close = { lock.withLock { closed = true; condition.signalAll() } }
        val work = launch {
            runClosingOnCancellation(close) {
                try {
                    entered.complete(Unit)
                    lock.withLock { while (!closed) condition.await() }
                    throw IOException("I/O interrupted by closing resource")
                } finally {
                    cleanupStarted.complete(Unit)
                    lock.withLock {
                        while (!allowCleanup) condition.await()
                        cleanupFinished = true
                    }
                }
            }
        }
        try {
            withTimeout(5000) { entered.await() }
            work.cancel()
            withTimeout(5000) { cleanupStarted.await() }
            assertTrue(lock.withLock { closed })
            assertFalse(work.isCompleted, "Caller completion must wait for worker cleanup")
            lock.withLock { allowCleanup = true; condition.signalAll() }
            withTimeout(5000) { work.join() }
            assertTrue(lock.withLock { cleanupFinished })
        } finally {
            close()
            lock.withLock { allowCleanup = true; condition.signalAll() }
            work.cancelAndJoin()
        }
    }

    @Test fun aFailingWorkerClosesItsResource() = runBlocking {
        val lock = BlockingLock()
        var closed = false
        val failure = assertFailsWith<IOException> {
            runClosingOnCancellation({ lock.withLock { closed = true } }) {
                throw IOException("failed connect")
            }
        }
        assertEquals("failed connect", failure.message)
        assertTrue(lock.withLock { closed })
    }

    @Test fun successPreservesCallerOwnership() = runBlocking {
        var closed = false
        assertEquals(42, runClosingOnCancellation({ closed = true }) { 42 })
        assertFalse(closed)
    }
}
