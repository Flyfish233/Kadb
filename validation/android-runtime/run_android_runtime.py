#!/usr/bin/env python3
"""Execute the real Android APK through ART against the existing independent Java peer."""

from __future__ import annotations

import argparse
import datetime
import json
from pathlib import Path
import re
import secrets
import subprocess
import sys
import time

from inspect_apk import inspect_apk

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "validation/pairing-peer"))
sys.path.insert(0, str(REPO / "validation/native-adbd"))
from run_interop import hash_file, report_line, verified_reference_classpath
# The logging/explicit-serial ADB runner is shared with Native validation.
from run_emulator import Runner

PACKAGE = "com.flyfishxu.kadb.validation.runtime"
COMPONENT = PACKAGE + "/" + PACKAGE + ".RuntimeInstrumentation"
EXPECTED_CHECKS = [
    "identity_generate", "identity_export_copy_isolation", "identity_import_certificate",
    "identity_file_persistence", "identity_diagnostic_redaction", "identity_parse_failure_retains_state",
    "pairing_positive", "pairing_wrong_code", "identity_clear",
]


def instrumentation_report(stdout: str) -> dict:
    prefix = "INSTRUMENTATION_RESULT: kadb_runtime_json="
    reports = [line[len(prefix):] for line in stdout.splitlines() if line.startswith(prefix)]
    if len(reports) != 1:
        raise RuntimeError("Instrumentation must emit exactly one JSON report")
    return json.loads(reports[0])


def require_instrumentation_pass(stdout: str, result: dict) -> dict:
    codes = re.findall(r"^INSTRUMENTATION_CODE: (-?\d+)\s*$", stdout, re.MULTILINE)
    if codes != ["-1"]:
        raise RuntimeError("Instrumentation must finish exactly once with RESULT_OK and one JSON report")
    if (result.get("status") != "passed" or result.get("checks") != EXPECTED_CHECKS
            or result.get("checks_executed") != len(EXPECTED_CHECKS)):
        raise RuntimeError("Android consumer did not execute all nine mandatory checks")
    if result.get("physical_device") is not False or result.get("device_kind") != "android_emulator":
        raise RuntimeError("Unexpected Android consumer execution scope")
    details = result.get("details", {})
    if details.get("vm_name") != "Dalvik" or details.get("bundled_conscrypt") is not False:
        raise RuntimeError("Android ART / platform TLS provider evidence is missing")
    return result


def parse_instrumentation(stdout: str) -> dict:
    return require_instrumentation_pass(stdout, instrumentation_report(stdout))


