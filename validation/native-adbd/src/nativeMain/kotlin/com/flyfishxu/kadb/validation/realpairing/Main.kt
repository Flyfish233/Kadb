package com.flyfishxu.kadb.validation.realpairing

import com.flyfishxu.kadb.Kadb
import com.flyfishxu.kadb.cert.InMemoryPrivateKeyStore
import com.flyfishxu.kadb.cert.KadbCert
import kotlinx.coroutines.runBlocking
import kotlinx.coroutines.withTimeout
import okio.FileSystem
import okio.IOException
import okio.Path.Companion.toPath
import kotlin.system.exitProcess
import kotlin.time.TimeSource

/** External compilation, public APIs only. The driver establishes the actual peer identity. */
fun main(arguments: Array<String>) {
    val started = TimeSource.Monotonic.markNow()
    val checks = mutableListOf<String>()
    var mode = "invalid"
    var rejectionType: String? = null
    var rejectionMessage: String? = null
    var fingerprint: String? = null
    var failure: Throwable? = null
    val store = InMemoryPrivateKeyStore()
    try {
        require(arguments.size == 10) { "Required: --mode pair|reject|connect --port PORT --private-key FILE --code-file FILE --run-id HEX" }
        val options = arguments.toList().chunked(2).associate { it[0] to it[1] }
        require(options.keys == setOf("--mode", "--port", "--private-key", "--code-file", "--run-id"))
        mode = options.getValue("--mode")
        require(mode in setOf("pair", "reject", "connect"))
        val port = options.getValue("--port").toInt()
        require(port in 1..65535)
        val runId = options.getValue("--run-id")
        require(runId.length == 32 && runId.all { it in "0123456789abcdef" })
        KadbCert.configure(store)
        val pem = FileSystem.SYSTEM.read(options.getValue("--private-key").toPath()) { readByteArray() }
        try {
            val identity = KadbCert.importPrivateKey(pem)
            fingerprint = identity.fingerprintSha256
            identity.privateKeyPem.fill(0)
        } finally {
            pem.fill(0)
        }
        checks += "identity_import"
        if (mode == "connect") {
            val client = Kadb.create("127.0.0.1", port, connectTimeout = 5_000, socketTimeout = 10_000)
            try {
                val response = client.shell("printf kadb-real-pair-$runId")
                check(response.exitCode == 0 && response.errorOutput.isEmpty())
                check(response.output == "kadb-real-pair-$runId")
                checks += "paired_connection_shell"
            } finally {
                client.close()
            }
            check(!client.connectionCheck())
            checks += "connection_closed"
        } else {
            val codeBytes = FileSystem.SYSTEM.read(options.getValue("--code-file").toPath()) { readByteArray() }
            try {
                val code = codeBytes.decodeToString().trim()
                require(code.length == 6 && code.all { it in '0'..'9' })
                runBlocking {
                    // A bounded public seam also exercises cancellation's close-and-join ownership.
                    withTimeout(20_000) {
                        if (mode == "pair") {
                            Kadb.pair("127.0.0.1", port, code, "kadb-m3-$runId")
                            checks += "real_aosp_public_pair_returned"
                        } else {
                            try {
                                Kadb.pair("127.0.0.1", port, code, "kadb-m3-$runId")
                                error("Incorrect pairing code was accepted")
                            } catch (error: IOException) {
                                rejectionType = error::class.simpleName
                                rejectionMessage = error.message
                                checks += "public_pair_rejected"
                            }
                        }
                    }
                }
            } finally {
                codeBytes.fill(0)
            }
        }
    } catch (error: Throwable) {
        failure = error
        error.printStackTrace()
    } finally {
        try {
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
        "identity_fingerprint_sha256" to (fingerprint?.let(::quote) ?: "null"),
        "rejection_type" to (rejectionType?.let(::quote) ?: "null"),
        "rejection_message" to (rejectionMessage?.let(::quote) ?: "null"),
        "error_type" to (failure?.let { quote(it::class.simpleName ?: "Throwable") } ?: "null"),
        "elapsed_ms" to started.elapsedNow().inWholeMilliseconds.toString(),
        "physical_device" to "false",
    )
    println("KADB_REAL_PAIRING_JSON " + fields.entries.joinToString(prefix = "{", postfix = "}") {
        "${quote(it.key)}:${it.value}"
    })
    if (failure != null) exitProcess(1)
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
