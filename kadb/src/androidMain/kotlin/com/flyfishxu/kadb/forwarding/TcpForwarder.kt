/*
 * Copyright (c) 2024 Flyfish-Xu
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *   http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 *
 */

package com.flyfishxu.kadb.forwarding

import com.flyfishxu.kadb.Kadb
import com.flyfishxu.kadb.concurrent.BlockingLock
import com.flyfishxu.kadb.concurrent.startKadbThread
import com.flyfishxu.kadb.concurrent.withLock
import com.flyfishxu.kadb.debug.log
import java.net.ServerSocket
import okio.buffer
import okio.sink
import okio.source

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
            val created = Listener(ServerSocket(hostPort))
            listener = created
            try {
                startKadbThread("kadb-forward-accept") { acceptClients(created) }
            } catch (failure: Throwable) {
                listener = null
                created.server.close()
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
            current.server.close()
        }
        clients.forEach { it.close() }
        lock.withLock { while (!current.closed) stopped.await() }
        clients.forEach { it.awaitStopped() }
        lock.withLock { if (listener === current) listener = null }
    }

    private fun acceptClients(current: Listener) {
        try {
            while (lock.withLock { current.active }) {
                val socket = current.server.accept()
                try {
                    val client = ForwardingSession(
                        kadb = kadb,
                        destination = "tcp:$targetPort",
                        localSource = socket.source(),
                        localSink = socket.sink().buffer(),
                        closeLocal = socket::close,
                        onFinished = { lock.withLock { current.clients.remove(it) } },
                    )
                    val accepted = lock.withLock {
                        if (current.active) {
                            current.clients.add(client)
                            true
                        } else false
                    }
                    if (accepted) client.start() else client.close()
                } catch (failure: Throwable) {
                    socket.close()
                    throw failure
                }
            }
        } catch (failure: Exception) {
            if (lock.withLock { current.active }) {
                log { "could not continue TCP port forwarding: ${failure.message}" }
            }
        } finally {
            current.server.close()
            val clients = lock.withLock {
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

    private class Listener(val server: ServerSocket) {
        var active = true
        var closed = false
        val clients = mutableSetOf<ForwardingSession>()
    }
}
