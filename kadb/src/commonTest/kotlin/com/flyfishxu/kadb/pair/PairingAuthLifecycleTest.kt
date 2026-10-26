package com.flyfishxu.kadb.pair

import kotlin.test.Test
import kotlin.test.assertFalse
import kotlin.test.assertNotNull
import kotlin.test.assertNull
import kotlin.test.assertTrue

/** These assertions deliberately fail against 75678915; they are product regression tests. */
class PairingAuthLifecycleTest {
    @Test fun cannotEncryptBeforeKeyAgreement() {
        val auth = assertNotNull(PairingAuthCtx.createAlice("session-bound-password".encodeToByteArray()))
        try {
            assertNull(auth.encrypt(byteArrayOf(1)), "Uninitialized pairing must never encrypt with an all-zero key")
        } finally { auth.destroy() }
    }

    @Test fun invalidPeerMessageConsumesContext() {
        val auth = assertNotNull(PairingAuthCtx.createAlice("session-bound-password".encodeToByteArray()))
        try {
            assertFalse(auth.initCipher(ByteArray(31)))
            assertTrue(auth.isDestroyed(), "A failed key agreement cannot be retried")
            assertNull(auth.encrypt(byteArrayOf(1)))
        } finally { auth.destroy() }
    }

    @Test fun destructionErasesTheOwnedOutboundMessage() {
        val auth = assertNotNull(PairingAuthCtx.createAlice("session-bound-password".encodeToByteArray()))
        auth.destroy()
        auth.destroy()
        assertTrue(auth.isDestroyed())
        assertTrue(auth.msg.all { it == 0.toByte() })
        assertNull(auth.encrypt(byteArrayOf(1)))
        assertNull(auth.decrypt(ByteArray(16)))
    }
}
