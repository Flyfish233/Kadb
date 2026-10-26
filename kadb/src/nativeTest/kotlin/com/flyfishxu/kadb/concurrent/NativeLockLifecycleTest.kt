package com.flyfishxu.kadb.concurrent

import kotlinx.coroutines.CompletableDeferred
import kotlinx.coroutines.runBlocking
import kotlinx.coroutines.withTimeout
import kotlin.test.Test
import kotlin.test.assertNull

class NativeLockLifecycleTest {
    @Test fun conditionRestoresRecursionAndWorkerExits() = runBlocking {
        val lock = BlockingLock()
        val condition = lock.newCondition()
        val waiting = CompletableDeferred<Unit>()
        val completed = CompletableDeferred<Throwable?>()
        var signalled = false
        startKadbThread("kadb-native-condition") {
            var failure: Throwable? = null
            try {
                lock.lock()
                lock.lock()
                try {
                    waiting.complete(Unit)
                    while (!signalled) condition.await()
                    lock.unlock()
                    condition.signalAll()
                } finally {
                    lock.unlock()
                }
            } catch (error: Throwable) {
                failure = error
            } finally {
                completed.complete(failure)
            }
        }
        withTimeout(5000) { waiting.await() }
        lock.withLock {
            signalled = true
            condition.signalAll()
        }
        assertNull(withTimeout(5000) { completed.await() })
    }
}
