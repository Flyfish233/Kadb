#!/usr/bin/env python3
"""Run M4 on one explicit, disposable, authenticated Android user emulator.

Only Android's normal Binder authorization APIs are used. Public-key dumps and
system logs are inspected in memory and redacted before persistence. The driver
never writes adbd authorization files, changes ro.* properties, or uses root.
"""
from __future__ import annotations

import argparse
import base64
import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import struct
import subprocess
import sys
import tempfile
import time

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "validation/m3-maven/ci"))
from run_pairing import Runner  # noqa: E402
from auth_observer import AuthRelay  # noqa: E402

PUBLIC_BLOB = re.compile(r"(?<![A-Za-z0-9+/])([A-Za-z0-9+/]{699}=)(?![A-Za-z0-9+/=])")
PRIVATE_PEM = re.compile(r"-----BEGIN (?:RSA |EC |ENCRYPTED )?PRIVATE KEY-----.*?-----END (?:RSA |EC |ENCRYPTED )?PRIVATE KEY-----", re.DOTALL)
EXPECTED_CHECKS = {
    "positive": ["identity_import", "initially_disconnected", "authenticated_connection", "shell_marker",
                 "attempt_bounded", "connection_closed", "closed_client_reuse_rejected", "temporary_identity_cleared"],
    "reject": ["identity_import", "initially_disconnected", "connection_attempt_rejected", "failed_connection_not_open",
               "attempt_bounded", "connection_closed", "closed_client_reuse_rejected", "temporary_identity_cleared"],
}


