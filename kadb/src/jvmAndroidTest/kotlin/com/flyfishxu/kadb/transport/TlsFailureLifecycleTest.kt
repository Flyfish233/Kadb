package com.flyfishxu.kadb.transport

import com.flyfishxu.kadb.cert.CertUtils
import com.flyfishxu.kadb.cert.KadbCertPolicy
import java.io.IOException
import java.net.InetAddress
import java.net.InetSocketAddress
import java.net.Socket
import java.net.SocketTimeoutException
import java.nio.ByteBuffer
import java.security.KeyStore
import java.util.concurrent.Executors
import java.util.concurrent.TimeUnit
import javax.net.ssl.KeyManagerFactory
import javax.net.ssl.SSLContext
import javax.net.ssl.SSLServerSocket
import javax.net.ssl.SSLSocket
import javax.net.ssl.TrustManagerFactory
import kotlinx.coroutines.runBlocking
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertFailsWith
import kotlin.test.assertFalse
import kotlin.test.assertTrue

/** Actual JDK TLS records; only the TCP sink is fault-injected after a completed handshake. */
class TlsFailureLifecycleTest {
    @Test fun partialCiphertextWriteFailurePermanentlyInvalidatesChannel(): Unit = exerciseWriteFailure(5)
    @Test fun writeTimeoutBeforeCiphertextDeliveryPermanentlyInvalidatesChannel(): Unit = exerciseWriteFailure(0)

    private fun exerciseWriteFailure(deliveredPrefix: Int): Unit = runBlocking {
        val context = tlsContext()
        val listener = context.serverSocketFactory.createServerSocket(
            0, 1, InetAddress.getLoopbackAddress()
        ) as SSLServerSocket
        listener.soTimeout = 5000
        listener.enabledProtocols = arrayOf("TLSv1.3")
        val executor = Executors.newSingleThreadExecutor()
        try {
            val peer = executor.submit {
                (listener.accept() as SSLSocket).use { socket ->
                    socket.soTimeout = 5000
                    socket.startHandshake()
                    // The deliberately incomplete application record must never arrive as plaintext.
                    try {
                        assertEquals(-1, socket.inputStream.read())
                    } catch (_: IOException) {
                        // Abrupt transport close is the correct outcome after a partial TLS write.
                    }
                }
            }
            val tcp = FaultInjectingTransport(Socket("127.0.0.1", listener.localPort))
            val engine = context.createSSLEngine("localhost", listener.localPort).apply {
                useClientMode = true
                enabledProtocols = arrayOf("TLSv1.3")
            }
            val tls = TlsNioChannel(tcp, engine)
            try {
                tls.handshake(3000, TimeUnit.MILLISECONDS)
                tcp.failAfterBytes = deliveredPrefix
                val plaintext = ByteBuffer.wrap("command-with-side-effects".encodeToByteArray())
                assertFailsWith<SocketTimeoutException> { tls.writeExactly(plaintext, 100, TimeUnit.MILLISECONDS) }
                assertTrue(plaintext.position() > 0,
                    "Regression requires SSLEngine.wrap to have consumed application plaintext")
                assertEquals(deliveredPrefix, tcp.bytesDeliveredByFailedWrite)
                assertFalse(tls.isOpen, "A failed TLS record cannot be safely retried")
                assertFalse(tcp.isOpen, "Poisoning must close the underlying socket")
                val attempts = tcp.writeCalls
                assertFailsWith<IOException> {
                    tls.writeExactly(ByteBuffer.wrap(byteArrayOf(1)), 100, TimeUnit.MILLISECONDS)
                }
                assertEquals(attempts, tcp.writeCalls, "No new TLS record may be emitted after failure")
                tls.close()
                tls.close()
                assertEquals(1, tcp.closeCalls, "Concurrent/repeated cleanup must be idempotent")
            } finally {
                tls.close()
            }
            peer.get(5, TimeUnit.SECONDS)
        } finally {
            listener.close()
            executor.shutdownNow()
            assertTrue(executor.awaitTermination(5, TimeUnit.SECONDS))
        }
    }

    private fun tlsContext(): SSLContext {
        val identity = CertUtils.generateNewIdentity(KadbCertPolicy()).keyPair
        val keys = KeyStore.getInstance(KeyStore.getDefaultType()).apply {
            load(null, null)
            setKeyEntry("peer", identity.privateKey, charArrayOf(), arrayOf(identity.certificate))
        }
        val km = KeyManagerFactory.getInstance(KeyManagerFactory.getDefaultAlgorithm()).apply {
            init(keys, charArrayOf())
        }
        val tm = TrustManagerFactory.getInstance(TrustManagerFactory.getDefaultAlgorithm()).apply { init(keys) }
        return SSLContext.getInstance("TLSv1.3").apply { init(km.keyManagers, tm.trustManagers, null) }
    }

    private class FaultInjectingTransport(private val socket: Socket) : TransportChannel {
        var failAfterBytes: Int? = null
        var bytesDeliveredByFailedWrite = 0
        var writeCalls = 0
        var closeCalls = 0
        override val isOpen get() = !socket.isClosed
        override val localAddress get() = socket.localSocketAddress as InetSocketAddress
        override val remoteAddress get() = socket.remoteSocketAddress as InetSocketAddress

        override suspend fun read(dst: ByteBuffer, timeout: Long, unit: TimeUnit): Int {
            socket.soTimeout = unit.toMillis(timeout).toInt()
            val bytes = ByteArray(dst.remaining())
            val read = socket.getInputStream().read(bytes)
            if (read > 0) dst.put(bytes, 0, read)
            return read
        }

        override suspend fun write(src: ByteBuffer, timeout: Long, unit: TimeUnit): Int {
            writeCalls++
            val fault = failAfterBytes
            if (fault != null) {
                val bytes = ByteArray(minOf(fault, src.remaining()))
                src.get(bytes)
                socket.getOutputStream().write(bytes)
                socket.getOutputStream().flush()
                bytesDeliveredByFailedWrite += bytes.size
                throw SocketTimeoutException("Injected TCP timeout after ${bytes.size} TLS bytes")
            }
            val bytes = ByteArray(src.remaining())
            src.get(bytes)
            socket.getOutputStream().write(bytes)
            socket.getOutputStream().flush()
            return bytes.size
        }

        override suspend fun readExactly(dst: ByteBuffer, timeout: Long, unit: TimeUnit) {
            while (dst.hasRemaining()) if (read(dst, timeout, unit) < 0) throw IOException("EOF")
        }

        override suspend fun writeExactly(src: ByteBuffer, timeout: Long, unit: TimeUnit) {
            while (src.hasRemaining()) write(src, timeout, unit)
        }

        override suspend fun shutdownInput() { socket.shutdownInput() }
        override suspend fun shutdownOutput() { socket.shutdownOutput() }
        override fun close() { closeCalls++; socket.close() }
    }
}
