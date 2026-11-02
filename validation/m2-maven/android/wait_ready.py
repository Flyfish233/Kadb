#!/usr/bin/env python3
"""Bounded emulator preflight on a fresh ART instance, retaining transport diagnostics."""

import argparse
import datetime
import json
from pathlib import Path
import re
import subprocess
import time


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--adb", required=True)
    parser.add_argument("--serial", required=True)
    parser.add_argument("--adb-server-port", type=int, default=5038)
    parser.add_argument("--timeout", type=int, default=120)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if (not re.fullmatch(r"emulator-[0-9]+", args.serial)
            or not 1 <= args.adb_server_port <= 65535 or not 1 <= args.timeout <= 300):
        parser.error("Require an explicit emulator serial, valid server port and 1..300-second bound")
    args.output.mkdir(parents=True, exist_ok=False)
    command = [args.adb, "-P", str(args.adb_server_port), "-s", args.serial]
    report = {"schema": 1, "status": "NOT VERIFIED", "serial": args.serial,
              "adb_server_port": args.adb_server_port, "timeout_seconds": args.timeout,
              "started_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
              "attempts": 1, "driver_checks_executed": 0}
    started = time.monotonic()
    deadline = started + args.timeout
    with (args.output / "commands.jsonl").open("x") as log:
        def run(label, arguments):
            full = command + arguments
            try:
                result = subprocess.run(full, capture_output=True, text=True, errors="replace",
                                        timeout=max(0.1, min(10, deadline - time.monotonic())))
                entry = {"label": label, "command": full, "exit_code": result.returncode,
                         "stdout": result.stdout, "stderr": result.stderr}
            except subprocess.TimeoutExpired as error:
                entry = {"label": label, "command": full, "exit_code": None,
                         "stdout": (error.stdout or b"").decode("utf-8", "replace"),
                         "stderr": (error.stderr or b"").decode("utf-8", "replace"),
                         "error": "command timeout"}
            entry["elapsed_seconds"] = round(time.monotonic() - started, 3)
            log.write(json.dumps(entry) + "\n")
            log.flush()
            return entry

        try:
            while time.monotonic() < deadline:
                state = run("transport-state", ["get-state"])
                report["last_transport_state"] = state
                if state["exit_code"] == 0 and state["stdout"].strip() == "device":
                    boot = run("boot-completed", ["shell", "getprop", "sys.boot_completed"])
                    report["last_boot_state"] = boot
                    if boot["exit_code"] == 0 and boot["stdout"].strip() == "1":
                        package = run("package-manager-ready", ["shell", "pm", "path", "android"])
                        report["last_package_manager_state"] = package
                        if package["exit_code"] == 0 and package["stdout"].strip().startswith("package:"):
                            qemu = run("emulator-identity", ["shell", "getprop", "ro.kernel.qemu"])
                            if qemu["exit_code"] != 0 or qemu["stdout"].strip() != "1":
                                raise RuntimeError("Explicit emulator serial did not report ro.kernel.qemu=1")
                            report["status"] = "PASS"
                            report["fingerprint"] = run("fingerprint", ["shell", "getprop", "ro.build.fingerprint"])["stdout"].strip()
                            break
                time.sleep(min(2, max(0, deadline - time.monotonic())))
            if report["status"] != "PASS":
                report["error"] = "Emulator transport, Android boot or package manager did not become ready within the single bounded attempt"
        except Exception as error:
            report["error"] = str(error)
            report["error_type"] = type(error).__name__
        finally:
            report["elapsed_seconds"] = round(time.monotonic() - started, 3)
            (args.output / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
