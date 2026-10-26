package com.flyfishxu.kadb

/** The write phase of an already-created PackageInstaller session. */
@Suppress("UNUSED_PARAMETER") // Baseline extraction: the following regression commit supplies cleanup.
internal inline fun <T> runInstallWrites(abandonSession: () -> Unit, writeApks: () -> T): T = writeApks()
