package com.flyfishxu.kadb.io

import okio.Path

internal actual val temporaryTestDirectory: Path get() = okio.FileSystem.SYSTEM_TEMPORARY_DIRECTORY
