package com.flyfishxu.kadb.pair

import io.github.flyfish233.spake2.EntropySource
import io.github.flyfish233.spake2.Role
import io.github.flyfish233.spake2.Spake2Exception
import io.github.flyfish233.spake2.legacy.LegacyPasswordScalarMode
import io.github.flyfish233.spake2.legacy.LegacySpake25519

/**
 * The one production SPAKE25519 implementation on every target. This is the
 * historical BoringSSL protocol; its 64-byte result is not authenticated until
 * PeerInfo's AES-GCM tag and protocol constraints have both been checked.
 */
internal class PairingCrypto(
    myName: ByteArray,
    theirName: ByteArray,
    entropy: EntropySource = EntropySource(::securePairingRandomBytes)
) {
    private val spake = LegacySpake25519(
        Role.ALICE, myName, theirName, entropy, LegacyPasswordScalarMode.HARDENED
    )
    private val primitives = PairingPrimitives()

    fun generateMessage(password: ByteArray): ByteArray = spake.generateMessage(password)

    fun processMessage(message: ByteArray?): ByteArray? {
        if (message == null) return null
        return try {
            spake.deriveUnconfirmedKey(message)
        } catch (_: Spake2Exception) { null }
    }

    fun deriveKey(material: ByteArray, info: ByteArray): ByteArray = primitives.deriveKey(material, info)

    fun encryptDecrypt(encrypt: Boolean, key: ByteArray, nonce: ByteArray, input: ByteArray): ByteArray? {
        require(key.size == HKDF_KEY_LENGTH) { "Pairing requires a 128-bit AES key" }
        require(nonce.size == 12) { "Pairing requires a 96-bit nonce" }
        return primitives.encryptDecrypt(encrypt, key, nonce, input)
    }

    fun destroy() = spake.destroy()
}

/** Return freshly allocated operating-system CSPRNG bytes; throw on failure. */
internal expect fun securePairingRandomBytes(size: Int): ByteArray

/** AES-GCM and HKDF remain behind the existing, tested provider boundary. */
internal expect class PairingPrimitives() {
    fun deriveKey(material: ByteArray, info: ByteArray): ByteArray
    fun encryptDecrypt(encrypt: Boolean, key: ByteArray, nonce: ByteArray, input: ByteArray): ByteArray?
}
