@file:OptIn(kotlinx.cinterop.ExperimentalForeignApi::class, kotlin.experimental.ExperimentalNativeApi::class)

package com.flyfishxu.kadb.concurrent

import kotlinx.cinterop.*
import platform.posix.*
import kotlin.native.ref.createCleaner

/** A recursive POSIX mutex preserves the synchronous JVM lock contract. */
internal actual class BlockingLock actual constructor() {
    private val mutex = allocateMutex(recursive = true)
    @Suppress("unused")
    private val cleaner = createCleaner(mutex) {
        pthread_mutex_destroy(it)
        nativeHeap.free(it)
    }
    private var owner: pthread_t = 0u
    private var depth = 0


    actual fun lock() {
        check(pthread_mutex_lock(mutex) == 0)
        owner = pthread_self()
        depth++
    }

    actual fun unlock() {
        checkHeld()
        depth--
        if (depth == 0) owner = 0u
        check(pthread_mutex_unlock(mutex) == 0)
    }

    actual fun newCondition(): BlockingCondition = BlockingCondition(this)

    internal fun checkHeld() {
        check(depth > 0 && pthread_equal(owner, pthread_self()) != 0) { "Current thread does not own the lock" }
    }

    internal fun releaseForWait(): Int {
        checkHeld()
        return depth.also { previousDepth -> repeat(previousDepth) { unlock() } }
    }

    internal fun restoreAfterWait(previousDepth: Int) = repeat(previousDepth) { lock() }
}

private fun allocateMutex(recursive: Boolean): CPointer<pthread_mutex_t> {
    val mutex = nativeHeap.alloc<pthread_mutex_t>().ptr
    try {
        memScoped {
            val attributes = alloc<pthread_mutexattr_t>()
            check(pthread_mutexattr_init(attributes.ptr) == 0)
            try {
                if (recursive) check(pthread_mutexattr_settype(attributes.ptr, PTHREAD_MUTEX_RECURSIVE.toInt()) == 0)
                check(pthread_mutex_init(mutex, attributes.ptr) == 0)
            } finally {
                pthread_mutexattr_destroy(attributes.ptr)
            }
        }
        return mutex
    } catch (failure: Throwable) {
        nativeHeap.free(mutex)
        throw failure
    }
}

private class ConditionStorage {
    val gate = allocateMutex(recursive = false)
    val condition = nativeHeap.alloc<pthread_cond_t>().ptr
    init {
        if (pthread_cond_init(condition, null) != 0) {
            nativeHeap.free(condition)
            pthread_mutex_destroy(gate)
            nativeHeap.free(gate)
            error("Unable to initialize the native condition")
        }
    }
}

internal actual class BlockingCondition(private val lock: BlockingLock) {
    private val storage = ConditionStorage()
    @Suppress("unused")
    private val cleaner = createCleaner(storage) {
        pthread_cond_destroy(it.condition)
        pthread_mutex_destroy(it.gate)
        nativeHeap.free(it.condition)
        nativeHeap.free(it.gate)
    }

    actual fun await() {
        lock.checkHeld()
        check(pthread_mutex_lock(storage.gate) == 0)
        val previousDepth = lock.releaseForWait()
        try {
            check(pthread_cond_wait(storage.condition, storage.gate) == 0)
        } finally {
            pthread_mutex_unlock(storage.gate)
            lock.restoreAfterWait(previousDepth)
        }
    }

    actual fun signalAll() {
        lock.checkHeld()
        check(pthread_mutex_lock(storage.gate) == 0)
        try {
            check(pthread_cond_broadcast(storage.condition) == 0)
        } finally {
            pthread_mutex_unlock(storage.gate)
        }
    }
}

internal actual fun startReaderThread(block: () -> Unit) = startKadbThread("kadb-reader", block)

internal actual fun startKadbThread(name: String, block: () -> Unit) {
    val reference = StableRef.create(block)
    try {
        memScoped {
            val thread = alloc<pthread_tVar>()
            val attributes = alloc<pthread_attr_t>()
            check(pthread_attr_init(attributes.ptr) == 0)
            try {
                check(pthread_attr_setdetachstate(attributes.ptr, PTHREAD_CREATE_DETACHED) == 0)
                val result = pthread_create(thread.ptr, attributes.ptr, staticCFunction { pointer ->
                    val saved = pointer!!.asStableRef<() -> Unit>()
                    val work = saved.get()
                    saved.dispose()
                    try {
                        work()
                    } catch (failure: Throwable) {
                        failure.printStackTrace()
                    }
                    null
                }, reference.asCPointer())
                check(result == 0) { "Unable to start $name: pthread_create failed with $result" }
            } finally {
                pthread_attr_destroy(attributes.ptr)
            }
        }
    } catch (failure: Throwable) {
        reference.dispose()
        throw failure
    }
}
