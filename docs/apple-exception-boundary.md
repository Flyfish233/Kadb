# Swift error handling without changing existing Kadb selectors

`KadbApple` is an additive adapter in `appleMain`. Its constructor takes an
existing Kadb instance; it opens no additional transport. It provides synchronous
`shell`, local-path `push`/`pull`, `install`, `installMultiple`, `uninstall`,
`resetConnection`, and `close` methods, plus a suspending companion `pair` entry point.
Each method delegates directly to Kadb's
common implementation, including the existing default file mode/timestamp logic.
Installation options and paths use Kotlin `List<String>`, which bridges to
Objective-C arrays and Swift arrays.

## Why a language adapter is necessary

Kotlin/Native exports a synchronous function annotated with `@Throws` as an
NSError-producing Objective-C method and a throwing Swift method. Undeclared
Kotlin exceptions crossing the Swift/Objective-C boundary can terminate the
process. These are compiler-defined interop rules, described in the official
[Kotlin/Native documentation](https://kotlinlang.org/docs/native-objc-interop.html#errors-and-exceptions).

Adding `@Throws` to existing synchronous Kadb methods would alter their exported
Objective-C selectors and Swift calling convention. The adapter instead adds new
methods with the error parameter from the outset; the existing Kadb methods are
left unchanged. A Swift closure wrapper around an old Kadb method would not solve
the problem: the original Kotlin method could cross its own undeclared exception
boundary before an outer wrapper got control.

The adapter uses `@Throws(Exception::class)`. It propagates ordinary Kotlin
exceptions, including I/O, certificate-store, argument, state and cancellation
failures, as NSError. It does not catch or declare `Throwable` or fatal `Error`
subclasses. There is no generic catch-and-return-success path.

## Call and ownership contract

```swift
let operations = KadbApple(client: existingKadb)
do {
    let response = try operations.shell(command: "echo hello")
    print(response.output)
    try operations.install(localPath: apkPath, options: [])
} catch {
    // This is an actual Kotlin operation failure exported through NSError.
    print(error)
}
```

The operations remain blocking. Swift callers select a suitable worker thread
when using them from a UI application. This adapter does not schedule work, alter
timeouts, retry commands, or weaken protocol checks. `close()` closes the
underlying Kadb and affects other callers/adapters sharing that same instance.
`resetConnection()` retains Kadb's lazy reconnection behavior.

Raw `AdbStream`, shell-stream, Sync-stream and Okio object operations are not
wrapped. Returning a raw stream here would not make subsequent calls from Swift
safe, because each call has its own interop boundary. Such a streaming adapter is
separate future work. The original unannotated synchronous Kadb methods still do
not propagate ordinary exceptions into Swift. The original unannotated suspend
`Kadb.pair` propagates cancellation through its completion error parameter, but
other exceptions can terminate at the language boundary. Swift callers should use
`KadbApple.companion.pair(host:port:pairingCode:name:completionHandler:)`, whose
ordinary exceptions are declared directly at the Apple entry point. It retains
the common pairing implementation's structured cancellation and password cleanup.

The earlier optional-expect/actual-typealias `NativeThrows` experiment was rejected
by Kotlin/Native 2.4.20 because aliases to compiler-significant annotations can
produce incorrect code. That failed candidate is retained in Git history and its
CI logs. The alias is removed, with no suppressed diagnostic or common annotation
which would change the Java throws signature.

## Required external validation

An external Swift consumer must link against the real generated framework, call
`KadbApple.shell`, and catch NSError after a real loopback peer accepts the socket
and disconnects during CNXN or OPEN. The peer must record the received frame so
the test cannot pass by failing before network I/O. Model construction or invoking
a Kotlin-only test is insufficient to validate this boundary. Compare generated
headers to confirm that the original synchronous Kadb selectors remain present
unchanged and that only the additive adapter introduces throwing methods.
Also invoke the adapter's suspending pairing function against a closed loopback
port and require an NSError callback; calling the original unannotated pair is
not an equivalent error-path test.

Until that external consumer has run, the adapter is source implementation with
a concrete validation entry point, not a claim of tested Swift error propagation.
