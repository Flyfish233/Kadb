package com.flyfishxu.kadb.pair

import io.github.flyfish233.spake2.EntropySource
import io.github.flyfish233.spake2.Role
import io.github.flyfish233.spake2.legacy.LegacySpake25519
import kotlin.test.assertContentEquals
import kotlin.test.Test
import kotlin.test.assertFalse
import kotlin.test.assertNotNull
import kotlin.test.assertNull
import kotlin.test.assertTrue

/** The original three assertions expose defects in 75678915; later cases protect the fix. */
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

    @Test fun repeatedInitializationIsTerminal() {
        val password = "session-bound-password".encodeToByteArray()
        val auth = assertNotNull(PairingAuthCtx.createAlice(password))
        val bob = LegacySpake25519(Role.BOB, "adb pair server\u0000".encodeToByteArray(),
            "adb pair client\u0000".encodeToByteArray(), EntropySource(::securePairingRandomBytes))
        try {
            val peerMessage = bob.generateMessage(password)
            assertTrue(auth.initCipher(peerMessage))
            assertFalse(auth.initCipher(peerMessage))
            assertTrue(auth.isDestroyed())
            assertNull(auth.encrypt(byteArrayOf(1)))
        } finally { auth.destroy(); bob.destroy(); password.fill(0) }
    }

    @Test fun failedAuthenticationConsumesTheKey() {
        val password = "session-bound-password".encodeToByteArray()
        val auth = assertNotNull(PairingAuthCtx.createAlice(password))
        val bob = LegacySpake25519(Role.BOB, "adb pair server\u0000".encodeToByteArray(),
            "adb pair client\u0000".encodeToByteArray(), EntropySource(::securePairingRandomBytes))
        try {
            assertTrue(auth.initCipher(bob.generateMessage(password)))
            assertNull(auth.decrypt(ByteArray(16)))
            assertTrue(auth.isDestroyed())
            assertNull(auth.encrypt(byteArrayOf(1)))
        } finally { auth.destroy(); bob.destroy(); password.fill(0) }
    }

    @Test fun nonceUsesAllSixtyFourBitsWithoutWrapping() {
        val sequence = PairingNonceSequence(ULong.MAX_VALUE - 1uL)
        assertContentEquals(ByteArray(12) { when (it) { 0 -> -2; in 1..7 -> -1; else -> 0 } }, sequence.next())
        assertContentEquals(ByteArray(12) { if (it < 8) -1 else 0 }, sequence.next())
        assertNull(sequence.next())
        sequence.destroy()
        assertNull(sequence.next())
    }
}
