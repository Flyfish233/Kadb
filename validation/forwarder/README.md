# Forwarder lifecycle validation

## Red: unchanged upstream production

The JVM product jar from the confirmed M1 red build contains production sources at
`75678915fd4bdd52345edbb6bc4913ae3415a680`; `red/source-audit.txt` records the test-only
changes in that worktree. The new public-API loopback tests were committed as
`d1e3756` and compiled independently against that jar with Kotlin 2.4.20, then run
with JUnit 4.13.2 on JDK 25.0.3. This small CLI run avoided starting a second Gradle
build while the Linux Native toolchain was being initialized.

**Compiler exit 0; JUnit exit 1; four tests executed, four intended assertion failures.**
The failures separately establish that closing a forwarder waits for its pending
OPEN, waits for the shared initial CNXN handshake, leaves idle forwarding workers
blocked, and fails to reclaim a service when its OKAY arrives after forwarder close.
The tests close the whole Kadb only in fixture teardown to release the defective
baseline's workers. The behavior assertions require the shared transport to survive.

`red/manifest.json` records exact commands, classpaths and product-jar SHA-256.
`red/compile.log` and `red/junit.log` are unmodified process output.
`red/sandbox-denied.log` is an earlier environment-only failure: socket creation was
forbidden in the restricted sandbox. It is **not** defect-reproduction evidence.

The same source can run through the normal build with:

```sh
./gradlew :kadb:jvmTest :kadb:testAndroidHostTest --tests '*TcpForwarderLifecycleTest'
```

The initial CLI evidence is JVM-only. It establishes neither Android execution nor
Native execution; those need separate test results after the fix.
