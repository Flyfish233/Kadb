pluginManagement {
    repositories {
        mavenLocal()
        google()
        mavenCentral()
        gradlePluginPortal()
    }
}

dependencyResolutionManagement {
    repositories {
        mavenLocal()
        google()
        mavenCentral()
        maven("https://jitpack.io")
    }
}

plugins {
    id("de.fayard.refreshVersions") version "0.60.6"
}

rootProject.name = "Kadb"
include(":kadb")
include(":kadb-mdns")

// Fixed-source fallback; this module has no publication configuration.
include(":spake2-legacy")
project(":spake2-legacy").projectDir = file("third-party/spake2")

// Executable consumers and a permission-free install fixture; none are published.
include(":validation-native-adbd", ":validation-android-fixture")
project(":validation-native-adbd").projectDir = file("validation/native-adbd")
project(":validation-android-fixture").projectDir = file("validation/android-fixture")
