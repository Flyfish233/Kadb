package com.flyfishxu.kadb

import com.flyfishxu.kadb.cert.InMemoryPrivateKeyStore
import com.flyfishxu.kadb.cert.KadbCert
import java.io.IOException
import java.util.concurrent.CountDownLatch
import java.util.concurrent.Executors
import java.util.concurrent.TimeUnit
import java.util.concurrent.atomic.AtomicReference
import kotlinx.coroutines.Job
import kotlinx.coroutines.TimeoutCancellationException
import kotlinx.coroutines.withTimeout
import kotlinx.coroutines.awaitCancellation
import kotlinx.coroutines.currentCoroutineContext
import kotlinx.coroutines.job
import kotlin.test.Test
import kotlin.test.assertFailsWith
import kotlin.test.assertFalse
import kotlin.test.assertIs
import kotlin.test.assertTrue

class KadbConnectionAttemptCancellationTest {
    @Test fun connectorTimeoutKeepsItsExistingExceptionType() {
        KadbCert.configure(InMemoryPrivateKeyStore())
        Kadb.createWithTransport(KadbOptions()) {
            withTimeout(25) { awaitCancellation() }
        }.use { client ->
            assertFailsWith<TimeoutCancellationException> { client.supportsFeature("shell_v2") }
        }
    }

    @Test fun closeCancelsAConnectAttemptBeforeAnyTransportIsPublished() {
        KadbCert.configure(InMemoryPrivateKeyStore())
        val entered = CountDownLatch(1)
        val exited = CountDownLatch(1)
        val connectorJob = AtomicReference<Job>()
        val client = Kadb.createWithTransport(KadbOptions()) {
            connectorJob.set(currentCoroutineContext().job)
            entered.countDown()
            try {
                awaitCancellation()
            } finally {
                exited.countDown()
            }
        }
        val executor = Executors.newSingleThreadExecutor()
        try {
            val call = executor.submit<Throwable?> {
                runCatching { client.supportsFeature("shell_v2") }.exceptionOrNull()
            }
            assertTrue(entered.await(5, TimeUnit.SECONDS))
            try {
                client.close()
                client.close()
                assertTrue(exited.await(2, TimeUnit.SECONDS),
                    "close() must cancel a pending connector even before it returns a socket")
                assertIs<IOException>(call.get(5, TimeUnit.SECONDS))
                assertFalse(client.connectionCheck())
            } finally {
                // Guarantees the deliberately defective baseline does not leave a hanging test worker.
                connectorJob.get()?.cancel()
                call.get(5, TimeUnit.SECONDS)
            }
        } finally {
            client.close()
            executor.shutdownNow()
            assertTrue(executor.awaitTermination(5, TimeUnit.SECONDS))
        }
    }
}
