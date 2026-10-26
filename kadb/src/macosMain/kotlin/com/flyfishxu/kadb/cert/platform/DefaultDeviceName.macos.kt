package com.flyfishxu.kadb.cert.platform

import platform.Foundation.NSProcessInfo

actual fun defaultDeviceName(software: String?): String {
    software?.trim()?.takeIf { it.isNotEmpty() }?.let { return it }
    val process = NSProcessInfo.processInfo
    return formatDefaultDeviceName(process.processName, process.hostName)
}
