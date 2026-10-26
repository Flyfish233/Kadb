import java.security.MessageDigest

plugins {
    alias(libs.plugins.kotlinMultiplatform)
    alias(libs.plugins.androidMultiplatformLibrary)
}

// Kadb-owned build adaptation; upstream sources below are verified unchanged.
kotlin {
    jvmToolchain(25)
    jvm()
    android {
        namespace = "io.github.flyfish233.spake2.legacy.kadb"
        compileSdk = 37
        minSdk = 23
        withHostTest {}
    }
    linuxX64()
    iosArm64()
    iosSimulatorArm64()
    macosArm64()
    macosX64()
    sourceSets {
        all { languageSettings.optIn("io.github.flyfish233.spake2.InternalSpake2Api") }
        commonMain {
            kotlin.setSrcDirs(listOf(
                "upstream/primitives/src/commonMain/kotlin",
                "upstream/legacy/src/commonMain/kotlin"
            ))
        }
        commonTest.dependencies { implementation(libs.kotlin.test) }
    }
}

@org.gradle.work.DisableCachingByDefault(because = "Always verify the immutable source dependency before compilation")
abstract class VerifyPinnedSpakeSources : DefaultTask() {
    @get:org.gradle.api.tasks.InputFile
    @get:org.gradle.api.tasks.PathSensitive(org.gradle.api.tasks.PathSensitivity.NONE)
    abstract val manifestFile: org.gradle.api.file.RegularFileProperty
    @get:org.gradle.api.tasks.InputFile
    @get:org.gradle.api.tasks.PathSensitive(org.gradle.api.tasks.PathSensitivity.NONE)
    abstract val commitFile: org.gradle.api.file.RegularFileProperty
    @get:org.gradle.api.tasks.InputDirectory
    @get:org.gradle.api.tasks.PathSensitive(org.gradle.api.tasks.PathSensitivity.RELATIVE)
    abstract val upstreamDirectory: org.gradle.api.file.DirectoryProperty

    @org.gradle.api.tasks.TaskAction
    fun verify() {
        check(commitFile.get().asFile.readText().trim() == "b837aba27bebc1050965fa124c2efa54b4e4544a")
        val expected = manifestFile.get().asFile.readLines().filter(String::isNotBlank).associate { line ->
            val (hash, path) = line.split("  ", limit = 2)
            path to hash
        }
        val upstream = upstreamDirectory.get().asFile
        val sourceRoot = upstream.parentFile
        val actualPaths = upstream.walkTopDown().filter { it.isFile }
            .map { it.relativeTo(sourceRoot).invariantSeparatorsPath }.toSet()
        check(actualPaths == expected.keys) { "SPAKE2 pinned source inventory has changed" }
        expected.forEach { (path, hash) ->
            val actual = MessageDigest.getInstance("SHA-256").digest(sourceRoot.resolve(path).readBytes())
                .joinToString("") { "%02x".format(it) }
            check(actual == hash) { "Pinned SPAKE2 source differs: $path" }
        }
    }
}

val verifyPinnedSources = tasks.register<VerifyPinnedSpakeSources>("verifyPinnedSources") {
    group = "verification"
    description = "Verify the exact immutable SPAKE2 source dependency and inventory"
    manifestFile.set(layout.projectDirectory.file("SHA256SUMS"))
    commitFile.set(layout.projectDirectory.file("UPSTREAM_COMMIT"))
    upstreamDirectory.set(layout.projectDirectory.dir("upstream"))
}

tasks.withType<org.jetbrains.kotlin.gradle.tasks.KotlinCompilationTask<*>>().configureEach {
    dependsOn(verifyPinnedSources)
}
