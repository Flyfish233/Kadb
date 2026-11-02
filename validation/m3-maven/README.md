# M3 — actual Android adbd integration

Recovered baseline: `ecc0f358b46a9805d0c102318f211b5e4fe67f14` on
`work/spake2-maven-migration`. M1 and M2 remain PASS under their existing scopes.
The candidate remains `0.1.0-dev.59105290820b`, source
`59105290820bcbfd4e0336a2e7713006a461527f`.

M3 records three independent acceptance layers:

* **M3-A:** external Native consumer → real emulator adbd, public ADB API and
  authorization. A transport-only run with `ro.adb.secure=0` cannot establish
  RSA AUTH rejection or acceptance, even if every API check passes.
* **M3-B:** public `Kadb.pair` → Android's real system pairing service, with
  positive pairing, representative authentication failures and session isolation.
  A Java reference peer is supplemental evidence only.
* **M3-C:** physical-device pairing and connection; no physical device is selected
  automatically, and none is available to this CI job.

`ci/` contains the dedicated, bounded workflow entry points. `recovery/` retains
the observed baseline failure and its distinction from M2's network readiness
issue. `runs/<run-id>/` will retain actual execution evidence and failures.
Verdicts are assigned from observed protocol results, not a green CI icon.

The local recovery environment has no Android SDK executable or `/dev/kvm` in
PATH/runtime. Actual emulator execution uses an isolated GitHub runner, an
explicit `emulator-5554`, separate ADB server port 5038, disposable AVD and keys.
Secrets, AVD data, RSA private keys and pairing codes are excluded from evidence.

R3-K01 (inherited bidirectional GCM nonce behavior) remains an open protocol risk;
this milestone does not change the AOSP wire protocol or production SPAKE2 code.
