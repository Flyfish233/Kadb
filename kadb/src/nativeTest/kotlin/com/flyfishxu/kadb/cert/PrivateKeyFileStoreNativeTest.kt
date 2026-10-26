@file:OptIn(kotlinx.cinterop.ExperimentalForeignApi::class)

package com.flyfishxu.kadb.cert

import com.flyfishxu.kadb.nativebridge.kadb_create_private_temp
import com.flyfishxu.kadb.nativebridge.kadb_remove_private_temp
import kotlinx.cinterop.*
import okio.FileSystem
import okio.Path
import okio.Path.Companion.toPath
import platform.posix.*
import kotlin.test.*

class PrivateKeyFileStoreNativeTest {
    @Test fun stagingDescriptorStartsOwnerOnlyAndCloseOnExec() = inPrivateDirectory { directory ->
        memScoped {
            val template = (directory / "staging-XXXXXX").toString().cstr.ptr
            val descriptor = kadb_create_private_temp(template)
            assertTrue(descriptor >= 0)
            try {
                val flags = fcntl(descriptor, F_GETFD)
                assertTrue(flags >= 0 && (flags and FD_CLOEXEC) != 0)
                val metadata = alloc<stat>()
                assertEquals(0, fstat(descriptor, metadata.ptr))
                assertEquals(0x180, metadata.st_mode.toInt() and 0x1ff)
            } finally {
                close(descriptor)
                kadb_remove_private_temp(template)
            }
        }
    }

    @Test fun privateKeyIsOwnerOnlyAndSurvivesAtomicReplacement() = inPrivateDirectory { directory ->
        val path = directory / "identity.pem"
        val store = OkioFilePrivateKeyStore(path)
        val first = "private fixture one".encodeToByteArray()
        val second = "private fixture two".encodeToByteArray()
        store.writePrivateKeyPemAtomic(first)
        assertContentEquals(first, store.readPrivateKeyPem())
        assertOwnerOnly(path)
        store.writePrivateKeyPemAtomic(second)
        assertContentEquals(second, store.readPrivateKeyPem())
        assertOwnerOnly(path)
        assertEquals(listOf(path), FileSystem.SYSTEM.list(directory))
    }

    @Test fun replacingSymlinkDoesNotOverwriteItsTarget() = inPrivateDirectory { directory ->
        val path = directory / "identity.pem"
        val target = directory / "unrelated.txt"
        FileSystem.SYSTEM.write(target) { writeUtf8("sentinel") }
        FileSystem.SYSTEM.createSymlink(path, target)
        val bytes = "private fixture".encodeToByteArray()
        OkioFilePrivateKeyStore(path).writePrivateKeyPemAtomic(bytes)
        assertEquals("sentinel", FileSystem.SYSTEM.read(target) { readUtf8() })
        assertNull(FileSystem.SYSTEM.metadata(path).symlinkTarget)
        assertContentEquals(bytes, OkioFilePrivateKeyStore(path).readPrivateKeyPem())
        assertOwnerOnly(path)
    }

    @Test fun failedRenameLeavesNoPlaintextStagingFile() = inPrivateDirectory { directory ->
        val destination = directory / "directory"
        FileSystem.SYSTEM.createDirectory(destination)
        assertFailsWith<okio.IOException> {
            OkioFilePrivateKeyStore(destination).writePrivateKeyPemAtomic("private fixture".encodeToByteArray())
        }
        assertEquals(listOf(destination), FileSystem.SYSTEM.list(directory))
    }

    private fun assertOwnerOnly(path: Path) = memScoped {
        val metadata = alloc<stat>()
        assertEquals(0, stat(path.toString(), metadata.ptr))
        assertEquals(0x180, metadata.st_mode.toInt() and 0x1ff, "Private PEM mode must be 0600")
    }

    private fun inPrivateDirectory(block: (Path) -> Unit) = memScoped {
        val pattern = (FileSystem.SYSTEM_TEMPORARY_DIRECTORY / "kadb-private-key-XXXXXX").toString().cstr.ptr
        val created = mkdtemp(pattern) ?: error("Unable to create private temporary directory")
        val directory = created.toKString().toPath()
        // Native tests run sequentially in their own process. Verify the store
        // enforces 0600 itself even under a permissive ambient umask.
        val previousMask = umask(0.convert())
        try {
            block(directory)
        } finally {
            umask(previousMask)
            FileSystem.SYSTEM.deleteRecursively(directory)
        }
    }
}
