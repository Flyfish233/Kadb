package com.flyfishxu.kadb.validation

import com.flyfishxu.kadb.Kadb
import com.flyfishxu.kadb.cert.InMemoryPrivateKeyStore
import com.flyfishxu.kadb.cert.KadbCert
import okio.Buffer
import okio.ByteString.Companion.toByteString
import okio.FileSystem
import okio.IOException
import okio.Path.Companion.toPath
import kotlin.system.exitProcess
import kotlin.time.TimeSource

private const val FIXTURE_PACKAGE = "com.flyfishxu.kadb.validation.fixture"
private const val MTIME_MS = 1_700_000_000_000L
private const val FILE_MODE = 384 // 0600

private class Report {
    val checks = mutableListOf<String>()
    val details = linkedMapOf<String, String>()
    var mode = "invalid-arguments"
    private val started = TimeSource.Monotonic.markNow()

    fun check(name: String, block: () -> Unit) {
        block()
        checks += name
        println("PASS $name")
    }

    fun emit(error: Throwable? = null) {
        val fields = linkedMapOf(
            "schema" to "1",
            "status" to jsonString(if (error == null) "passed" else "failed"),
            "kind" to jsonString(if (mode == "probe") "connection_probe" else "native_adbd_e2e"),
            "device_kind" to jsonString("android_emulator"),
            "checks_executed" to checks.size.toString(),
            "checks" to checks.joinToString(prefix = "[", postfix = "]") { jsonString(it) },
            "elapsed_ms" to started.elapsedNow().inWholeMilliseconds.toString(),
            "details" to details.entries.joinToString(prefix = "{", postfix = "}") {
                "${jsonString(it.key)}:${jsonString(it.value)}"
            },
        )
        if (error != null) {
            fields["error_type"] = jsonString(error::class.simpleName ?: "Throwable")
            fields["error"] = jsonString(error.message ?: "No message")
        }
        println("KADB_VALIDATION_JSON " + fields.entries.joinToString(prefix = "{", postfix = "}") {
            "${jsonString(it.key)}:${it.value}"
        })
    }
}

private fun jsonString(value: String): String = buildString {
    append('"')
    value.forEach { character ->
        when (character) {
            '"' -> append("\\\"")
            '\\' -> append("\\\\")
            '\n' -> append("\\n")
            '\r' -> append("\\r")
            '\t' -> append("\\t")
            else -> if (character.code < 32) append("\\u" + character.code.toString(16).padStart(4, '0'))
            else append(character)
        }
    }
    append('"')
}

private data class Options(
    val mode: String,
    val host: String,
    val port: Int,
    val privateKey: String,
    val apk: String,
    val runId: String,
) {
    companion object {
        fun parse(arguments: Array<String>): Options {
            require(arguments.size == 12) {
                "Required: --mode e2e|probe --host 127.0.0.1 --port PORT --private-key PEM --apk APK --run-id HEX"
            }
            val values = linkedMapOf<String, String>()
            arguments.toList().chunked(2).forEach { (key, value) ->
                require(values.put(key, value) == null) { "Duplicate argument $key" }
            }
            require(values.keys == setOf("--mode", "--host", "--port", "--private-key", "--apk", "--run-id"))
            val mode = values.getValue("--mode")
            require(mode == "e2e" || mode == "probe")
            // This executable is deliberately scoped to the driver's loopback relay.
            require(values.getValue("--host") == "127.0.0.1")
            val port = values.getValue("--port").toInt()
            require(port in 1..65535)
            val runId = values.getValue("--run-id")
            require(runId.length in 16..64 && runId.all { it in '0'..'9' || it in 'a'..'f' })
            return Options(mode, "127.0.0.1", port, values.getValue("--private-key"), values.getValue("--apk"), runId)
        }
    }
}

private fun Kadb.successfulShell(command: String): String = shell(command).let { result ->
    check(result.exitCode == 0 && result.errorOutput.isEmpty()) { "Shell failed: $result" }
    result.output
}

