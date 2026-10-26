package com.flyfishxu.kadb

/** Owns an already-created session until APK writes return normally. */
internal inline fun <T> runInstallWrites(abandonSession: () -> Unit, writeApks: () -> T): T =
    try {
        writeApks()
    } catch (failure: Throwable) {
        try {
            abandonSession()
        } catch (cleanup: Throwable) {
            // A broken transport can report the same exception for both operations.
            if (cleanup !== failure) failure.addSuppressed(cleanup)
        }
        throw failure
    }
