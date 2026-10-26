/*
 * Copyright (c) 2024 Flyfish-Xu
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *   http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 *
 */

package com.flyfishxu.kadb.pair

// Protocol labels include the terminating zero where AOSP uses sizeof(string literal).
private val CLIENT_NAME get() = "adb pair client\u0000".encodeToByteArray()
private val SERVER_NAME get() = "adb pair server\u0000".encodeToByteArray()
internal val INFO get() = "adb pairing_auth aes-128-gcm key".encodeToByteArray()
internal const val HKDF_KEY_LENGTH = 16

/**
 * Single-use pairing authentication owned by the PairingConnectionCtx worker.
 * Closing a transport must unblock that worker before its finally block destroys this state.
 */
internal class PairingAuthCtx private constructor(private val crypto: PairingCrypto, password: ByteArray) {
    val msg: ByteArray = crypto.generateMessage(password)
    private val secretKey = ByteArray(HKDF_KEY_LENGTH)
    private val decryptNonces = PairingNonceSequence()
    private val encryptNonces = PairingNonceSequence()
    private var state = State.MESSAGE_GENERATED

    fun initCipher(theirMsg: ByteArray?): Boolean {
        if (state != State.MESSAGE_GENERATED) {
            destroy()
            return false
        }
        return try {
            val material = crypto.processMessage(theirMsg)
            if (material == null) {
                destroy()
                false
            } else {
                try {
                    val key = crypto.deriveKey(material, INFO)
                    try {
                        check(key.size == secretKey.size) { "Invalid pairing key length" }
                        key.copyInto(secretKey)
                        state = State.CIPHER_READY
                    } finally { key.fill(0) }
                    true
                } finally { material.fill(0) }
            }
        } catch (_: IllegalArgumentException) {
            destroy()
            false
        } catch (_: IllegalStateException) {
            destroy()
            false
        } catch (failure: Throwable) {
            destroy()
            throw failure
        }
    }

    fun encrypt(input: ByteArray): ByteArray? = crypt(true, input, encryptNonces)
    fun decrypt(input: ByteArray): ByteArray? = crypt(false, input, decryptNonces)
    fun isDestroyed(): Boolean = state == State.DESTROYED

    fun destroy() {
        if (state == State.DESTROYED) return
        state = State.DESTROYED
        secretKey.fill(0)
        msg.fill(0)
        encryptNonces.destroy()
        decryptNonces.destroy()
        crypto.destroy()
    }

    private fun crypt(encrypt: Boolean, input: ByteArray, nonces: PairingNonceSequence): ByteArray? {
        if (state != State.CIPHER_READY) {
            destroy()
            return null
        }
        val nonce = nonces.next() ?: run { destroy(); return null }
        return try {
            crypto.encryptDecrypt(encrypt, secretKey, nonce, input).also {
                // Authentication failure is terminal; do not accept another ciphertext/nonce on this key.
                if (it == null) destroy()
            }
        } catch (failure: Throwable) {
            destroy()
            throw failure
        } finally { nonce.fill(0) }
    }

    private enum class State { MESSAGE_GENERATED, CIPHER_READY, DESTROYED }

    companion object {
        internal fun create(password: ByteArray): PairingAuthCtx? {
            val crypto = PairingCrypto(CLIENT_NAME, SERVER_NAME)
            return try {
                PairingAuthCtx(crypto, password)
            } catch (_: IllegalArgumentException) {
                crypto.destroy()
                null
            } catch (_: IllegalStateException) {
                crypto.destroy()
                null
            } catch (failure: Throwable) {
                crypto.destroy()
                throw failure
            }
        }
    }
}

internal fun PairingAuthCtx.Companion.createAlice(password: ByteArray): PairingAuthCtx? = create(password)

/** ADB's 64-bit little-endian counter followed by four zero bytes; never wraps. */
internal class PairingNonceSequence(initial: ULong = 0uL) {
    private var counter = initial
    private var exhausted = false

    fun next(): ByteArray? {
        if (exhausted) return null
        val value = counter
        if (value == ULong.MAX_VALUE) exhausted = true else counter++
        return ByteArray(12) { index -> if (index < 8) (value shr (index * 8)).toByte() else 0 }
    }

    fun destroy() {
        counter = 0uL
        exhausted = true
    }
}
