#!/usr/bin/env python3
"""Prevent a matrix-job PASS or reconstructed AUTH3 string from overstating M4."""
from __future__ import annotations

import base64
import hashlib
import json
import struct
import unittest

from run_auth import aggregate_verdicts, apply_pending_confirmation, stage_scope


def report_for(selection):
    return {**stage_scope(selection), "sessions": [], "cleanup_errors": [], "cleanup_verdict": "PASS"}


class StageScopeTest(unittest.TestCase):
    def test_single_stage_success_is_ci_success_but_never_complete_m4_pass(self):
        for selection, selected, omitted in (("rsa", "M4-A", "M4-B"), ("tls", "M4-B", "M4-A")):
            with self.subTest(selection=selection):
                report = report_for(selection)
                report[selected]["verdict"] = "PASS"
                self.assertEqual([selected], report["requested_stages"])
                self.assertFalse(report["execution_scope"]["includes_all_required_stages"])
                self.assertEqual("not_executed", report[omitted]["status"])
                self.assertEqual("NOT VERIFIED", report[omitted]["verdict"])
                self.assertEqual(0, aggregate_verdicts(report))
                self.assertEqual("passed", report["status"])
                self.assertEqual("PASS", report["run_verdict"])
                self.assertEqual("NOT VERIFIED", report["verdict"])

    def test_stale_unselected_stage_pass_cannot_create_overall_m4_pass(self):
        report = report_for("tls")
        report["M4-A"]["verdict"] = "PASS"
        report["M4-B"]["verdict"] = "PASS"
        self.assertEqual(0, aggregate_verdicts(report))
        self.assertEqual("NOT VERIFIED", report["verdict"])

    def test_all_requires_both_real_stage_results(self):
        report = report_for("all")
        report["M4-A"]["verdict"] = "PASS"
        self.assertEqual(1, aggregate_verdicts(report))
        self.assertEqual("CONDITIONAL PASS", report["verdict"])
        self.assertNotEqual("PASS", report["run_verdict"])
        report["M4-B"]["verdict"] = "PASS"
        self.assertEqual(0, aggregate_verdicts(report))
        self.assertEqual("PASS", report["verdict"])

    def test_missing_selected_evidence_and_cleanup_failures_do_not_pass_ci(self):
        report = report_for("rsa")
        self.assertEqual(1, aggregate_verdicts(report))
        self.assertEqual("NOT VERIFIED", report["run_verdict"])
        for problem in ("cleanup_missing", "cleanup_error", "execution_error", "stage_error"):
            with self.subTest(problem=problem):
                report = report_for("rsa")
                report["M4-A"]["verdict"] = "PASS"
                if problem == "cleanup_missing":
                    report["cleanup_verdict"] = "NOT VERIFIED"
                elif problem == "cleanup_error":
                    report["cleanup_errors"].append({"step": "owned-key-removal"})
                elif problem == "execution_error":
                    report["error"] = "actual execution interrupted"
                else:
                    report["M4-A"]["execution_error"] = "stage raised after its nominal verdict"
                    report["M4-A"]["status"] = "failed"
                self.assertEqual(1, aggregate_verdicts(report))
                self.assertNotEqual("PASS", report["run_verdict"])
                self.assertEqual("NOT VERIFIED", report["verdict"])

    def test_unapproved_session_success_overrides_nominal_stage_pass(self):
        report = report_for("tls")
        report["M4-B"]["verdict"] = "PASS"
        report["sessions"] = [{"mode": "reject", "consumer": {"adb_handshake_completed": True}}]
        self.assertEqual(1, aggregate_verdicts(report))
        self.assertEqual("FAIL", report["run_verdict"])
        self.assertEqual("FAIL", report["verdict"])
        self.assertEqual("failed", report["status"])

    def test_explicit_stage_failure_and_invalid_scope_are_rejected(self):
        report = report_for("rsa")
        report["M4-A"]["verdict"] = "FAIL"
        self.assertEqual(1, aggregate_verdicts(report))
        self.assertEqual("FAIL", report["verdict"])
        for invalid in ([], ["M4-C"], ["M4-A", "M4-A"]):
            with self.subTest(invalid=invalid):
                report["requested_stages"] = invalid
                with self.assertRaises(ValueError):
                    aggregate_verdicts(report)


class FakeRelay:
    """The real relay independently validates the current AUTH token/signature."""
    def __init__(self, request):
        self.request = request
        self.taken = False

    def take_verified_public_key(self):
        if self.taken:
            raise RuntimeError("Current AUTH3 already consumed")
        self.taken = True
        return self.request


class FakeRunner:
    def __init__(self):
        self.calls = []

    def binder(self, *args):
        self.calls.append(args)


class PendingConfirmationTest(unittest.TestCase):
    def setUp(self):
        raw = struct.pack("<I", 64) + bytes(520)
        self.blob = base64.b64encode(raw).decode("ascii")
        self.other_blob = base64.b64encode(raw[:-1] + b"\x01").decode("ascii")
        self.request = self.blob + " Kadb@current-test-host"
        self.identity = {"blob": self.blob, "public": self.blob + " runner@keygen-host", "fingerprint": "fixture-md5"}

    def test_allow_uses_exact_observed_comment_and_reports_only_request_digests(self):
        runner, relay = FakeRunner(), FakeRelay(self.request)
        result = apply_pending_confirmation(runner, relay, "enroll-a", self.identity, "allow")
        self.assertEqual([("enroll-a-allow-normal-confirmation", 1, "i32", 1, "s16", self.request)], runner.calls)
        self.assertNotEqual(self.identity["public"], runner.calls[0][-1])
        self.assertEqual(hashlib.sha256((self.request + "\x00").encode()).hexdigest(), result["auth3_payload_sha256"])
        self.assertTrue(result["observed_request_used_verbatim_for_allow"])
        encoded = json.dumps(result)
        for secret in (self.blob, "Kadb@current-test-host", "runner@keygen-host"):
            self.assertNotIn(secret, encoded)
        with self.assertRaises(RuntimeError):
            apply_pending_confirmation(runner, relay, "repeat-a", self.identity, "allow")
        self.assertEqual(1, len(runner.calls))

    def test_deny_consumes_same_verified_request_without_sending_another_key(self):
        runner, relay = FakeRunner(), FakeRelay(self.request)
        result = apply_pending_confirmation(runner, relay, "deny-b", self.identity, "deny")
        self.assertEqual([("deny-b-deny-normal-confirmation", 2)], runner.calls)
        self.assertTrue(relay.taken)
        self.assertTrue(result["current_connection_AUTH3_matches_identity"])
        self.assertFalse(result["observed_request_used_verbatim_for_allow"])

    def test_wrong_key_or_malformed_auth3_cannot_reach_android_allow_or_deny(self):
        for request in (self.other_blob + " Kadb@wrong", self.request + "\x00", self.request + "\n",
                        self.request + "\r", "comment " + self.request, self.request + " \u00e9", ""):
            for action in ("allow", "deny"):
                with self.subTest(request_type=repr(request[-24:]), action=action):
                    runner = FakeRunner()
                    with self.assertRaises(RuntimeError):
                        apply_pending_confirmation(runner, FakeRelay(request), "current", self.identity, action)
                    self.assertEqual([], runner.calls)


if __name__ == "__main__":
    unittest.main()
