#!/usr/bin/env python3
"""False-pass regression checks for evidence gates; not Android execution evidence."""
from __future__ import annotations

import copy
import unittest

from rsa_stage import require_wire
from tls_stage import _auth, _negative, _positive


REFERENCE_PEER = {"pid": "417", "listener_present": True, "ro.adb.secure": "1"}


def rsa_sample(*, enrolled=True):
    counts = {"adbd_to_host:AUTH:1": 1, "host_to_adbd:AUTH:2": 1, "adbd_to_host:CNXN": 1}
    public_events = []
    if not enrolled:
        counts["adbd_to_host:AUTH:1"] = 2
        counts["host_to_adbd:AUTH:3"] = 1
        public_events = [{"auth_type": 3, "direction": "host_to_adbd",
                          "public_key_matches_expected_identity": True}]
    return {
        "wire": {
            "connections": 1,
            "counts": counts,
            "connection_counts": {"1": dict(counts)},
            "header_errors": [],
            "auth_verifications": {"1": [{"token_observed_on_this_connection": True,
                                             "signature_matches_expected_identity": True,
                                             "token_length": 20, "signature_length": 256}]},
            "auth_events": {"1": public_events},
        },
        "consumer": {"adb_handshake_completed": True, "shell_succeeded": True},
        "system": {"auth_not_required": False},
    }


def tls_sample(*, accepted):
    return {
        "wire": {
            "connections": 1,
            "header_errors": [],
            "active_connections": 0,
            "counts": {"host_to_adbd:STLS": 1, "adbd_to_host:STLS": 1},
            "tls": {"1": {
                "host_to_adbd": {"server_hello": [], "tls_parse_errors": []},
                "adbd_to_host": {"server_hello": [{"selected_version": 0x304, "cipher_suite": 0x1301}],
                                   "tls_parse_errors": []},
            }},
        },
        "consumer": {"adb_handshake_completed": accepted, "shell_succeeded": accepted,
                     "rejection_category": None if accepted else "tls_authentication_error_mapping"},
        "system": {"auth_not_required": False, "tls_matched_identity": accepted,
                   "tls_key_mismatch": not accepted, "tls_handshake_failed": not accepted,
                   "tls_certificate_verify_failed": not accepted},
        "peer_before": dict(REFERENCE_PEER),
        "peer_after": dict(REFERENCE_PEER),
    }


class RsaVerdictTest(unittest.TestCase):
    def test_current_key_challenge_signature_and_cnxn_reference_is_accepted(self):
        require_wire(rsa_sample(), enrolled=True)

    def test_normal_enrollment_requires_submitted_public_key_identity(self):
        reference = rsa_sample(enrolled=False)
        require_wire(reference, enrolled=False)
        for change in ("wrong_identity", "missing_public_frame", "duplicate_public_event"):
            with self.subTest(change=change):
                record = copy.deepcopy(reference)
                if change == "wrong_identity":
                    record["wire"]["auth_events"]["1"][0]["public_key_matches_expected_identity"] = False
                elif change == "missing_public_frame":
                    del record["wire"]["counts"]["host_to_adbd:AUTH:3"]
                else:
                    record["wire"]["auth_events"]["1"] *= 2
                with self.assertRaises(AssertionError):
                    require_wire(record, enrolled=False)

    def test_wrong_key_or_noncurrent_token_never_satisfies_rsa_identity(self):
        for field in ("signature_matches_expected_identity", "token_observed_on_this_connection"):
            with self.subTest(field=field):
                record = rsa_sample()
                record["wire"]["auth_verifications"]["1"][0][field] = False
                with self.assertRaises(AssertionError):
                    require_wire(record, enrolled=True)

    def test_missing_challenge_signature_or_cnxn_cannot_be_positive_authentication(self):
        for command in ("adbd_to_host:AUTH:1", "host_to_adbd:AUTH:2", "adbd_to_host:CNXN"):
            with self.subTest(command=command):
                record = rsa_sample()
                record["wire"]["counts"].pop(command)
                record["wire"]["connection_counts"]["1"].pop(command)
                with self.assertRaises(AssertionError):
                    require_wire(record, enrolled=True)

    def test_evidence_from_multiple_connections_is_not_one_rsa_acceptance(self):
        record = rsa_sample()
        record["wire"]["connections"] = 2
        with self.assertRaises(AssertionError):
            require_wire(record, enrolled=True)

    def test_signature_size_and_challenge_size_are_required(self):
        for field, value in (("token_length", 19), ("signature_length", 255)):
            with self.subTest(field=field):
                record = rsa_sample()
                record["wire"]["auth_verifications"]["1"][0][field] = value
                with self.assertRaises(AssertionError):
                    require_wire(record, enrolled=True)

    def test_tls_and_auth_bypass_cannot_be_labeled_rsa_auth(self):
        for reason in ("stls", "auth_bypass", "successful_shell_without_handshake"):
            with self.subTest(reason=reason):
                record = rsa_sample()
                if reason == "stls":
                    record["wire"]["counts"]["adbd_to_host:STLS"] = 1
                elif reason == "auth_bypass":
                    record["system"]["auth_not_required"] = True
                else:
                    record["consumer"]["adb_handshake_completed"] = False
                with self.assertRaises(AssertionError):
                    require_wire(record, enrolled=True)


