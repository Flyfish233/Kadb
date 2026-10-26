@file:OptIn(kotlinx.cinterop.ExperimentalForeignApi::class)

package com.flyfishxu.kadb.pair

import com.flyfishxu.kadb.cert.withNativeBytes
import com.flyfishxu.kadb.nativebridge.*
import kotlinx.cinterop.*
import platform.posix.size_tVar

internal actual fun securePairingRandomBytes(size: Int): ByteArray = ByteArray(size).also { bytes ->
    val success = bytes.withNativeBytes { output, length -> kadb_random_bytes(output, length) }
    if (success != 1) {
        bytes.fill(0)
        error("Operating-system CSPRNG failed")
    }
}

internal actual class PairingPrimitives actual constructor() {
    actual fun deriveKey(material: ByteArray, info: ByteArray): ByteArray = ByteArray(HKDF_KEY_LENGTH).also { key ->
        val success = material.withNativeBytes { bytes, length ->
            info.withNativeBytes { infoBytes, infoLength ->
                key.withNativeBytes { output, _ -> kadb_hkdf_sha256(bytes, length, infoBytes, infoLength, output) }
            }
        }
        if (success != 1) {
            key.fill(0)
            error("Failed to derive pairing key")
        }
    }

    actual fun encryptDecrypt(encrypt: Boolean, key: ByteArray, nonce: ByteArray, input: ByteArray): ByteArray? {
        if ((!encrypt && input.size < 16) || input.size > Int.MAX_VALUE - 16) return null
        // Keep a non-null output buffer for authenticated empty plaintexts.
        val output = ByteArray(if (encrypt) input.size + 16 else maxOf(1, input.size - 16))
        return memScoped {
            val written = alloc<size_tVar>()
            val success = key.withNativeBytes { keyBytes, _ ->
                nonce.withNativeBytes { iv, _ ->
                    input.withNativeBytes { bytes, length ->
                        output.withNativeBytes { result, capacity ->
                            kadb_aes_gcm(if (encrypt) 1 else 0, keyBytes, iv, bytes, length, result, capacity, written.ptr)
                        }
                    }
                }
            }
            try {
                if (success == 1) output.copyOf(written.value.toInt()) else null
            } finally { output.fill(0) }
        }
    }
}
