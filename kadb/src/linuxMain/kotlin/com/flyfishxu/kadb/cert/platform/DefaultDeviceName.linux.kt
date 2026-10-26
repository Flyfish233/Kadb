@file:OptIn(kotlinx.cinterop.ExperimentalForeignApi::class)

package com.flyfishxu.kadb.cert.platform

import kotlinx.cinterop.*
import platform.posix.gethostname

actual fun defaultDeviceName(software: String?): String {
    software?.trim()?.takeIf { it.isNotEmpty() }?.let { return it }
    val host = memScoped {
        val name = allocArray<ByteVar>(256)
        if (gethostname(name, 255.convert()) == 0) {
            name[255] = 0
            name.toKString()
        } else "Linux"
    }
    return formatDefaultDeviceName("Kadb", host)
}
