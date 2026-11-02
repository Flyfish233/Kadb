package com.flyfishxu.kadb.validation.pairing

import com.flyfishxu.kadb.Kadb
import com.flyfishxu.kadb.cert.InMemoryPrivateKeyStore
import com.flyfishxu.kadb.cert.KadbCert
import kotlinx.cinterop.ExperimentalForeignApi
import kotlinx.cinterop.toKString
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.TimeoutCancellationException
import kotlinx.coroutines.cancelAndJoin
import kotlinx.coroutines.coroutineScope
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import kotlinx.coroutines.runBlocking
import kotlinx.coroutines.withTimeout
import okio.IOException
import platform.posix.getenv
import kotlin.system.exitProcess
import kotlin.time.TimeSource

/** Mandatory public-API consumer: missing configuration is a failure, never a skipped pass. */
@OptIn(ExperimentalForeignApi::class)
fun main(arguments: Array<String>) {
    var completed = 0
    val completedCases = mutableListOf<String>()
    val started = TimeSource.Monotonic.markNow()
    try {
        require(arguments.size in 2..3 && arguments[0] == "--port" &&
            (arguments.size == 2 || arguments[2] == "--m3-negative-suite")) {
            "Required: --port REFERENCE_PEER_PORT [--m3-negative-suite]"
        }
        val port = arguments[1].toInt()
        require(port in 1..65535)
        val m3 = arguments.size == 3
        val temporaryCode = if (m3) requireNotNull(getenv("KADB_M3_PAIRING_CODE")?.toKString()) {
            "M3 requires an ephemeral pairing code supplied by the driver"
        }.also { require(it.length == 6 && it.all(Char::isDigit)) } else null
        val store = InMemoryPrivateKeyStore()
        KadbCert.configure(store)
        try {
            // Return value contains a private-key copy; keep only the identity held by Kadb.
            KadbCert.ensureReady().privateKeyPem.fill(0)
            runBlocking {
                if (m3) {
                    runM3(port, requireNotNull(temporaryCode)) { scenario ->
                        completedCases += scenario
                        completed++
                        println("PASS controlled_peer_$scenario")
                    }
                } else {
                    Kadb.pair("127.0.0.1", port, "123456", "kadb-ios-interop")
                    completed++
                    println("PASS independent_reference_pairing")
                    var rejected = false
                    try {
                        Kadb.pair("127.0.0.1", port, "654321", "kadb-ios-interop")
                    } catch (_: IOException) {
                        rejected = true
                    }
                    check(rejected) { "Incorrect pairing code was accepted" }
                    completed++
                    println("PASS independent_reference_wrong_code_rejection")
                }
            }
        } finally {
            KadbCert.clear()
            store.clear()
        }
        println("KADB_NATIVE_PAIRING_JSON {\"status\":\"passed\",\"checks_executed\":$completed," +
            "\"elapsed_ms\":${started.elapsedNow().inWholeMilliseconds},\"physical_device\":false," +
            "\"real_adbd\":false,\"cases\":[${completedCases.joinToString(",") { "\"$it\"" }}]}")
    } catch (failure: Throwable) {
        // The detailed exception/stack is useful diagnostic evidence; no pairing code or key is printed here.
        failure.printStackTrace()
        println("KADB_NATIVE_PAIRING_JSON {\"status\":\"failed\",\"checks_executed\":$completed," +
            "\"elapsed_ms\":${started.elapsedNow().inWholeMilliseconds},\"physical_device\":false," +
            "\"real_adbd\":false,\"cases\":[${completedCases.joinToString(",") { "\"$it\"" }}]}")
        exitProcess(1)
    }
}

private suspend fun runM3(port: Int, pairingCode: String, record: (String) -> Unit) {
    val cases = listOf("positive_seed", "wrong_code", "stale_exporter", "wrong_role", "missing_identity_nul",
        "invalid_spake_length", "invalid_header", "bad_gcm_tag", "invalid_peer_info",
        "network_disconnect", "timeout", "cancellation", "positive_recovery")
    for (scenario in cases) {
        val code = if (scenario == "wrong_code") "${(pairingCode.first().digitToInt() + 1) % 10}${pairingCode.drop(1)}"
            else pairingCode
        suspend fun pair() = Kadb.pair("127.0.0.1", port, code, "kadb-ios-interop")
        when {
            scenario.startsWith("positive_") -> withTimeout(10_000) { pair() }
            scenario == "timeout" -> {
                var timedOut = false
                try {
                    withTimeout(1_500) { pair() }
                } catch (_: TimeoutCancellationException) {
                    timedOut = true
                }
                check(timedOut) { "Stalled exchange did not propagate coroutine timeout" }
            }
            scenario == "cancellation" -> withTimeout(8_000) {
                coroutineScope {
                    var cancellationObserved = false
                    val job = launch {
                        try {
                            pair()
                            error("Stalled exchange unexpectedly succeeded")
                        } catch (cancelled: CancellationException) {
                            cancellationObserved = true
                            throw cancelled
                        }
                    }
                    delay(1_500)
                    check(job.isActive) { "Pairing ended before explicit cancellation" }
                    job.cancelAndJoin()
                    check(job.isCancelled && cancellationObserved) { "Cancellation did not complete" }
                }
            }
            else -> withTimeout(10_000) {
                var rejected = false
                try {
                    pair()
                } catch (_: IOException) {
                    rejected = true
                }
                check(rejected) { "Controlled peer fault was accepted: $scenario" }
            }
        }
        record(scenario)
    }
}
