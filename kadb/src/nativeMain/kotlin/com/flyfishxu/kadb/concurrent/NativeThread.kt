package com.flyfishxu.kadb.concurrent

/** Starts one detached blocking worker owned by the caller's lifecycle. */
internal expect fun startKadbThread(name: String, block: () -> Unit)
