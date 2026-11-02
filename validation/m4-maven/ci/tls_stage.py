#!/usr/bin/env python3
"""Real rootless AOSP pairing, TLS identity acceptance, rejection and revocation.

This module never patches Android, writes authorization files, or changes TLS
verification. The caller owns the disposable AVD, identities and forward cleanup.
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import re
import secrets
import tempfile
import time

REPO = Path(__file__).resolve().parents[3]
_spec = importlib.util.spec_from_file_location(
    "kadb_m3_pairing_for_m4", REPO / "validation/m3-maven/ci/run_pairing.py")
_m3 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_m3)
PairingRelay = _m3.PairingRelay


def _require(condition, message):
    if not condition:
        raise RuntimeError(message)


def _listener(text, port):
    for line in text.splitlines():
        fields = line.split()
        if len(fields) >= 5 and fields[0] == "LISTEN" and fields[3].rsplit(":", 1)[-1] == str(port):
            return True
    return False


def parse_wireless_port(reply):
    """Decode API 35 IAdbManager.getAdbWirelessPort's exception + signed int32.

    `service call` prints hexadecimal Parcel words, optionally with addresses
    and an ASCII column. Empty/denied output must never mean "listener stopped".
    """
    parcel = re.search(r"\bParcel\((.*)\)\s*$", reply.strip(), re.DOTALL)
    _require(parcel is not None, "Wireless-port Binder reply contains no Parcel")
    words = []
    for line in parcel.group(1).splitlines():
        hex_column = line.split("'", 1)[0]
        hex_column = re.sub(r"^\s*0x[0-9a-fA-F]+:\s*", "", hex_column)
        words.extend(re.findall(r"(?<![A-Za-z0-9])[0-9a-fA-F]{8}(?![A-Za-z0-9])", hex_column))
    _require(len(words) == 2 and int(words[0], 16) == 0,
             "Wireless-port Binder reply is not a successful int32 result")
    unsigned = int(words[1], 16)
    port = unsigned - (1 << 32) if unsigned & (1 << 31) else unsigned
    _require(-1 <= port <= 65535, "Wireless-port Binder result is outside the API's port range")
    return port


def wireless_port(runner, label):
    # API 35 AIDL declaration order is pinned in the M4 source investigation.
    # Unlike service.adb.tls.port, this normal Binder getter is shell-readable.
    return parse_wireless_port(runner.binder(label, 10))


def _same_peer(reference, observed):
    return (bool(reference.get("pid")) and observed.get("pid") == reference.get("pid")
            and observed.get("listener_present") is True and observed.get("ro.adb.secure") == "1")


def _tls_wire(session):
    wire = session.get("wire", {})
    counts = wire.get("counts", {})
    _require(wire.get("connections") == 1, "Expected exactly one fresh TLS connection")
    _require(not wire.get("header_errors"), "Invalid plaintext ADB framing before STLS")
    _require(counts.get("host_to_adbd:STLS") == 1 and counts.get("adbd_to_host:STLS") == 1,
             "Expected reciprocal STLS on this connection")
    observations = [item for directions in wire.get("tls", {}).values()
                    for item in directions.values()]
    _require(observations and all(not item.get("tls_parse_errors") for item in observations),
             "TLS metadata unavailable or malformed")
    hellos = [hello for item in observations for hello in item.get("server_hello", [])]
    _require(hellos and all(hello.get("selected_version") == 0x304 for hello in hellos),
             "TLS 1.3 ServerHello missing on this connection")
    _require(wire.get("active_connections") == 0, "Relay still owns an active connection")
    _require(not session.get("system", {}).get("auth_not_required"),
             "Real adbd reported authentication was not required")
    session["tls_server_hello_is_only_negotiation_evidence"] = True


def _positive(session, reference):
    _tls_wire(session)
    _require(_same_peer(reference, session.get("peer_before", {}))
             and _same_peer(reference, session.get("peer_after", {})),
             "adbd changed or listener/authentication was unavailable during positive TLS check")
    consumer = session.get("consumer", {})
    _require(consumer.get("adb_handshake_completed") is True and consumer.get("shell_succeeded") is True,
             "Authorized identity did not establish a real ADB session and Shell")
    _require(session.get("system", {}).get("tls_matched_identity") is True,
             "Successful connection lacks adbd matching this identity's public key")
    session["identity_acceptance_verdict"] = "PASS"


def _negative(session, reference):
    _tls_wire(session)
    _require(_same_peer(reference, session.get("peer_before", {}))
             and _same_peer(reference, session.get("peer_after", {})),
             "adbd changed or listener/authentication was unavailable during negative TLS check")
    consumer = session.get("consumer", {})
    system = session.get("system", {})
    _require(consumer.get("adb_handshake_completed") is False and consumer.get("shell_succeeded") is False,
             "Unauthorized TLS identity obtained a successful ADB session")
    _require(system.get("tls_key_mismatch") is True and system.get("tls_handshake_failed") is True
             and system.get("tls_certificate_verify_failed") is True,
             "Connection failure lacks actual adbd key mismatch and certificate verification rejection")
    _require(not system.get("tls_matched_identity"), "Rejected identity was also reported accepted")
    _require(consumer.get("rejection_category") not in ("network_connect_error", "io_timeout"),
             "A network failure or timeout cannot replace TLS identity rejection")
    session["identity_rejection_verdict"] = "PASS"


def _auth(runner, stage, label, identity, forward, mode):
    record = {"label": label, "identity": identity["name"], "mode": mode}
    stage["sessions"].append(record)
    try:
        record.update(runner.auth_session(label, identity, forward, mode))
    except Exception as error:
        record["execution_error"] = runner.redact(error)
        # The shared runner saves the actual attempt before raising. Retain it
        # here too so a rejected identity that unexpectedly established CNXN
        # cannot disappear behind this stage's placeholder record.
        partial = next((item for item in reversed(runner.sessions) if item.get("label") == label), None)
        if partial:
            record.update(partial)
        if mode == "reject" and record.get("consumer", {}).get("adb_handshake_completed") is True:
            stage["verdict"] = "FAIL"
        raise
    return record


def run_tls(runner, identities, report):
    """Populate report['M4-B']; raise after preserving checks and bounded cleanup."""
    stage = {"verdict": "NOT VERIFIED", "status": "running", "sessions": [],
             "pairing_verdict": "NOT VERIFIED", "paired_identity_acceptance": "NOT VERIFIED",
             "unpaired_identity_rejection": "NOT VERIFIED", "revocation_rejection": "NOT VERIFIED",
             "physical_device": False, "authorization_api": "android.debug.IAdbManager",
             "root_used": False, "authorization_files_written_by_driver": False,
             "revocation_boundary": "Fresh connections after targeted unpair and persisted public-key removal; no adbd restart"}
    report["M4-B"] = stage
    identity_a, identity_b = identities["tls_a"], identities["tls_b"]
    baseline = runner.keys("tls-original-authorizations")
    _require(identity_a["blob"] not in baseline and identity_b["blob"] not in baseline,
             "TLS test identities must both be absent before pairing")
    original_wifi = runner.shell("tls-original-wifi-setting", "settings", "get", "global", "adb_wifi_enabled").stdout.strip()
    stage["original_wifi_setting"] = original_wifi
    stage["original_authorized_key_count"] = len(baseline)
    pairing_started = False
    wifi_changed = False
    connect_port = None
    error = None
    cleanup_errors = []
    try:
        system_pid = runner.shell("tls-system-server-pid", "pidof", "system_server").stdout.strip()
        _require(re.fullmatch(r"\d+", system_pid), "Cannot identify the real Android system_server")
        stage["system_server_pid"] = int(system_pid)
        wifi_status = runner.shell("tls-current-wifi-status", "cmd", "wifi", "status").stdout
        bssids = re.findall(r"BSSID:\s*([0-9a-fA-F]{2}(?::[0-9a-fA-F]{2}){5})", wifi_status)
        _require(bssids, "Connected emulator Wi-Fi BSSID unavailable")
        wifi_changed = True
        # The normal allow handler sets adb_wifi_enabled itself. Pre-setting it
        # causes an unnecessary untrusted-network prompt/reset race.
        runner.binder("tls-allow-current-network-once", 4, "i32", 0, "s16", bssids[0])
        deadline = time.monotonic() + 30
        reference = None
        while time.monotonic() < deadline:
            port = wireless_port(runner, "tls-await-listener-port-binder")
            if port > 0:
                state = runner.peer_state("tls-await-listener-state", port)
                if state.get("listener_present") and state.get("pid") and state.get("ro.adb.secure") == "1":
                    connect_port, reference = port, state
                    break
            time.sleep(0.5)
        _require(connect_port is not None, "Authenticated wireless adbd listener did not become ready")
        stage["connection_listener"] = {"port": connect_port, "state": reference,
                                         "identity_sources": ["IAdbManager.getAdbWirelessPort transaction 10", "adbd PID", "rootless ss listener", "per-session adbd auth logs"]}
        connection_forward = runner.forward(connect_port)

        pairing_marker = runner.mark("tls-real-pairing")
        with tempfile.TemporaryDirectory(prefix="kadb-m4-pairing-code-") as directory:
            code = f"{secrets.randbelow(1_000_000):06d}"
            runner.secrets.append(code)
            code_file = Path(directory) / "code"
            code_file.write_text(code, encoding="ascii")
            code_file.chmod(0o600)
            pairing_started = True
            runner.binder("tls-start-real-aosp-pairing", 9, "s16", "kadb-m4-" + runner.run_id, "s16", code)
            deadline = time.monotonic() + 20
            pair_port = None
            while time.monotonic() < deadline:
                logs = runner.logs("tls-pairing-start", pairing_marker)
                # threadtime: MM-DD HH:MM:SS.mmm PID TID priority tag: message.
                owned = [line for line in logs.splitlines()
                         if re.search(r"\s" + re.escape(system_pid) + r"\s+\d+\s+[VDIWEF]\s", line)]
                ports = re.findall(r"Pairing server started on port\s+(\d+)", "\n".join(owned))
                listings = runner.shell("tls-pairing-listeners", "ss", "-ltn").stdout
                if ports and _listener(listings, int(ports[-1])):
                    pair_port = int(ports[-1])
                    stage["pairing_listener"] = {"port": pair_port, "system_server_pid": int(system_pid),
                                                  "owner_evidence": "system_server JNI start log and matching rootless ss listener",
                                                  "server_start_log": runner.redact("\n".join(owned))}
                    break
                time.sleep(0.5)
            _require(pair_port is not None and pair_port != connect_port,
                     "Distinct real system_server pairing endpoint not established")
            pair_forward = runner.forward(pair_port)
            pairing = {"mode": "pair", "identity": identity_a["name"], "real_AOSP_system_service": True}
            stage["pairing"] = pairing
            relay = PairingRelay(pair_forward)
            try:
                with relay:
                    result = runner.run("tls-public-kadb-pair", [runner.args.pairing_consumer,
                                        "--mode", "pair", "--port", relay.port,
                                        "--private-key", identity_a["key"], "--code-file", code_file,
                                        "--run-id", runner.run_id], timeout=30, check=False)
                    pairing["exit_code"] = result.returncode
                    lines = [line.removeprefix("KADB_REAL_PAIRING_JSON ") for line in result.stdout.splitlines()
                             if line.startswith("KADB_REAL_PAIRING_JSON ")]
                    _require(len(lines) == 1, "Missing or ambiguous Native real-pairing result")
                    parsed = json.loads(lines[0])
                    pairing["consumer"] = parsed
                    _require(result.returncode == 0 and parsed.get("status") == "passed",
                             "Public Kadb.pair failed against real Android")
                    _require(parsed.get("checks") == ["identity_import", "real_aosp_public_pair_returned", "temporary_identity_cleared"]
                             and parsed.get("checks_executed") == 3, "Pairing consumer omitted required checks")
            finally:
                pairing["wire"] = relay.snapshot()
            wire = pairing["wire"]
            _require(wire.get("connections") == 1 and not wire.get("parse_errors") and wire.get("server_hello")
                     and all(h.get("selected_version") == 0x304 for h in wire["server_hello"]),
                     "Real pairing TLS 1.3 evidence unavailable")
            stage["pairing_authorizations"] = runner.wait_keys("tls-pairing-key-persisted", baseline | {identity_a["blob"]})
            stage["pairing_verdict"] = "PASS"
        stage["temporary_pairing_code_deleted"] = True
        runner.binder("tls-stop-completed-pairing", 11)
        pairing_started = False

        first = _auth(runner, stage, "tls-paired-a-before", identity_a, connection_forward, "positive")
        _positive(first, reference)
        stage["paired_identity_acceptance"] = "PASS"
        stage["keys_before_unpaired_attempt"] = runner.wait_keys("tls-before-b-keys", baseline | {identity_a["blob"]})
        unpaired = _auth(runner, stage, "tls-unpaired-b", identity_b, connection_forward, "reject")
        _negative(unpaired, reference)
        stage["keys_after_unpaired_attempt"] = runner.wait_keys("tls-after-b-keys", baseline | {identity_a["blob"]})
        again = _auth(runner, stage, "tls-paired-a-after", identity_a, connection_forward, "positive")
        _positive(again, reference)
        stage["unpaired_identity_rejection"] = "PASS"
        stage["authorized_identity_survived_negative"] = True

        stage["revocation"] = runner.unpair(identity_a, "tls-revoke-paired-a")
        stage["revocation_persisted_authorizations"] = runner.wait_keys("tls-revocation-persisted", baseline)
        revoked = _auth(runner, stage, "tls-revoked-a", identity_a, connection_forward, "reject")
        _negative(revoked, reference)
        stage["keys_after_revoked_attempt"] = runner.wait_keys("tls-after-revoked-a-keys", baseline)
        control = _auth(runner, stage, "tls-authorized-control-after-revocation", identities["control"], connection_forward, "positive")
        _positive(control, reference)
        stage["revocation_rejection"] = "PASS"
        stage["listener_healthy_after_revocation"] = True
        stage["no_adbd_restart_required"] = True
        stage["verdict"] = "PASS"
        stage["status"] = "passed"
    except Exception as failure:
        error = failure
        stage["status"] = "failed"
        stage["error"] = runner.redact(failure)
        stage["error_type"] = type(failure).__name__
        if any(s.get("mode") == "reject" and s.get("consumer", {}).get("adb_handshake_completed") is True
               for s in stage["sessions"]):
            stage["verdict"] = "FAIL"
    finally:
        def clean(label, operation):
            try:
                operation()
            except Exception as cleanup:
                cleanup_errors.append({"step": label, "error": runner.redact(cleanup)})

        if pairing_started:
            clean("cancel-pairing", lambda: runner.binder("tls-cleanup-pairing", 11))

        def remove_own_identity():
            if identity_a["blob"] in runner.keys("tls-cleanup-current-keys"):
                stage["cleanup_revocation"] = runner.unpair(identity_a, "tls-cleanup-unpair-a")
            stage["cleanup_authorizations"] = runner.wait_keys("tls-cleanup-original-keys", baseline)
        clean("restore-original-key-set", remove_own_identity)
        if wifi_changed:
            if original_wifi == "null":
                clean("restore-absent-wifi-setting", lambda: runner.shell("tls-cleanup-wifi-setting", "settings", "delete", "global", "adb_wifi_enabled"))
            else:
                clean("restore-wifi-setting", lambda: runner.shell("tls-cleanup-wifi-setting", "settings", "put", "global", "adb_wifi_enabled", original_wifi))

            def verify_wifi():
                deadline = time.monotonic() + 15
                while time.monotonic() < deadline:
                    setting = runner.shell("tls-cleanup-observe-wifi-setting", "settings", "get", "global", "adb_wifi_enabled").stdout.strip()
                    port = wireless_port(runner, "tls-cleanup-observe-wifi-port-binder")
                    listings = runner.shell("tls-cleanup-observe-listeners", "ss", "-ltn").stdout
                    active = port > 0
                    tested_listener_present = connect_port is not None and _listener(listings, connect_port)
                    listener_restored = (_listener(listings, port) if original_wifi == "1"
                                         else not tested_listener_present)
                    stage["wireless_cleanup_observation"] = {"setting": setting, "binder_port": port,
                                                              "tested_listener_present": tested_listener_present}
                    if setting == original_wifi and active == (original_wifi == "1") and listener_restored:
                        stage["wifi_setting_restored"] = True
                        return
                    time.sleep(0.5)
                raise RuntimeError("Wireless setting/listener did not restore within bounded cleanup")
            clean("verify-wifi-restoration", verify_wifi)
        stage["cleanup_errors"] = cleanup_errors
        if cleanup_errors:
            stage["status"] = "failed"
            if stage["verdict"] == "PASS":
                stage["verdict"] = "CONDITIONAL PASS"
    if error is not None:
        raise error
    if cleanup_errors:
        raise RuntimeError("TLS checks completed but cleanup failed")
    return stage
