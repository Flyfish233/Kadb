package com.flyfishxu.kadb

import kotlinx.coroutines.CancellationException
import okio.IOException
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertFailsWith
import kotlin.test.assertSame
import kotlin.test.assertTrue

class InstallSessionLifecycleTest {
    @Test fun successfulWritesDoNotAbandonTheSession() {
        var abandoned = 0
        assertEquals("ready-to-commit", runInstallWrites({ abandoned++ }) { "ready-to-commit" })
        assertEquals(0, abandoned)
    }

    @Test fun writeFailureAbandonsOnceAndKeepsTheOriginalException() {
        val original = IOException("APK source failed after the session was created")
        var abandoned = 0
        val observed = assertFailsWith<IOException> {
            runInstallWrites({ abandoned++ }) { throw original }
        }
        assertSame(original, observed)
        assertEquals(1, abandoned)
        assertTrue(observed.suppressedExceptions.isEmpty())
    }

    @Test fun cleanupFailureIsSuppressedOnTheWriteFailure() {
        val original = IOException("original write failure")
        val cleanup = IOException("session abandon failed")
        var abandoned = 0
        val observed = assertFailsWith<IOException> {
            runInstallWrites({ abandoned++; throw cleanup }) { throw original }
        }
        assertSame(original, observed)
        assertEquals(1, abandoned)
        assertEquals(listOf(cleanup), observed.suppressedExceptions)
    }

    @Test fun identicalCleanupExceptionCannotMaskTheOriginalWithSelfSuppression() {
        val original = IOException("same underlying transport failure")
        var abandoned = 0
        val observed = assertFailsWith<IOException> {
            runInstallWrites({ abandoned++; throw original }) { throw original }
        }
        assertSame(original, observed)
        assertEquals(1, abandoned)
        assertTrue(observed.suppressedExceptions.isEmpty())
    }

    @Test fun cancellationDuringWritesStillAttemptsToAbandon() {
        val original = CancellationException("write cancelled")
        var abandoned = 0
        val observed = assertFailsWith<CancellationException> {
            runInstallWrites({ abandoned++ }) { throw original }
        }
        assertSame(original, observed)
        assertEquals(1, abandoned)
    }
}
