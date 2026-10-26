plugins {
    alias(libs.plugins.kotlinMultiplatform)
    alias(libs.plugins.androidMultiplatformLibrary)
}

kotlin {
    iosArm64()
    iosSimulatorArm64()
    macosArm64()
    macosX64()
    // Data models and parsers only: there is no Linux discovery backend yet.
    linuxX64()

    jvmToolchain(25)

    android {
        namespace = "com.flyfishxu.kadb.mdns"
        compileSdk = 37
        minSdk = 23

        withJava()
        withHostTest {}
    }

    sourceSets {
        commonMain.dependencies {
            api(libs.kotlinx.coroutines.core)
        }

        commonTest.dependencies {
            implementation(libs.kotlin.test)
        }


    }
}

tasks.withType<org.jetbrains.kotlin.gradle.tasks.KotlinCompilationTask<*>>().configureEach {
    compilerOptions {
        freeCompilerArgs.add("-Xexpect-actual-classes")
    }
}

tasks.withType<org.jetbrains.kotlin.gradle.targets.native.tasks.KotlinNativeSimulatorTest>().configureEach {
    device.set(providers.gradleProperty("iosSimulatorDevice").orElse("booted"))
    standalone.set(false)
}

// Scope gate, separate from runtime/compilation evidence. Android is retained;
// validation-only Java processes never restore a production desktop JVM target.
tasks.register("verifyProductionTargetScope") {
    group = "verification"
    inputs.property("targetPlatforms", kotlin.targets.map { "${it.name}:${it.platformType.name}" }.sorted())
    doLast {
        val targets = inputs.properties.getValue("targetPlatforms") as List<*>
        check(targets.none { it.toString().endsWith(":jvm") }) { "Unexpected desktop JVM target: $targets" }
        check("android:androidJvm" in targets) { "Android production target was lost: $targets" }
        check("macosArm64:native" in targets && "iosArm64:native" in targets) { "Darwin targets were lost: $targets" }
        println("PRODUCTION_TARGET_SCOPE_OK $path $targets")
    }
}
