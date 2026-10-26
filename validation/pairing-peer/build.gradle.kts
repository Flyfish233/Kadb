import java.security.MessageDigest
import java.io.File

plugins { java }

// An independent reference process. No Kadb/Kotlin dependency or desktop library artifact.
java { toolchain.languageVersion.set(JavaLanguageVersion.of(25)) }
dependencies {
    implementation(libs.spake2)
    implementation(libs.conscrypt.java)
    implementation(libs.bcpkix)
}

tasks.jar { enabled = false }
// Gradle 9.6 locks Java configuration roles at creation. Remove outgoing
// archives instead of mutating their role; this validation process has no JAR
// or publication task and is never a dependency of a production module.
configurations.matching { it.name == "apiElements" || it.name == "runtimeElements" }.configureEach {
    outgoing.artifacts.clear()
}

@org.gradle.work.DisableCachingByDefault(because = "Reference artifacts must be verified before every independent peer run")
abstract class VerifyReferenceClasspath : DefaultTask() {
    @get:org.gradle.api.tasks.InputFile
    @get:org.gradle.api.tasks.PathSensitive(org.gradle.api.tasks.PathSensitivity.NONE)
    abstract val manifestFile: org.gradle.api.file.RegularFileProperty
    @get:org.gradle.api.tasks.InputFiles
    @get:org.gradle.api.tasks.PathSensitive(org.gradle.api.tasks.PathSensitivity.NONE)
    abstract val artifacts: org.gradle.api.file.ConfigurableFileCollection

    @org.gradle.api.tasks.TaskAction
    fun verify() {
        val expected = manifestFile.get().asFile.readLines().filter(String::isNotBlank).associate { line ->
            val (hash, name) = line.split("  ", limit = 2)
            name to hash
        }
        val files = artifacts.files
        check(files.map { it.name }.toSet() == expected.keys) { "Reference runtime artifact inventory changed" }
        files.forEach { artifact ->
            val hash = MessageDigest.getInstance("SHA-256").digest(artifact.readBytes())
                .joinToString("") { "%02x".format(it) }
            check(hash == expected.getValue(artifact.name)) { "Reference artifact checksum changed: ${artifact.name}" }
        }
    }
}

val verifyReferenceClasspath = tasks.register<VerifyReferenceClasspath>("verifyReferenceClasspath") {
    group = "verification"
    description = "Verify the immutable Java SPAKE/TLS reference artifacts used only for validation"
    manifestFile.set(layout.projectDirectory.file("SHA256SUMS"))
    artifacts.from(configurations.runtimeClasspath)
}

tasks.compileJava { dependsOn(verifyReferenceClasspath) }

tasks.register<JavaExec>("iosInteropPeer") {
    group = "verification"
    description = "Serve two mandatory Native pairing sessions using the independent Java reference"
    dependsOn(tasks.classes, verifyReferenceClasspath)
    classpath = sourceSets.main.get().runtimeClasspath
    mainClass.set("com.flyfishxu.kadb.validation.peer.IosPairingPeer")
    jvmArgs("--enable-native-access=ALL-UNNAMED")
    args(providers.gradleProperty("iosInteropReadyFile")
        .orElse(layout.buildDirectory.file("peer-ready").get().asFile.absolutePath).get())
}

@org.gradle.work.DisableCachingByDefault(because = "Writes machine-local paths to independent validation artifacts")
abstract class WritePeerClasspath : DefaultTask() {
    @get:org.gradle.api.tasks.InputFiles
    @get:org.gradle.api.tasks.PathSensitive(org.gradle.api.tasks.PathSensitivity.NONE)
    abstract val runtimeFiles: org.gradle.api.file.ConfigurableFileCollection
    @get:org.gradle.api.tasks.OutputFile
    abstract val destination: org.gradle.api.file.RegularFileProperty

    @org.gradle.api.tasks.TaskAction
    fun write() {
        val output = destination.get().asFile
        output.parentFile.mkdirs()
        // The resources directory may not exist when processResources is NO-SOURCE.
        output.writeText(runtimeFiles.files.filter { it.exists() }.joinToString(File.pathSeparator) + "\n")
    }
}

tasks.register<WritePeerClasspath>("writePeerClasspath") {
    group = "verification"
    description = "Write the local classpath for the bounded external Native/Java pairing driver"
    dependsOn(tasks.classes, verifyReferenceClasspath)
    runtimeFiles.from(sourceSets.main.get().runtimeClasspath)
    destination.set(layout.buildDirectory.file("reference-classpath.txt"))
}
