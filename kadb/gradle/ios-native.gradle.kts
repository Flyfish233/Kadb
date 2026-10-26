import java.net.URI
import java.io.IOException
import java.net.http.HttpClient
import java.net.http.HttpRequest
import java.net.http.HttpResponse
import java.nio.channels.FileChannel
import java.nio.file.Files
import java.nio.file.StandardCopyOption
import java.nio.file.StandardOpenOption
import java.security.MessageDigest
import java.time.Duration
import javax.inject.Inject
import org.gradle.api.file.DirectoryProperty
import org.gradle.api.file.RegularFileProperty
import org.gradle.api.provider.Property
import org.gradle.api.tasks.*
import org.gradle.process.ExecOperations
import org.gradle.work.DisableCachingByDefault

@CacheableTask
abstract class DownloadVerifiedArchive : DefaultTask() {
    @get:Input abstract val sourceUrl: Property<String>
    @get:Input abstract val sha256: Property<String>
    @get:OutputFile abstract val archiveFile: RegularFileProperty

    private fun checksum(file: File): String {
        val digest = MessageDigest.getInstance("SHA-256")
        file.inputStream().buffered().use { input ->
            val bytes = ByteArray(64 * 1024)
            while (true) {
                val count = input.read(bytes)
                if (count < 0) break
                digest.update(bytes, 0, count)
            }
        }
        return digest.digest().joinToString("") { "%02x".format(it.toInt() and 0xff) }
    }

    @TaskAction fun download() {
        val archive = archiveFile.get().asFile
        archive.parentFile.mkdirs()
        val lockFile = archive.resolveSibling("${archive.name}.lock").toPath()
        FileChannel.open(lockFile, StandardOpenOption.CREATE, StandardOpenOption.WRITE).use { channel ->
            channel.lock().use {
                if (archive.isFile && checksum(archive) == sha256.get()) return
                val temporary = archive.resolveSibling("${archive.name}.download")
                val client = HttpClient.newBuilder().followRedirects(HttpClient.Redirect.NORMAL)
                    .connectTimeout(Duration.ofSeconds(30)).build()
                val request = HttpRequest.newBuilder(URI(sourceUrl.get()))
                    .timeout(Duration.ofMinutes(5)).GET().build()
                for (attempt in 1..3) {
                    try {
                        logger.lifecycle("Downloading verified native dependency: ${archive.name} (attempt $attempt/3)")
                        val response = client.send(request, HttpResponse.BodyHandlers.ofFile(temporary.toPath(),
                            StandardOpenOption.CREATE, StandardOpenOption.WRITE, StandardOpenOption.TRUNCATE_EXISTING))
                        val status = response.statusCode()
                        if (status == 408 || status == 429 || status in 500..599) {
                            throw IOException("Temporary HTTP $status while downloading ${archive.name}")
                        }
                        check(status == 200) { "Download failed with HTTP $status: ${sourceUrl.get()}" }
                        // A hash mismatch is not a retryable network error. Never accept other bytes.
                        check(checksum(temporary) == sha256.get()) { "SHA-256 mismatch for ${archive.name}" }
                        Files.move(temporary.toPath(), archive.toPath(), StandardCopyOption.REPLACE_EXISTING,
                            StandardCopyOption.ATOMIC_MOVE)
                        return
                    } catch (error: IOException) {
                        if (attempt == 3) throw error
                        logger.warn("Native dependency download failed; bounded retry follows: ${error.message}")
                        Thread.sleep(attempt * 1000L)
                    } finally {
                        temporary.delete()
                    }
                }
            }
        }
    }
}

@DisableCachingByDefault(because = "Expands a locally cached, verified upstream archive")
abstract class ExtractNativeArchive : DefaultTask() {
    @get:InputFile @get:PathSensitive(PathSensitivity.NONE)
    abstract val archiveFile: RegularFileProperty
    @get:OutputDirectory abstract val destinationDirectory: DirectoryProperty
    @get:Inject abstract val execOperations: ExecOperations

