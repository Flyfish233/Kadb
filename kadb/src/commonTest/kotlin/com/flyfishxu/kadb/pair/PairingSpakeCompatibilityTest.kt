package com.flyfishxu.kadb.pair

import io.github.flyfish233.spake2.EntropySource
import io.github.flyfish233.spake2.Role
import io.github.flyfish233.spake2.legacy.LegacySpake25519
import kotlin.test.*
import okio.Buffer

/** Shared-path integration. Independent BoringSSL expected bytes are tested separately. */
class PairingSpakeCompatibilityTest {
    @Test fun pairsAndUsesIndependentNonceCounters() = exchange(wrongPassword = false)
    @Test fun wrongPasswordFailsAtAuthenticatedDecryption() = exchange(wrongPassword = true)

    private fun exchange(wrongPassword: Boolean) {
        val clientName = "adb pair client\u0000".encodeToByteArray()
        val serverName = "adb pair server\u0000".encodeToByteArray()
        val password = "123456-tls-exported-session-binding".encodeToByteArray()
        val alice = assertNotNull(PairingAuthCtx.createAlice(password))
        val bob = LegacySpake25519(Role.BOB, serverName, clientName, EntropySource(::securePairingRandomBytes))
        val cipher = PairingCrypto(clientName, serverName)
        try {
            val serverPassword = if (wrongPassword) "654321-tls-exported-session-binding".encodeToByteArray() else password
            val serverMessage = bob.generateMessage(serverPassword)
            val material = bob.deriveUnconfirmedKey(alice.msg)
            val key = cipher.deriveKey(material, INFO)
            material.fill(0)
            assertTrue(alice.initCipher(serverMessage))
            if (wrongPassword) {
                assertNull(cipher.encryptDecrypt(false, key, ByteArray(12), assertNotNull(alice.encrypt(byteArrayOf(1)))))
            } else {
                repeat(2) { counter ->
                    val nonce = Buffer().writeLongLe(counter.toLong()).writeIntLe(0).readByteArray()
                    val plaintext = "peer-info-$counter".encodeToByteArray()
                    val serverEncrypted = assertNotNull(cipher.encryptDecrypt(true, key, nonce, plaintext))
                    assertContentEquals(serverEncrypted, alice.encrypt(plaintext))
                    assertContentEquals(plaintext, alice.decrypt(serverEncrypted))
                }
                val replay = assertNotNull(cipher.encryptDecrypt(true, key, ByteArray(12), byteArrayOf(1)))
                assertNull(alice.decrypt(replay))
            }
            key.fill(0)
            alice.destroy()
            assertTrue(alice.isDestroyed())
            assertNull(alice.encrypt(byteArrayOf(1)))
            assertNull(alice.decrypt(byteArrayOf(1)))
        } finally {
            alice.destroy()
            cipher.destroy()
            bob.destroy()
            password.fill(0)
        }
    }
}