def digest(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def valid_key_blobs(text):
    result = set()
    for match in PUBLIC_BLOB.finditer(text):
        try:
            raw = base64.b64decode(match.group(1), validate=True)
            if len(raw) == 524 and struct.unpack_from("<I", raw)[0] == 64:
                result.add(match.group(1))
        except (ValueError, struct.error):
            pass
    return result


def key_summary(keys):
    return {"count": len(keys), "public_key_sha256": sorted(
        hashlib.sha256(base64.b64decode(blob)).hexdigest() for blob in keys)}


def safe_label(label):
    if not re.fullmatch(r"[a-z0-9-]+", label):
        raise ValueError("Unsafe evidence label")
    return label


class M4Runner(Runner):
    def __init__(self, args):
        super().__init__(args)
        self.run_id = secrets.token_hex(16)
        self.initial_keys = None
        self.owned_forwards = {}
        self.sessions = []
        self.marker_count = 0
        self.system_server_pid = None
        self.emulator_verified = False

    def redact(self, value):
        # Discover even an unexpected public key before Runner persists output.
        # The original raw string is still returned to the in-memory predicates.
        text = PRIVATE_PEM.sub("<REDACTED-PRIVATE-KEY>", str(value))
        for blob in valid_key_blobs(text):
            key_hash = hashlib.sha256(base64.b64decode(blob)).hexdigest()
            text = text.replace(blob, "<REDACTED-PUBLIC-KEY:" + key_hash + ">")
        for secret in getattr(self, "secrets", []):
            if secret:
                text = text.replace(secret, "<REDACTED>")
        return text

    def keys(self, label):
        result = self.shell(label, "dumpsys", "adb", timeout=8)
        if "user_keys" not in result.stdout or "Permission Denial" in result.stdout:
            raise RuntimeError("Rootless Android authorization dump unavailable")
        keys = valid_key_blobs(result.stdout)
        if not keys:
            raise RuntimeError("Authorization dump contains no valid ADB public keys")
        return keys

    def wait_keys(self, label, expected, timeout=10):
        started = time.monotonic()
        deadline = started + timeout
        polls = 0
        while time.monotonic() < deadline:
            polls += 1
            observed = self.keys(label)
            if observed == expected:
                return {**key_summary(observed), "expected_set_matched": True,
                        "elapsed_ms": round((time.monotonic() - started) * 1000), "polls": polls}
            time.sleep(0.2)
        raise RuntimeError("Authorization set did not match the expected identity set: " + label)

    def forward(self, port):
        if not 1 <= port <= 65535:
            raise ValueError("Invalid Android listener port")
        host_port = int(self.adb("forward-owned-port-" + str(port), "forward", "tcp:0", f"tcp:{port}").stdout.strip())
        if not 1 <= host_port <= 65535 or host_port in self.owned_forwards:
            raise RuntimeError("ADB returned an invalid or reused forward port")
        self.owned_forwards[host_port] = port
        return host_port

    def peer_state(self, label, port):
        pid_text = self.shell(label + "-pid", "pidof", "adbd", timeout=5).stdout.strip()
        if not re.fullmatch(r"\d+", pid_text):
            raise RuntimeError("A single real adbd PID is required")
        listing = self.shell(label + "-listeners", "ss", "-ltn", timeout=5).stdout
        present = any(len(fields := line.split()) >= 5 and fields[0] == "LISTEN"
                      and fields[3].rsplit(":", 1)[-1] == str(port) for line in listing.splitlines())
        return {"pid": int(pid_text), "guest_port": port, "listener_present": present,
                "ro.adb.secure": self.shell(label + "-secure", "getprop", "ro.adb.secure", timeout=5).stdout.strip()}

    def mark(self, label):
        self.marker_count += 1
        marker = f"kadb-m4-{self.run_id}-{self.marker_count}-{safe_label(label)}"
        self.shell(label + "-log-marker", "log", "-t", "KadbM4", marker, timeout=5)
        return marker

    def logs(self, label, marker):
        result = self.adb(label + "-logcat", "logcat", "-d", "-v", "threadtime", timeout=15)
        lines = result.stdout.splitlines()
        starts = [index for index, line in enumerate(lines) if marker in line and "KadbM4" in line]
        if len(starts) != 1:
            raise RuntimeError("Missing or ambiguous current-session system log marker: " + label)
        raw = "\n".join(lines[starts[0]:]) + "\n"
        (self.args.output / (safe_label(label) + "-logcat-redacted.txt")).write_text(self.redact(raw), encoding="utf-8")
        return raw

    def unpair(self, identity, label):
        before = self.keys(label + "-before")
        started = time.monotonic()
        self.binder(label + "-normal-unpair", 7, "s16", identity["fingerprint"])
        state = self.wait_keys(label + "-await-removal", before - {identity["blob"]})
        return {"identity": identity["name"], "fingerprint_md5": identity["fingerprint"],
                "normal_api": "IAdbManager.unpairDevice", "originally_authorized": identity["blob"] in before,
                "elapsed_ms": round((time.monotonic() - started) * 1000),
                "polls": state["polls"], "identity_absent": True, "authorization_state": state}

    def pending_identity(self, label, identity):
        result = self.shell(label, "dumpsys", "adb", timeout=5)
        if "user_keys" not in result.stdout or "Permission Denial" in result.stdout:
            raise RuntimeError("Pending authorization dump unavailable")
        fingerprints = re.findall(r"last_key_received\s*=\s*([0-9A-Fa-f]{2}(?::[0-9A-Fa-f]{2}){15})", result.stdout)
        return len(fingerprints) == 1 and fingerprints[0].upper() == identity["fingerprint"]

    def system_evidence(self, raw, identity, adbd_pid):
        # PID scoping excludes unrelated application TLS and background logs.
        adbd = [line for line in raw.splitlines()
                if re.search(r"\s" + str(adbd_pid) + r"\s+\d+\s+[VDIWEF]\s", line)]
        framework = [line for line in raw.splitlines()
                     if self.system_server_pid and re.search(r"\s" + str(self.system_server_pid) + r"\s+\d+\s+[VDIWEF]\s", line)]
        text = "\n".join(adbd)
        return {
            "adbd_pid": adbd_pid, "system_server_pid": self.system_server_pid,
            "tls_matched_identity": any("Matched auth_key=" in line and identity["blob"] in line for line in adbd),
            "tls_key_mismatch": "auth_key doesn't match [" in text,
            "tls_certificate_verify_failed": bool(re.search(r"CERTIFICATE_VERIFY_FAILED|certificate verify failed", text, re.I)),
            "tls_handshake_failed": bool(re.search(r"(?:TLS|SSL|tls|ssl)[^\n]*(?:handshake[^\n]*(?:fail|error)|error)|(?:certificate verify failed|CERTIFICATE_VERIFY_FAILED|certificate_unknown|bad_certificate|unknown ca)", text, re.I)),
            "auth_not_required": "auth not required" in text,
            "framework_no": "adbd_auth: received packet: NO" in text,
            "framework_deny": any("Denying adb confirmation" in line for line in framework),
            "adbd_logs": self.redact(text), "framework_auth_logs": self.redact("\n".join(
                line for line in framework if "AdbDebuggingManager" in line or "AdbService" in line)),
        }

    def auth_session(self, label, identity, forward_port, mode, approval=None, timeout_ms=8000):
        safe_label(label)
        if mode not in EXPECTED_CHECKS or approval not in (None, "allow", "deny"):
            raise ValueError("Invalid Native authentication mode or approval action")
        if approval == "allow" and mode != "positive" or approval == "deny" and mode != "reject":
            raise ValueError("Approval action does not match the expected connection result")
        if forward_port not in self.owned_forwards:
            raise RuntimeError("Native session must use this driver's owned Android forward")
        record = {"label": label, "identity": identity["name"], "identity_fingerprint_md5": identity["fingerprint"],
                  "mode": mode, "approval_requested": approval, "status": "running",
                  "checks_executed_known": False, "system": {}, "consumer": {}}
        self.sessions.append(record)
        relay = AuthRelay(forward_port, identity["blob"])
        process = None
        relay_started = False
        primary = None
        marker = None
        command = [self.args.consumer, "--mode", mode, "--port", str(relay.port),
                   "--private-key", str(identity["key"]), "--run-id", self.run_id,
                   "--socket-timeout-ms", str(timeout_ms)]
        started = time.monotonic()
        self.count += 1
        sequence = self.count
        stdout, stderr, exit_code = "", "", None
        with tempfile.TemporaryFile() as output, tempfile.TemporaryFile() as errors:
            try:
                record["peer_before"] = self.peer_state(label + "-before", self.owned_forwards[forward_port])
                if not record["peer_before"]["listener_present"] or record["peer_before"]["ro.adb.secure"] != "1":
                    raise RuntimeError("Authenticated real adbd listener unavailable before session")
                marker = self.mark(label)
                with relay:
                    relay_started = True
                    process = subprocess.Popen(command, stdout=output, stderr=errors)
                    record["native_pid"] = process.pid
                    if approval:
                        deadline = time.monotonic() + min(15, timeout_ms / 1000 - 1)
                        while time.monotonic() < deadline and process.poll() is None:
                            wire = relay.snapshot()
                            submissions = [event for events in wire.get("auth_events", {}).values() for event in events
                                           if event.get("direction") == "host_to_adbd" and event.get("auth_type") == 3
                                           and event.get("public_key_matches_expected_identity")]
                            if len(submissions) == 1 and self.pending_identity(label + "-pending-key", identity):
                                record["pending_confirmation"] = {"current_connection_AUTH3_matches_identity": True,
                                                                  "last_key_received_matches_identity": True,
                                                                  "fingerprint_md5": identity["fingerprint"], "action": approval}
                                if approval == "allow":
                                    self.binder(label + "-allow-normal-confirmation", 1, "i32", 1, "s16", identity["public"])
                                else:
                                    self.binder(label + "-deny-normal-confirmation", 2)
                                record["pending_confirmation"]["binder_action_completed"] = True
                                break
                            time.sleep(0.1)
                        if not record.get("pending_confirmation", {}).get("binder_action_completed"):
                            raise RuntimeError("Expected current identity did not reach Android's pending confirmation")
                    try:
                        process.wait(timeout=timeout_ms / 1000 * 2 + 10)
                    except subprocess.TimeoutExpired as failure:
                        record["native_process_deadline_exceeded"] = True
                        raise RuntimeError("Native consumer exceeded the bounded process deadline") from failure
            except Exception as failure:
                primary = failure
            finally:
                if not relay_started:
                    relay.server.server_close()
                if process is not None:
                    if process.poll() is None:
                        process.terminate()
                        try:
                            process.wait(timeout=3)
                        except subprocess.TimeoutExpired:
                            process.kill()
                            process.wait(timeout=3)
                    exit_code = process.returncode
                output.seek(0)
                errors.seek(0)
                stdout = output.read().decode("utf-8", "replace")
                stderr = errors.read().decode("utf-8", "replace")
                record["exit_code"] = exit_code
                record["wire"] = relay.snapshot()
                record["elapsed_ms"] = round((time.monotonic() - started) * 1000)
                self.log.write(json.dumps({"sequence": sequence, "label": "native-" + label,
                                           "async_subprocess": True, "command": self.sanitized(command),
                                           "exit_code": exit_code, "elapsed_ms": record["elapsed_ms"],
                                           "stdout": self.redact(stdout), "stderr": self.redact(stderr)}) + "\n")
                self.log.flush()
                (self.args.output / (label + "-native-stdout.txt")).write_text(self.redact(stdout))
                (self.args.output / (label + "-native-stderr.txt")).write_text(self.redact(stderr))
                results = [line.removeprefix("KADB_AUTH_JSON ") for line in stdout.splitlines()
                           if line.startswith("KADB_AUTH_JSON ")]
                record["native_report_count"] = len(results)
                try:
                    if len(results) != 1:
                        raise RuntimeError("Missing or ambiguous Native auth result")
                    parsed = json.loads(results[0])
                    record["consumer"] = parsed
                    record["checks_executed_known"] = True
                    if exit_code != 0 or parsed.get("status") != "passed" or parsed.get("mode") != mode:
                        raise RuntimeError("Native authentication consumer reported failure")
                    if parsed.get("checks") != EXPECTED_CHECKS[mode] or parsed.get("checks_executed") != 8:
                        raise RuntimeError("Native authentication consumer omitted required lifecycle checks")
                    record["native_lifecycle_checks"] = "PASS"
                except Exception as failure:
                    if primary is None:
                        primary = failure
                try:
                    record["peer_after"] = self.peer_state(label + "-after", self.owned_forwards[forward_port])
                    if marker is not None:
                        raw = self.logs(label, marker)
                        record["system"] = self.system_evidence(raw, identity, record["peer_before"]["pid"])
                except Exception as failure:
                    record["system_evidence_error"] = self.redact(failure)
                    if primary is None:
                        primary = failure
                if primary is not None:
                    record["status"] = "failed"
                    record["error_type"] = type(primary).__name__
                    record["error"] = self.redact(primary)
                else:
                    record["status"] = "executed"
                (self.args.output / (label + "-session.json")).write_text(json.dumps(self.sanitized(record), indent=2) + "\n")
        if primary is not None:
            raise primary
        return record


def identity(runner, name, key):
    public = key.with_name(key.name + ".pub").read_text().strip()
    blobs = valid_key_blobs(public)
    if len(blobs) != 1 or public.split()[0] not in blobs:
        raise RuntimeError("Malformed temporary ADB public identity")
    blob = public.split()[0]
    pem = key.read_text()
    if "PRIVATE KEY-----" not in pem:
        raise RuntimeError("Missing temporary private identity")
    runner.secrets.extend([blob, pem])
    return {"name": name, "key": key, "public": public, "blob": blob,
            "fingerprint": ":".join(re.findall("..", hashlib.md5(base64.b64decode(blob)).hexdigest().upper()))}


def execute(runner, report):
    runner.ready()
    props = {}
    for prop in ("ro.kernel.qemu", "ro.adb.secure", "ro.build.version.sdk", "ro.build.type", "ro.secure",
                 "ro.debuggable", "ro.build.fingerprint", "ro.product.cpu.abi"):
        props[prop] = runner.shell("environment-" + prop.replace(".", "-"), "getprop", prop).stdout.strip()
    report["properties"] = props
    if not (props["ro.kernel.qemu"] == "1" and props["ro.adb.secure"] == "1"
            and props["ro.build.version.sdk"] == "35" and props["ro.build.type"] == "user"):
        raise RuntimeError("M4 requires the explicit disposable, authenticated API 35 user emulator")
    runner.emulator_verified = True
    report["shell_uid"] = runner.shell("environment-shell-uid", "id", "-u").stdout.strip()
    if report["shell_uid"] != "2000":
        raise RuntimeError("M4 requires rootless Android shell")
    pid = runner.shell("environment-system-server-pid", "pidof", "system_server").stdout.strip()
    if not re.fullmatch(r"\d+", pid):
        raise RuntimeError("Cannot identify actual Android system_server")
    runner.system_server_pid = int(pid)
    report["system_server_pid"] = int(pid)
    control_path = Path(os.environ["ANDROID_USER_HOME"]) / "adbkey"
    identities = {"control": identity(runner, "control", control_path)}
    runner.initial_keys = runner.keys("environment-initial-authorizations")
    if identities["control"]["blob"] not in runner.initial_keys:
        raise RuntimeError("Dedicated emulator control identity does not match Android authorization")
    report["original_authorizations"] = key_summary(runner.initial_keys)
    report["control_identity"] = {"fingerprint_md5": identities["control"]["fingerprint"],
                                  "authorized_in_baseline": True, "independent_of_test_identities": True}
    cleanup_errors = report["cleanup_errors"]
    with tempfile.TemporaryDirectory(prefix="kadb-m4-identities-") as directory:
        report["temporary_identity_directory_created"] = True
        try:
            for name in ("rsa_a", "rsa_b", "tls_a", "tls_b"):
                key = Path(directory) / name
                runner.run("generate-" + name.replace("_", "-"), [runner.args.adb, "keygen", key])
                key.chmod(0o600)
                identities[name] = identity(runner, name, key)
            blobs = {item["blob"] for item in identities.values()}
            if len(blobs) != 5 or any(identities[name]["blob"] in runner.initial_keys for name in identities if name != "control"):
                raise RuntimeError("M4 identities are not independent and initially unauthorized")
            report["temporary_identity_fingerprints_md5"] = {name: item["fingerprint"] for name, item in identities.items() if name != "control"}
            from rsa_stage import run_rsa
            from tls_stage import run_tls
            for label, operation in (("M4-A", run_rsa), ("M4-B", run_tls)):
                try:
                    operation(runner, identities, report)
                except Exception as failure:
                    report[label]["execution_error"] = runner.redact(failure)
                    report[label]["error_type"] = type(failure).__name__
                    report[label]["status"] = "failed"
                finally:
                    report["sessions"] = runner.sessions
                    (runner.args.output / "report-in-progress.json").write_text(json.dumps(runner.sanitized(report), indent=2) + "\n")
        finally:
            for name, item in identities.items():
                if name == "control":
                    continue
                try:
                    if item["blob"] in runner.keys("cleanup-" + name.replace("_", "-") + "-keys"):
                        runner.unpair(item, "cleanup-" + name.replace("_", "-") + "-unpair")
                    if runner.pending_identity("cleanup-" + name.replace("_", "-") + "-pending", item):
                        runner.binder("cleanup-" + name.replace("_", "-") + "-dismiss-own-prompt", 2)
                except Exception as failure:
                    cleanup_errors.append({"step": "remove-owned-identity-" + name, "error": runner.redact(failure)})
            try:
                report["final_authorizations"] = runner.wait_keys("cleanup-original-key-set", runner.initial_keys)
                secure = runner.shell("cleanup-auth-remains-enabled", "getprop", "ro.adb.secure").stdout.strip()
                uid = runner.shell("cleanup-shell-remains-unprivileged", "id", "-u").stdout.strip()
                if secure != "1" or uid != "2000":
                    raise RuntimeError("Original enforced-authentication or rootless shell state changed")
                report["authentication_and_uid_restored"] = True
            except Exception as failure:
                cleanup_errors.append({"step": "verify-original-auth-state", "error": runner.redact(failure)})
    report["temporary_private_keys_deleted"] = not Path(directory).exists()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--adb", required=True)
    parser.add_argument("--serial", required=True)
    parser.add_argument("--adb-server-port", type=int, default=5038)
    parser.add_argument("--consumer", required=True)
    parser.add_argument("--pairing-consumer", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if not re.fullmatch(r"emulator-\d+", args.serial):
        parser.error("An explicit emulator serial is required; physical devices are refused")
    if not 1 <= args.adb_server_port <= 65535:
        parser.error("Invalid dedicated ADB server port")
    args.output.mkdir(parents=True, exist_ok=False)
    for name in ("adb", "consumer", "pairing_consumer"):
        path = Path(getattr(args, name)).resolve(strict=True)
        if not os.access(path, os.X_OK):
            parser.error("All consumers and adb must be executable")
        setattr(args, name, str(path))
    runner = M4Runner(args)
    report = {"schema": 1, "milestone": "M4", "status": "running", "verdict": "NOT VERIFIED",
              "started_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(), "run_id": runner.run_id,
              "physical_device": False, "root_used": False, "authorization_files_written_by_driver": False,
              "M4-A": {"verdict": "NOT VERIFIED"}, "M4-B": {"verdict": "NOT VERIFIED"},
              "M4-C": {"verdict": "NOT VERIFIED", "reason": "No physical device authorized or selected"},
              "cleanup_errors": [], "sessions": runner.sessions,
              "fixed_candidate": {"version": "0.1.0-dev.59105290820b", "source_revision": "59105290820bcbfd4e0336a2e7713006a461527f"},
              "R3_K01": "Inherited bidirectional GCM nonce risk remains unchanged; no protocol alteration",
              "production_cryptography_modified": False}
    try:
        report["code_sha"] = runner.run("source-commit", ["git", "-C", REPO, "rev-parse", "HEAD"]).stdout.strip()
        report["tracked_worktree_changes"] = runner.run("source-cleanliness", ["git", "-C", REPO, "status", "--porcelain", "--untracked-files=no"]).stdout
        if report["tracked_worktree_changes"]:
            raise RuntimeError("Actual execution requires committed, clean tracked source")
        report["artifacts"] = {name: {"path": getattr(args, name), "sha256": digest(getattr(args, name)),
                                      "bytes": Path(getattr(args, name)).stat().st_size}
                               for name in ("adb", "consumer", "pairing_consumer")}
        report["source_lock_sha256"] = digest(REPO / "validation/source-bundle/dependencies.lock.json")
        report["adb_version"] = runner.run("host-adb-version", [args.adb, "version"]).stdout
        execute(runner, report)
    except Exception as failure:
        report["error_type"] = type(failure).__name__
        report["error"] = runner.redact(failure)
    finally:
        for port in list(runner.owned_forwards):
            try:
                runner.adb("cleanup-owned-forward-" + str(port), "forward", "--remove", "tcp:" + str(port), timeout=8)
                del runner.owned_forwards[port]
            except Exception as failure:
                report["cleanup_errors"].append({"step": "remove-forward-" + str(port), "error": runner.redact(failure)})
        report["owned_forwards_remaining"] = len(runner.owned_forwards)
        if runner.emulator_verified:
            try:
                final = runner.adb("final-redacted-logcat", "logcat", "-d", "-v", "threadtime", timeout=15, check=False)
                (args.output / "final-logcat-redacted.txt").write_text(runner.redact(final.stdout))
                report["final_logcat_exit_code"] = final.returncode
            except Exception as failure:
                report["final_logcat_error"] = runner.redact(failure)
        report["sessions"] = runner.sessions
        report["commands_executed"] = runner.count
        report["checks_executed"] = sum(session.get("consumer", {}).get("checks_executed", 0) for session in runner.sessions)
        report["checks_executed"] += report["M4-B"].get("pairing", {}).get("consumer", {}).get("checks_executed", 0)
        unexpected_success = any(s["mode"] == "reject" and s.get("consumer", {}).get("adb_handshake_completed") for s in runner.sessions)
        stage_verdicts = [report["M4-A"].get("verdict"), report["M4-B"].get("verdict")]
        if unexpected_success or "FAIL" in stage_verdicts:
            report["verdict"] = "FAIL"
        elif stage_verdicts == ["PASS", "PASS"]:
            report["verdict"] = "PASS" if not report["cleanup_errors"] and not report.get("error") else "CONDITIONAL PASS"
        elif "PASS" in stage_verdicts or "CONDITIONAL PASS" in stage_verdicts:
            report["verdict"] = "CONDITIONAL PASS"
        report["cleanup_verdict"] = "PASS" if (not report["cleanup_errors"] and report.get("authentication_and_uid_restored")
                                                  and report.get("temporary_private_keys_deleted") and not runner.owned_forwards) else "NOT VERIFIED"
        if report["verdict"] == "PASS" and report["cleanup_verdict"] != "PASS":
            report["verdict"] = "CONDITIONAL PASS"
        report["status"] = "passed" if report["verdict"] == "PASS" else "incomplete" if report["verdict"] != "FAIL" else "failed"
        report["finished_utc"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        runner.log.close()
        (args.output / "report.json").write_text(json.dumps(runner.sanitized(report), indent=2) + "\n")
    print(json.dumps({key: report[key] for key in ("status", "verdict", "checks_executed", "cleanup_verdict")}))
    return 0 if report["verdict"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
