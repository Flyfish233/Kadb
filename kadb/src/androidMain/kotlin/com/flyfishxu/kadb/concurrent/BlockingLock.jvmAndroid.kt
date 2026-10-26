package com.flyfishxu.kadb.concurrent

import java.util.concurrent.locks.Condition
import java.util.concurrent.locks.ReentrantLock
import kotlin.concurrent.thread

internal actual class BlockingLock actual constructor() {
    private val delegate = ReentrantLock()
    actual fun lock() = delegate.lock()
    actual fun unlock() = delegate.unlock()
    actual fun newCondition(): BlockingCondition = BlockingCondition(delegate.newCondition())
}

internal actual class BlockingCondition(private val delegate: Condition) {
    actual fun await() = delegate.await()
    actual fun signalAll() = delegate.signalAll()
}

internal actual fun startReaderThread(block: () -> Unit) {
    startKadbThread("kadb-reader", block)
}

internal actual fun startKadbThread(name: String, block: () -> Unit) {
    thread(name = name, isDaemon = true, block = block)
}
