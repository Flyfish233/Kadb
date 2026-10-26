@file:OptIn(kotlinx.cinterop.ExperimentalForeignApi::class)

package com.flyfishxu.kadb.pair

import com.flyfishxu.kadb.cert.CertUtils
import com.flyfishxu.kadb.cert.KadbCertPolicy
import kotlinx.cinterop.toKString
import okio.IOException
import okio.use
import platform.posix.getenv
import kotlin.test.Test
import kotlin.test.Ignore
import kotlin.test.assertFailsWith
import kotlin.test.assertTrue

@Ignore // Replaced by the mandatory external Native consumer; retained as a baseline harness reference.
class JvmPairingInteropTest {
    /** Historical internal-API harness. Use validation/pairing-peer/run_interop.py for actual evidence. */
    @Test fun pairsWithJvmPeerAndRejectsWrongCode() {
        val port = requireNotNull(getenv("KADB_PAIRING_PEER_PORT")?.toKString()?.toInt()) {
            "Missing KADB_PAIRING_PEER_PORT; no interoperability test was executed"
        }
        val identity = CertUtils.generateNewIdentity(KadbCertPolicy())
        for (wrongCode in listOf(false, true)) {
            val password = (if (wrongCode) "654321" else "123456").encodeToByteArray()
            PairingConnectionCtx("127.0.0.1", port, password, identity.keyPair, "kadb-ios-interop").use { pairing ->
                if (wrongCode) assertFailsWith<IOException> { pairing.start() } else pairing.start()
            }
            assertTrue(password.all { it == 0.toByte() }, "Closing pairing must erase the supplied code")
        }
    }
}
