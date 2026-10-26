plugins {
    alias(libs.plugins.androidApplication)
}

val fixtureKeyStore = layout.buildDirectory.file("keys/fixture-debug.keystore")
val generateFixtureKeyStore by tasks.registering(Exec::class) {
    val output = fixtureKeyStore.get().asFile
    outputs.file(output)
    onlyIf { !output.isFile }
    doFirst { output.parentFile.mkdirs() }
    commandLine(
        "${System.getProperty("java.home")}/bin/keytool", "-genkeypair", "-noprompt",
        "-keystore", output.absolutePath, "-storepass", "android", "-keypass", "android",
        "-alias", "androiddebugkey", "-keyalg", "RSA", "-keysize", "2048",
        "-validity", "3650", "-dname", "CN=Kadb disposable validation fixture",
    )
}

android {
    namespace = "com.flyfishxu.kadb.validation.fixture"
    compileSdk = 37
    defaultConfig {
        applicationId = "com.flyfishxu.kadb.validation.fixture"
        minSdk = 23
        targetSdk = 35
        versionCode = 1
        versionName = "1-validation"
    }
    signingConfigs.getByName("debug") {
        storeFile = fixtureKeyStore.get().asFile
        storePassword = "android"
        keyAlias = "androiddebugkey"
        keyPassword = "android"
    }
}

tasks.matching { it.name == "validateSigningDebug" }.configureEach {
    dependsOn(generateFixtureKeyStore)
}