    @TaskAction fun extract() {
        val destination = destinationDirectory.get().asFile
        destination.deleteRecursively()
        destination.mkdirs()
        // macOS tar preserves the CMake bundle's executable permissions and symbolic links.
        execOperations.exec {
            commandLine("/usr/bin/tar", "-xzf", archiveFile.get().asFile,
                "-C", destination, "--strip-components=1")
        }.assertNormalExitValue()
    }
}

@DisableCachingByDefault(because = "CMake builds incrementally using the local platform toolchain")
abstract class BuildPosixNative : DefaultTask() {
    @get:InputDirectory @get:PathSensitive(PathSensitivity.RELATIVE)
    abstract val bridgeDirectory: DirectoryProperty
    @get:InputDirectory @get:PathSensitive(PathSensitivity.RELATIVE)
    abstract val boringSslDirectory: DirectoryProperty
    @get:InputFile @get:PathSensitive(PathSensitivity.NONE)
    abstract val cmakeExecutable: RegularFileProperty
    @get:InputDirectory @get:Optional @get:PathSensitive(PathSensitivity.RELATIVE)
    abstract val linuxToolchainDirectory: DirectoryProperty
    @get:InputDirectory @get:Optional @get:PathSensitive(PathSensitivity.RELATIVE)
    abstract val linuxLlvmDirectory: DirectoryProperty
    @get:Input abstract val operatingSystem: Property<String>
    @get:Input abstract val sdk: Property<String>
    @get:Input abstract val deploymentTarget: Property<String>
    @get:Input abstract val architecture: Property<String>
    @get:Input abstract val configuration: Property<String>
    @get:LocalState abstract val cmakeBuildDirectory: DirectoryProperty
    @get:OutputFile abstract val nativeLibrary: RegularFileProperty
    @get:OutputFile abstract val sslLibrary: RegularFileProperty
    @get:OutputFile abstract val cryptoLibrary: RegularFileProperty
    @get:Inject abstract val execOperations: ExecOperations

    @TaskAction fun build() {
        val apple = operatingSystem.get() != "Linux"
        check(System.getProperty("os.name").startsWith(if (apple) "Mac" else "Linux")) {
            "The ${operatingSystem.get()} backend must be built on ${if (apple) "macOS with Xcode" else "Linux"}"
        }
        val cmake = cmakeExecutable.get().asFile
        check(cmake.canExecute()) { "CMake is not executable: $cmake" }
        val buildDirectory = cmakeBuildDirectory.get().asFile
        execOperations.exec {
            val arguments = mutableListOf<Any>(cmake, "-S", bridgeDirectory.get().asFile, "-B", buildDirectory,
                "-G", "Unix Makefiles", "-DBORINGSSL_SOURCE=${boringSslDirectory.get().asFile}",
                "-DCMAKE_BUILD_TYPE=${configuration.get()}", "-DCMAKE_POSITION_INDEPENDENT_CODE=ON")
            if (apple) arguments.addAll(listOf(
                "-DCMAKE_SYSTEM_NAME=${operatingSystem.get()}", "-DCMAKE_OSX_SYSROOT=${sdk.get()}",
                "-DCMAKE_OSX_ARCHITECTURES=${architecture.get()}",
                "-DCMAKE_OSX_DEPLOYMENT_TARGET=${deploymentTarget.get()}", "-DCMAKE_MACOSX_BUNDLE=OFF"))
            else {
                // Match the compiler/sysroot used by Kotlin/Native. Host GCC may
                // import newer glibc symbols (for example __isoc23_strtoull).
                val gcc = linuxToolchainDirectory.get().asFile
                val llvm = linuxLlvmDirectory.get().asFile
                arguments.addAll(listOf(
                    "-DCMAKE_C_COMPILER=${llvm.resolve("bin/clang")}",
                    "-DCMAKE_CXX_COMPILER=${llvm.resolve("bin/clang++")}",
                    "-DCMAKE_C_COMPILER_TARGET=x86_64-unknown-linux-gnu",
                    "-DCMAKE_CXX_COMPILER_TARGET=x86_64-unknown-linux-gnu",
                    "-DCMAKE_C_COMPILER_EXTERNAL_TOOLCHAIN=$gcc",
                    "-DCMAKE_CXX_COMPILER_EXTERNAL_TOOLCHAIN=$gcc",
                    "-DCMAKE_SYSROOT=${gcc.resolve("x86_64-unknown-linux-gnu/sysroot")}",
                    "-DCMAKE_EXE_LINKER_FLAGS=-fuse-ld=lld"))
            }
            commandLine(arguments)
        }.assertNormalExitValue()
        execOperations.exec {
            commandLine(cmake, "--build", buildDirectory, "--target", "kadb_native", "--parallel",
                Runtime.getRuntime().availableProcessors().coerceAtMost(8).toString())
        }.assertNormalExitValue()
        listOf(nativeLibrary, sslLibrary, cryptoLibrary).forEach { output ->
            val destination = output.get().asFile
            destination.parentFile.mkdirs()
            Files.copy(buildDirectory.resolve("lib/${destination.name}").toPath(), destination.toPath(),
                StandardCopyOption.REPLACE_EXISTING)
        }
    }
}

