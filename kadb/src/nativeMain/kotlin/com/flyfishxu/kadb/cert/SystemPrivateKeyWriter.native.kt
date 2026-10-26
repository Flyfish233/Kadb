@file:OptIn(kotlinx.cinterop.ExperimentalForeignApi::class)

package com.flyfishxu.kadb.cert

import com.flyfishxu.kadb.nativebridge.kadb_create_private_temp
import com.flyfishxu.kadb.nativebridge.kadb_commit_private_temp
import com.flyfishxu.kadb.nativebridge.kadb_remove_private_temp
import kotlinx.cinterop.*
import okio.FileSystem
import okio.IOException
import okio.Path
import platform.posix.*

internal actual fun writeSystemPrivateKeyAtomically(fileSystem: FileSystem, path: Path, payload: ByteArray): Boolean {
    // A caller-supplied FileSystem may be virtual, encrypted or remote. Never
    // bypass its semantics by issuing unrelated POSIX operations on its paths.
    if (fileSystem !== FileSystem.SYSTEM) return false
    val destination = path.toString()
    if ('\u0000' in destination) throw IOException("Private-key path contains NUL")
    path.parent?.let { fileSystem.createDirectories(it) }
    return memScoped {
        val template = "$destination.tmp-XXXXXX".cstr.ptr
        // mkostemp creates a new, exclusive 0600 file with CLOEXEC atomically.
        var descriptor = kadb_create_private_temp(template)
        if (descriptor < 0) throw privateFileFailure("Create private-key staging file")
        var committed = false
        try {
            if (fchmod(descriptor, 0x180.convert()) != 0) throw privateFileFailure("Protect private-key staging file")
            val metadata = alloc<stat>()
            if (fstat(descriptor, metadata.ptr) != 0) throw privateFileFailure("Check private-key staging file")
            if ((metadata.st_mode.toInt() and 0x1ff) != 0x180) {
                throw IOException("Private-key filesystem did not enforce mode 0600")
            }
            payload.usePinned { bytes ->
                var offset = 0
                while (offset < payload.size) {
                    val written = write(descriptor, bytes.addressOf(offset), (payload.size - offset).convert())
                    if (written < 0 && errno == EINTR) continue
                    if (written < 0) throw privateFileFailure("Write private-key staging file")
                    if (written == 0L) throw IOException("Private-key staging write made no progress")
                    offset += written.toInt()
                }
            }
            while (fsync(descriptor) != 0) {
                if (errno != EINTR) throw privateFileFailure("Flush private-key staging file")
            }
            val closing = descriptor
            descriptor = -1
            // Do not retry a failed close: the OS may already have recycled fd.
            if (close(closing) != 0) throw privateFileFailure("Close private-key staging file")
            if (kadb_commit_private_temp(template, destination) != 0) throw privateFileFailure("Replace private-key file")
            committed = true
            true
        } finally {
            if (descriptor >= 0) close(descriptor)
            if (!committed) kadb_remove_private_temp(template)
        }
    }
}

private fun privateFileFailure(operation: String): IOException {
    val code = errno
    return IOException("$operation: ${strerror(code)?.toKString() ?: "errno $code"}")
}
