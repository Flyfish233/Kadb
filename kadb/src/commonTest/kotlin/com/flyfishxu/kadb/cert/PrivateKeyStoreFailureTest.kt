package com.flyfishxu.kadb.cert

import com.flyfishxu.kadb.io.platformFileSystem
import com.flyfishxu.kadb.io.temporaryTestDirectory
import okio.Buffer
import okio.FileMetadata
import okio.ForwardingFileSystem
import okio.IOException
import okio.Path
import okio.Sink
import kotlin.random.Random
import kotlin.test.Test
import kotlin.test.assertContentEquals
import kotlin.test.assertEquals
import kotlin.test.assertFailsWith
import kotlin.test.assertSame
import kotlin.test.assertTrue

class PrivateKeyStoreFailureTest {
    @Test fun partialWriteRemovesStagingFileAndPreservesOriginal() = inDirectory { directory ->
        val destination = directory / "identity.pem"
        val original = "synthetic original".encodeToByteArray()
        platformFileSystem.write(destination) { write(original) }
        val primary = IOException("synthetic partial-write failure")
        val fileSystem = partialWriteFailure(primary)

        val thrown = assertFailsWith<IOException> {
            OkioFilePrivateKeyStore(destination, fileSystem)
                .writePrivateKeyPemAtomic("synthetic replacement".encodeToByteArray())
        }

        assertSame(primary, thrown)
        assertContentEquals(original, platformFileSystem.read(destination) { readByteArray() })
        assertEquals(listOf(destination), platformFileSystem.list(directory), "A failed write must remove its staging file")
    }

    @Test fun cleanupLookupFailureDoesNotReplaceCommitFailure() = inDirectory { directory ->
        val destination = directory / "identity.pem"
        val primary = IOException("synthetic atomic-move failure")
        val cleanup = IOException("synthetic cleanup-lookup failure")
        var failedCommit = false
        val fileSystem = object : ForwardingFileSystem(platformFileSystem) {
            override fun atomicMove(source: Path, target: Path) {
                failedCommit = true
                throw primary
            }
            override fun metadataOrNull(path: Path): FileMetadata? {
                if (failedCommit) throw cleanup
                return super.metadataOrNull(path)
            }
        }

        val thrown = assertFailsWith<IOException> {
            OkioFilePrivateKeyStore(destination, fileSystem)
                .writePrivateKeyPemAtomic("synthetic replacement".encodeToByteArray())
        }

        assertSame(primary, thrown, "Cleanup failure must not replace the failed atomic move")
        assertTrue(failedCommit)
    }

    @Test fun cleanupDeleteFailureDoesNotReplaceWriteFailure() = inDirectory { directory ->
        val destination = directory / "identity.pem"
        val primary = IOException("synthetic partial-write failure")
        val cleanup = IOException("synthetic cleanup-delete failure")
        var deletionAttempted = false
        val fileSystem = object : ForwardingFileSystem(partialWriteFailure(primary)) {
            override fun delete(path: Path, mustExist: Boolean) {
                deletionAttempted = true
                throw cleanup
            }
        }

        val thrown = assertFailsWith<IOException> {
            OkioFilePrivateKeyStore(destination, fileSystem)
                .writePrivateKeyPemAtomic("synthetic replacement".encodeToByteArray())
        }

        assertSame(primary, thrown, "Cleanup failure must not replace the failed write")
        assertTrue(deletionAttempted, "A failed write must attempt to remove its staging file")
    }

    private fun partialWriteFailure(primary: IOException) = object : ForwardingFileSystem(platformFileSystem) {
        override fun sink(file: Path, mustCreate: Boolean): Sink {
            val sink = super.sink(file, mustCreate)
            return object : Sink by sink {
                override fun write(source: Buffer, byteCount: Long) {
                    // Real OS writes leave a partial payload before the injected error.
                    sink.write(source, minOf(byteCount, 3L))
                    throw primary
                }
            }
        }
    }

    private fun inDirectory(block: (Path) -> Unit) {
        val directory = temporaryTestDirectory / "kadb-store-failure-${Random.nextLong().toULong().toString(16)}"
        platformFileSystem.createDirectory(directory, mustCreate = true)
        try {
            block(directory)
        } finally {
            // The real delegate cleans fixtures even when the injected wrapper fails.
            platformFileSystem.deleteRecursively(directory)
        }
    }
}
