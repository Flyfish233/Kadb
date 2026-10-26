package com.flyfishxu.kadb.shell

import com.flyfishxu.kadb.core.AdbReader
import com.flyfishxu.kadb.core.AdbWriter
import com.flyfishxu.kadb.queue.AdbMessageQueue
import com.flyfishxu.kadb.stream.AdbStream
import okio.Buffer
import kotlin.test.Test
import kotlin.test.assertEquals

class AdbShellEncodingTest {
    @Test fun utf8CodePointsMayCrossShellPacketsAndInterleavedStderr() {
        val stdout = "你好🌍\n".encodeToByteArray()
        val stderr = "错误é".encodeToByteArray()
        val wire = Buffer()
        for (index in 0 until maxOf(stdout.size, stderr.size)) {
            if (index < stdout.size) wire.packet(1, byteArrayOf(stdout[index]))
            if (index < stderr.size) wire.packet(2, byteArrayOf(stderr[index]))
        }
        wire.packet(3, byteArrayOf(201.toByte()))
        read(wire) { result ->
            assertEquals("你好🌍\n", result.output)
            assertEquals("错误é", result.errorOutput)
            assertEquals(201, result.exitCode)
        }
    }

    @Test fun incompleteUtf8AtExitRetainsTheExistingReplacementPolicy() {
        val wire = Buffer().packet(1, byteArrayOf(0xe4.toByte())).packet(3, byteArrayOf(0))
        read(wire) { result ->
            assertEquals("\uFFFD", result.output)
            assertEquals("", result.errorOutput)
        }
    }

    private fun Buffer.packet(id: Int, payload: ByteArray): Buffer =
        writeByte(id).writeIntLe(payload.size).write(payload)

    private inline fun read(wire: Buffer, check: (AdbShellResponse) -> Unit) {
        // Feed the real shell decoder through the stream's existing read buffer.
        // No socket or ADB peer is claimed by this portable framing test.
        val queue = AdbMessageQueue(AdbReader(Buffer())) {}
        val stream = AdbStream(queue, AdbWriter(Buffer()), 4096, 1, 2)
        stream.source.buffer.writeAll(wire)
        try {
            check(AdbShellStream(stream).readAll())
        } finally {
            stream.close()
            queue.close()
        }
    }
}
