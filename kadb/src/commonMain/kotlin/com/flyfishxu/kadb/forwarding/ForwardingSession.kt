package com.flyfishxu.kadb.forwarding

import com.flyfishxu.kadb.Kadb
import com.flyfishxu.kadb.concurrent.BlockingLock
import com.flyfishxu.kadb.concurrent.startKadbThread
import com.flyfishxu.kadb.concurrent.withLock
import com.flyfishxu.kadb.debug.log
import kotlinx.coroutines.Job
import okio.BufferedSink
import okio.Source

/** Owns one accepted socket and both data pumps, including an OPEN which has no stream yet. */
internal class ForwardingSession(
    private val kadb: Kadb,
    private val destination: String,
    private val localSource: Source,
    private val localSink: BufferedSink,
    private val closeLocal: () -> Unit,
    private val onFinished: (ForwardingSession) -> Unit,
) : AutoCloseable {
    private val lock = BlockingLock()
    private val stopped = lock.newCondition()
    private val lifetime = Job()
    private var workers = 0
    private var started = false
    private var completed = false
    private var closed = false

    fun start() {
        val shouldStart = lock.withLock {
            check(!started) { "Forwarding session is already started" }
            started = true
            if (closed) false else {
                workers = 1
                true
            }
        }
        if (!shouldStart) {
            finished()
            return
        }
        launchRegisteredWorker("kadb-forward-download") {
            val stream = kadb.openCancellable(destination, lifetime)
            val upload = lock.withLock {
                if (closed) false else {
                    workers++
                    true
                }
            }
            if (upload) {
                launchRegisteredWorker("kadb-forward-upload") { forward(localSource, stream.sink) }
                forward(stream.source, localSink)
            }
        }
    }

    private fun launchRegisteredWorker(name: String, block: () -> Unit) {
        try {
            startKadbThread(name) {
                try {
                    block()
                } catch (failure: Exception) {
                    if (lifetime.isActive) log { "TCP forwarding stopped: ${failure.message}" }
                } finally {
                    close()
                    workerFinished()
                }
            }
        } catch (failure: Throwable) {
            close()
            workerFinished()
            throw failure
        }
    }

    private fun workerFinished() {
        val finished = lock.withLock {
            check(workers > 0)
            workers--
            workers == 0
        }
        if (finished) finished()
    }

    private fun finished() {
        try {
            onFinished(this)
        } finally {
            lock.withLock {
                completed = true
                stopped.signalAll()
            }
        }
    }

    override fun close() {
        lock.withLock {
            if (closed) return
            closed = true
        }
        // A local read/write must wake even if sending the ADB CLSE subsequently fails.
        runCatching(closeLocal).onFailure { log { "TCP forwarding socket close failed: ${it.message}" } }
        runCatching { lifetime.cancel() }
            .onFailure { log { "TCP forwarding stream close failed: ${it.message}" } }
    }

    fun awaitStopped() = lock.withLock {
        while (workers != 0 || (started && !completed)) stopped.await()
    }

    private fun forward(source: Source, sink: BufferedSink) {
        while (source.read(sink.buffer, 8192) != -1L) sink.flush()
    }
}
