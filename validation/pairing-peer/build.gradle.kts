import java.security.MessageDigest

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

val referenceClasspath = configurations.runtimeClasspath
val verifyReferenceClasspath by tasks.registering {
    group = "verification"
    description = "Verify the immutable Java SPAKE/TLS reference artifacts used only for validation"
    inputs.file("SHA256SUMS")
    inputs.files(referenceClasspath)
    doLast {
        val expected = file("SHA256SUMS").readLines().filter(String::isNotBlank).associate { line ->
            val (hash, name) = line.split("  ", limit = 2)
            name to hash
        }
        val artifacts = referenceClasspath.get().files
        check(artifacts.map { it.name }.toSet() == expected.keys) { "Reference runtime artifact inventory changed" }
        artifacts.forEach { artifact ->
            val hash = MessageDigest.getInstance("SHA-256").digest(artifact.readBytes())
                .joinToString("") { "%02x".format(it) }
            check(hash == expected.getValue(artifact.name)) { "Reference artifact checksum changed: ${artifact.name}" }
        }
    }
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

tasks.register("writePeerClasspath") {
    group = "verification"
    description = "Write the local classpath for the bounded external Native/Java pairing driver"
    dependsOn(tasks.classes, verifyReferenceClasspath)
    val destination = layout.buildDirectory.file("reference-classpath.txt")
    inputs.files(sourceSets.main.get().runtimeClasspath)
    outputs.file(destination)
    doLast {
        // Java source sets include an absent resources directory when processResources is NO-SOURCE.
        destination.get().asFile.writeText(sourceSets.main.get().runtimeClasspath.filter { it.exists() }.asPath + "\n")
    }
}
