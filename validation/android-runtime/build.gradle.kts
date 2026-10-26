plugins {
    alias(libs.plugins.androidApplication)
}

// A real APK consumer of the Android production variant. No AndroidX test runner,
// test-only Conscrypt provider, publication task, or production source override.
dependencies {
    implementation(project(":kadb"))
    implementation(libs.kotlinx.coroutines.core)
}

val runtimeKeyStore = layout.buildDirectory.file("keys/runtime-debug.keystore")
val generateRuntimeKeyStore by tasks.registering(Exec::class) {
    val output = runtimeKeyStore.get().asFile
    outputs.file(output)
    onlyIf { !output.isFile }
    doFirst { output.parentFile.mkdirs() }
    commandLine(
        "${System.getProperty("java.home")}/bin/keytool", "-genkeypair", "-noprompt",
        "-keystore", output.absolutePath, "-storepass", "android", "-keypass", "android",
        "-alias", "androiddebugkey", "-keyalg", "RSA", "-keysize", "2048",
        "-validity", "3650", "-dname", "CN=Kadb disposable Android runtime validation",
    )
}

android {
    namespace = "com.flyfishxu.kadb.validation.runtime"
    compileSdk = 37
    defaultConfig {
        applicationId = "com.flyfishxu.kadb.validation.runtime"
        minSdk = 23
        targetSdk = 35
        versionCode = 1
        versionName = "1-validation"
    }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    packaging.resources {
        // All three BC runtime JARs carry this notice. Keep every copy in the APK.
        merges += "META-INF/LICENSE.md"
        // These distinct Java 9 OSGi bundle manifests do not describe this Android APK.
        // Their original bytes remain in the pinned dependency/source inventory.
        excludes += "META-INF/versions/9/OSGI-INF/MANIFEST.MF"
    }
    signingConfigs.getByName("debug") {
        storeFile = runtimeKeyStore.get().asFile
        storePassword = "android"
        keyAlias = "androiddebugkey"
        keyPassword = "android"
    }
}

tasks.matching { it.name == "validateSigningDebug" }.configureEach {
    dependsOn(generateRuntimeKeyStore)
}