val boringSslRevision = "5b83e5d1abf0ae0033ae52ab579d906b67633b2c"
val cmakeVersion = "3.31.8"
val nativeRoot = layout.buildDirectory.dir("native")
val downloadBoringSsl = tasks.register<DownloadVerifiedArchive>("downloadIosBoringSsl") {
    sourceUrl.set("https://codeload.github.com/google/boringssl/tar.gz/$boringSslRevision")
    sha256.set("4117ae02de040d4469284673ed63a14e648af7c3974aa9e85bcef2975a9c9ea8")
    archiveFile.set(nativeRoot.map { it.file("downloads/boringssl.tar.gz") })
}
val prepareBoringSsl = tasks.register<ExtractNativeArchive>("prepareIosBoringSsl") {
    archiveFile.set(downloadBoringSsl.flatMap { it.archiveFile })
    destinationDirectory.set(nativeRoot.map { it.dir("boringssl-$boringSslRevision") })
}

// The pinned K/N 2.4.20 distribution names this exact Linux sysroot. Keep the
// C archives compatible with it, without relying on internal KGP task APIs.
val linuxToolchainName = "x86_64-unknown-linux-gnu-gcc-8.3.0-glibc-2.19-kernel-4.9-2"
val downloadLinuxToolchain = tasks.register<DownloadVerifiedArchive>("downloadNativeLinuxToolchain") {
    sourceUrl.set("https://download.jetbrains.com/kotlin/native/$linuxToolchainName.tar.gz")
    sha256.set("a048397d50fb5a2bd6cc0f89d5a30e0b8ff0373ebff9c1d78ce1f1fb7f185a50")
    archiveFile.set(nativeRoot.map { it.file("downloads/$linuxToolchainName.tar.gz") })
}
val prepareLinuxToolchain = tasks.register<ExtractNativeArchive>("prepareNativeLinuxToolchain") {
    archiveFile.set(downloadLinuxToolchain.flatMap { it.archiveFile })
    destinationDirectory.set(nativeRoot.map { it.dir(linuxToolchainName) })
}

val linuxLlvmName = "llvm-21-x86_64-linux-essentials-116"
val downloadLinuxLlvm = tasks.register<DownloadVerifiedArchive>("downloadNativeLinuxLlvm") {
    sourceUrl.set("https://download.jetbrains.com/kotlin/native/resources/llvm/21-x86_64-linux/$linuxLlvmName.tar.gz")
    sha256.set("0b1f290214dd7ec20e2506210967e0ebd735cdefc3a3b4485bbccb439fa78e5b")
    archiveFile.set(nativeRoot.map { it.file("downloads/$linuxLlvmName.tar.gz") })
}
val prepareLinuxLlvm = tasks.register<ExtractNativeArchive>("prepareNativeLinuxLlvm") {
    archiveFile.set(downloadLinuxLlvm.flatMap { it.archiveFile })
    destinationDirectory.set(nativeRoot.map { it.dir(linuxLlvmName) })
}

