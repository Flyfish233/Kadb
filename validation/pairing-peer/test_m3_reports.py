"""Acceptance-gate regressions: incomplete/falsely attributed runtime evidence must fail."""

import copy
from pathlib import Path
import tempfile
import unittest

from run_interop import M3_CASES, M3_CLOSURE, M3_STAGES, preserve_process_reports, verify_reports


class M3ReportAcceptanceTest(unittest.TestCase):
    def complete_report(self):
        return {
            "native": {"status": "passed", "checks_executed": 13, "cases": list(M3_CASES), "real_adbd": False},
            "peer": {"status": "passed", "sessions_executed": 13, "completed_sessions": 13,
                     "positive_sessions": 2, "expected_negative_sessions": 11, "real_adbd": False,
                     "negative_sessions_completed": 11, "tls_sessions_completed": 13,
                     "cases": [{"case": case, "status": "passed", "stage": M3_STAGES[case],
                                "closure": M3_CLOSURE[case]} for case in M3_CASES]},
        }

    def test_requires_all_actual_native_and_peer_sessions(self):
        report = self.complete_report()
        verify_reports(report, True)
        for side in ("native", "peer"):
            with self.subTest(side=side):
                incomplete = copy.deepcopy(report)
                incomplete[side]["cases"].pop()
                with self.assertRaises(RuntimeError):
                    verify_reports(incomplete, True)

    def test_generic_network_error_cannot_replace_gcm_failure_evidence(self):
        report = self.complete_report()
        for case in report["peer"]["cases"]:
            if case["case"] == "stale_exporter":
                case["stage"] = "network_failure"
        with self.assertRaises(RuntimeError):
            verify_reports(report, True)

    def test_controlled_peer_cannot_be_labelled_real_adbd(self):
        for side in ("native", "peer"):
            with self.subTest(side=side):
                report = self.complete_report()
                report[side]["real_adbd"] = True
                with self.assertRaises(RuntimeError):
                    verify_reports(report, True)

    def test_default_m2_two_session_contract_is_unchanged(self):
        verify_reports({"native": {"status": "passed", "checks_executed": 2},
                        "peer": {"status": "passed", "sessions_executed": 2,
                                 "positive_sessions": 1, "wrong_code_rejections": 1}}, False)

    def test_early_native_failure_preserves_actual_partial_counts(self):
        with tempfile.TemporaryDirectory() as directory:
            native = Path(directory) / "native.log"
            peer = Path(directory) / "peer.log"
            native.write_text('KADB_NATIVE_PAIRING_JSON {"status":"failed","checks_executed":4}\n')
            peer.write_text('KADB_PAIRING_CASE_JSON {"case":"positive_seed","status":"passed"}\n')
            report = {}
            preserve_process_reports(report, native, peer)
            self.assertEqual(report["native"]["checks_executed"], 4)
            self.assertNotIn("peer", report)
            self.assertIn("peer", report["result_record_errors"])
            self.assertEqual(len(report["peer_completed_case_records"]), 1)

    def test_peer_closure_cannot_be_relabelled_client_cleanup(self):
        report = self.complete_report()
        report["peer"]["cases"][1]["closure"] = "client_initiated"
        with self.assertRaises(RuntimeError):
            verify_reports(report, True)


if __name__ == "__main__":
    unittest.main()
