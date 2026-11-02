#!/usr/bin/env python3
"""Checkpoint A: official disposable user image, real AUTH, rootless management.

This is an environment probe, not the Native public API M4 acceptance suite.
No system properties, authorization files, or production binaries are patched.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import socket
import struct
import sys

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "validation/m3-maven/ci"))
from run_pairing import Runner


def receive(sock, count):
    value = b""
    while len(value) < count:
        part = sock.recv(count - len(value))
        if not part:
            raise RuntimeError("adbd closed before the complete AUTH frame")
        value += part
    return value


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--adb", required=True)
    parser.add_argument("--serial", choices=["emulator-5554"], required=True)
    parser.add_argument("--adb-server-port", type=int, default=5038)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    runner = Runner(args)
    report = {"schema": 1, "status": "failed", "milestone": "M4-environment",
              "physical_device": False, "M4_A": "NOT VERIFIED", "M4_B": "NOT VERIFIED",
              "auth_disabled": False, "image_modified": False}
    forward = None
    cleanup_errors = []
    try:
        bootstrap = Path(os.environ["ANDROID_USER_HOME"]) / "adbkey.pub"
        if bootstrap.exists():
            runner.secrets.append(bootstrap.read_text().split()[0])
        runner.ready()
        props = {}
        for key in ("ro.kernel.qemu", "ro.adb.secure", "ro.debuggable", "ro.secure",
                    "ro.build.fingerprint", "ro.build.version.sdk", "ro.build.type",
                    "ro.product.cpu.abi", "service.adb.tcp.port", "service.adb.tls.port"):
            props[key] = runner.shell("property-" + key, "getprop", key).stdout.strip()
        report["properties"] = props
        assert props["ro.kernel.qemu"] == "1", "Only the disposable emulator is permitted"
        assert props["ro.adb.secure"] == "1", "Authentication is not enabled"
        assert props["ro.build.type"] == "user", "Expected the unmodified official user image"
        assert props["ro.build.version.sdk"] == "35", "Binder ABI requires API 35"
        report["shell_uid"] = runner.shell("shell-uid", "id", "-u").stdout.strip()
        assert report["shell_uid"] == "2000", "Must exercise rootless system management"
        for label, command in {
            "adbd-version": "/apex/com.android.adbd/bin/adbd --version",
            "adbd-sha256": "sha256sum /apex/com.android.adbd/bin/adbd",
            "processes": "ps -A -o PID,UID,NAME",
            "shell-permissions": "dumpsys package com.android.shell",
            "authorized-keys": "dumpsys adb",
            "listeners": "ss -ltn",
            "wifi": "cmd wifi status",
        }.items():
            result = runner.raw_shell(label, command, check=False)
            (args.output / (label + ".txt")).write_text(runner.redact(result.stdout))
            report[label] = {"exit_code": result.returncode}
            if label == "shell-permissions":
                report["MANAGE_DEBUGGING_granted"] = "android.permission.MANAGE_DEBUGGING: granted=true" in result.stdout
            if label == "adbd-sha256":
                report["adbd_sha256"] = result.stdout.split()[0] if result.returncode == 0 else None
            if label == "authorized-keys":
                report["bootstrap_control_key_visible"] = bootstrap.read_text().split()[0] in result.stdout
                report["authorization_dump_structure_valid"] = "user_keys" in result.stdout and "Permission Denial" not in result.stdout
        capability = runner.binder("verify-api35-wireless-binder", 12)
        report["wireless_supported"] = "00000001" in capability
        report["rootless_authorization_dump_available"] = report["authorized-keys"]["exit_code"] == 0
        forward = int(runner.adb("forward-real-legacy-listener", "forward", "tcp:0", "tcp:5555").stdout.strip())
        with socket.create_connection(("127.0.0.1", forward), timeout=8) as connection:
            payload = b"host::features=shell_v2,cmd\x00"
            command = int.from_bytes(b"CNXN", "little")
            connection.sendall(struct.pack("<6I", command, 0x01000001, 1024 * 1024,
                                           len(payload), sum(payload), command ^ 0xFFFFFFFF) + payload)
            header = receive(connection, 24)
            command, arg0, arg1, size, checksum, magic = struct.unpack("<6I", header)
            assert size < 65536, "Unexpected response size"
            token = receive(connection, size)
            report["fresh_unauthorized_connection_response"] = {
                "command": header[:4].decode("ascii"), "arg0": arg0, "arg1": arg1,
                "payload_length": size, "payload_sha256": hashlib.sha256(token).hexdigest(),
                "header_valid": magic == command ^ 0xFFFFFFFF,
                "successful_session": header[:4] == b"CNXN"}
            assert header[:4] == b"AUTH" and arg0 == 1 and size == 20, "Real RSA AUTH token required"
            assert magic == command ^ 0xFFFFFFFF
        assert report["MANAGE_DEBUGGING_granted"], "Normal system authorization permission absent"
        assert report["bootstrap_control_key_visible"] and report["authorization_dump_structure_valid"], "Rootless authorization evidence unavailable"
        assert report["wireless_supported"], "Wireless debugging unsupported"
        report["status"] = "passed"
        report["authentication_enabled_target"] = True
    except Exception as error:
        report["error"] = runner.redact(error)
        report["error_type"] = type(error).__name__
    finally:
        if forward is not None:
            try:
                runner.adb("remove-owned-forward", "forward", "--remove", f"tcp:{forward}")
            except Exception as error:
                cleanup_errors.append(runner.redact(error))
        try:
            logs = runner.adb("environment-logcat", "logcat", "-d", "-v", "threadtime", timeout=15, check=False)
            (args.output / "logcat-redacted.txt").write_text(runner.redact(logs.stdout))
        except Exception as error:
            report["logcat_error"] = runner.redact(error)
        report["cleanup_errors"] = cleanup_errors
        if cleanup_errors:
            report["status"] = "failed"
        runner.log.close()
        (args.output / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    sys.exit(main())