val cmakeOverride = providers.environmentVariable("CMAKE").orNull?.trim()?.takeIf { it.isNotEmpty() }
val pathDirectories = providers.environmentVariable("PATH").getOrElse("").split(File.pathSeparator)
val externalCmake = when {
    cmakeOverride != null && (cmakeOverride.contains('/') || cmakeOverride.contains('\\')) -> file(cmakeOverride)
    else -> pathDirectories.asSequence().map { File(it, cmakeOverride ?: "cmake") }
        .firstOrNull { it.canExecute() && it.isFile } ?: cmakeOverride?.let { file(it) }
}
val cmakeBinary = if (externalCmake != null) {
    layout.file(provider { externalCmake })
} else if (System.getProperty("os.name").startsWith("Mac")) {
    val downloadCmake = tasks.register<DownloadVerifiedArchive>("downloadIosCmake") {
        sourceUrl.set("https://github.com/Kitware/CMake/releases/download/v$cmakeVersion/cmake-$cmakeVersion-macos-universal.tar.gz")
        sha256.set("d1449f969c54d5c00886d5b643340d493dfb3c81cb39ee29b35453395c11ebf7")
        archiveFile.set(nativeRoot.map { it.file("downloads/cmake.tar.gz") })
    }
    val prepareCmake = tasks.register<ExtractNativeArchive>("prepareIosCmake") {
        archiveFile.set(downloadCmake.flatMap { it.archiveFile })
        destinationDirectory.set(nativeRoot.map { it.dir("cmake-$cmakeVersion-macos-universal") })
    }
    prepareCmake.flatMap { it.destinationDirectory.file("CMake.app/Contents/bin/cmake") }
} else {
    // Linux CI provisions CMake through its image; no Apple binary is downloaded.
    layout.file(provider { file("/usr/bin/cmake") })
}

data class NativePlatform(val system: String, val sdk: String, val arch: String, val minimumVersion: String)
val platforms = mapOf(
    "iosArm64" to NativePlatform("iOS", "iphoneos", "arm64", "15.0"),
    "iosSimulatorArm64" to NativePlatform("iOS", "iphonesimulator", "arm64", "15.0"),
    "macosArm64" to NativePlatform("Darwin", "macosx", "arm64", "12.0"),
    "macosX64" to NativePlatform("Darwin", "macosx", "x86_64", "12.0"),
    "linuxX64" to NativePlatform("Linux", "", "x86_64", "")
)
platforms.forEach { (target, platform) ->
    tasks.register<BuildPosixNative>("buildNative${target.replaceFirstChar(Char::uppercaseChar)}") {
        group = "build"
        description = "Build the pinned native ADB backend for $target"
        bridgeDirectory.set(layout.projectDirectory.dir("src/nativeInterop"))
        boringSslDirectory.set(prepareBoringSsl.flatMap { it.destinationDirectory })
        cmakeExecutable.set(cmakeBinary)
        operatingSystem.set(platform.system)
        if (platform.system == "Linux") {
            linuxToolchainDirectory.set(prepareLinuxToolchain.flatMap { it.destinationDirectory })
            linuxLlvmDirectory.set(prepareLinuxLlvm.flatMap { it.destinationDirectory })
        }
        sdk.set(platform.sdk)
        deploymentTarget.set(platform.minimumVersion)
        architecture.set(platform.arch)
        configuration.set("Release")
        cmakeBuildDirectory.set(nativeRoot.map { it.dir("$target/cmake") })
        nativeLibrary.set(nativeRoot.map { it.file("$target/libkadb_native.a") })
        sslLibrary.set(nativeRoot.map { it.file("$target/libssl.a") })
        cryptoLibrary.set(nativeRoot.map { it.file("$target/libcrypto.a") })
    }
}
