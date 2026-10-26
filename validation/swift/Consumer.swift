import Foundation
import Kadb

// This is an external Swift compilation against the produced static framework.
// It cannot see internal Kotlin declarations or use test friend modules.
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

// Exercise Native exception export, not an uncaught Kotlin process abort.
// A bad port is deterministic; the callback must report an error. Pump the main
// run loop because Native dispatches suspend completion there for Swift callers.
var completed = false
var rejected = false
Kadb.companion.pair(host: "127.0.0.1", port: 0, pairingCode: "123456", name: "swift-consumer") { error in
    rejected = error != nil
    completed = true
}
let deadline = Date().addingTimeInterval(20)
while !completed && Date() < deadline {
    RunLoop.current.run(until: Date().addingTimeInterval(0.01))
}
precondition(completed && rejected, "Expected pairing error callback before the deadline")
print("SWIFT_CONSUMER_OK model identity pairing-error-callback")
