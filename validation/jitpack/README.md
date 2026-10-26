# Fixed-commit JitPack consumption probe — failed, source fallback in use

Dependency: `com.github.Flyfish233.spake2:legacy:b837aba27bebc1050965fa124c2efa54b4e4544a`.

This standalone Gradle KMP consumer was actually executed on 2026-10-26, using
Gradle 8.14.3, JDK 17, and the pinned SPAKE2 project's Kotlin version 2.2.21.
`resolveJitPackConsumer` attempts to resolve actual platform compilation classpaths;
a JitPack status page is not its success criterion. It exited **1** and every
requested JVM / Linux / iOS / macOS classpath failed. This is a failed dependency
integration probe, not a passing product health test.

Raw evidence is retained under `logs/`:

- `gradle-consumer.log`: the executed Gradle task and six failed configurations.
- `legacy-module-response.log`: the requested Legacy `.module` returned HTTP 404.
- `jitpack-status.json`: `status: Error`, `modules: []`, no build artifacts.
- `jitpack-build.log`: `publishToMavenLocal` does not exist in the pinned build.

Metadata URL:
<https://jitpack.io/com/github/Flyfish233/spake2/legacy/b837aba27bebc1050965fa124c2efa54b4e4544a/legacy-b837aba27bebc1050965fa124c2efa54b4e4544a.module>

Build log:
<https://jitpack.io/com/github/Flyfish233/spake2/b837aba27bebc1050965fa124c2efa54b4e4544a/build.log>

The root repository's source is public. Its first API response still reported
`private: true`; after the real request the failed build reports `private: false`.
Privacy is not the cause asserted here: the build log identifies the missing
publication task. No upstream repository was modified to fix it.

The standalone probe did **not** execute an Android variant consumer. Publication
failed before a usable module or Android variant existed. The pinned upstream
also lacks macOS targets and enables Android only with `-PenableAndroid=true`.
Therefore Android/JVM/Native JitPack integration is **not complete**. Later
Android/Native source-fallback builds must be recorded separately.

Reproduction with Gradle 8.14.3 / JDK 17 (or the unchanged wrapper from the exact
SPAKE2 source checkout):

```sh
gradle --no-daemon -p validation/jitpack \
  -Dorg.gradle.internal.http.connectionTimeout=15000 \
  -Dorg.gradle.internal.http.socketTimeout=15000 resolveJitPackConsumer
```

JitPack's documented multi-module coordinate convention and Gradle publication
requirements: <https://docs.jitpack.io/building/>.

Kadb instead consumes the fixed, hash-checked source subset in
`third-party/spake2`. That Gradle target adaptation is explicit; it must never be
reported as Maven/JitPack integration success.
