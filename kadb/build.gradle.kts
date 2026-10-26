plugins {
    alias(libs.plugins.kotlinMultiplatform)
    alias(libs.plugins.androidMultiplatformLibrary)
}

apply(from = "gradle/ios-native.gradle.kts")

kotlin {
    listOf(iosArm64(), iosSimulatorArm64(), macosArm64(), macosX64(), linuxX64()).forEach { target ->
        val nativeOutput = layout.buildDirectory.dir("native/${target.name}")
        val buildNative = tasks.named("buildNative${target.name.replaceFirstChar(Char::uppercaseChar)}")
        val interop = target.compilations.getByName("main").cinterops.create("kadbNative") {
            definitionFile.set(project.file("src/nativeInterop/cinterop/" +
                if (target.name == "linuxX64") "kadb-linux.def" else "kadb.def"))
            includeDirs(project.file("src/nativeInterop/cinterop"))
            extraOpts("-libraryPath", nativeOutput.get().asFile.absolutePath)
        }
        tasks.named(interop.interopProcessingTaskName).configure {
            dependsOn(buildNative)
            // Cinterop embeds these archives; changing C must invalidate the produced KLIB.
            inputs.files(nativeOutput.map { it.file("libkadb_native.a") },
                nativeOutput.map { it.file("libssl.a") }, nativeOutput.map { it.file("libcrypto.a") })
        }
        if (target.name != "linuxX64") target.binaries.framework {
            baseName = "Kadb"
            isStatic = true
            binaryOption("bundleId", "com.flyfishxu.kadb")
        }
    }

    jvmToolchain(25)

    android {
        namespace = "com.flyfishxu.kadb"
        compileSdk = 37
        minSdk = 23

        withJava()
        withHostTest {}
    }

    applyDefaultHierarchyTemplate()

    sourceSets {
        // Device-dependent tests are absent from the default simulator suite.
        // Explicit opt-in requires all device parameters and may contact that device.
        if (providers.gradleProperty("enableIosDeviceSmoke").map(String::toBoolean).orElse(false).get()) {
            getByName("iosTest").kotlin.srcDir("src/iosDeviceTest/kotlin")
        }
        commonMain.dependencies {
            implementation(project(":spake2-legacy"))
            implementation(libs.kotlinx.coroutines.core)
            api(libs.okio)
        }
        androidMain.dependencies {
            implementation(libs.bcprov)
            implementation(libs.bcpkix)
            implementation(libs.documentfile)
            implementation(libs.hiddenapibypass)
        }

        commonTest.dependencies {
            implementation(libs.kotlin.test)
        }
        getByName("androidHostTest").dependencies {
            // These independent oracles validate the Android production variant.
            implementation(libs.spake2)
            implementation(libs.conscrypt.java)
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

// Validation-only Java reference process, with no Kadb runtime dependency.
tasks.register("iosInteropPeer") {
    group = "verification"
    dependsOn(":validation-pairing-peer:iosInteropPeer")
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
