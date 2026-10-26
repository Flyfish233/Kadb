package com.flyfishxu.kadb.cert

import okio.FileSystem
import okio.Path

// Preserve the existing Android/JVM and custom-FileSystem behavior.
internal actual fun writeSystemPrivateKeyAtomically(fileSystem: FileSystem, path: Path, payload: ByteArray): Boolean = false
