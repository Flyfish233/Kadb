#!/usr/bin/env python3
"""Run a linked Native consumer against a disposable, already booted Android emulator.

Never selects a physical device, disables authentication, publishes an APK, or treats
an expected authentication failure as a healthy product execution.
"""

from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import shlex
import subprocess
import sys
import tempfile
import time

from adb_observer import AdbRelay

PACKAGE = "com.flyfishxu.kadb.validation.fixture"
EXPECTED_CHECKS = [
    "identity_import", "feature_negotiation", "shell_v2", "sync_transfer", "sync_stat",
    "sync_shell_metadata", "sync_directory", "sync_symlink", "sync_empty_file", "install",
    "uninstall", "reconnect_1", "reconnect_2", "cleanup", "close_terminal",
]


def sha256(path: Path) -> str:
    with path.open("rb") as source:
        return hashlib.file_digest(source, "sha256").hexdigest()


def parse_consumer(stdout: str) -> dict:
    reports = [line.removeprefix("KADB_VALIDATION_JSON ") for line in stdout.splitlines()
               if line.startswith("KADB_VALIDATION_JSON ")]
    if len(reports) != 1:
        raise RuntimeError(f"Expected exactly one consumer report, observed {len(reports)}")
    return json.loads(reports[0])


class Runner:
    def __init__(self, arguments, output: Path):
        self.arguments = arguments
        self.log = (output / "commands.jsonl").open("w", encoding="utf-8")
        self.output = output
        self.counter = 0

    def run(self, label, command, *, timeout=30, check=True):
        self.counter += 1
        started = time.monotonic()
        stdout, stderr, code = "", "", None
        try:
            result = subprocess.run([str(item) for item in command], capture_output=True,
                                    text=True, errors="replace", timeout=timeout)
            stdout, stderr, code = result.stdout, result.stderr, result.returncode
        except subprocess.TimeoutExpired as error:
            stdout = (error.stdout or b"").decode("utf-8", "replace")
            stderr = (error.stderr or b"").decode("utf-8", "replace")
            raise RuntimeError(f"{label} exceeded {timeout}s") from error
        finally:
            entry = {"sequence": self.counter, "label": label, "command": [str(item) for item in command],
                     "exit_code": code, "elapsed_ms": int((time.monotonic() - started) * 1000),
                     "stdout": stdout, "stderr": stderr}
            self.log.write(json.dumps(entry, ensure_ascii=False) + "\n")
            self.log.flush()
        if check and code != 0:
            raise RuntimeError(f"{label} failed with exit {code}: {stderr.strip() or stdout.strip()}")
        return result

    def adb(self, label, *arguments, timeout=30, check=True):
        return self.run(label, [self.arguments.adb, "-P", str(self.arguments.adb_server_port),
                               "-s", self.arguments.serial, *arguments], timeout=timeout, check=check)

    def shell(self, label, command, *, check=True):
        return self.adb(label, "shell", command, check=check)

    def wait_ready(self):
        deadline = time.monotonic() + 120
        while time.monotonic() < deadline:
            state = self.adb("wait-for-emulator", "get-state", timeout=10, check=False)
            if state.returncode == 0 and state.stdout.strip() == "device":
                boot = self.shell("wait-for-boot", "getprop sys.boot_completed", check=False)
                if boot.returncode == 0 and boot.stdout.strip() == "1":
                    return
            time.sleep(1)
        raise RuntimeError("The selected emulator did not become ready within 120s")

    def forward(self) -> int:
        result = self.adb("create-forward", "forward", "tcp:0", f"tcp:{self.arguments.guest_port}")
        port = int(result.stdout.strip())
        if not 1 <= port <= 65535:
            raise RuntimeError("adb forward did not return a valid host port")
        return port

    def consumer(self, mode: str, key: Path, relay: AdbRelay, run_id: str):
        return self.run(f"native-{mode}", [self.arguments.consumer, "--mode", mode,
                         "--host", "127.0.0.1", "--port", str(relay.port), "--private-key", key,
                         "--apk", self.arguments.apk, "--run-id", run_id],
                        timeout=25 if mode == "probe" else 300, check=False)


