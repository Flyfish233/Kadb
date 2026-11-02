#!/usr/bin/env python3
"""Real Android RSA AUTH enrollment, signature acceptance and explicit rejection."""
from pathlib import Path
import sys

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "validation/native-adbd"))
from run_emulator import authenticated_connection_count


def require_wire(session, *, enrolled):
    wire = session["wire"]
    assert wire["connections"] == 1 and not wire["header_errors"], "One unambiguous actual connection required"
    counts = wire["counts"]
    assert counts.get("adbd_to_host:AUTH:1", 0) >= 1, "No real AUTH challenge"
    assert counts.get("host_to_adbd:AUTH:2", 0) == 1, "Expected one actual Kadb signature"
    signatures = [item for values in wire.get("auth_verifications", {}).values() for item in values]
    assert len(signatures) == 1 and signatures[0]["token_observed_on_this_connection"], "Current connection token not associated"
    assert signatures[0]["signature_matches_expected_identity"], "Kadb signature failed independent public-key verification"
    assert signatures[0]["token_length"] == 20 and signatures[0]["signature_length"] == 256
    assert not counts.get("host_to_adbd:STLS") and not counts.get("adbd_to_host:STLS"), "RSA AUTH must not be inferred from TLS"
    assert not session["system"]["auth_not_required"], "Authentication bypass reported by adbd"
    if enrolled:
        assert authenticated_connection_count(wire) == 1, "No AUTH/signature/CNXN acceptance on this connection"
        assert counts.get("host_to_adbd:AUTH:3", 0) == 0, "Already authorized key unexpectedly required new enrollment"
        assert session["consumer"]["adb_handshake_completed"] and session["consumer"]["shell_succeeded"]
    else:
        assert counts.get("host_to_adbd:AUTH:3", 0) == 1, "Pending normal public-key confirmation missing"
        public_events = [event for values in wire.get("auth_events", {}).values() for event in values
                         if event.get("auth_type") == 3]
        assert len(public_events) == 1 and public_events[0].get("public_key_matches_expected_identity"), "Submitted identity differs from specified key"


def same_peer(first, other):
    assert first["pid"] == other["pid"] and first["pid"], "adbd restarted during acceptance"
    assert other["listener_present"] and other["ro.adb.secure"] == "1"


def session(runner, stage, label, identity, target, mode, **options):
    record = {"label": label, "identity": identity["name"], "mode": mode}
    stage["sessions"].append(record)
    try:
        record.update(runner.auth_session(label, identity, target, mode, **options))
    except Exception as error:
        record["execution_error"] = runner.redact(error)
        # The shared runner also persists this actual attempt independently.
        partial = next((s for s in reversed(runner.sessions) if s["label"] == label), None)
        if partial:
            record.update(partial)
        raise
    return record


def run_rsa(runner, identities, report):
    stage = report["M4-A"]
    stage.update({"verdict": "NOT VERIFIED", "layer": "Native public API to real authenticated Android adbd",
                  "sessions": [], "authorization_method": "normal pending-key IAdbManager.allowDebugging",
                  "rejection_method": "normal IAdbManager.denyDebugging with actual adbd NO",
                  "normal_deny_may_leave_socket_waiting": True})
    a, b = identities["rsa_a"], identities["rsa_b"]
    initial = runner.keys("rsa-initial-authorizations")
    assert a["blob"] not in initial and b["blob"] not in initial
    target = runner.forward(5555)
    state = runner.peer_state("rsa-start-peer", 5555)
    stage["peer"] = state
    assert state["listener_present"] and state["ro.adb.secure"] == "1"
    primary = None
    try:
        enrollment = session(runner, stage, "rsa-a-normal-enrollment", a, target, "positive", approval="allow", timeout_ms=20000)
        require_wire(enrollment, enrolled=False)
        assert enrollment["consumer"]["adb_handshake_completed"] and enrollment["consumer"]["shell_succeeded"]
        stage["enrollment_authorization_state"] = runner.wait_keys("rsa-a-persisted", initial | {a["blob"]})
        stage["enrollment"] = "PASS"

        before = session(runner, stage, "rsa-a-authorized-before", a, target, "positive")
        require_wire(before, enrolled=True)
        same_peer(state, before["peer_before"])
        same_peer(state, before["peer_after"])
        stage["authorized_positive"] = "PASS"

        negative = session(runner, stage, "rsa-b-unapproved-denied", b, target, "reject", approval="deny")
        require_wire(negative, enrolled=False)
        assert negative["system"]["framework_deny"] and negative["system"]["framework_no"], "Actual framework/adbd refusal required"
        assert not negative["wire"]["counts"].get("adbd_to_host:CNXN", 0), "Unapproved identity obtained CNXN"
        assert not negative["consumer"]["adb_handshake_completed"] and not negative["consumer"]["shell_succeeded"]
        assert negative["consumer"]["rejection_category"] != "network_connect_error", "Network failure cannot prove rejection"
        same_peer(state, negative["peer_before"])
        same_peer(state, negative["peer_after"])
        stage["negative_authorization_state"] = runner.wait_keys("rsa-b-not-authorized", initial | {a["blob"]})
        stage["unauthorized_rejection"] = "PASS"

        after = session(runner, stage, "rsa-a-authorized-after", a, target, "positive")
        require_wire(after, enrolled=True)
        same_peer(state, after["peer_before"])
        same_peer(state, after["peer_after"])
        stage["positive_after_rejection"] = "PASS"
        stage["protocol_identity_evidence"] = "PASS"
        stage["verdict"] = "PASS"
    except Exception as error:
        primary = error
        stage["error"] = runner.redact(error)
        stage["verdict"] = "FAIL"
    finally:
        try:
            if a["blob"] in runner.keys("rsa-cleanup-current-authorizations"):
                stage["revocation_cleanup"] = runner.unpair(a, "rsa-cleanup-unpair-a")
            stage["cleanup_authorization_state"] = runner.wait_keys("rsa-original-authorizations-restored", initial)
            stage["cleanup"] = "PASS"
        except Exception as error:
            stage["cleanup"] = "FAIL"
            stage["cleanup_error"] = runner.redact(error)
            stage["verdict"] = "FAIL"
            if primary is None:
                primary = error
    if primary:
        raise primary