def execute(args, runner: Runner, report: dict) -> None:
    report["commit"] = runner.run("git-commit", ["git", "-C", REPO, "rev-parse", "HEAD"]).stdout.strip()
    report["tracked_worktree_changes"] = runner.run("git-status", ["git", "-C", REPO, "status", "--porcelain", "--untracked-files=no"]).stdout
    for name in ("apk", "adb", "aapt2", "java"):
        path = Path(getattr(args, name)).resolve(strict=True)
        setattr(args, name, str(path))
        report.setdefault("artifacts", {})[name] = {"bytes": path.stat().st_size, "sha256": hash_file(path)}
    report["apk_dex"] = inspect_apk(Path(args.apk))
    badging = runner.run("inspect-apk", [args.aapt2, "dump", "badging", args.apk]).stdout
    if not re.search(rf"^package: name='{re.escape(PACKAGE)}' ", badging, re.MULTILINE):
        raise RuntimeError("APK is not the disposable Android runtime package")
    permissions = re.findall(r"^uses-permission(?:-sdk-\d+)?: name='([^']+)'", badging, re.MULTILINE)
    if permissions != ["android.permission.INTERNET"]:
        raise RuntimeError(f"Runtime fixture permission inventory changed: {permissions}")
    report["adb_version"] = runner.run("adb-version", [args.adb, "version"]).stdout.strip()
    report["java_version"] = runner.run("java-version", [args.java, "-version"]).stderr.strip()
    runner.wait_ready()
    if runner.shell("verify-emulator", "getprop ro.kernel.qemu").stdout.strip() != "1":
        raise RuntimeError("Refusing to install on a non-emulator transport")
    report["serial"] = args.serial
    report["device_kind"] = "android_emulator"
    report["fingerprint"] = runner.shell("device-fingerprint", "getprop ro.build.fingerprint").stdout.strip()
    absent = runner.shell("fixture-must-be-absent", f"pm path {PACKAGE}", check=False)
    if absent.returncode != 1 or absent.stdout.strip() or absent.stderr.strip():
        raise RuntimeError("Runtime fixture is already installed or its package state is uncertain")
    classpath = verified_reference_classpath(args.classpath_file, report)
    install_attempted = False
    peer = None
    primary_error = None
    cleanup_errors = []
    try:
        # Do not replace an installed package or alter the no-permission install fixture.
        install_attempted = True
        runner.adb("install-runtime-fixture", "install", args.apk, timeout=120)
        ready = args.output / "peer-ready"
        peer_log_path = args.output / "java-peer.log"
        command = [args.java, "--enable-native-access=ALL-UNNAMED", "-cp", classpath,
                   "com.flyfishxu.kadb.validation.peer.IosPairingPeer", str(ready.resolve())]
        report["peer_command"] = command
        with peer_log_path.open("w") as peer_log:
            peer = subprocess.Popen(command, stdout=peer_log, stderr=subprocess.STDOUT)
            deadline = time.monotonic() + 45
            while not ready.exists():
                if peer.poll() is not None:
                    raise RuntimeError(f"Independent reference exited before readiness: {peer.returncode}")
                if time.monotonic() >= deadline:
                    raise RuntimeError("Independent peer did not become ready")
                time.sleep(0.1)
            port = int(ready.read_text())
            if not 1 <= port <= 65535:
                raise RuntimeError("Invalid reference port")
            run_id = secrets.token_hex(16)
            report["run_id"] = run_id
            instrumentation = runner.adb(
                "android-runtime-instrumentation", "shell", "am", "instrument", "-w", "-r",
                "-e", "peer_host", "10.0.2.2", "-e", "peer_port", str(port), "-e", "run_id", run_id,
                COMPONENT, timeout=120, check=False)
            (args.output / "instrumentation.log").write_text(instrumentation.stdout + instrumentation.stderr)
            report["instrumentation_adb_exit_code"] = instrumentation.returncode
            if instrumentation.returncode != 0:
                raise RuntimeError("ADB instrumentation command failed")
            # Preserve actual partial execution even when the pass gate fails.
            report["android"] = instrumentation_report(instrumentation.stdout)
            require_instrumentation_pass(instrumentation.stdout, report["android"])
            report["peer_exit_code"] = peer.wait(timeout=15)
        report["peer"] = report_line(peer_log_path, "KADB_PAIRING_PEER_JSON ")
        if (report["peer_exit_code"] != 0 or report["peer"].get("status") != "passed"
                or report["peer"].get("sessions_executed") != 2 or report["peer"].get("positive_sessions") != 1
                or report["peer"].get("wrong_code_rejections") != 1):
            raise RuntimeError("Independent peer did not confirm both real pairing sessions")
        report["scope"] = {"android_apk_dex_and_art_executed": True,
                           "platform_android_tls_exporter_and_peer_info": True,
                           "independent_legacy_spake_peer": True,
                           "physical_device": False, "real_adbd_pairing": False,
                           "security_or_performance_acceptance": False}
    except Exception as error:
        primary_error = error
    finally:
        # A stuck reference process must not prevent fixture removal or replace
        # the original instrumentation failure with a shutdown exception.
        try:
            if peer is not None and peer.poll() is None:
                peer.terminate()
                try:
                    peer.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    peer.kill()
                    peer.wait(timeout=5)
        except Exception as error:
            cleanup_errors.append("Reference peer cleanup: " + str(error))
        if peer is not None:
            report.setdefault("peer_exit_code", peer.returncode)
        if install_attempted:
            try:
                state = runner.shell("cleanup-fixture-state", f"pm path {PACKAGE}", check=False)
                if state.returncode == 0 and state.stdout.startswith("package:"):
                    runner.adb("stop-runtime-instrumentation", "shell", "am", "force-stop", PACKAGE)
                    runner.adb("uninstall-runtime-fixture", "uninstall", PACKAGE, timeout=60)
                elif state.returncode != 1 or state.stdout.strip() or state.stderr.strip():
                    raise RuntimeError("Cannot determine runtime fixture state during cleanup")
                absent = runner.shell("independent-uninstall-check", f"pm path {PACKAGE}", check=False)
                if absent.returncode != 1 or absent.stdout.strip() or absent.stderr.strip():
                    raise RuntimeError("Official ADB did not confirm runtime fixture removal")
            except Exception as error:
                cleanup_errors.append(str(error))
        report["cleanup_errors"] = cleanup_errors
    if primary_error is not None:
        raise primary_error
    if cleanup_errors:
        raise RuntimeError("Runtime checks completed but fixture cleanup failed")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("serial", "adb", "aapt2", "java", "apk"):
        parser.add_argument("--" + name, required=True)
    parser.add_argument("--classpath-file", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--adb-server-port", type=int, default=5038)
    args = parser.parse_args()
    if not re.fullmatch(r"emulator-[0-9]+", args.serial):
        parser.error("Explicit --serial emulator-N is required")
    if not 1 <= args.adb_server_port <= 65535:
        parser.error("ADB server port is invalid")
    args.output.mkdir(parents=True, exist_ok=False)
    report = {"schema": 1, "status": "failed", "checks_expected": len(EXPECTED_CHECKS),
              "started_utc": datetime.datetime.now(datetime.timezone.utc).isoformat()}
    runner = Runner(args, args.output)
    try:
        execute(args, runner, report)
        report["status"] = "passed"
        code = 0
    except Exception as error:
        report["error_type"] = type(error).__name__
        report["error"] = str(error)
        code = 1
    finally:
        report["commands_executed"] = runner.counter
        runner.log.close()
        (args.output / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"status": report["status"], "report": str(args.output / "report.json"),
                      "checks_executed": report.get("android", {}).get("checks_executed", 0),
                      "commands_executed": report["commands_executed"],
                      "error_type": report.get("error_type"), "error": report.get("error")}))
    return code


if __name__ == "__main__":
    sys.exit(main())
