package com.flyfishxu.kadb.pair

import com.flyfishxu.kadb.cert.AdbKeyPair
import com.flyfishxu.kadb.concurrent.BlockingLock
import com.flyfishxu.kadb.concurrent.withLock
import com.flyfishxu.kadb.transport.PosixTransportChannel
import okio.Closeable
import okio.EOFException
import okio.IOException

internal actual class PairingTlsConnection actual constructor(
    private val host: String, private val port: Int, private val keyPair: AdbKeyPair
) : Closeable {
    private val lock = BlockingLock()
    // Allocate the closeable owner before connecting so cancellation can close a
    // pending connect/handshake, and cannot race with publishing a new channel.
    private val channel = PosixTransportChannel.create()
    private var started = false
    private var ready = false
    private var closed = false

    actual fun start() {
        lock.withLock {
            if (closed) throw IOException("Pairing TLS connection closed")
            check(!started) { "Pairing TLS already started" }
            started = true
        }
        try {
            channel.connectTo(host, port, 0)
            channel.startTls(listOf(keyPair), 0)
            lock.withLock {
                if (closed) throw IOException("Pairing TLS connection closed")
                ready = true
            }
        } catch (error: Throwable) {
            close()
            throw error
        }
    }

    private fun readyChannel(): PosixTransportChannel = lock.withLock {
        if (closed) throw IOException("Pairing TLS connection closed")
        check(ready) { "Pairing TLS is not ready" }
        channel
    }

    actual fun exportKeyingMaterial(): ByteArray = readyChannel().exportPairingKey()

    actual fun readFully(bytes: ByteArray) {
        val socket = readyChannel()
        var offset = 0
        while (offset < bytes.size) {
            val count = socket.read(bytes, offset, bytes.size - offset, 0)
            if (count < 0) throw EOFException("Pairing TLS connection ended")
            offset += count
        }
    }

    actual fun write(bytes: ByteArray) = readyChannel().write(bytes, 0, bytes.size, 0)

    actual override fun close() {
        lock.withLock {
            if (closed) return
            closed = true
        }
        channel.close()
    }
}
