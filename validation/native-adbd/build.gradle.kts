plugins {
    alias(libs.plugins.kotlinMultiplatform)
}

kotlin {
    listOf(linuxX64(), macosArm64(), macosX64(), iosSimulatorArm64()).forEach { target ->
        target.binaries.executable {
            baseName = "kadb-native-adbd"
            entryPoint = "com.flyfishxu.kadb.validation.main"
        }
        target.binaries.executable("pairing") {
            baseName = "kadb-native-pairing"
            entryPoint = "com.flyfishxu.kadb.validation.pairing.main"
        }
    }
    applyDefaultHierarchyTemplate()
    sourceSets {
        commonMain.dependencies {
            // External compilation: this consumer can access only Kadb's public API.
            implementation(project(":kadb"))
            implementation(libs.kotlinx.coroutines.core)
        }
    }
}
