# Standalone JVM exit experiment

## Decision and compatibility boundary

This branch removes production `jvm()` targets from Kadb, mDNS and the adapted
Legacy SPAKE module. The former desktop NIO/runtime/Java-USB/JmDNS providers are
removed. Platform-independent protocol logic already lived mainly in common
code at the iOS baseline; the material additional sharing is the Legacy PAKE
core, protocol/state hardening and POSIX/Darwin/Linux provider reuse.

Android remains a Kotlin/Android library using ART. Its former shared Java
provider sources move into `androidMain` with file basenames preserved where
that may affect generated JVM facades. Existing package names, File bridges,
default signatures and normal protocol paths are retained and compared against
actual baseline AAR inventories. This is not an attempt to remove Java APIs
from Android.

## Deliberate losses

- Desktop Java/Kotlin/JVM and Compose Desktop consumers can no longer select a
  Kadb JVM artifact. Native consumers need a Native build and native linking.
- Desktop USB support through Java Does USB is removed. No unverified libusb or
  Windows provider is substituted. Android USB remains.
- Desktop JmDNS discovery is removed. macOS uses the shared Foundation Bonjour
  adapter. The Linux mDNS artifact contains only shared models and parsers, with
  no discovery provider; Linux callers must supply a discovered address.
- Windows desktop users lose the old JVM path; `mingwX64` is not declared.
- Java reflection, `java.io.File` desktop convenience overloads and JCA provider
  customization are not APIs of the Native targets. Android equivalents remain.

These are explicit scope changes authorized for the experiment, not claimed
binary compatibility for the removed platform. No `main` branch is changed.

## Validation that survives removal

The exact old baseline continues to build in its own frozen workflow, preserving
its JVM/Android behavior. Historical Java SPAKE/Conscrypt peers are validation
processes only: a Java-only module with no Kadb runtime dependency, no outgoing
archive and no publication plugin. The production tree does not regain a JVM
target to run those oracles. Android Host tests still execute on a host JVM as
required by the Android toolchain. The former shared JVM/Android test sources
now live in `androidHostTest`; their production-independent regressions are
retained rather than lost with the desktop target.

The Native replacement gates include actual Linux/macOS test binaries, iOS
Simulator execution, static frameworks, an external Swift consumer, a separate
Native public-API consumer, independent TLS/pairing reference peers and actual
Android Emulator adbd. The ledger records which of these ran at each commit.
A missing/skipped target gate does not establish Native replacement parity.

## Distribution boundary

Maven publishing and signing plugins/tasks are removed from the experimental
production modules. No new Maven Central/JitPack version, tag or GitHub Release
is created. CI binaries carry their exact source archive and license context.
The AGPL-covered combination is not represented by the upstream Apache-only
2.1.5 publication metadata. See [LICENSES.md](LICENSES.md).
