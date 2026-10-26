@file:OptIn(kotlinx.cinterop.ExperimentalForeignApi::class)

package com.flyfishxu.kadb.core

import kotlinx.cinterop.toKString
import platform.posix.getenv

internal actual fun aospDefaultDelayedAckEnabled(): Boolean = getenv("ADB_BURST_MODE")?.toKString() == "1"
