package com.flyfishxu.kadb.validation.auth

import com.flyfishxu.kadb.Kadb
import com.flyfishxu.kadb.cert.InMemoryPrivateKeyStore
import com.flyfishxu.kadb.cert.KadbCert
import com.flyfishxu.kadb.exception.AdbAuthException
import com.flyfishxu.kadb.exception.AdbPairAuthException
import okio.FileSystem
import okio.IOException
import okio.Path.Companion.toPath
import kotlin.system.exitProcess
import kotlin.time.TimeSource

/** Public API consumer only. Authentication proof belongs to the independent wire/system driver. */
fun main(arguments: Array<String>) {
    val started = TimeSource.Monotonic.markNow()
    val checks = mutableListOf<String>()
    val store = InMemoryPrivateKeyStore()
    var mode = "invalid"
    var failure: Throwable? = null
    var rejection: IOException? = null
    var fingerprint: String? = null
    var client: Kadb? = null
    var handshakeCompleted = false
    var shellSucceeded = false
    var timeoutMs = 8_000
    var attemptElapsedMs: Long? = null
    var closedReuseElapsedMs: Long? = null

    try {
        require(arguments.size in setOf(8, 10)) {
            "Required: --mode positive|reject --port PORT --private-key FILE --run-id HEX [--socket-timeout-ms MS]"
        }
        val options = linkedMapOf<String, String>()
        arguments.toList().chunked(2).forEach { (key, value) ->
            require(options.put(key, value) == null) { "Duplicate argument $key" }
        }
        require(options.keys == setOf("--mode", "--port", "--private-key", "--run-id") ||
            options.keys == setOf("--mode", "--port", "--private-key", "--run-id", "--socket-timeout-ms"))
        mode = options.getValue("--mode")
        require(mode in setOf("positive", "reject"))
        val port = options.getValue("--port").toInt()
        require(port in 1..65535)
        timeoutMs = options["--socket-timeout-ms"]?.toInt() ?: 8_000
        require(timeoutMs in 1_000..30_000)
        val runId = options.getValue("--run-id")
        require(runId.length == 32 && runId.all { it in "0123456789abcdef" })

        // Explicitly exclude additional identities and persistent stores from this process.
        KadbCert.configure(store, additionalPrivateKeysPem = emptyList())
        val pem = FileSystem.SYSTEM.read(options.getValue("--private-key").toPath()) { readByteArray() }
        try {
            val identity = KadbCert.importPrivateKey(pem)
            fingerprint = identity.fingerprintSha256
            identity.privateKeyPem.fill(0)
        } finally {
            pem.fill(0)
        }
        checks += "identity_import"

        // Kadb.create is lazy. Retain this exact object even if its handshake fails.
        val current = Kadb.create("127.0.0.1", port, connectTimeout = 5_000, socketTimeout = timeoutMs)
        client = current
        check(!current.connectionCheck())
        checks += "initially_disconnected"
        val attemptStarted = TimeSource.Monotonic.markNow()
        if (mode == "positive") {
            current.supportsFeature("shell_v2") // Completes this connection's actual ADB handshake.
            handshakeCompleted = true
            check(current.connectionCheck())
            checks += "authenticated_connection"
            val marker = "kadb-m4-$runId"
            val response = current.shell("printf $marker")
            check(response.exitCode == 0 && response.errorOutput.isEmpty() && response.output == marker)
            shellSucceeded = true
            checks += "shell_marker"
        } else {
            try {
                current.supportsFeature("shell_v2")
                handshakeCompleted = true
            } catch (error: IOException) {
                rejection = error
            }
            // A connection followed by a failing shell is not an identity rejection.
            check(!handshakeCompleted) { "Unexpected successful ADB handshake for rejected identity" }
            check(rejection != null) { "No I/O rejection was observed" }
            checks += "connection_attempt_rejected"
            check(!current.connectionCheck())
            checks += "failed_connection_not_open"
        }
        attemptElapsedMs = attemptStarted.elapsedNow().inWholeMilliseconds
        check(attemptElapsedMs <= timeoutMs * 2L + 5_000) { "Connection attempt exceeded its bounded deadline" }
        checks += "attempt_bounded"

        current.close()
        check(!current.connectionCheck())
        checks += "connection_closed"
        val reuseStarted = TimeSource.Monotonic.markNow()
        var closedError: IOException? = null
        try {
            current.supportsFeature("shell_v2")
        } catch (error: IOException) {
            closedError = error
        }
        closedReuseElapsedMs = reuseStarted.elapsedNow().inWholeMilliseconds
        check(closedError?.message == "Kadb is closed") { "Closed client became reusable or failed for another reason" }
        check(closedReuseElapsedMs < 1_000) { "Closed-client operation did not reject promptly" }
        check(!current.connectionCheck())
        checks += "closed_client_reuse_rejected"
    } catch (error: Throwable) {
        failure = error
        error.printStackTrace()
    } finally {
        try {
            client?.close()
            KadbCert.clear()
            store.clear()
            check(KadbCert.exportIdentityOrNull() == null)
            checks += "temporary_identity_cleared"
        } catch (cleanup: Throwable) {
            if (failure == null) failure = cleanup
        }
    }

    val fields = linkedMapOf(
        "schema" to "1",
        "status" to quote(if (failure == null) "passed" else "failed"),
        "mode" to quote(mode),
        "checks_executed" to checks.size.toString(),
        "checks" to checks.joinToString(prefix = "[", postfix = "]", transform = ::quote),
        // This identifies the regenerated certificate, not the stable ADB RSA public key.
        "certificate_fingerprint_sha256" to (fingerprint?.let(::quote) ?: "null"),
        "adb_handshake_completed" to handshakeCompleted.toString(),
        "shell_succeeded" to shellSucceeded.toString(),
        "rejection_type" to (rejection?.let { quote(it::class.simpleName ?: "IOException") } ?: "null"),
        "rejection_message" to (rejection?.message?.let(::quote) ?: "null"),
        "rejection_category" to (rejection?.let { quote(classify(it)) } ?: "null"),
        "rejection_alone_proves_authentication" to "false",
        "socket_timeout_ms" to timeoutMs.toString(),
        "attempt_elapsed_ms" to (attemptElapsedMs?.toString() ?: "null"),
        "closed_reuse_elapsed_ms" to (closedReuseElapsedMs?.toString() ?: "null"),
        "elapsed_ms" to started.elapsedNow().inWholeMilliseconds.toString(),
        "error_type" to (failure?.let { quote(it::class.simpleName ?: "Throwable") } ?: "null"),
        "error" to (failure?.message?.let(::quote) ?: "null"),
        "physical_device" to "false",
    )
    println("KADB_AUTH_JSON " + fields.entries.joinToString(prefix = "{", postfix = "}") {
        "${quote(it.key)}:${it.value}"
    })
    if (failure != null) exitProcess(1)
}

private fun classify(error: IOException): String {
    if (error is AdbPairAuthException) return "tls_authentication_error_mapping"
    if (error is AdbAuthException) return "adb_authentication_error_mapping"
    val message = error.message.orEmpty().lowercase()
    return when {
        "timed out" in message || "timeout" in message -> "io_timeout"
        "tls" in message || "ssl" in message || "certificate" in message -> "tls_io_error"
        "refused" in message || "unreachable" in message -> "network_connect_error"
        "closed" in message || "reset" in message || "eof" in message || "ended" in message -> "peer_closed_or_reset"
        else -> "other_io_error"
    }
}

private fun quote(value: String): String = buildString {
    append('"')
    value.forEach {
        when (it) {
            '"' -> append("\\\"")
            '\\' -> append("\\\\")
            '\n' -> append("\\n")
            '\r' -> append("\\r")
            '\t' -> append("\\t")
            else -> if (it.code < 32) append("\\u" + it.code.toString(16).padStart(4, '0')) else append(it)
        }
    }
    append('"')
}
