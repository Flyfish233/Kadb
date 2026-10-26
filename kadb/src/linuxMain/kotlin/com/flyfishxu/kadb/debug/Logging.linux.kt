@file:OptIn(kotlinx.cinterop.ExperimentalForeignApi::class)

package com.flyfishxu.kadb.debug

import kotlinx.cinterop.toKString
import platform.posix.getenv
import platform.posix.pthread_self

internal actual val loggingEnabled: Boolean = getenv("KADB_LOGGING")?.toKString() == "true"
internal actual fun currentThreadName(): String = "kadb-${pthread_self()}"
