package com.flyfishxu.kadb.transport

import com.flyfishxu.kadb.TcpKeepAlive
import com.flyfishxu.kadb.concurrent.runClosingOnCancellation

internal actual object TransportFactory {
    actual suspend fun connect(host: String, port: Int, connectTimeoutMs: Long, tcpKeepAlive: TcpKeepAlive?): TransportChannel {
        val channel = PosixTransportChannel.create()
        return runClosingOnCancellation(channel::close) {
            channel.connectTo(host, port, connectTimeoutMs, tcpKeepAlive)
            channel
        }
    }
}
