pluginManagement {
    repositories {
        mavenLocal()
        google()
        mavenCentral()
        gradlePluginPortal()
    }
}

// Restore the checked-in, byte-pinned CI candidate with:
// python3 scripts/prepare_spake2_candidate.py
// An explicit alternative directory must contain the same verified Maven files.
val spake2CandidateUri = uri(providers.gradleProperty("spake2Repository")
    .orElse(file("build/spake2-candidate/maven").absolutePath).get())
require(spake2CandidateUri.scheme == "file") {
    "SPAKE2 M1 requires a verified local Maven candidate repository"
}
require(file(spake2CandidateUri).isDirectory) {
    "Missing SPAKE2 candidate: run python3 scripts/prepare_spake2_candidate.py " +
        "or pass -Pspake2Repository=/absolute/path/to/verified/maven"
}

dependencyResolutionManagement {
    repositoriesMode.set(RepositoriesMode.FAIL_ON_PROJECT_REPOS)
    repositories {
        exclusiveContent {
            forRepository {
                maven {
                    name = "spake2ValidatedCandidate"
                    url = spake2CandidateUri
                    metadataSources { gradleMetadata(); mavenPom() }
                }
            }
            filter { includeGroup("io.github.flyfish233") }
        }
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

// Executable consumers and a permission-free install fixture; none are published.
include(":validation-native-adbd", ":validation-android-fixture")
project(":validation-native-adbd").projectDir = file("validation/native-adbd")
project(":validation-android-fixture").projectDir = file("validation/android-fixture")
include(":validation-pairing-peer")
project(":validation-pairing-peer").projectDir = file("validation/pairing-peer")
include(":validation-android-runtime")
project(":validation-android-runtime").projectDir = file("validation/android-runtime")
