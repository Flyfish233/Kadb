plugins { kotlin("multiplatform") version "2.2.21" }
kotlin {
    jvm()
    linuxX64()
    iosArm64()
    iosSimulatorArm64()
    macosArm64()
    macosX64()
    sourceSets.commonMain.dependencies {
        implementation("com.github.Flyfish233.spake2:legacy:b837aba27bebc1050965fa124c2efa54b4e4544a")
    }
}
tasks.register("resolveJitPackConsumer") {
    doLast {
        val names = listOf("jvmCompileClasspath", "linuxX64CompileKlibraries", "iosArm64CompileKlibraries", "iosSimulatorArm64CompileKlibraries", "macosArm64CompileKlibraries", "macosX64CompileKlibraries")
        val failures = mutableListOf<String>()
        for (name in names) {
            try {
                val resolved = configurations.getByName(name).resolve()
                require(resolved.isNotEmpty()) { "Empty classpath" }
                println("RESOLVED $name: ${resolved.map { it.name }}")
            } catch (failure: Exception) {
                println("FAILED $name: ${failure.message}")
                failures.add(name)
            }
        }
        check(failures.isEmpty()) { "JitPack consumer failed: $failures" }
    }
}