class TlsVerdictTest(unittest.TestCase):
    def test_failed_native_rejection_attempt_preserves_unexpected_success_and_marks_stage_fail(self):
        class FailingRunner:
            def __init__(self):
                self.sessions = []

            def auth_session(self, label, identity, forward, mode):
                self.sessions.append({"label": label, "identity": identity["name"], "mode": mode,
                                      "status": "failed", "exit_code": 1,
                                      "consumer": {"adb_handshake_completed": True, "shell_succeeded": False,
                                                   "status": "failed", "checks_executed": 3},
                                      "wire": {"connections": 1}})
                raise RuntimeError("Native authentication consumer reported failure")

            @staticmethod
            def redact(value):
                return str(value)

        stage = {"verdict": "NOT VERIFIED", "sessions": []}
        runner = FailingRunner()
        with self.assertRaisesRegex(RuntimeError, "Native authentication consumer"):
            _auth(runner, stage, "tls-unpaired-b", {"name": "tls_b"}, 12345, "reject")
        self.assertEqual(stage["verdict"], "FAIL")
        self.assertEqual(len(stage["sessions"]), 1)
        preserved = stage["sessions"][0]
        self.assertIs(preserved["consumer"]["adb_handshake_completed"], True)
        self.assertEqual(preserved["consumer"]["checks_executed"], 3)
        self.assertEqual(preserved["exit_code"], 1)
        self.assertEqual(preserved["wire"]["connections"], 1)
        self.assertIn("execution_error", preserved)

    def test_reference_acceptance_and_refusal_require_different_real_evidence(self):
        accepted = tls_sample(accepted=True)
        refused = tls_sample(accepted=False)
        _positive(accepted, REFERENCE_PEER)
        _negative(refused, REFERENCE_PEER)
        self.assertEqual(accepted["identity_acceptance_verdict"], "PASS")
        self.assertEqual(refused["identity_rejection_verdict"], "PASS")

    def test_server_hello_alone_proves_neither_acceptance_nor_rejection(self):
        for accepted, gate in ((True, _positive), (False, _negative)):
            with self.subTest(accepted=accepted):
                record = tls_sample(accepted=accepted)
                record["system"] = {"auth_not_required": False}
                with self.assertRaises(RuntimeError):
                    gate(record, REFERENCE_PEER)

    def test_successful_shell_without_matched_identity_is_not_verified_authentication(self):
        record = tls_sample(accepted=True)
        record["system"]["tls_matched_identity"] = False
        with self.assertRaises(RuntimeError):
            _positive(record, REFERENCE_PEER)

    def test_socket_timeout_or_network_failure_cannot_replace_tls_refusal(self):
        for category in ("io_timeout", "network_connect_error"):
            with self.subTest(category=category):
                record = tls_sample(accepted=False)
                record["consumer"]["rejection_category"] = category
                with self.assertRaises(RuntimeError):
                    _negative(record, REFERENCE_PEER)

    def test_key_mismatch_and_handshake_rejection_are_both_required(self):
        for field in ("tls_key_mismatch", "tls_handshake_failed", "tls_certificate_verify_failed"):
            for missing in (True, False):
                with self.subTest(field=field, missing=missing):
                    record = tls_sample(accepted=False)
                    if missing:
                        del record["system"][field]
                    else:
                        record["system"][field] = False
                    with self.assertRaises(RuntimeError):
                        _negative(record, REFERENCE_PEER)

    def test_intermediate_key_mismatch_plus_generic_ssl_error_is_not_certificate_refusal(self):
        record = tls_sample(accepted=False)
        # adbd compares a certificate against each authorized public key. A
        # nonmatching candidate can precede acceptance; a later generic SSL I/O
        # error must not turn that comparison into certificate rejection.
        record["system"]["tls_key_mismatch"] = True
        record["system"]["tls_handshake_failed"] = True
        record["system"]["tls_certificate_verify_failed"] = False
        with self.assertRaisesRegex(RuntimeError, "certificate verification rejection"):
            _negative(record, REFERENCE_PEER)

    def test_successful_b_is_a_failure_even_if_shell_or_system_log_later_fails(self):
        for field in ("adb_handshake_completed", "shell_succeeded"):
            with self.subTest(field=field):
                record = tls_sample(accepted=False)
                record["consumer"][field] = True
                with self.assertRaises(RuntimeError):
                    _negative(record, REFERENCE_PEER)

    def test_contradictory_match_or_auth_bypass_cannot_pass_rejection(self):
        for field in ("tls_matched_identity", "auth_not_required"):
            with self.subTest(field=field):
                record = tls_sample(accepted=False)
                record["system"][field] = True
                with self.assertRaises(RuntimeError):
                    _negative(record, REFERENCE_PEER)

    def test_listener_restart_or_unavailable_port_cannot_pass_either_gate(self):
        for accepted, gate in ((True, _positive), (False, _negative)):
            for phase in ("peer_before", "peer_after"):
                for field, value in (("pid", "999"), ("listener_present", False), ("ro.adb.secure", "0")):
                    with self.subTest(accepted=accepted, phase=phase, field=field):
                        record = tls_sample(accepted=accepted)
                        record[phase][field] = value
                        with self.assertRaises(RuntimeError):
                            gate(record, REFERENCE_PEER)

    def test_stls_and_tls_metadata_must_belong_to_a_complete_observed_connection(self):
        for defect in ("missing_stls", "no_server_hello", "wrong_tls_version", "malformed_tls", "live_socket", "extra_connection"):
            with self.subTest(defect=defect):
                record = tls_sample(accepted=False)
                wire = record["wire"]
                server = wire["tls"]["1"]["adbd_to_host"]
                if defect == "missing_stls":
                    del wire["counts"]["host_to_adbd:STLS"]
                elif defect == "no_server_hello":
                    server["server_hello"] = []
                elif defect == "wrong_tls_version":
                    server["server_hello"][0]["selected_version"] = 0x303
                elif defect == "malformed_tls":
                    server["tls_parse_errors"] = ["malformed_server_hello"]
                elif defect == "live_socket":
                    wire["active_connections"] = 1
                else:
                    wire["connections"] = 2
                with self.assertRaises(RuntimeError):
                    _negative(record, REFERENCE_PEER)


if __name__ == "__main__":
    unittest.main()
