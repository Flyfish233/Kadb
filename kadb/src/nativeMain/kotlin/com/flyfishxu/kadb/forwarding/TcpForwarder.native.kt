@file:OptIn(kotlinx.cinterop.ExperimentalForeignApi::class)

package com.flyfishxu.kadb.forwarding

import com.flyfishxu.kadb.Kadb
import com.flyfishxu.kadb.concurrent.BlockingLock
import com.flyfishxu.kadb.concurrent.startKadbThread
import com.flyfishxu.kadb.concurrent.withLock
import com.flyfishxu.kadb.debug.log
import com.flyfishxu.kadb.transport.PosixTransportChannel
import com.flyfishxu.kadb.transport.asOkioSink
import com.flyfishxu.kadb.transport.asOkioSource
import kotlinx.cinterop.*
import okio.IOException
import okio.buffer
import com.flyfishxu.kadb.nativebridge.kadb_create_listener
import platform.posix.*

internal actual class TcpForwarder actual constructor(
    private val kadb: Kadb,
    private val hostPort: Int,
    private val targetPort: Int,
) : AutoCloseable {
    private val lock = BlockingLock()
    private val stopped = lock.newCondition()
    private var listener: Listener? = null

    actual fun start() {
        require(hostPort in 0..65535) { "Invalid host port: $hostPort" }
        require(targetPort in 1..65535) { "Invalid target port: $targetPort" }
        lock.withLock {
            check(listener == null) { "Forwarder is already started at port $hostPort" }
            val created = Listener(createListener(hostPort))
            listener = created
            try {
                startKadbThread("kadb-forward-accept") { acceptClients(created) }
            } catch (failure: Throwable) {
                listener = null
                platform.posix.close(created.fd)
                throw failure
            }
        }
    }

    actual override fun close() {
        val current: Listener
        val clients: List<ForwardingSession>
        lock.withLock {
            current = listener ?: return
            current.active = false
            clients = current.clients.toList()
            // Wake poll/accept, but let the accepting thread close its own descriptor.
            // Closing here could let an in-flight accept use a newly reused descriptor.
            if (!current.closed) shutdown(current.fd, SHUT_RDWR)
        }
        clients.forEach { it.close() }
        lock.withLock { while (!current.closed) stopped.await() }
        clients.forEach { it.awaitStopped() }
        lock.withLock { if (listener === current) listener = null }
    }

    private fun acceptClients(current: Listener) {
        try {
            memScoped {
                val pollFd = alloc<pollfd> {
                    fd = current.fd
                    events = POLLIN.toShort()
                }
                while (lock.withLock { current.active }) {
                    val ready = poll(pollFd.ptr, 1.convert(), 200)
                    if (ready < 0) {
                        if (errno == EINTR) continue
                        throw socketFailure("poll")
                    }
                    if (ready == 0 || !lock.withLock { current.active }) continue
                    val clientFd = accept(current.fd, null, null)
                    if (clientFd < 0) {
                        if (errno == EINTR || errno == EAGAIN || errno == EWOULDBLOCK) continue
                        if (!lock.withLock { current.active }) break
                        throw socketFailure("accept")
                    }
                    // The channel takes ownership, including its initialization-failure path.
                    val channel = PosixTransportChannel(clientFd)
                    val client = ForwardingSession(
                        kadb = kadb,
                        destination = "tcp:$targetPort",
                        localSource = channel.asOkioSource(),
                        localSink = channel.asOkioSink().buffer(),
                        closeLocal = channel::close,
                        onFinished = { lock.withLock { current.clients.remove(it) } },
                    )
                    val accepted = lock.withLock {
                        if (current.active) {
                            current.clients.add(client)
                            true
                        } else false
                    }
                    if (!accepted) {
                        client.close()
                        continue
                    }
                    try {
                        client.start()
                    } catch (failure: Throwable) {
                        lock.withLock { current.clients.remove(client) }
                        client.close()
                        throw failure
                    }
                }
            }
        } catch (failure: Exception) {
            if (lock.withLock { current.active }) {
                log { "could not continue TCP port forwarding: ${failure.message}" }
            }
        } finally {
            val clients = lock.withLock {
                platform.posix.close(current.fd)
                current.active = false
                current.clients.toList()
            }
            clients.forEach { it.close() }
            lock.withLock {
                current.closed = true
                stopped.signalAll()
            }
        }
    }

    private class Listener(val fd: Int) {
        var active = true
        var closed = false
        val clients = mutableSetOf<ForwardingSession>()
    }
}

private fun createListener(port: Int): Int = memScoped {
    val error = allocArray<ByteVar>(512)
    error[0] = 0
    kadb_create_listener(port, error, 512.convert()).also { fd ->
        if (fd < 0) throw IOException(error.toKString())
    }
}

private fun socketFailure(operation: String): IOException =
    IOException("$operation failed: ${strerror(errno)?.toKString() ?: errno.toString()}")
