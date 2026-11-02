#!/usr/bin/env python3
"""Bounded emulator preflight on a fresh ART instance, retaining transport diagnostics."""

import argparse
import datetime
import ipaddress
import json
from pathlib import Path
import re
import subprocess
import time


def network_readiness(connectivity: str, routes: str) -> dict | None:
    """Require Android's default network plus IPv4 routing to the host alias."""
    # Android 15 ConnectivityService.dump() prints the netId or literal "none".
    defaults = re.findall(r"^\s*Active default network:\s*(\d+)\s*$", connectivity, re.MULTILINE)
    if len(defaults) != 1 or int(defaults[0]) <= 0:
        return None
    host = ipaddress.IPv4Address("10.0.2.2")
    entries = [line.split() for line in routes.splitlines() if line.strip()]
    for entry in entries:
        if (entry[0] != "default" or "via" not in entry or "dev" not in entry or "linkdown" in entry):
            continue
        try:
            gateway = entry[entry.index("via") + 1]
            interface = entry[entry.index("dev") + 1]
        except IndexError:
            continue
        if gateway != str(host) or interface == "lo":
            continue
        for direct in entries:
            if "via" in direct or "dev" not in direct or "linkdown" in direct:
                continue
            try:
                subnet = ipaddress.IPv4Network(direct[0], strict=False)
                direct_interface = direct[direct.index("dev") + 1]
            except (ValueError, IndexError):
                continue
            if host in subnet and direct_interface == interface:
                return {"active_default_network": int(defaults[0]), "host_alias": str(host),
                        "interface": interface, "default_route": " ".join(entry),
                        "on_link_route": " ".join(direct)}
    return None


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
                            # sys.boot_completed can precede Wi-Fi/DHCP/default
                            # route assignment. Do not begin the finite peer
                            # sessions while ordinary app sockets get ENETUNREACH.
                            report.setdefault("network_wait_started_seconds", round(time.monotonic() - started, 3))
                            connectivity = run("android-default-network", ["shell", "dumpsys", "connectivity"])
                            routes = run("android-ipv4-routes", ["shell", "ip", "-4", "route", "show", "table", "all"])
                            report["last_connectivity_state"] = connectivity
                            report["last_ipv4_routes"] = routes
                            network = (network_readiness(connectivity["stdout"], routes["stdout"])
                                       if connectivity["exit_code"] == routes["exit_code"] == 0 else None)
                            if network is not None:
                                report["network_readiness"] = network
                                report["status"] = "PASS"
                                report["fingerprint"] = run("fingerprint", ["shell", "getprop", "ro.build.fingerprint"])["stdout"].strip()
                                break
                time.sleep(min(2, max(0, deadline - time.monotonic())))
            if report["status"] != "PASS":
                report["error"] = "Emulator transport, Android boot, package manager or host-network route did not become ready within the single bounded attempt"
        except Exception as error:
            report["error"] = str(error)
            report["error_type"] = type(error).__name__
        finally:
            report["elapsed_seconds"] = round(time.monotonic() - started, 3)
            if "network_wait_started_seconds" in report:
                report["network_wait_seconds"] = round(report["elapsed_seconds"] - report["network_wait_started_seconds"], 3)
            (args.output / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
