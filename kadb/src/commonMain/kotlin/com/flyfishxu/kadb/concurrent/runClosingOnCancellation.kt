package com.flyfishxu.kadb.concurrent

import kotlinx.coroutines.CoroutineStart
import kotlinx.coroutines.DelicateCoroutinesApi
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.IO
import kotlinx.coroutines.coroutineScope
import kotlinx.coroutines.launch
import kotlinx.coroutines.suspendCancellableCoroutine
import kotlin.coroutines.resume
import kotlin.coroutines.resumeWithException

/**
 * Runs blocking I/O with an already-owned resource. Cancellation closes the resource to unblock I/O;
 * it never destroys state still used by the worker. The worker must release its own temporary state
 * in finally. The caller does not resume until that worker has exited.
 *
 * close must be thread-safe and idempotent, and must not wait for this coroutine to complete.
 * Successful calls keep ownership with the caller; failed/cancelled calls always close it.
 */
@OptIn(DelicateCoroutinesApi::class)
internal suspend fun <T> runClosingOnCancellation(close: () -> Unit, block: () -> T): T = try {
    coroutineScope {
        suspendCancellableCoroutine { continuation ->
            continuation.invokeOnCancellation { runCatching(close) }
            // ATOMIC ensures the child completes even if cancellation precedes dispatch.
            launch(Dispatchers.IO, start = CoroutineStart.ATOMIC) {
                try {
                    if (continuation.isActive) continuation.resume(block())
                } catch (error: Throwable) {
                    continuation.resumeWithException(error)
                }
            }
        }
    }
} catch (error: Throwable) {
    // Also covers prompt cancellation while coroutineScope is returning a successful result.
    runCatching(close)
    throw error
}
