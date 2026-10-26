import Foundation
import Darwin
import Dispatch
import Kadb

// This is an external Swift compilation against the produced static framework.
// It cannot see internal Kotlin declarations or use test friend modules.
private final class LockedValue<Value: Sendable>: @unchecked Sendable {
    private let lock = NSLock()
    private var value: Value
    init(_ value: Value) { self.value = value }
    func update(_ body: (inout Value) -> Void) {
        lock.lock()
        defer { lock.unlock() }
        body(&value)
    }
    func snapshot() -> Value {
        lock.lock()
        defer { lock.unlock() }
        return value
    }
}

private struct PairingStatus: Sendable {
    var completed = false
    var rejected = false
}

private struct PeerStatus: Sendable {
    var command = ""
    var payloadBytes = 0
    var failure: String?
}

private enum PeerFailure: Error {
    case systemCall(String, Int32)
    case invalidFrame(String)
    case deadline
}

// The worker owns both descriptors. It records a complete CNXN before closing
// the accepted socket, so a client-side precondition error cannot pass this test.
private final class DisconnectingAdbPeer {
    let port: Int32
    private let status = LockedValue(PeerStatus())
    private let finished = DispatchGroup()

    init() throws {
        let listener = Darwin.socket(AF_INET, SOCK_STREAM, 0)
        guard listener >= 0 else { throw PeerFailure.systemCall("socket", errno) }
        var transferred = false
        defer { if !transferred { Darwin.close(listener) } }

        var address = sockaddr_in()
        address.sin_len = UInt8(MemoryLayout<sockaddr_in>.size)
        address.sin_family = sa_family_t(AF_INET)
        address.sin_port = 0
        address.sin_addr.s_addr = inet_addr("127.0.0.1")
        let bound = withUnsafePointer(to: &address) { pointer in
            pointer.withMemoryRebound(to: sockaddr.self, capacity: 1) {
                Darwin.bind(listener, $0, socklen_t(MemoryLayout<sockaddr_in>.size))
            }
        }
        guard bound == 0 else { throw PeerFailure.systemCall("bind", errno) }
        guard Darwin.listen(listener, 1) == 0 else { throw PeerFailure.systemCall("listen", errno) }
        var length = socklen_t(MemoryLayout<sockaddr_in>.size)
        let named = withUnsafeMutablePointer(to: &address) { pointer in
            pointer.withMemoryRebound(to: sockaddr.self, capacity: 1) {
                Darwin.getsockname(listener, $0, &length)
            }
        }
        guard named == 0 else { throw PeerFailure.systemCall("getsockname", errno) }
        port = Int32(UInt16(bigEndian: address.sin_port))
        precondition(port > 0)

        let status = self.status
        let finished = self.finished
        finished.enter()
        DispatchQueue(label: "kadb-swift-disconnecting-peer").async {
            defer {
                Darwin.close(listener)
                finished.leave()
            }
            do {
                try Self.awaitConnection(listener)
                let accepted = Darwin.accept(listener, nil, nil)
                guard accepted >= 0 else { throw PeerFailure.systemCall("accept", errno) }
                defer {
                    Darwin.shutdown(accepted, SHUT_RDWR)
                    Darwin.close(accepted)
                }
                var timeout = timeval(tv_sec: 5, tv_usec: 0)
                let configured = withUnsafePointer(to: &timeout) {
                    Darwin.setsockopt(accepted, SOL_SOCKET, SO_RCVTIMEO, $0,
                                      socklen_t(MemoryLayout<timeval>.size))
                }
                guard configured == 0 else { throw PeerFailure.systemCall("setsockopt", errno) }
                let header = try Self.readExactly(accepted, count: 24)
                let command = Self.littleEndianWord(header, at: 0)
                let payloadBytes = Int(Self.littleEndianWord(header, at: 12))
                guard command == 0x4e584e43,
                      Self.littleEndianWord(header, at: 20) == (command ^ UInt32.max),
                      payloadBytes > 0, payloadBytes <= 4096 else {
                    throw PeerFailure.invalidFrame("Expected a bounded CNXN frame")
                }
                _ = try Self.readExactly(accepted, count: payloadBytes)
                status.update {
                    $0.command = "CNXN"
                    $0.payloadBytes = payloadBytes
                }
                // Deliberately send no reply. The deferred shutdown/close is the
                // source of the client's real transport EOF/IOException.
            } catch {
                status.update { $0.failure = String(describing: error) }
            }
        }
        transferred = true
    }

    func join() -> PeerStatus {
        precondition(finished.wait(timeout: .now() + 12) == .success,
                     "The loopback peer worker did not exit")
        return status.snapshot()
    }

