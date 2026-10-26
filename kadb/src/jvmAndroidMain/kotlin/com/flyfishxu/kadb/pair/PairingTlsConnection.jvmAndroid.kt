package com.flyfishxu.kadb.pair

import com.flyfishxu.kadb.cert.AdbKeyPair
import java.io.DataInputStream
import java.io.DataOutputStream
import java.net.InetSocketAddress
import java.net.Socket
import javax.net.ssl.SSLException
import javax.net.ssl.SSLSocket
import okio.Closeable
import okio.IOException

internal actual class PairingTlsConnection actual constructor(
    private val host: String, private val port: Int, keyPair: AdbKeyPair
) : Closeable {
    private val sslContext = SslUtils.getSslContext(keyPair)
    private val lifecycleLock = Any()
    private var started = false
    private var closed = false
    private var tcpSocket: Socket? = null
    private var tlsSocket: SSLSocket? = null
    private var input: DataInputStream? = null
    private var output: DataOutputStream? = null

    actual fun start() {
        val tcp = Socket()
        synchronized(lifecycleLock) {
            if (started || closed) {
                tcp.close()
                throw IOException("Pairing TLS connection is not ready")
            }
            started = true
            // Publish ownership before the first blocking operation so cancellation can close it.
            tcpSocket = tcp
        }
        try {
            tcp.connect(InetSocketAddress(host, port))
            tcp.tcpNoDelay = true
            val tls = sslContext.socketFactory.createSocket(tcp, host, port, true) as SSLSocket
            synchronized(lifecycleLock) {
                if (closed) {
                    tls.close()
                    throw IOException("Pairing TLS connection is closed")
                }
                tlsSocket = tls
            }
            tls.startHandshake()
            val newInput = DataInputStream(tls.inputStream)
            val newOutput = DataOutputStream(tls.outputStream)
            synchronized(lifecycleLock) {
                if (closed) throw IOException("Pairing TLS connection is closed")
                input = newInput
                output = newOutput
            }
        } catch (error: Throwable) {
            close()
            throw error
        }
    }

    actual fun exportKeyingMaterial(): ByteArray {
        val tls = synchronized(lifecycleLock) {
            if (closed) throw IOException("Pairing TLS connection is closed")
            tlsSocket ?: throw IOException("Pairing TLS connection has not started")
        }
        return try {
            val method = getConscryptClass().getMethod(
                "exportKeyingMaterial", SSLSocket::class.java, String::class.java,
                ByteArray::class.java, Int::class.javaPrimitiveType
            )
            method.invoke(null, tls, "adb-label\u0000", null, 64) as ByteArray
        } catch (error: SSLException) {
            throw error
        } catch (error: Throwable) {
            throw SSLException(error)
        }
    }

    actual fun readFully(bytes: ByteArray) {
        val stream = synchronized(lifecycleLock) {
            if (closed) throw IOException("Pairing TLS connection is closed")
            input ?: throw IOException("Pairing TLS connection has not started")
        }
        try {
            stream.readFully(bytes)
        } catch (error: Throwable) {
            close()
            throw error
        }
    }

    actual fun write(bytes: ByteArray) {
        val stream = synchronized(lifecycleLock) {
            if (closed) throw IOException("Pairing TLS connection is closed")
            output ?: throw IOException("Pairing TLS connection has not started")
        }
        try {
            stream.write(bytes)
        } catch (error: Throwable) {
            // A partial TLS record cannot be retried with another record or nonce.
            close()
            throw error
        }
    }

    actual override fun close() {
        val sockets = synchronized(lifecycleLock) {
            if (closed) return
            closed = true
            (tcpSocket to tlsSocket).also {
                tcpSocket = null
                tlsSocket = null
                input = null
                output = null
            }
        }
        // Abort TCP first: closing/flushing a TLS stream alone may wait for a stalled peer.
        try { sockets.first?.close() } catch (_: IOException) { }
        try { sockets.second?.close() } catch (_: IOException) { }
    }
}

internal expect fun PairingTlsConnection.getConscryptClass(): Class<*>
