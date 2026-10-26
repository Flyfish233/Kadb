import java.security.MessageDigest

plugins {
    alias(libs.plugins.kotlinMultiplatform)
    alias(libs.plugins.androidMultiplatformLibrary)
}

// Kadb-owned build adaptation; upstream sources below are verified unchanged.
kotlin {
    jvm { jvmToolchain(25) }
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
        commonMain {
            kotlin.setSrcDirs(listOf(
                "upstream/primitives/src/commonMain/kotlin",
                "upstream/legacy/src/commonMain/kotlin"
            ))
            languageSettings.optIn("io.github.flyfish233.spake2.InternalSpake2Api")
        }
        commonTest.dependencies { implementation(libs.kotlin.test) }
    }
}

val verifyPinnedSources by tasks.registering {
    group = "verification"
    description = "Verify the exact immutable SPAKE2 source dependency and inventory"
    inputs.file("SHA256SUMS")
    inputs.file("UPSTREAM_COMMIT")
    inputs.dir("upstream")
    doLast {
        check(file("UPSTREAM_COMMIT").readText().trim() == "b837aba27bebc1050965fa124c2efa54b4e4544a")
        val expected = file("SHA256SUMS").readLines().filter(String::isNotBlank).associate { line ->
            val (hash, path) = line.split("  ", limit = 2)
            path to hash
        }
        val actualPaths = fileTree("upstream").files.map { it.relativeTo(projectDir).invariantSeparatorsPath }.toSet()
        check(actualPaths == expected.keys) { "SPAKE2 pinned source inventory has changed" }
        expected.forEach { (path, hash) ->
            val actual = MessageDigest.getInstance("SHA-256").digest(file(path).readBytes())
                .joinToString("") { "%02x".format(it) }
            check(actual == hash) { "Pinned SPAKE2 source differs: $path" }
        }
    }
}

tasks.withType<org.jetbrains.kotlin.gradle.tasks.KotlinCompilationTask<*>>().configureEach {
    dependsOn(verifyPinnedSources)
}
