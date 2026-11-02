#!/usr/bin/env python3
"""Bounded Native Kadb.pair -> the selected disposable emulator's AOSP pairing service.

The Binder request is the same system service used by Settings QR pairing. No
test pairing server, adbd patch, auth override, or system-partition write exists
in this driver. Codes/private keys live only in a TemporaryDirectory and logs
are redacted before persistence. An ADB forwarding tunnel is only transport.
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
import select
import shlex
import socket
import socketserver
import struct
import subprocess
import sys
import tempfile
import threading
import time

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "validation/native-adbd"))
from adb_observer import AdbRelay  # noqa: E402

AOSP = "https://android.googlesource.com/platform/frameworks/base/+/refs/heads/android15-release/"
ABI_SOURCE = AOSP + "core/java/android/debug/IAdbManager.aidl"
JNI_SOURCE = AOSP + "services/core/jni/com_android_server_adb_AdbDebuggingManager.cpp"
EXPECTED = {
    "reject": ["identity_import", "public_pair_rejected", "temporary_identity_cleared"],
    "pair": ["identity_import", "real_aosp_public_pair_returned", "temporary_identity_cleared"],
    "connect": ["identity_import", "paired_connection_shell", "connection_closed", "temporary_identity_cleared"],
}


def digest(path):
    with Path(path).open("rb") as source:
        return hashlib.file_digest(source, "sha256").hexdigest()


class Runner:
    def __init__(self, args):
        self.args = args
        self.log = (args.output / "commands.jsonl").open("w", encoding="utf-8")
        self.secrets = []
        self.count = 0

    def redact(self, value):
        text = str(value)
        for secret in self.secrets:
            if secret:
                text = text.replace(secret, "<REDACTED>")
        return text

    def sanitized(self, value):
        # Redaction cannot turn a coincidentally matching numeric measurement
        # into invalid JSON. Only text fields can contain pairing secrets.
        if isinstance(value, str):
            return self.redact(value)
        if isinstance(value, list):
            return [self.sanitized(item) for item in value]
        if isinstance(value, dict):
            return {key: self.sanitized(item) for key, item in value.items()}
        return value

    def run(self, label, command, timeout=30, check=True):
        self.count += 1
        started = time.monotonic()
        code, stdout, stderr = None, "", ""
        try:
            result = subprocess.run(list(map(str, command)), text=True, errors="replace",
                                    capture_output=True, timeout=timeout)
            code, stdout, stderr = result.returncode, result.stdout, result.stderr
        except subprocess.TimeoutExpired as error:
            stdout = (error.stdout or b"").decode("utf-8", "replace")
            stderr = (error.stderr or b"").decode("utf-8", "replace")
            raise RuntimeError(f"{label} timed out after {timeout}s") from error
        finally:
            entry = {"sequence": self.count, "label": label,
                     "command": [self.redact(item) for item in command], "exit_code": code,
                     "elapsed_ms": round((time.monotonic() - started) * 1000),
                     "stdout": self.redact(stdout), "stderr": self.redact(stderr)}
            self.log.write(json.dumps(entry, ensure_ascii=False) + "\n")
            self.log.flush()
        if check and code != 0:
            raise RuntimeError(f"{label} failed (exit {code}): {self.redact(stderr.strip())}")
        return result

    def adb(self, label, *arguments, **kwargs):
        return self.run(label, [self.args.adb, "-P", self.args.adb_server_port,
                               "-s", self.args.serial, *arguments], **kwargs)

    def shell(self, label, *arguments, **kwargs):
        return self.adb(label, "shell", shlex.join(list(map(str, arguments))), **kwargs)

    def raw_shell(self, label, command, **kwargs):
        return self.adb(label, "shell", command, **kwargs)

    def ready(self):
        deadline = time.monotonic() + 45
        while time.monotonic() < deadline:
            result = self.adb("wait-device", "get-state", timeout=5, check=False)
            if result.returncode == 0 and result.stdout.strip() == "device":
                return
            time.sleep(1)
        raise RuntimeError("Selected emulator did not return to device state")

    def binder(self, label, number, *arguments):
        result = self.shell(label, "service", "call", "adb", number, *arguments)
        if "Exception" in result.stdout or "does not exist" in result.stdout:
            raise RuntimeError(f"{label}: Binder rejected the operation")
        return result.stdout


class TlsMetadata:
    """Parse only public ServerHello negotiation metadata; retain no TLS payloads."""
    def __init__(self):
        self.buffer = bytearray()
        self.handshake = bytearray()
        self.records = {}
        self.negotiated = []
        self.errors = []

    def feed(self, data):
        self.buffer.extend(data)
        while len(self.buffer) >= 5:
            kind, version, length = struct.unpack("!BHH", self.buffer[:5])
            if kind not in (20, 21, 22, 23) or length > 18432:
                self.errors.append("invalid_tls_record_header")
                self.buffer.clear()
                return
            if len(self.buffer) < length + 5:
                return
            payload = bytes(self.buffer[5:5 + length])
            del self.buffer[:5 + length]
            self.records[str(kind)] = self.records.get(str(kind), 0) + 1
            if kind != 22:
                continue
            self.handshake.extend(payload)
            while len(self.handshake) >= 4:
                size = int.from_bytes(self.handshake[1:4], "big")
                if size > 65536:
                    self.errors.append("oversized_public_handshake")
                    self.handshake.clear()
                    break
                if len(self.handshake) < size + 4:
                    break
                message = bytes(self.handshake[4:4 + size])
                message_type = self.handshake[0]
                del self.handshake[:4 + size]
                if message_type == 2:
                    try:
                        offset = 35 + message[34]
                        cipher = int.from_bytes(message[offset:offset + 2], "big")
                        extension_length = int.from_bytes(message[offset + 3:offset + 5], "big")
                        offset += 5
                        end = offset + extension_length
                        if end != len(message):
                            raise ValueError("ServerHello length")
                        selected = None
                        while offset < end:
                            ext, length = struct.unpack("!HH", message[offset:offset + 4])
                            value = message[offset + 4:offset + 4 + length]
                            if ext == 43 and length == 2:
                                selected = int.from_bytes(value, "big")
                            offset += 4 + length
                        self.negotiated.append({"selected_version": selected, "cipher_suite": cipher})
                    except (IndexError, ValueError, struct.error):
                        self.errors.append("malformed_server_hello")


class PairingRelay:
    def __init__(self, target_port):
        self.target_port = target_port
        self.metadata = TlsMetadata()
        self.connections = 0
        self.bytes = {"client_to_android": 0, "android_to_client": 0}
        self.sockets = set()
        self.lock = threading.Lock()
        owner = self

        class Server(socketserver.ThreadingTCPServer):
            daemon_threads = True
            block_on_close = False

        class Handler(socketserver.BaseRequestHandler):
            def handle(self):
                owner.handle(self.request)

        self.server = Server(("127.0.0.1", 0), Handler)
        self.port = self.server.server_address[1]
        self.thread = threading.Thread(target=self.server.serve_forever,
                                       kwargs={"poll_interval": 0.05}, daemon=True)

    def handle(self, incoming):
        outgoing = None
        with self.lock:
            self.connections += 1
            self.sockets.add(incoming)
        try:
            outgoing = socket.create_connection(("127.0.0.1", self.target_port), timeout=5)
            outgoing.settimeout(None)
            with self.lock:
                self.sockets.add(outgoing)
            peers = {incoming: outgoing, outgoing: incoming}
            readable = list(peers)
            while readable:
                ready, _, _ = select.select(readable, [], [], 1)
                for source in ready:
                    data = source.recv(65536)
                    if not data:
                        readable.remove(source)
                        try:
                            peers[source].shutdown(socket.SHUT_WR)
                        except OSError:
                            pass
                        continue
                    if source is outgoing:
                        self.metadata.feed(data)
                    peers[source].sendall(data)
                    self.bytes["client_to_android" if source is incoming else "android_to_client"] += len(data)
        except (OSError, ValueError):
            pass
        finally:
            for endpoint in (incoming, outgoing):
                if endpoint:
                    with self.lock:
                        self.sockets.discard(endpoint)
                    endpoint.close()

    def __enter__(self):
        self.thread.start()
        return self

    def __exit__(self, *_):
        self.server.shutdown()
        self.server.server_close()
        with self.lock:
            for endpoint in self.sockets:
                try:
                    endpoint.shutdown(socket.SHUT_RDWR)
                except OSError:
                    pass
        self.thread.join(timeout=3)

    def snapshot(self):
        return {"connections": self.connections, "bytes_forwarded": self.bytes,
                "server_tls_record_counts": self.metadata.records,
                "server_hello": self.metadata.negotiated, "parse_errors": self.metadata.errors}


def listener_owned(text, port, process):
    for line in text.splitlines():
        fields = line.split()
        if len(fields) >= 5 and fields[0] == "LISTEN" and fields[3].rsplit(":", 1)[-1] == str(port):
            if re.search(r'\("' + re.escape(process) + r'",pid=\d+', line):
                return True
    return False


def consumer(runner, mode, port, key, code_file, run_id, record):
    record["checks_executed_known"] = False
    try:
        result = runner.run("native-" + mode, [runner.args.consumer, "--mode", mode,
                            "--port", port, "--private-key", key, "--code-file", code_file,
                            "--run-id", run_id], timeout=30, check=False)
    except Exception as error:
        record["execution_error"] = runner.redact(error)
        record["exit_code"] = None
        raise
    record["exit_code"] = result.returncode
    lines = [line.removeprefix("KADB_REAL_PAIRING_JSON ") for line in result.stdout.splitlines()
             if line.startswith("KADB_REAL_PAIRING_JSON ")]
    record["native_report_count"] = len(lines)
    if len(lines) != 1:
        raise RuntimeError(f"{mode}: missing or ambiguous Native result")
    parsed = json.loads(lines[0])
    record["consumer"] = parsed
    record["checks_executed_known"] = True
    if result.returncode != 0 or parsed.get("status") != "passed":
        raise RuntimeError(f"{mode}: Native public API execution failed")
    if parsed.get("checks") != EXPECTED[mode] or parsed.get("checks_executed") != len(EXPECTED[mode]):
        raise RuntimeError(f"{mode}: Native result omitted required checks")
    return record


def execute(args, runner, report):
    run_id = secrets.token_hex(16)
    report["run_id"] = run_id
    report["code_commit"] = runner.run("source-commit", ["git", "-C", REPO, "rev-parse", "HEAD"]).stdout.strip()
    report["tracked_worktree_changes"] = runner.run("source-status", ["git", "-C", REPO, "status", "--porcelain", "--untracked-files=no"]).stdout
    report["consumer_sha256"] = digest(args.consumer)
    report["adb_version"] = runner.run("adb-version", [args.adb, "version"]).stdout
    source_lock_path = REPO / "validation/source-bundle/dependencies.lock.json"
    source_lock = json.loads(source_lock_path.read_text())
    report["native_tls_provider"] = {"name": "BoringSSL", "linkage": "static",
                                    "source_revision": source_lock["boringssl_revision"],
                                    "source_lock_sha256": digest(source_lock_path),
                                    "evidence_kind": "pinned_native_build_configuration"}
    runner.ready()
    if runner.shell("emulator-only", "getprop", "ro.kernel.qemu").stdout.strip() != "1":
        raise RuntimeError("Selected transport is not a disposable emulator")
    report["emulator_verified"] = True
    props = {}
    for key in ("ro.build.fingerprint", "ro.build.version.sdk", "ro.build.version.release", "ro.adb.secure",
                "ro.debuggable", "persist.adb.tls_server.enable", "persist.adb.wifi.guid", "service.adb.tls.port"):
        props[key] = runner.shell("get-" + key, "getprop", key).stdout.strip()
    report["android_properties"] = props
    # This transaction map was verified against the Android 15 AIDL, not guessed on a vendor ABI.
    if props["ro.build.version.sdk"] != "35":
        raise RuntimeError("Pairing Binder ABI has only been verified for this driver's API 35 image")
    services = runner.shell("binder-descriptors", "service", "list").stdout
    if not re.search(r"\badb: \[android\.debug\.IAdbManager\]", services):
        raise RuntimeError("Real android.debug.IAdbManager Binder service absent")
    supported = runner.shell("wireless-capability", "cmd", "adb", "is-wifi-supported").stdout.strip()
    if supported != "true":
        raise RuntimeError("System reports wireless adb unsupported")
    abi_probe = runner.binder("verify-abi-wifi-transaction", 12)
    if not re.search(r"00000000\s+00000001", abi_probe):
        raise RuntimeError("IAdbManager transaction 12 does not match the verified API 35 ABI")
    report["peer"] = {"kind": "android_system_AOSP_pairing_service", "binder": "android.debug.IAdbManager",
                      "binder_abi_source": ABI_SOURCE, "native_service_source": JNI_SOURCE,
                      "start_method": "enablePairingByQrCode", "physical_device": False}
    original_wifi = runner.shell("snapshot-adb-wifi-setting", "settings", "get", "global", "adb_wifi_enabled").stdout.strip()
    original_uid = runner.shell("snapshot-adbd-uid", "id", "-u").stdout.strip()
    if original_uid not in ("0", "2000"):
        raise RuntimeError("Unexpected adbd identity")
    report["original_wifi_setting"] = original_wifi
    report["original_adbd_uid"] = original_uid
    rooted = False
    mutated = False
    pairing_attempted = False
    forwards = []
    fingerprint = None
    key_blob = None
    original_keys = set()
    connect_port = 0
    errors = []
    failure = None
    with tempfile.TemporaryDirectory(prefix="kadb-m3-pair-") as directory:
        temporary = Path(directory)
        key = temporary / "identity"
        code_file = temporary / "code"
        try:
            runner.adb("root-only-disposable-emulator", "root")
            rooted = True
            runner.ready()
            if runner.shell("verify-root", "id", "-u").stdout.strip() != "0":
                raise RuntimeError("Rootable emulator required for ownership and cleanup evidence")
            for name, command in {
                "version": "/apex/com.android.adbd/bin/adbd --version",
                "binary": "readlink -f /apex/com.android.adbd/bin/adbd",
                "sha256": "sha256sum /apex/com.android.adbd/bin/adbd",
                "processes": "ps -A -o PID,UID,NAME | grep -E 'adbd|system_server'",
                "framework_native": "ls -l /system/lib64/libandroid_servers.so /apex/com.android.adbd/lib64/libadb_pairing_connection.so",
            }.items():
                result = runner.raw_shell("android-identity-" + name, command, check=False)
                report["peer"][name] = {"stdout": result.stdout, "exit_code": result.returncode}
            system_pid = runner.shell("system-server-pid", "pidof", "system_server").stdout.strip()
            if not re.fullmatch(r"\d+", system_pid):
                raise RuntimeError("Cannot identify the real system_server PID")
            report["peer"]["system_server_pid"] = int(system_pid)
            original = runner.raw_shell("snapshot-authorized-public-keys", "cat /data/misc/adb/adb_keys 2>/dev/null", check=False)
            original_keys = {line.split()[0] for line in original.stdout.splitlines() if line.strip()}
            report["original_authorized_key_count"] = len(original_keys)
            runner.run("generate-temporary-identity", [args.adb, "keygen", key])
            key.chmod(0o600)
            runner.secrets.append(key.read_text())
            key_blob = (temporary / "identity.pub").read_text().split()[0]
            fingerprint = ":".join(re.findall("..", hashlib.md5(base64.b64decode(key_blob)).hexdigest().upper()))
            report["temporary_public_key_fingerprint_md5"] = fingerprint
            if key_blob in original_keys:
                raise RuntimeError("Temporary identity unexpectedly already trusted")
            wifi = runner.shell("wifi-network-status", "cmd", "wifi", "status").stdout
            bssids = re.findall(r"BSSID:\s*([0-9a-fA-F]{2}(?::[0-9a-fA-F]{2}){5})", wifi)
            if not bssids:
                raise RuntimeError("Wireless debugging requires the emulator's connected Wi-Fi BSSID")
            mutated = True
            runner.shell("enable-wireless-debugging", "settings", "put", "global", "adb_wifi_enabled", 1)
            runner.binder("allow-current-emulator-network-once", 4, "i32", 0, "s16", bssids[0])
            deadline = time.monotonic() + 30
            connect_port = 0
            while time.monotonic() < deadline:
                port = runner.shell("await-real-tls-port", "getprop", "service.adb.tls.port").stdout.strip()
                if port.isdigit() and 0 < int(port) < 65536:
                    listings = runner.shell("verify-adbd-tls-listener-owner", "ss", "-ltnp").stdout
                    if listener_owned(listings, int(port), "adbd"):
                        connect_port = int(port)
                        report["connection_listener"] = {"port": connect_port, "owner": "adbd", "ss": listings}
                        break
                time.sleep(1)
            if not connect_port:
                raise RuntimeError("System did not expose an adbd-owned wireless TLS connection listener")
            device_epoch = int(runner.shell("pairing-log-start-time", "date", "+%s").stdout.strip())
            # Android's QR path takes an out-of-band secret. A six-digit ephemeral
            # value exercises the same native SPAKE2 service as code pairing.
            code = f"{secrets.randbelow(1_000_000):06d}"
            wrong_code = f"{(int(code) + 1) % 1_000_000:06d}"
            runner.secrets.extend([code, wrong_code])
            pairing_attempted = True
            runner.binder("start-real-aosp-qr-pairing", 9, "s16", "kadb-m3-" + run_id, "s16", code)
            pair_port = 0
            deadline = time.monotonic() + 20
            while time.monotonic() < deadline:
                logs = runner.shell("pairing-server-start-log", "logcat", "-d", "-v", "epoch", "--pid", system_pid, "-t", 1000).stdout
                recent = [line for line in logs.splitlines() if re.match(r"^\s*\d+\.\d+", line)
                          and float(line.split()[0]) >= device_epoch]
                ports = re.findall(r"Pairing server started on port\s+(\d+)", "\n".join(recent))
                listings = runner.shell("verify-pairing-listener-owner", "ss", "-ltnp").stdout
                if ports and listener_owned(listings, int(ports[-1]), "system_server"):
                    pair_port = int(ports[-1])
                    report["pairing_listener"] = {"port": pair_port, "owner": "system_server", "ss": listings,
                                                    "server_started_log": runner.redact("\n".join(recent))}
                    break
                time.sleep(1)
            if not pair_port or pair_port == connect_port:
                raise RuntimeError("Distinct genuine system_server pairing endpoint not established")
            paired_forward = int(runner.adb("forward-real-pairing", "forward", "tcp:0", f"tcp:{pair_port}").stdout.strip())
            forwards.append(paired_forward)
            report["sessions"] = []
            for mode, secret in (("reject", wrong_code), ("pair", code)):
                code_file.write_text(secret, encoding="ascii")
                code_file.chmod(0o600)
                session = {"mode": mode, "peer_kind": "real_AOSP_system_service"}
                report["sessions"].append(session)
                relay = PairingRelay(paired_forward)
                try:
                    with relay:
                        consumer(runner, mode, relay.port, key, code_file, run_id, session)
                finally:
                    session["wire"] = relay.snapshot()
                hello = session["wire"]["server_hello"]
                if session["wire"]["connections"] != 1 or not hello or any(h["selected_version"] != 0x304 for h in hello) or session["wire"]["parse_errors"]:
                    raise RuntimeError(f"{mode}: real TLS 1.3 ServerHello evidence missing")
                if mode == "reject":
                    logs = runner.shell("wrong-code-real-server-log", "logcat", "-d", "-v", "epoch", "--pid", system_pid, "-t", 1000).stdout
                    recent = [line for line in logs.splitlines() if re.match(r"^\s*\d+\.\d+", line)
                              and float(line.split()[0]) >= device_epoch]
                    rejection_log = "\n".join(recent)
                    session["server_gcm_rejection_observed"] = bool(re.search(r"Failed to decrypt|Unable to decrypt data", rejection_log))
                    session["server_log"] = runner.redact(rejection_log)
                    current_keys = runner.raw_shell("wrong-code-did-not-authorize", "cat /data/misc/adb/adb_keys 2>/dev/null", check=False).stdout
                    session["temporary_key_absent"] = key_blob not in current_keys
                    if not session["server_gcm_rejection_observed"] or not session["temporary_key_absent"]:
                        raise RuntimeError("Wrong-code failure lacks actual system GCM rejection or left authorization behind")
            deadline = time.monotonic() + 10
            while time.monotonic() < deadline:
                current_keys = runner.raw_shell("confirm-pairing-persisted-only-public-identity", "cat /data/misc/adb/adb_keys 2>/dev/null", check=False).stdout
                if key_blob in current_keys:
                    report["paired_key_persisted_by_android"] = True
                    break
                time.sleep(0.5)
            if not report.get("paired_key_persisted_by_android"):
                raise RuntimeError("Kadb pair returned, but Android did not authorize the temporary public key")
            report["pairing_verdict"] = "PASS"
            report["session_isolation_verdict"] = "NOT VERIFIED"
            connection_forward = int(runner.adb("forward-real-adbd-tls", "forward", "tcp:0", f"tcp:{connect_port}").stdout.strip())
            forwards.append(connection_forward)
            connection = {"mode": "connect"}
            report["post_pair_connection"] = connection
            relay = AdbRelay(connection_forward)
            try:
                with relay:
                    consumer(runner, "connect", relay.port, key, code_file, run_id, connection)
            finally:
                connection["wire"] = relay.snapshot()
            counts = connection["wire"]["counts"]
            if not counts.get("host_to_adbd:STLS") or not counts.get("adbd_to_host:STLS") or connection["wire"]["header_errors"]:
                raise RuntimeError("Paired connection shell succeeded without observed reciprocal STLS")
            report["post_pair_connection_verdict"] = "PASS"
            report["post_pair_identity_enforcement_verdict"] = "NOT VERIFIED"
            report["post_pair_identity_enforcement_note"] = (
                "The paired identity connected; no separate unpaired TLS-identity rejection probe was executed. "
                "The recorded ro.adb.secure setting alone is not rejection evidence.")
        except Exception as error:
            failure = error
        finally:
            def clean(label, action):
                try:
                    action()
                except Exception as error:
                    errors.append({"step": label, "error": runner.redact(error)})

            if pairing_attempted:
                clean("cancel-system-pairing", lambda: runner.binder("cleanup-cancel-pairing", 11))
            if fingerprint:
                clean("unpair-only-temporary-identity", lambda: runner.binder("cleanup-unpair-test-identity", 7, "s16", fingerprint))
                def verify_keys():
                    deadline = time.monotonic() + 10
                    while time.monotonic() < deadline:
                        current = runner.raw_shell("cleanup-verify-authorized-keys", "cat /data/misc/adb/adb_keys 2>/dev/null", check=False).stdout
                        keys = {line.split()[0] for line in current.splitlines() if line.strip()}
                        if key_blob not in keys and keys == original_keys:
                            report["authorized_key_set_restored"] = True
                            return
                        time.sleep(0.5)
                    raise RuntimeError("Original public key set not restored by targeted unpair")
                clean("verify-original-authorizations", verify_keys)
            for port in forwards:
                clean("remove-forward-" + str(port), lambda port=port: runner.adb("cleanup-forward", "forward", "--remove", f"tcp:{port}"))
            if mutated:
                if original_wifi == "null":
                    clean("restore-wifi-setting-absent", lambda: runner.shell("cleanup-wifi-setting", "settings", "delete", "global", "adb_wifi_enabled"))
                else:
                    clean("restore-wifi-setting", lambda: runner.shell("cleanup-wifi-setting", "settings", "put", "global", "adb_wifi_enabled", original_wifi))
                def settle_wifi_handler():
                    # ContentObserver/Binder work is asynchronous. Do not let a
                    # queued disable overwrite the exact property restoration.
                    expected_enabled = original_wifi == "1"
                    deadline = time.monotonic() + 10
                    while time.monotonic() < deadline:
                        enabled = runner.shell("cleanup-await-wifi-handler", "getprop", "persist.adb.tls_server.enable").stdout.strip()
                        port = runner.shell("cleanup-await-tls-server", "getprop", "service.adb.tls.port").stdout.strip()
                        active = port.isdigit() and 0 < int(port) < 65536
                        if expected_enabled and enabled == "1" and active:
                            return
                        if not expected_enabled and enabled in ("", "0") and not active:
                            return
                        time.sleep(0.25)
                    raise RuntimeError("Wireless debugging handler did not settle before property restoration")
                clean("await-wifi-handler-before-property-restore", settle_wifi_handler)
                # Restore only properties observed before this run; never touch ro.* or partitions.
                for prop in ("persist.adb.tls_server.enable", "persist.adb.wifi.guid"):
                    clean("restore-" + prop, lambda prop=prop: runner.shell("cleanup-" + prop, "setprop", prop, props[prop]))
            if rooted and original_uid == "2000":
                clean("restore-adbd-unroot", lambda: runner.adb("cleanup-unroot", "unroot"))
                clean("await-restored-adbd", runner.ready)
            if rooted:
                def verify_state():
                    if runner.shell("cleanup-verify-uid", "id", "-u").stdout.strip() != original_uid:
                        raise RuntimeError("adbd privilege state not restored")
                    if runner.shell("cleanup-verify-auth", "getprop", "ro.adb.secure").stdout.strip() != props["ro.adb.secure"]:
                        raise RuntimeError("Authentication configuration changed")
                    observed = runner.shell("cleanup-verify-wifi-setting", "settings", "get", "global", "adb_wifi_enabled").stdout.strip()
                    if observed != original_wifi:
                        raise RuntimeError("Wireless debugging setting was not restored")
                    for prop in ("persist.adb.tls_server.enable", "persist.adb.wifi.guid"):
                        if runner.shell("cleanup-verify-" + prop, "getprop", prop).stdout.strip() != props[prop]:
                            raise RuntimeError("Wireless property not restored: " + prop)
                    report["emulator_auth_wifi_and_uid_restored"] = True
                clean("verify-original-emulator-state", verify_state)
    report["temporary_private_key_and_codes_deleted"] = True
    report["cleanup_errors"] = errors
    if failure:
        raise failure
    if errors:
        raise RuntimeError("Pairing checks completed but cleanup failed")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--adb", required=True)
    parser.add_argument("--serial", required=True)
    parser.add_argument("--consumer", required=True)
    parser.add_argument("--adb-server-port", type=int, default=5038)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if not re.fullmatch(r"emulator-[0-9]+", args.serial):
        parser.error("An explicit emulator-N serial is required; physical devices are refused")
    if not 1 <= args.adb_server_port <= 65535:
        parser.error("Invalid dedicated adb server port")
    args.adb = str(Path(args.adb).resolve(strict=True))
    args.consumer = str(Path(args.consumer).resolve(strict=True))
    if not os.access(args.consumer, os.X_OK):
        parser.error("Consumer must be the built executable")
    args.output.mkdir(parents=True, exist_ok=False)
    report = {"schema": 1, "status": "failed", "test_layer": "Native_public_API_to_AOSP_system_pairing_service",
              "physical_device": False, "pairing_verdict": "NOT VERIFIED", "post_pair_connection_verdict": "NOT VERIFIED",
              "started_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
              "spake2_expected_version": "0.1.0-dev.59105290820b",
              "spake2_expected_source": "59105290820bcbfd4e0336a2e7713006a461527f",
              "cryptographic_compatibility": "HARDENED, NUL identities, adb-label NUL exporter, existing HKDF/GCM/PeerInfo",
              "R3_K01": "Inherited bidirectional GCM nonce risk remains; wire protocol unchanged"}
    runner = Runner(args)
    code = 1
    try:
        execute(args, runner, report)
        report["status"] = "passed"
        code = 0
    except Exception as error:
        report["error_type"] = type(error).__name__
        report["error"] = runner.redact(error)
    finally:
        # Capture before forgetting the temporary values, including failure paths.
        # The workflow must use this redacted file instead of a second raw logcat.
        if report.get("emulator_verified"):
            try:
                logcat = runner.adb("final-redacted-emulator-logcat", "logcat", "-d", "-v", "threadtime", timeout=15, check=False)
                (args.output / "emulator-logcat-redacted.log").write_text(runner.redact(logcat.stdout), encoding="utf-8")
                report["redacted_logcat_exit_code"] = logcat.returncode
            except Exception as error:
                report["redacted_logcat_error"] = runner.redact(error)
        report["commands_executed"] = runner.count
        report["checks_executed"] = sum(s.get("consumer", {}).get("checks_executed", 0) for s in report.get("sessions", []))
        report["checks_executed"] += report.get("post_pair_connection", {}).get("consumer", {}).get("checks_executed", 0)
        runner.log.close()
        (args.output / "report.json").write_text(json.dumps(runner.sanitized(report), ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({key: report[key] for key in ("status", "pairing_verdict", "post_pair_connection_verdict", "checks_executed")}, ensure_ascii=False))
    return code


if __name__ == "__main__":
    sys.exit(main())
