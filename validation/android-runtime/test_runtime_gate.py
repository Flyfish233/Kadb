"""Negative checks for false-positive instrumentation/DEX reports; no device used."""

import json
from pathlib import Path
import struct
import tempfile
import unittest
import zipfile

from inspect_apk import REQUIRED_CLASSES, inspect_apk
from run_android_runtime import EXPECTED_CHECKS, parse_instrumentation


class AndroidRuntimeGateTest(unittest.TestCase):
    def report(self):
        return {"status": "passed", "checks": EXPECTED_CHECKS, "checks_executed": len(EXPECTED_CHECKS),
                "physical_device": False, "device_kind": "android_emulator",
                "details": {"vm_name": "Dalvik", "bundled_conscrypt": False}}

    def output(self, report=None, code=-1):
        return ("INSTRUMENTATION_RESULT: kadb_runtime_json=" + json.dumps(report or self.report()) +
                f"\nINSTRUMENTATION_CODE: {code}\n")

    def test_complete_instrumentation_report_is_accepted(self):
        self.assertEqual(9, parse_instrumentation(self.output())["checks_executed"])

    def test_adb_exit_without_instrumentation_success_is_not_a_pass(self):
        for output in ("", "INSTRUMENTATION_FAILED: process crashed\n", self.output(code=0)):
            with self.subTest(output=output), self.assertRaises(RuntimeError):
                parse_instrumentation(output)

    def test_missing_or_duplicate_report_is_rejected(self):
        with self.assertRaises(RuntimeError):
            parse_instrumentation("INSTRUMENTATION_CODE: -1\n")
        with self.assertRaises(RuntimeError):
            parse_instrumentation(self.output() + self.output())

    def test_partial_or_failed_checks_are_rejected(self):
        for changes in ({"checks_executed": 0}, {"checks": EXPECTED_CHECKS[:-1]}, {"status": "failed"}):
            with self.subTest(changes=changes), self.assertRaises(RuntimeError):
                parse_instrumentation(self.output({**self.report(), **changes}))

    def test_host_provider_or_wrong_runtime_is_rejected(self):
        for details in ({"vm_name": "OpenJDK", "bundled_conscrypt": False},
                        {"vm_name": "Dalvik", "bundled_conscrypt": True}):
            with self.subTest(details=details), self.assertRaises(RuntimeError):
                parse_instrumentation(self.output({**self.report(), "details": details}))

    @staticmethod
    def dex(descriptors, include_definitions=True):
        count = len(descriptors)
        strings_at = 112
        types_at = strings_at + count * 4
        classes_at = types_at + count * 4
        data_at = classes_at + count * 32
        data = bytearray(data_at)
        data[:8] = b"dex\n035\0"
        struct.pack_into("<I", data, 40, 0x12345678)
        struct.pack_into("<II", data, 56, count, strings_at)
        struct.pack_into("<II", data, 64, count, types_at)
        struct.pack_into("<II", data, 96, count if include_definitions else 0, classes_at)
        for index, descriptor in enumerate(descriptors):
            struct.pack_into("<I", data, strings_at + index * 4, len(data))
            struct.pack_into("<I", data, types_at + index * 4, index)
            struct.pack_into("<I", data, classes_at + index * 32, index)
            raw = descriptor.encode()
            assert len(raw) < 128
            data += bytes([len(raw)]) + raw + b"\0"
        return data

    def inspect(self, descriptors, include_definitions=True):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "test.apk"
            with zipfile.ZipFile(path, "w") as archive:
                archive.writestr("classes.dex", self.dex(descriptors, include_definitions))
            return inspect_apk(path)

    def test_dex_class_definitions_are_required_not_strings(self):
        self.assertEqual("verified", self.inspect(sorted(REQUIRED_CLASSES))["status"])
        with self.assertRaisesRegex(ValueError, "lacks actual DEX class definitions"):
            self.inspect(sorted(REQUIRED_CLASSES), include_definitions=False)

    def test_host_only_reference_class_in_apk_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "Host-only Conscrypt"):
            self.inspect(sorted(REQUIRED_CLASSES | {"Lorg/conscrypt/OpenSSLProvider;"}))


if __name__ == "__main__":
    unittest.main()