def execute(arguments, runner: Runner, report: dict) -> None:
    run_id = secrets.token_hex(16)
    remote_root = f"/data/local/tmp/kadb-native-validation-{run_id}"
    remote_public = f"/data/local/tmp/kadb-native-public-{run_id}"
    remote_backup = f"/data/local/tmp/kadb-native-keys-{run_id}"
    report["run_id"] = run_id
    for name in ("consumer", "apk", "adb", "aapt2"):
        path = Path(getattr(arguments, name)).resolve(strict=True)
        setattr(arguments, name, str(path))
        report.setdefault("artifacts", {})[name] = {"path": str(path), "bytes": path.stat().st_size,
                                                    "sha256": sha256(path)}
    if not os.access(arguments.consumer, os.X_OK):
        raise RuntimeError("Native consumer is not an executable file")
    with Path(arguments.consumer).open("rb") as native_file:
        magic = native_file.read(4)
    if magic == b"\x7fELF":
        report["native_binary_format"] = "ELF"
    elif magic in (b"\xcf\xfa\xed\xfe", b"\xfe\xed\xfa\xcf", b"\xca\xfe\xba\xbe", b"\xbe\xba\xfe\xca"):
        report["native_binary_format"] = "Mach-O"
    else:
        raise RuntimeError("Consumer is not a linked ELF or Mach-O executable")
    badging = runner.run("inspect-apk", [arguments.aapt2, "dump", "badging", arguments.apk]).stdout
    if not re.search(rf"^package: name='{re.escape(PACKAGE)}' ", badging, re.MULTILINE):
        raise RuntimeError("APK is not the exact disposable Kadb fixture package")
    if re.search(r"^uses-permission(?:-sdk-\d+)?:", badging, re.MULTILINE):
        raise RuntimeError("Fixture APK unexpectedly requests permissions")
    report["adb_version"] = runner.run("adb-version", [arguments.adb, "version"]).stdout.strip()
    if arguments.emulator:
        report["emulator_version"] = runner.run("emulator-version", [arguments.emulator, "-no-window", "-no-audio", "-version"]).stdout.strip()
    repo = Path(__file__).resolve().parents[2]
    report["commit"] = runner.run("git-commit", ["git", "-C", repo, "rev-parse", "HEAD"]).stdout.strip()
    report["tracked_worktree_changes"] = runner.run(
        "git-status", ["git", "-C", repo, "status", "--porcelain", "--untracked-files=no"]).stdout

    runner.wait_ready()
    qemu = runner.shell("verify-emulator", "getprop ro.kernel.qemu").stdout.strip()
    if qemu != "1":
        raise RuntimeError("Selected serial is not an Android emulator (ro.kernel.qemu != 1)")
    report["device_kind"] = "android_emulator"
    report["serial"] = arguments.serial
    report["properties"] = {}
    for prop in ("ro.build.fingerprint", "ro.build.version.sdk", "ro.product.cpu.abi",
                 "ro.adb.secure", "ro.secure", "ro.debuggable", "service.adb.tcp.port"):
        report["properties"][prop] = runner.shell("get-" + prop, "getprop " + prop).stdout.strip()
    previous_port = report["properties"]["service.adb.tcp.port"]
    if previous_port and not re.fullmatch(r"-?\d{1,5}", previous_port):
        raise RuntimeError("Unexpected original adbd TCP property; refusing to change it")
    original_uid = runner.shell("initial-uid", "id -u").stdout.strip()
    existing = runner.shell("fixture-must-be-absent", f"pm path {PACKAGE}", check=False)
    if existing.stdout.strip() or existing.returncode not in (0, 1):
        raise RuntimeError("Fixture package already exists or package manager is unavailable")

    forward = None
    keys_changed = False
    original_keys_existed = False
    rooted = False
    tcp_changed = False
    attempted_consumer = False
    primary_error = None
    cleanup_errors = []
    with tempfile.TemporaryDirectory(prefix="kadb-native-emulator-") as temporary:
        work = Path(temporary)
        key = work / "kadb-test-key"
        key_backup = work / "original-public-keys"
        try:
            runner.run("generate-ephemeral-rsa-key", [arguments.adb, "keygen", key])
            key.chmod(0o600)
            runner.adb("root-disposable-emulator", "root")
            rooted = True
            runner.wait_ready()
            if runner.shell("verify-root", "id -u").stdout.strip() != "0":
                raise RuntimeError("This test requires a rootable, disposable emulator image")

            tcp_changed = True
            runner.adb("enable-test-tcp-port", "tcpip", str(arguments.guest_port))
            runner.wait_ready()
            forward = runner.forward()
            auth_denial_verified = False
            if report["properties"]["ro.adb.secure"] == "1":
                with AdbRelay(forward) as relay:
                    result = runner.consumer("probe", key, relay, run_id)
                probe_report = parse_consumer(result.stdout)
                observation = relay.snapshot()
                counts = observation["counts"]
                auth_denial_verified = (result.returncode != 0 and probe_report.get("status") == "failed"
                                        and counts.get("adbd_to_host:AUTH:1", 0) > 0
                                        and counts.get("host_to_adbd:AUTH:2", 0) > 0
                                        and counts.get("adbd_to_host:CNXN", 0) == 0
                                        and not observation["header_errors"])
                report["unauthorized_probe"] = {
                    "kind": "expected_rejection_probe", "product_health_test": False,
                    "consumer_exit_code": result.returncode, "auth_denial_verified": auth_denial_verified,
                    "consumer": probe_report, "wire": observation,
                }
            else:
                report["unauthorized_probe"] = {"kind": "not_executed", "product_health_test": False,
                                                "reason": "image ro.adb.secure is not 1"}
            runner.adb("remove-probe-forward", "forward", "--remove", f"tcp:{forward}")
            forward = None

            original_keys_existed = runner.shell(
                "original-public-keys-exist", "test -e /data/misc/adb/adb_keys", check=False).returncode == 0
            if original_keys_existed:
                runner.adb("backup-public-keys", "pull", "/data/misc/adb/adb_keys", key_backup)
            runner.adb("stage-test-public-key", "push", str(key) + ".pub", remote_public)
            # Only the public key reaches the emulator. Preserve the existing authorization list.
            keys_changed = True
            runner.shell("authorize-test-public-key",
                         "mkdir -p /data/misc/adb && printf '\\n' >> /data/misc/adb/adb_keys && "
                         f"cat '{remote_public}' >> /data/misc/adb/adb_keys && "
                         "chown system:shell /data/misc/adb/adb_keys && chmod 640 /data/misc/adb/adb_keys && "
                         "restorecon /data/misc/adb/adb_keys")
            runner.adb("reload-test-authorized-key", "tcpip", str(arguments.guest_port))
            runner.wait_ready()
            forward = runner.forward()

            attempted_consumer = True
            with AdbRelay(forward) as relay:
                result = runner.consumer("e2e", key, relay, run_id)
            consumer_report = parse_consumer(result.stdout)
            observation = relay.snapshot()
            report["consumer"] = consumer_report
            report["wire"] = observation
            report["consumer_exit_code"] = result.returncode
            if result.returncode != 0 or consumer_report.get("status") != "passed":
                raise RuntimeError("Native end-to-end consumer failed; inspect commands.jsonl and consumer report")
            if consumer_report.get("checks") != EXPECTED_CHECKS or consumer_report.get("checks_executed") != len(EXPECTED_CHECKS):
                raise RuntimeError("Native consumer did not execute the entire expected check list")
            if observation["connections"] < 3 or observation["header_errors"]:
                raise RuntimeError("Wire evidence does not establish three valid connections/reconnections")
            counts = observation["counts"]
            auth_positive = (counts.get("adbd_to_host:AUTH:1", 0) >= 3
                             and counts.get("host_to_adbd:AUTH:2", 0) >= 3
                             and counts.get("adbd_to_host:CNXN", 0) >= 3)
            report["scope"] = {
                "native_executable_linked_and_executed": True,
                "real_android_adbd_interoperability": True,
                "physical_device": False,
                "transport": "loopback relay -> adb forward -> emulator TCP adbd",
                "rsa_auth_positive_interop_observed": auth_positive,
                "unauthorized_key_rejection_observed": auth_denial_verified,
                "tls_upgrade_observed": counts.get("host_to_adbd:STLS", 0) > 0 or counts.get("adbd_to_host:STLS", 0) > 0,
                "wireless_pairing": False,
                "security_or_performance_acceptance": False,
            }
            if arguments.require_auth and not (auth_positive and auth_denial_verified):
                raise RuntimeError("--require-auth requested, but positive RSA AUTH and negative rejection were not both observed")
            absent = runner.shell("independent-uninstall-check", f"pm path {PACKAGE}", check=False)
            if absent.returncode != 1 or absent.stdout.strip() or absent.stderr.strip():
                raise RuntimeError("Official adb did not confirm fixture removal")
            missing = runner.shell("independent-remote-cleanup-check", f"test ! -e '{remote_root}'", check=False)
            if missing.returncode != 0:
                raise RuntimeError("Official adb did not confirm remote test-directory removal")
        except Exception as error:
            primary_error = error
        finally:
            def cleanup(label, function):
                try:
                    function()
                except Exception as error:
                    cleanup_errors.append({"step": label, "error": str(error)})

            if forward is not None:
                cleanup("remove-forward", lambda: runner.adb("cleanup-forward", "forward", "--remove", f"tcp:{forward}"))
            if attempted_consumer:
                cleanup("remove-owned-files", lambda: runner.shell("cleanup-owned-files", f"rm -rf '{remote_root}'"))
                # The package was verified absent before this run. Check first; an already absent package is normal.
                def remove_fixture():
                    result = runner.shell("cleanup-fixture-state", f"pm path {PACKAGE}", check=False)
                    if result.returncode == 0 and result.stdout.startswith("package:"):
                        runner.adb("cleanup-fixture-package", "uninstall", PACKAGE)
                    elif result.returncode != 1 or result.stdout.strip() or result.stderr.strip():
                        raise RuntimeError("Cannot determine fixture package state during cleanup")
                cleanup("remove-fixture", remove_fixture)
            if keys_changed:
                def restore_keys():
                    if original_keys_existed:
                        runner.adb("stage-original-public-keys", "push", key_backup, remote_backup)
                        runner.shell("restore-original-public-keys", f"cat '{remote_backup}' > /data/misc/adb/adb_keys && "
                                     "chown system:shell /data/misc/adb/adb_keys && chmod 640 /data/misc/adb/adb_keys && "
                                     "restorecon /data/misc/adb/adb_keys")
                    else:
                        runner.shell("remove-test-public-keys-file", "rm -f /data/misc/adb/adb_keys")
                cleanup("restore-public-keys", restore_keys)
            if rooted:
                cleanup("remove-staging-files", lambda: runner.shell(
                    "cleanup-staging-files", f"rm -f '{remote_public}' '{remote_backup}'"))
            if tcp_changed:
                cleanup("restore-adbd-tcp-property", lambda: runner.shell(
                    "restore-adbd-tcp-property", "setprop service.adb.tcp.port " + shlex.quote(previous_port)))
                cleanup("wait-after-tcp-restore", runner.wait_ready)
            if rooted and original_uid != "0":
                cleanup("restore-adbd-uid", lambda: runner.adb("restore-adbd-uid", "unroot"))
                cleanup("wait-after-unroot", runner.wait_ready)
    report["cleanup_errors"] = cleanup_errors
    report["ephemeral_private_key_deleted"] = True
    if primary_error is not None:
        raise primary_error
    if cleanup_errors:
        raise RuntimeError("Validation checks passed but emulator cleanup failed")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--serial", required=True)
    parser.add_argument("--consumer", required=True)
    parser.add_argument("--apk", required=True)
    parser.add_argument("--adb", required=True)
    parser.add_argument("--aapt2", required=True)
    parser.add_argument("--emulator", help="Optional SDK emulator executable, to preserve its version output")
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--adb-server-port", type=int, default=5038)
    parser.add_argument("--guest-port", type=int, default=5556)
    parser.add_argument("--require-auth", action="store_true")
    arguments = parser.parse_args()
    if not re.fullmatch(r"emulator-[0-9]+", arguments.serial):
        parser.error("--serial must explicitly name an emulator-N transport")
    if not 1 <= arguments.adb_server_port <= 65535 or not 1 <= arguments.guest_port <= 65535:
        parser.error("Ports must be in 1..65535")
    arguments.output.mkdir(parents=True, exist_ok=False)
    report = {"schema": 1, "status": "failed", "started_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
              "require_auth": arguments.require_auth, "checks_expected": len(EXPECTED_CHECKS)}
    runner = Runner(arguments, arguments.output)
    try:
        execute(arguments, runner, report)
        report["status"] = "passed"
        return_code = 0
    except Exception as error:
        report["error_type"] = type(error).__name__
        report["error"] = str(error)
        return_code = 1
    finally:
        report["commands_executed"] = runner.counter
        runner.log.close()
        (arguments.output / "report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    summary = {"status": report["status"], "report": str(arguments.output / "report.json"),
               "checks_executed": report.get("consumer", {}).get("checks_executed", 0),
               "commands_executed": report["commands_executed"]}
    for field in ("error_type", "error"):
        if field in report:
            summary[field] = report[field]
    print(json.dumps(summary))
    return return_code


if __name__ == "__main__":
    sys.exit(main())
