#!/usr/bin/env python3
"""Regression gate for the real API 35 Binder port response, not device evidence."""
import unittest

from tls_stage import parse_wireless_port, wireless_port


class WirelessPortTest(unittest.TestCase):
    def test_actual_service_call_single_line_port(self):
        self.assertEqual(parse_wireless_port("Result: Parcel(00000000 00008d4f   '....O...')\n"), 36175)

    def test_multiline_parcel_address_is_not_a_payload_word(self):
        self.assertEqual(parse_wireless_port("Result: Parcel(\n  0x00000000: 00000000 00008d4f   'deadbeef')\n"), 36175)

    def test_signed_minus_one_and_zero_are_explicit_inactive_states(self):
        self.assertEqual(parse_wireless_port("Result: Parcel(00000000 ffffffff '........')"), -1)
        self.assertEqual(parse_wireless_port("Result: Parcel(00000000 00000000 '........')"), 0)

    def test_valid_port_boundaries(self):
        self.assertEqual(parse_wireless_port("Result: Parcel(00000000 00000001)"), 1)
        self.assertEqual(parse_wireless_port("Result: Parcel(00000000 0000ffff)"), 65535)

    def test_denied_empty_exception_or_ambiguous_result_is_never_inactive(self):
        for reply in ("", "Permission Denial", "Result: Parcel()",
                      "Result: Parcel(00000000)", "Result: Parcel(ffffffff 00008d4f)",
                      "Result: Parcel(00000000 00008d4f 00000000)",
                      "Result: Parcel(00000000 fffffffe)",
                      "Result: Parcel(00000000 00010000)"):
            with self.subTest(reply=reply), self.assertRaises(RuntimeError):
                parse_wireless_port(reply)

    def test_query_uses_normal_api35_transaction_ten(self):
        class FakeRunner:
            def __init__(self):
                self.calls = []

            def binder(self, label, number):
                self.calls.append((label, number))
                return "Result: Parcel(00000000 00008d4f)"

        runner = FakeRunner()
        self.assertEqual(wireless_port(runner, "port-query"), 36175)
        self.assertEqual(runner.calls, [("port-query", 10)])


if __name__ == "__main__":
    unittest.main()
