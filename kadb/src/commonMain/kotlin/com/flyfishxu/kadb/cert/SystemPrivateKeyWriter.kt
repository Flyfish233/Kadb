package com.flyfishxu.kadb.cert

import okio.FileSystem
import okio.Path

/** Returns true when the platform securely handled the system filesystem write. */
internal expect fun writeSystemPrivateKeyAtomically(fileSystem: FileSystem, path: Path, payload: ByteArray): Boolean
