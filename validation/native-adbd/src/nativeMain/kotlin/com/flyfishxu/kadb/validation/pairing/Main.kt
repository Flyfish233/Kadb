package com.flyfishxu.kadb.validation.pairing

import com.flyfishxu.kadb.Kadb
import com.flyfishxu.kadb.cert.InMemoryPrivateKeyStore
import com.flyfishxu.kadb.cert.KadbCert
import kotlinx.coroutines.runBlocking
import okio.IOException
import kotlin.system.exitProcess
import kotlin.time.TimeSource

/** Mandatory public-API consumer: missing configuration is a failure, never a skipped pass. */
fun main(arguments: Array<String>) {
    var completed = 0
    val started = TimeSource.Monotonic.markNow()
    try {
        require(arguments.size == 2 && arguments[0] == "--port") { "Required: --port REFERENCE_PEER_PORT" }
        val port = arguments[1].toInt()
        require(port in 1..65535)
        val store = InMemoryPrivateKeyStore()
        KadbCert.configure(store)
        try {
            // Return value contains a private-key copy; keep only the identity held by Kadb.
            KadbCert.ensureReady().privateKeyPem.fill(0)
            runBlocking {
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
        } finally {
            KadbCert.clear()
            store.clear()
        }
        println("KADB_NATIVE_PAIRING_JSON {\"status\":\"passed\",\"checks_executed\":$completed," +
            "\"elapsed_ms\":${started.elapsedNow().inWholeMilliseconds},\"physical_device\":false}")
    } catch (failure: Throwable) {
        // The detailed exception/stack is useful diagnostic evidence; no pairing code or key is printed here.
        failure.printStackTrace()
        println("KADB_NATIVE_PAIRING_JSON {\"status\":\"failed\",\"checks_executed\":$completed," +
            "\"elapsed_ms\":${started.elapsedNow().inWholeMilliseconds},\"physical_device\":false}")
        exitProcess(1)
    }
}
