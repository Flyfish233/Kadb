package com.flyfishxu.kadb.pair

import java.security.SecureRandom
import org.bouncycastle.crypto.InvalidCipherTextException
import org.bouncycastle.crypto.digests.SHA256Digest
import org.bouncycastle.crypto.engines.AESEngine
import org.bouncycastle.crypto.generators.HKDFBytesGenerator
import org.bouncycastle.crypto.modes.GCMBlockCipher
import org.bouncycastle.crypto.params.AEADParameters
import org.bouncycastle.crypto.params.HKDFParameters
import org.bouncycastle.crypto.params.KeyParameter

internal actual fun securePairingRandomBytes(size: Int): ByteArray =
    ByteArray(size).also { SecureRandom().nextBytes(it) }

internal actual class PairingPrimitives actual constructor() {
    actual fun deriveKey(material: ByteArray, info: ByteArray): ByteArray = ByteArray(HKDF_KEY_LENGTH).also {
        val hkdf = HKDFBytesGenerator(SHA256Digest())
        hkdf.init(HKDFParameters(material, null, info))
        hkdf.generateBytes(it, 0, it.size)
    }

    actual fun encryptDecrypt(encrypt: Boolean, key: ByteArray, nonce: ByteArray, input: ByteArray): ByteArray? {
        val cipher = GCMBlockCipher.newInstance(AESEngine.newInstance())
        cipher.init(encrypt, AEADParameters(KeyParameter(key), key.size * 8, nonce))
        val output = ByteArray(cipher.getOutputSize(input.size))
        return try {
            val offset = cipher.processBytes(input, 0, input.size, output, 0)
            cipher.doFinal(output, offset)
            output
        } catch (_: InvalidCipherTextException) {
            output.fill(0)
            null
        } catch (failure: Throwable) {
            output.fill(0)
            throw failure
        }
    }
}
