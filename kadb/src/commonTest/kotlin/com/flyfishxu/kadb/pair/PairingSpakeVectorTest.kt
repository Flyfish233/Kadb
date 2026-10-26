// Original test runner is Apache-2.0 (Kadb experiment).
// Embedded expected bytes: GPLv3 fixture data from Flyfish233/spake2-java
// 809ad7aa731f475c07763b1ad2c165ae192dfb5f, via spake2 b837aba27bebc1050965fa124c2efa54b4e4544a.
// See validation/spake2/README.md and GPL-3.0-fixture-license.txt.
package com.flyfishxu.kadb.pair

import io.github.flyfish233.spake2.EntropySource
import kotlin.test.Test
import kotlin.test.assertContentEquals
import kotlin.test.assertEquals
import kotlin.test.assertFalse
import kotlin.test.assertTrue

class PairingSpakeVectorTest {
    @Test fun matchesIndependentBoringSslMessagesAndUnconfirmedKeys() {
        // The expected bytes are immutable external C-oracle results, never Kotlin-generated.
        val vectors = listOf(
            "normal|616c696365|626f62|353135313039|01000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000|1876811ed2c78beb885abcfeee9174e822e056d67474d7f924e5c019d087dc71|e814a51e5e1032ce32bd9e47f74fb58a42f02b61b355e062a36836dbd8de35c5|f1e5cb026ca1dc0780d629cd1747b834bceed4b05417b80f2133a2bd0a0e8b21c1467782f8cab09ba0a20c4a785029dc95c028e20deff35812c01a3a0d8e9cb2",
            "high-bit-carry-2^252|616c696365|626f62|353135313039|00000000000000000000000000000000000000000000000000000000000000100000000000000000000000000000000000000000000000000000000000000000|ae3b60414ba76934aa1f268bfc23d343a0fcc004f1da1f4ab0f0cf191af6fa40|e814a51e5e1032ce32bd9e47f74fb58a42f02b61b355e062a36836dbd8de35c5|94a8e9b7620d03d981cacb1fb8b75337551d07d595cc4fe427e77c3478830a89d7832622732aa35be50b946586e0376b08ce00593cbb973c239747de688e8a97",
            "high-bit-carry-2^252-plus-5|616c696365|626f62|353135313039|05000000000000000000000000000000000000000000000000000000000000100000000000000000000000000000000000000000000000000000000000000000|fa76a5e293956ffd1e7782ead10efb67e5564de8a0ff5c8dfb1a96d9e4eee476|e814a51e5e1032ce32bd9e47f74fb58a42f02b61b355e062a36836dbd8de35c5|d9397e9aa2c7ea8a681206cf7744325d91324086d92561b2e7519d32b5a1035d8899c849c8e96b3d0348ae3798517fc33358be1333a5a219a9e90f2259c8f3bc",
            "order-minus-one|616c696365|626f62|353135313039|ecd3f55c1a631258d69cf7a2def9de14000000000000000000000000000000100000000000000000000000000000000000000000000000000000000000000000|58e879f7c7c7dee563d11a0764f8e323dd0c2f46799b69de637409343c9094c5|e814a51e5e1032ce32bd9e47f74fb58a42f02b61b355e062a36836dbd8de35c5|4cda88ce6753f4dc818b81411b8b12400ac6d038deb1b18c96c4b6e20da80e7b2ceae5eba89db3b9b3de52d9222e2d1fb0049b4c474c3d55d5e2fc9f40666419",
            "aosp-adb-names|616462207061697220636c69656e7400|61646220706169722073657276657200|353135313039|01000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000|1876811ed2c78beb885abcfeee9174e822e056d67474d7f924e5c019d087dc71|e814a51e5e1032ce32bd9e47f74fb58a42f02b61b355e062a36836dbd8de35c5|5c1a3ba6d4176e4f1cce1b33d22d10ea5c94078c35d6adde6b01365f0df35d1f50b7a5ad6910bfc17295e5d1969e502a6141cdc5c7e2cc99b238d786c9275865"
        )
        assertEquals(5, vectors.size)
        for (line in vectors) {
            val v = line.split('|')
            lateinit var transferredEntropy: ByteArray
            val crypto = PairingCrypto(v[1].hex(), v[2].hex(), EntropySource { count ->
                v[4].hex().also { assertEquals(count, it.size); transferredEntropy = it }
            })
            try {
                assertContentEquals(v[5].hex(), crypto.generateMessage(v[3].hex()), "${v[0]} message")
                assertTrue(transferredEntropy.all { it == 0.toByte() }, "Entropy ownership must transfer and be cleared")
                val material = crypto.processMessage(v[6].hex())
                assertContentEquals(v[7].hex(), material, "${v[0]} key")
                material?.fill(0)
            } finally { crypto.destroy() }
        }
    }

    @Test fun operatingSystemEntropyReturnsIndependentOwnedBuffers() {
        val first = securePairingRandomBytes(64)
        val second = securePairingRandomBytes(64)
        try {
            assertEquals(64, first.size)
            assertEquals(64, second.size)
            assertFalse(first === second)
            assertFalse(first.contentEquals(second))
            first.fill(0)
            assertTrue(second.any { it != 0.toByte() })
        } finally { first.fill(0); second.fill(0) }
    }

    private fun String.hex(): ByteArray = ByteArray(length / 2) {
        substring(it * 2, it * 2 + 2).toInt(16).toByte()
    }
}
