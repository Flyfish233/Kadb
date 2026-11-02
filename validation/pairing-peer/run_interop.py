#!/usr/bin/env python3
"""Require both the independent Java peer and external Native consumer to finish two sessions."""

from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import secrets
import subprocess
import sys
import time

M3_CASES = [
    "positive_seed", "wrong_code", "stale_exporter", "wrong_role", "missing_identity_nul",
    "invalid_spake_length", "invalid_header", "bad_gcm_tag", "invalid_peer_info",
    "network_disconnect", "timeout", "cancellation", "positive_recovery",
]
M3_STAGES = {
    "positive_seed": "valid_peer_info_and_client_close",
    "wrong_code": "peer_gcm_rejected_client_authentication",
    "stale_exporter": "peer_gcm_rejected_client_authentication",
    "wrong_role": "peer_gcm_rejected_client_authentication",
    "missing_identity_nul": "peer_gcm_rejected_client_authentication",
    "invalid_spake_length": "client_rejected_31_byte_spake",
    "invalid_header": "client_rejected_header_version_2",
    "bad_gcm_tag": "client_rejected_corrupt_gcm_tag",
    "invalid_peer_info": "client_rejected_wrong_peer_info_type",
    "network_disconnect": "peer_closes_after_client_spake",
    "timeout": "client_closed_stalled_exchange",
    "cancellation": "client_closed_stalled_exchange",
    "positive_recovery": "valid_peer_info_and_client_close",
}
M3_CLOSURE = {case: ("peer_initiated" if case in {
    "wrong_code", "stale_exporter", "wrong_role", "missing_identity_nul", "network_disconnect",
} else "client_initiated") for case in M3_CASES}


def report_line(path: Path, prefix: str) -> dict:
    lines = [line[len(prefix):] for line in path.read_text(errors="replace").splitlines() if line.startswith(prefix)]
    if len(lines) != 1:
        raise RuntimeError(f"Expected one {prefix.strip()} result in {path.name}; got {len(lines)}")
    return json.loads(lines[0])


def hash_file(path: Path) -> str:
    with path.open("rb") as source:
        return hashlib.file_digest(source, "sha256").hexdigest()


def preserve_process_reports(report: dict, native_log: Path, peer_log: Path) -> None:
    """Keep any actual final/partial evidence even when a process failed or was terminated."""
    for key, path, prefix in (("native", native_log, "KADB_NATIVE_PAIRING_JSON "),
                              ("peer", peer_log, "KADB_PAIRING_PEER_JSON ")):
        try:
            report[key] = report_line(path, prefix)
        except (OSError, ValueError, RuntimeError) as error:
            report.setdefault("result_record_errors", {})[key] = str(error)
        if path.is_file():
            report.setdefault("process_log_sha256", {})[key] = hash_file(path)
    if peer_log.is_file():
        partial = []
        events = []
        for line in peer_log.read_text(errors="replace").splitlines():
            if line.startswith("KADB_PAIRING_CASE_JSON "):
                try:
                    partial.append(json.loads(line.removeprefix("KADB_PAIRING_CASE_JSON ")))
                except ValueError as error:
                    report.setdefault("result_record_errors", {})["peer_partial"] = str(error)
            if line.startswith("KADB_PAIRING_SESSION_JSON "):
                try:
                    events.append(json.loads(line.removeprefix("KADB_PAIRING_SESSION_JSON ")))
                except ValueError as error:
                    report.setdefault("result_record_errors", {})["peer_session_events"] = str(error)
        report["peer_completed_case_records"] = partial
        report["peer_session_events"] = events


def verified_reference_classpath(classpath_file: Path, report: dict) -> str:
    """Shared process-launch preflight; neither consumer duplicates the reference protocol."""
    classpath = classpath_file.resolve(strict=True).read_text().strip()
    if not classpath or "\n" in classpath:
        raise RuntimeError("Malformed reference-classpath file")
    entries = [Path(entry).resolve(strict=True) for entry in classpath.split(os.pathsep)]
    expected = dict(line.split("  ", 1)[::-1] for line in (Path(__file__).parent / "SHA256SUMS").read_text().splitlines() if line)
    artifacts = {entry.name: hash_file(entry) for entry in entries if entry.is_file()}
    if artifacts != expected:
        raise RuntimeError("Reference classpath artifact inventory/checksums differ from SHA256SUMS")
    class_files = {}
    for entry in entries:
        if entry.is_dir():
            for compiled in sorted(entry.rglob("*.class")):
                class_files[compiled.relative_to(entry).as_posix()] = hash_file(compiled)
    if "com/flyfishxu/kadb/validation/peer/IosPairingPeer.class" not in class_files:
        raise RuntimeError("Independent peer class was not compiled")
    if any(not name.startswith("com/flyfishxu/kadb/validation/peer/") for name in class_files):
        raise RuntimeError("Reference class directory includes unrelated or Kadb production classes")
    report["reference_artifacts"] = artifacts
    report["reference_classes"] = class_files
    return classpath


