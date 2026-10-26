package com.flyfishxu.kadb.pair

import com.flyfishxu.kadb.Kadb
import com.flyfishxu.kadb.cert.CertUtils
import com.flyfishxu.kadb.cert.InMemoryPrivateKeyStore
import com.flyfishxu.kadb.cert.KadbCert
import com.flyfishxu.kadb.cert.KadbCertPolicy
import java.io.IOException
import java.net.InetAddress
import java.net.ServerSocket
import java.net.Socket
import java.util.concurrent.CountDownLatch
import java.util.concurrent.Executors
import java.util.concurrent.TimeUnit
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.runBlocking
import kotlinx.coroutines.withTimeout
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertFailsWith
import kotlin.test.assertTrue

/** A peer deliberately accepts TCP and never answers ClientHello. Cleanup is bounded even on the old bug. */
class PairingCancellationTest {
    @Test fun cancellationClosesHandshakeSocketAndJoinsWorker() {
        KadbCert.configure(InMemoryPrivateKeyStore())
        KadbCert.ensureReady()
        server().use { listener ->
            runBlocking {
                val exited = CountDownLatch(1)
                val pairing = launch(Dispatchers.Default) {
                    try {
                        Kadb.pair("127.0.0.1", listener.localPort, "123456", "cancel-test")
                    } finally {
                        exited.countDown()
                    }
                }
                listener.accept().use { peer ->
                    try {
                        readClientHelloStart(peer)
                        pairing.cancel()
                        assertTrue(exited.await(2, TimeUnit.SECONDS),
                            "Cancelled pairing must close blocked TLS I/O and finish its worker")
                        withTimeout(1000) { pairing.join() }
                        assertTrue(pairing.isCompleted, "Cancellation must not leave an orphan worker")
                    } finally {
                        // Makes the regression test terminate on the defective implementation too.
                        peer.close()
                        withTimeout(5000) { pairing.join() }
                    }
                }
            }
        }
    }

    @Test fun closeDuringHandshakeIsIdempotentAndUnblocksStart() {
        val identity = CertUtils.generateNewIdentity(KadbCertPolicy())
        server().use { listener ->
            val password = "123456".encodeToByteArray()
            val context = PairingConnectionCtx("127.0.0.1", listener.localPort, password,
                identity.keyPair, "close-test")
            val executor = Executors.newSingleThreadExecutor()
            try {
                val call = executor.submit {
                    assertFailsWith<IOException> { context.start() }
                }
                listener.accept().use { peer ->
                    try {
                        readClientHelloStart(peer)
                        context.close()
                        context.close()
                        call.get(2, TimeUnit.SECONDS)
                        assertTrue(password.all { it == 0.toByte() })
                        assertFailsWith<IOException> { context.start() }
                    } finally {
                        peer.close()
                        call.get(5, TimeUnit.SECONDS)
                    }
                }
            } finally {
                context.close()
                executor.shutdownNow()
                assertTrue(executor.awaitTermination(5, TimeUnit.SECONDS))
            }
        }
    }

    private fun server() = ServerSocket(0, 8, InetAddress.getLoopbackAddress()).apply { soTimeout = 5000 }

    private fun readClientHelloStart(peer: Socket) {
        peer.soTimeout = 5000
        assertEquals(22, peer.getInputStream().read(), "A real TLS handshake must have started")
    }
}
