#!/usr/bin/env python3
"""Record independent Android M2 outcomes without promoting absent execution to PASS."""

import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence", required=True, type=Path)
    args = parser.parse_args()
    args.evidence.mkdir(parents=True, exist_ok=True)
    outcomes = {name.lower(): os.environ.get("M2_" + name, "unknown") for name in (
        "CANDIDATE", "BUILD", "RUNTIME_SOURCE", "SOURCE", "ASSOCIATION", "PROVISION", "READY", "ART")}

    def status(name):
        return {"success": "PASS", "failure": "FAIL"}.get(outcomes[name], "NOT VERIFIED")

    def read(relative):
        path = args.evidence / relative
        return json.loads(path.read_text()) if path.is_file() else None

    runtime = read("android-runtime/report.json")
    apk = read("android-runtime-apk.json")
    source = read("android-runtime-source-verification.json")
    stages = {"maven_candidate_integrity": status("candidate"), "compile_and_package": status("build"),
              "apk_runtime_graph_and_source": status("runtime_source"),
              "complete_corresponding_source": status("source"),
              "apk_source_association": status("association"),
              "android_ART_and_protocol": status("art")}
    stages["emulator_environment"] = "PASS" if outcomes["ready"] == "success" else "NOT VERIFIED"
    # A provision/readiness failure prevents product execution and is not itself
    # evidence that the migrated library failed on ART.
    if any(stages[key] == "FAIL" for key in stages if key != "emulator_environment"):
        verdict = "FAIL"
    elif all(value == "PASS" for value in stages.values()):
        verdict = "PASS"
    else:
        verdict = "NOT VERIFIED"
    hashes = {}
    for path in sorted(args.evidence.rglob("*")):
        if path.is_file() and path.name != "platform-status.json" and path.suffix != ".gz":
            hashes[path.relative_to(args.evidence).as_posix()] = {
                "bytes": path.stat().st_size, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
    report = {
        "schema": 1, "platform": "Android Emulator API 35 x86_64 ART", "verdict": verdict,
        "source_sha": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
        "run_id": os.environ.get("GITHUB_RUN_ID"), "run_attempt": os.environ.get("GITHUB_RUN_ATTEMPT"),
        "recorded_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "candidate_version": "0.1.0-dev.59105290820b", "stages": stages, "step_outcomes": outcomes,
        "instrumentation_checks_executed": (runtime or {}).get("android", {}).get("checks_executed", 0),
        "independent_peer_sessions": (runtime or {}).get("peer", {}).get("sessions_executed", 0),
        "apk": apk, "runtime_source": source, "runtime": runtime,
        "readiness": read("emulator-readiness/report.json"),
        "historical_baseline": {"source_sha": "49a88b14e9b731e4c086c920eb74664450c79d9f",
                                "run_id": 40331404006, "checks_executed": 0,
                                "failure": "ART readiness timeout after earlier Native driver changed adbd to TCP mode; emulator initially booted in about 30 seconds"},
        "scope": {"physical_device": False, "real_adbd_pairing": False,
                  "host_tests_counted_as_ART": False, "production_crypto_changed": False},
        "evidence_files": hashes,
    }
    (args.evidence / "platform-status.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"verdict": verdict, "stages": stages,
                      "instrumentation_checks_executed": report["instrumentation_checks_executed"],
                      "independent_peer_sessions": report["independent_peer_sessions"]}))


if __name__ == "__main__":
    main()
