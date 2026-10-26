package com.flyfishxu.kadb

import com.flyfishxu.kadb.shell.AdbShellResponse
import okio.Path.Companion.toPath

/**
 * Synchronous, throwing Swift/Objective-C entry points for a caller-owned [Kadb].
 *
 * These methods directly invoke the shared implementation inside the Kotlin exception boundary.
 * Ordinary [Exception] failures are exported as NSError/Swift Error; fatal [Error] failures are
 * not intercepted. Existing Kadb declarations and Objective-C selectors remain unchanged.
 *
 * The adapter does not create another connection. [close] closes the underlying Kadb, including
 * its shared transport; it consequently affects every caller using that same Kadb instance.
 * Methods block just like Kadb's synchronous methods, so callers choose an appropriate thread.
 * Raw stream APIs are intentionally outside this adapter's exception boundary.
 */
class KadbApple(private val client: Kadb) {
    companion object {
        /** The suspending pairing lifetime and password cleanup remain owned by common Kadb. */
        @Throws(Exception::class)
        suspend fun pair(host: String, port: Int, pairingCode: String, name: String) =
            Kadb.pair(host, port, pairingCode, name)
    }

    @Throws(Exception::class)
    fun shell(command: String): AdbShellResponse = client.shell(command)

    /** Preserve Kadb's default file mode and timestamp lookup. */
    @Throws(Exception::class)
    fun push(localPath: String, remotePath: String) = client.push(localPath.toPath(), remotePath)

    @Throws(Exception::class)
    fun push(localPath: String, remotePath: String, mode: Int, lastModifiedMs: Long) =
        client.push(localPath.toPath(), remotePath, mode, lastModifiedMs)

    @Throws(Exception::class)
    fun pull(localPath: String, remotePath: String) = client.pull(localPath.toPath(), remotePath)

    /** Lists bridge to NSArray/Swift arrays; callers pass an empty options list when unnecessary. */
    @Throws(Exception::class)
    fun install(localPath: String, options: List<String>) =
        client.install(localPath.toPath(), *options.toTypedArray())

    @Throws(Exception::class)
    fun installMultiple(localPaths: List<String>, options: List<String>) =
        client.installMultiple(localPaths.map { it.toPath() }, *options.toTypedArray())

    @Throws(Exception::class)
    fun uninstall(packageName: String) = client.uninstall(packageName)

    @Throws(Exception::class)
    fun resetConnection() = client.resetConnection()

    @Throws(Exception::class)
    fun close() = client.close()
}
