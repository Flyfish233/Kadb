package com.flyfishxu.kadb.core

import okio.Buffer
import okio.ByteString.Companion.decodeHex
import okio.EOFException
import okio.IOException
import kotlin.test.Test
import kotlin.test.assertContentEquals
import kotlin.test.assertEquals
import kotlin.test.assertFailsWith

class AdbWireGoldenTest {
    @Test fun stlsHeaderMatchesTheAospWireLayout() {
        // STLS(version=0x01000000, arg1=0), zero payload/checksum, command XOR UINT32_MAX.
        val golden = "53544c5300000001000000000000000000000000acab b3ac".replace(" ", "").decodeHex()
        assertContentEquals(golden.toByteArray(), AdbProtocol.generateStls())
        val output = Buffer()
        AdbWriter(output).writeStls(AdbProtocol.A_STLS_VERSION)
        assertEquals(golden, output.readByteString())
    }

    @Test fun checksumUsesUnsignedBytesAndIsDisabledAfterVersionNegotiation() {
        val payload = byteArrayOf(0x7f, 0x80.toByte(), 0xff.toByte())
        val legacy = Buffer()
        AdbWriter(legacy).writeWrite(1, 2, payload, 0, payload.size)
        assertEquals("57525445010000000200000003000000fe010000a8adabba7f80ff", legacy.readByteString().hex())
        val modern = Buffer()
        AdbWriter(modern).apply {
            updateProtocolVersion(AdbProtocol.A_VERSION_SKIP_CHECKSUM)
            writeWrite(1, 2, payload, 0, payload.size)
        }
        assertEquals("5752544501000000020000000300000000000000a8adabba7f80ff", modern.readByteString().hex())
    }

    @Test fun corruptMagicAndOversizedOrNegativeLengthsFailBeforeReadingPayload() {
        for (length in listOf(-1, Int.MAX_VALUE, 4097)) {
            val input = header(length = length)
            assertFailsWith<IOException> { AdbReader(input, 4096).readMessage() }
        }
        assertFailsWith<IOException> { AdbReader(header(magic = 0)).readMessage() }
        assertFailsWith<EOFException> { AdbReader(header(length = 3).writeByte(1)).readMessage() }
    }

    @Test fun emptyAndBinaryFramesRoundTripWithoutStringConversions() {
        val wire = Buffer()
        val writer = AdbWriter(wire)
        writer.writeOkay(1, 2)
        val payload = ByteArray(256) { it.toByte() }
        writer.writeWrite(1, 2, payload, 0, payload.size)
        val reader = AdbReader(wire)
        assertEquals(0, reader.readMessage().payloadLength)
        assertContentEquals(payload, reader.readMessage().payload)
    }

    private fun header(length: Int = 0, magic: Int = AdbProtocol.CMD_WRTE.inv()): Buffer =
        Buffer().writeIntLe(AdbProtocol.CMD_WRTE).writeIntLe(1).writeIntLe(2)
            .writeIntLe(length).writeIntLe(0).writeIntLe(magic)
}