def execute(args, report: dict) -> None:
    repo = Path(__file__).resolve().parents[2]
    report["commit"] = subprocess.run(["git", "-C", repo, "rev-parse", "HEAD"], capture_output=True,
                                       text=True, check=True, timeout=10).stdout.strip()
    report["tracked_worktree_changes"] = subprocess.run(
        ["git", "-C", repo, "status", "--porcelain", "--untracked-files=no"], capture_output=True,
        text=True, check=True, timeout=10).stdout
    consumer = args.consumer.resolve(strict=True)
    if not os.access(consumer, os.X_OK):
        raise RuntimeError("Native consumer is not executable")
    with consumer.open("rb") as binary:
        magic = binary.read(4)
    if magic not in (b"\x7fELF", b"\xcf\xfa\xed\xfe", b"\xfe\xed\xfa\xcf", b"\xca\xfe\xba\xbe", b"\xbe\xba\xfe\xca"):
        raise RuntimeError("Consumer is not a linked ELF/Mach-O binary")
    report["consumer_sha256"] = hash_file(consumer)
    report["consumer_bytes"] = consumer.stat().st_size
    report["java_version"] = subprocess.run([args.java, "-version"], capture_output=True, text=True,
                                             check=True, timeout=10).stderr.strip()
    classpath = verified_reference_classpath(args.classpath_file, report)
    ready = args.output / "peer-ready"
    peer_class = "M3PairingPeer" if args.m3_negative_suite else "IosPairingPeer"
    command = [args.java, "--enable-native-access=ALL-UNNAMED", "-cp", classpath,
               "com.flyfishxu.kadb.validation.peer." + peer_class, str(ready.resolve())]
    report["peer_command"] = command
    peer_log_path = args.output / "java-peer.log"
    native_log_path = args.output / "native-consumer.log"
    process_env = dict(os.environ)
    if args.m3_negative_suite:
        # Environment-only, per-run secret. Neither commands nor reports contain its value.
        process_env["KADB_M3_PAIRING_CODE"] = f"{secrets.randbelow(1_000_000):06d}"
        if args.simulator_udid:
            process_env["SIMCTL_CHILD_KADB_M3_PAIRING_CODE"] = process_env["KADB_M3_PAIRING_CODE"]
    with peer_log_path.open("w") as peer_log:
        peer = subprocess.Popen(command, stdout=peer_log, stderr=subprocess.STDOUT, env=process_env)
        try:
            deadline = time.monotonic() + 45
            while not ready.exists():
                if peer.poll() is not None:
                    raise RuntimeError(f"Reference peer exited before becoming ready: {peer.returncode}")
                if time.monotonic() >= deadline:
                    raise RuntimeError("Reference peer did not become ready within 45s")
                time.sleep(0.1)
            port = int(ready.read_text())
            if not 1 <= port <= 65535:
                raise RuntimeError("Invalid reference peer port")
            native_command = [str(consumer), "--port", str(port)]
            if args.m3_negative_suite:
                native_command.append("--m3-negative-suite")
            if args.simulator_udid:
                state = subprocess.run(["xcrun", "simctl", "list", "devices", "booted", "--json"],
                                       capture_output=True, text=True, timeout=10, check=True)
                devices = [device for group in json.loads(state.stdout)["devices"].values() for device in group]
                if not any(device.get("udid") == args.simulator_udid and device.get("state") == "Booted" for device in devices):
                    raise RuntimeError("Explicit iOS Simulator UDID is not booted")
                report["simulator_udid"] = args.simulator_udid
                report["simulator_inventory"] = json.loads(state.stdout)
                native_command = ["xcrun", "simctl", "spawn", args.simulator_udid, *native_command]
            report["native_command"] = native_command
            with native_log_path.open("w") as native_log:
                native = subprocess.run(native_command, stdout=native_log, stderr=subprocess.STDOUT,
                                        timeout=150 if args.m3_negative_suite else 75, env=process_env)
            report["native_exit_code"] = native.returncode
            if native.returncode != 0:
                raise RuntimeError("Native consumer exited unsuccessfully; preserving its actual partial results")
            report["peer_exit_code"] = peer.wait(timeout=15)
        finally:
            if peer.poll() is None:
                peer.terminate()
                try:
                    peer.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    peer.kill()
                    peer.wait(timeout=5)
            report.setdefault("peer_exit_code", peer.returncode)
            preserve_process_reports(report, native_log_path, peer_log_path)
    if report.get("result_record_errors"):
        raise RuntimeError("Missing or malformed process result records; see result_record_errors")
    if report["native_exit_code"] != 0 or report["peer_exit_code"] != 0:
        raise RuntimeError("Interop requires successful exits from both actual processes")
    verify_reports(report, args.m3_negative_suite)
    report["scope"] = {"native_executable_linked_and_executed": True,
                       "ios_simulator_executed": args.simulator_udid is not None,
                       "independent_legacy_spake_peer": True, "tls_exporter_and_peer_info": True,
                       "real_adbd": False, "physical_device": False,
                       "independent_security_audit": False, "performance_acceptance": False}
    if args.m3_negative_suite:
        report["scope"].update({"test_layer": "supplementary_independent_controlled_peer",
                                "faults_injected_by_peer": True, "fresh_session_recovery": True,
                                "closure_initiator_by_case": M3_CLOSURE,
                                "client_initiated_close_observed_for": [case for case in M3_CASES
                                    if M3_CLOSURE[case] == "client_initiated"],
                                "peer_initiated_close_only_for": [case for case in M3_CASES
                                    if M3_CLOSURE[case] == "peer_initiated"],
                                "internal_memory_zeroization_observed": False,
                                "inherited_r3_k01_nonce_risk": "unchanged AOSP-compatible bidirectional nonce 0"})


