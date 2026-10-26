#!/usr/bin/env python3
"""Require both the independent Java peer and external Native consumer to finish two sessions."""

from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time


def report_line(path: Path, prefix: str) -> dict:
    lines = [line[len(prefix):] for line in path.read_text(errors="replace").splitlines() if line.startswith(prefix)]
    if len(lines) != 1:
        raise RuntimeError(f"Expected one {prefix.strip()} result in {path.name}; got {len(lines)}")
    return json.loads(lines[0])


def hash_file(path: Path) -> str:
    with path.open("rb") as source:
        return hashlib.file_digest(source, "sha256").hexdigest()


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
    classpath = args.classpath_file.resolve(strict=True).read_text().strip()
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
    ready = args.output / "peer-ready"
    command = [args.java, "--enable-native-access=ALL-UNNAMED", "-cp", classpath,
               "com.flyfishxu.kadb.validation.peer.IosPairingPeer", str(ready.resolve())]
    report["peer_command"] = command
    peer_log_path = args.output / "java-peer.log"
    native_log_path = args.output / "native-consumer.log"
    with peer_log_path.open("w") as peer_log:
        peer = subprocess.Popen(command, stdout=peer_log, stderr=subprocess.STDOUT)
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
                native = subprocess.run(native_command, stdout=native_log, stderr=subprocess.STDOUT, timeout=75)
            report["native_exit_code"] = native.returncode
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
    report["native"] = report_line(native_log_path, "KADB_NATIVE_PAIRING_JSON ")
    report["peer"] = report_line(peer_log_path, "KADB_PAIRING_PEER_JSON ")
    if report["native_exit_code"] != 0 or report["peer_exit_code"] != 0:
        raise RuntimeError("Interop requires successful exits from both actual processes")
    if report["native"].get("status") != "passed" or report["native"].get("checks_executed") != 2:
        raise RuntimeError("Native consumer did not complete both checks")
    if (report["peer"].get("status") != "passed" or report["peer"].get("sessions_executed") != 2
            or report["peer"].get("positive_sessions") != 1 or report["peer"].get("wrong_code_rejections") != 1):
        raise RuntimeError("Reference peer did not confirm both independent sessions")
    report["scope"] = {"native_executable_linked_and_executed": True,
                       "ios_simulator_executed": args.simulator_udid is not None,
                       "independent_legacy_spake_peer": True, "tls_exporter_and_peer_info": True,
                       "real_adbd": False, "physical_device": False,
                       "independent_security_audit": False, "performance_acceptance": False}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--consumer", type=Path, required=True)
    parser.add_argument("--classpath-file", type=Path, required=True)
    parser.add_argument("--java", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--simulator-udid", help="Explicit booted iOS Simulator UDID; otherwise run directly on the host")
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