private fun runConsumer(options: Options, report: Report) {
    val keyStore = InMemoryPrivateKeyStore()
    KadbCert.configure(keyStore)
    try {
        val privatePem = FileSystem.SYSTEM.read(options.privateKey.toPath()) { readByteArray() }
        try {
            report.check("identity_import") {
                // Both the file buffer and the public API's returned private-key copy are owned here.
                KadbCert.importPrivateKey(privatePem).privateKeyPem.fill(0)
            }
        } finally {
            privatePem.fill(0)
        }

        val timeout = if (options.mode == "probe") 4_000 else 30_000
        Kadb.create(options.host, options.port, connectTimeout = 5_000, socketTimeout = timeout).use { client ->
            if (options.mode == "probe") {
                report.check("probe_shell") {
                    check(client.successfulShell("printf kadb-auth-probe") == "kadb-auth-probe")
                }
                return
            }

            report.check("feature_negotiation") {
                val required = listOf("shell_v2", "stat_v2", "ls_v2", "sendrecv_v2", "cmd")
                required.forEach { check(client.supportsFeature(it)) { "Required emulator feature absent: $it" } }
                report.details["features"] = required.joinToString(",")
            }
            report.check("shell_v2") {
                val response = client.shell("printf kadb-stdout; printf kadb-stderr >&2; exit 7")
                check(response.output == "kadb-stdout")
                check(response.errorOutput == "kadb-stderr")
                check(response.exitCode == 7)
            }

            val remoteRoot = "/data/local/tmp/kadb-native-validation-${options.runId}"
            val remoteFile = "$remoteRoot/payload.bin"
            val remoteLink = "$remoteRoot/payload.link"
            val remoteEmpty = "$remoteRoot/empty.bin"
            check(client.successfulShell("mkdir '$remoteRoot'").isEmpty())
            // More than one ADB payload and sixteen Sync chunks, with zero and high-bit bytes.
            val payload = ByteArray(1024 * 1024 + 13) { ((it * 31 + it / 251) and 255).toByte() }
            val digest = payload.toByteString().sha256().hex()
            report.details["payload_bytes"] = payload.size.toString()
            report.details["payload_sha256"] = digest

            report.check("sync_transfer") {
                client.push(Buffer().write(payload), remoteFile, FILE_MODE, MTIME_MS)
                val received = Buffer()
                client.pull(received, remoteFile)
                check(received.readByteArray().contentEquals(payload))
            }
            report.check("sync_stat") {
                client.openSync().use { sync ->
                    val stat = sync.statV2(remoteFile)
                    check(stat.errorCode == 0)
                    check(stat.size == payload.size.toLong())
                    check(stat.mode and 0xF000 == 0x8000)
                    check(stat.mode and 0x1FF == FILE_MODE)
                    check(stat.mtimeSec == MTIME_MS / 1000)
                }
            }
            report.check("sync_shell_metadata") {
                // Independent Android utilities check content and metadata, outside Kadb's Sync parser.
                check(client.successfulShell("sha256sum '$remoteFile'").substringBefore(' ') == digest)
                check(client.successfulShell("stat -c '%a %Y %s' '$remoteFile'").trim() ==
                    "600 ${MTIME_MS / 1000} ${payload.size}")
            }
            report.check("sync_directory") {
                client.openSync().use { sync ->
                    val entries = sync.listV2(remoteRoot)
                    val file = entries.single { it.name == "payload.bin" }
                    check(file.errorCode == 0 && file.size == payload.size.toLong())
                }
            }
            report.check("sync_symlink") {
                client.successfulShell("ln -s '$remoteFile' '$remoteLink'")
                client.openSync().use { sync ->
                    val link = sync.lstatV2(remoteLink)
                    val target = sync.statV2(remoteLink)
                    check(link.errorCode == 0 && link.mode and 0xF000 == 0xA000)
                    check(target.errorCode == 0 && target.mode and 0xF000 == 0x8000)
                    check(target.size == payload.size.toLong())
                    check(target.mtimeSec == MTIME_MS / 1000)
                }
                val received = Buffer()
                client.pull(received, remoteLink)
                check(received.readByteArray().contentEquals(payload))
            }
            report.check("sync_empty_file") {
                client.push(Buffer(), remoteEmpty, FILE_MODE, MTIME_MS)
                val received = Buffer()
                client.pull(received, remoteEmpty)
                check(received.size == 0L)
                client.openSync().use { sync ->
                    val stat = sync.statV2(remoteEmpty)
                    check(stat.errorCode == 0 && stat.size == 0L)
                }
            }
            report.check("install") {
                client.install(options.apk.toPath())
                check(client.successfulShell("pm path $FIXTURE_PACKAGE").startsWith("package:"))
            }
            report.check("uninstall") {
                client.uninstall(FIXTURE_PACKAGE)
                val absent = client.shell("pm path $FIXTURE_PACKAGE")
                check(absent.exitCode == 1 && absent.allOutput.isEmpty())
            }
            repeat(2) { cycle ->
                report.check("reconnect_${cycle + 1}") {
                    check(client.connectionCheck())
                    client.resetConnection()
                    check(!client.connectionCheck())
                    check(client.successfulShell("printf reconnect-${cycle + 1}") == "reconnect-${cycle + 1}")
                    check(client.connectionCheck())
                }
            }
            report.check("cleanup") {
                client.successfulShell("rm '$remoteLink' '$remoteFile' '$remoteEmpty' && rmdir '$remoteRoot'")
            }
            report.check("close_terminal") {
                client.close()
                client.close()
                check(!client.connectionCheck())
                var rejected = false
                try {
                    client.shell("printf must-not-run")
                } catch (_: IOException) {
                    rejected = true
                }
                check(rejected) { "Closed client accepted a new command" }
            }
        }
    } finally {
        // The Python driver also removes owned remote files/package after failures.
        KadbCert.clear()
        keyStore.clear()
    }
}

fun main(arguments: Array<String>) {
    val report = Report()
    try {
        val options = Options.parse(arguments)
        report.mode = options.mode
        runConsumer(options, report)
        report.emit()
    } catch (failure: Throwable) {
        report.emit(failure)
        exitProcess(1)
    }
}
