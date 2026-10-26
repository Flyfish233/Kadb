package com.flyfishxu.kadb.transport

import com.flyfishxu.kadb.cert.HostKeySet
import com.flyfishxu.kadb.concurrent.runClosingOnCancellation

internal actual suspend fun upgradeTls(
    channel: TransportChannel, host: String, port: Int, keys: HostKeySet, timeoutMs: Long
): TransportChannel {
    val socket = channel as PosixTransportChannel
    return runClosingOnCancellation(socket::close) {
        socket.startTls(keys.keyPairs, timeoutMs)
        socket
    }
}

internal actual fun mapInitialTlsReadError(error: Throwable): Throwable = error