def verify_reports(report: dict, m3: bool) -> None:
    native, peer = report["native"], report["peer"]
    if m3:
        if (native.get("status") != "passed" or native.get("checks_executed") != len(M3_CASES)
                or native.get("cases") != M3_CASES or native.get("real_adbd") is not False):
            raise RuntimeError("Native consumer did not execute every controlled-peer check")
        cases = peer.get("cases", [])
        if (peer.get("status") != "passed" or peer.get("sessions_executed") != len(M3_CASES)
                or peer.get("positive_sessions") != 2 or peer.get("expected_negative_sessions") != 11
                or peer.get("negative_sessions_completed") != 11 or peer.get("tls_sessions_completed") != 13
                or peer.get("completed_sessions") != len(M3_CASES) or peer.get("real_adbd") is not False
                or [case.get("case") for case in cases] != M3_CASES
                or any(case.get("status") != "passed"
                       or case.get("stage") != M3_STAGES.get(case.get("case"))
                       or case.get("closure") != M3_CLOSURE.get(case.get("case")) for case in cases)):
            raise RuntimeError("Controlled peer did not confirm all actual fault-injection sessions")
    else:
        if native.get("status") != "passed" or native.get("checks_executed") != 2:
            raise RuntimeError("Native consumer did not complete both checks")
        if (peer.get("status") != "passed" or peer.get("sessions_executed") != 2
                or peer.get("positive_sessions") != 1 or peer.get("wrong_code_rejections") != 1):
            raise RuntimeError("Reference peer did not confirm both independent sessions")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--consumer", type=Path, required=True)
    parser.add_argument("--classpath-file", type=Path, required=True)
    parser.add_argument("--java", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--simulator-udid", help="Explicit booted iOS Simulator UDID; otherwise run directly on the host")
    parser.add_argument("--m3-negative-suite", action="store_true",
                        help="Run supplemental controlled-peer faults; never counted as real adbd pairing")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    report = {"schema": 1, "status": "failed", "started_utc": datetime.datetime.now(datetime.timezone.utc).isoformat()}
    code = 1
    try:
        execute(args, report)
        report["status"] = "passed"
        code = 0
    except Exception as error:
        report["error_type"] = type(error).__name__
        report["error"] = str(error)
    finally:
        (args.output / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"status": report["status"], "report": str(args.output / "report.json")}))
    return code


if __name__ == "__main__":
    sys.exit(main())