    private static func awaitConnection(_ descriptor: Int32) throws {
        let deadline = DispatchTime.now().uptimeNanoseconds + 5_000_000_000
        while true {
            let now = DispatchTime.now().uptimeNanoseconds
            guard now < deadline else { throw PeerFailure.deadline }
            let remaining = Int32(max(1, (deadline - now) / 1_000_000))
            var pending = pollfd(fd: descriptor, events: Int16(POLLIN), revents: 0)
            let ready = Darwin.poll(&pending, 1, remaining)
            if ready > 0 {
                guard pending.revents & Int16(POLLIN) != 0 else {
                    throw PeerFailure.invalidFrame("Listener poll did not report a connection")
                }
                return
            }
            if ready == 0 { throw PeerFailure.deadline }
            if errno != EINTR { throw PeerFailure.systemCall("poll", errno) }
        }
    }

    private static func readExactly(_ descriptor: Int32, count: Int) throws -> [UInt8] {
        var bytes = [UInt8](repeating: 0, count: count)
        var offset = 0
        while offset < count {
            let received = bytes.withUnsafeMutableBytes { buffer in
                Darwin.recv(descriptor, buffer.baseAddress!.advanced(by: offset), count - offset, 0)
            }
            if received < 0 && errno == EINTR { continue }
            guard received > 0 else {
                throw PeerFailure.invalidFrame("Client closed or timed out before complete CNXN")
            }
            offset += received
        }
        return bytes
    }

    private static func littleEndianWord(_ bytes: [UInt8], at offset: Int) -> UInt32 {
        (0..<4).reduce(UInt32(0)) { result, index in
            result | (UInt32(bytes[offset + index]) << (index * 8))
        }
    }
}

private func testSocketDisconnectExportsIOException() throws {
    let peer = try DisconnectingAdbPeer()
    let options = KadbOptions(delayedAckMode: DelayedAckMode.aospDefault, tcpKeepAlive: nil)
    let client = Kadb.companion.create(host: "127.0.0.1", port: peer.port,
                                       connectTimeout: 2000, socketTimeout: 2000, options: options)
    let operations = KadbApple(client: client)
    var operationError: NSError?
    do {
        _ = try operations.shell(command: "echo socket-eof-must-fail")
    } catch {
        operationError = error as NSError
    }
    let cleanup = Result { try operations.close() }
    let observed = peer.join()
    try cleanup.get()
    precondition(observed.failure == nil, "Loopback peer failed: \(observed.failure ?? "")")
    precondition(observed.command == "CNXN" && observed.payloadBytes > 0,
                 "The peer must receive the client's complete CNXN before disconnecting")
    precondition(operationError?.kotlinException is OkioIOException,
                 "Expected the socket EOF to reach Swift as an NSError backed by IOException")
    print("SWIFT_SOCKET_EOF_OK command=\(observed.command) payloadBytes=\(observed.payloadBytes) peerJoined=true")
}

let response = AdbShellResponse(output: "你好🌍", errorOutput: "stderr", exitCode: 7)
precondition(response.output == "你好🌍")
precondition(response.allOutput == "你好🌍stderr")
precondition(response.exitCode == 7)
let keepAlive = TcpKeepAlive(idleSeconds: 1, intervalSeconds: 2, probeCount: 3)
precondition(keepAlive.probeCount == 3)
let identity = KadbCert.shared.ensureReady()
precondition(identity.privateKeyPem.size > 0)
precondition(identity.certificatePem.size > 0)
precondition(!identity.fingerprintSha256.isEmpty)

// Pump the main run loop so either a main-thread or background completion can
// finish. Callback state is locked; no assumption about its thread is required.
private let pairing = LockedValue(PairingStatus())
KadbApple.companion.pair(host: "127.0.0.1", port: 0, pairingCode: "123456", name: "swift-consumer") { error in
    pairing.update {
        $0.rejected = error != nil
        $0.completed = true
    }
}
let deadline = DispatchTime.now().uptimeNanoseconds + 20_000_000_000
while !pairing.snapshot().completed && DispatchTime.now().uptimeNanoseconds < deadline {
    RunLoop.current.run(until: Date().addingTimeInterval(0.01))
}
private let pairingResult = pairing.snapshot()
precondition(pairingResult.completed && pairingResult.rejected,
             "Expected pairing error callback before the deadline")
try testSocketDisconnectExportsIOException()
print("SWIFT_CONSUMER_OK model identity pairing-error-callback shell-io-error-loopback-peer-joined")
