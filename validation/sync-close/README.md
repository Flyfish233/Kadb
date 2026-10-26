# Sync close failure: exact baseline and focused repair verification

## Defect

At baseline `75678915fd4bdd52345edbb6bc4913ae3415a680`,
`AdbSyncStream.close()` sends `QUIT` before calling `AdbStream.close()`. If the
QUIT write throws, stream close never runs and its listener remains registered
in `AdbMessageQueue`.

`AdbSyncCloseLifecycleTest` uses the real Sync stream, ADB stream, writer and
message queue. A common blocking Source keeps the reader alive; a controlled
Sink consumes bytes and then throws selected I/O exceptions. No mock replaces
the production close or queue operations. Fixture cleanup runs only after the
assertions and waits for the reader's final Source close, including on the
defective baseline. These tests do not use a network socket or an Android device.

## Exact baseline: defect confirmed

Only the test source at commit `7e5b538` was compiled with Kotlin 2.4.20; production
came from the frozen baseline JVM jar SHA-256
`70de6f6feec77f0453dcf3a87031aacc7fceb56270345ccb61221a02c22d23c5`.

JUnit executed 5 tests in 0.636 seconds, with 3 expected failures and 2 passing
controls, exit 1. Two failures directly report `ADB streams still open: [1]`;
the third observes no suppressed cleanup exception because cleanup never ran.
Successful close and CLSE-only failure were already handled correctly by the
baseline. **The expected failures confirm the defect; this is not a
product-health pass.** `red/` contains raw logs and exact commands/source digest.

## Minimal fix and focused green

`AdbSyncStream.close()` now uses `stream.use { writePacket(ID_QUIT, 0) }`.
The same QUIT precedes stream close, and stream close runs when QUIT fails. The
standard resource helper preserves the original throwable, suppresses a distinct
cleanup throwable and avoids self-suppression. No public signature or synchronous
calling contract changes, and no protocol retry is added.

The unchanged test source and the two production source files (Sync stream plus
its unchanged JVM platform actual) were compiled as a focused overlay on the
same frozen jar, with the correct common/JVM fragment relationship and bytecode
target 25. No source transformation was used. JUnit executed all 5 tests in
1.275 seconds, with 0 failures, exit 0. Tests verify listener removal, exact
exception identity, distinct and identical cleanup failures, and the successful
`WRTE(QUIT, 0)` then `CLSE` byte sequence.

`green-cli/` records source hashes, compiled-class hashes, exact commands and raw
logs. This is a focused JVM repair result, not a complete Gradle module build,
Native execution, Android device run, or performance acceptance. Integrated
`commonTest` must also execute on the retained supported targets. The fix does
not promise bounded shutdown if the underlying transport write itself never
returns, nor delivery of QUIT after a failed transport.
