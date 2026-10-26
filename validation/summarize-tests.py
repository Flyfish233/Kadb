#!/usr/bin/env python3
"""Make executed tests, failures, and opt-in/non-executed checks explicit.

A successful Gradle process without XML test cases is not test evidence.
Hardware opt-in tests from the baseline return normally when unconfigured;
their suites are reported separately and never establish device coverage.
"""
import argparse
import json
from pathlib import Path
import xml.etree.ElementTree as ET


def summarize(root: Path) -> dict:
    suites = []
    for path in sorted(root.glob("**/build/test-results/**/TEST-*.xml")):
        xml = ET.parse(path).getroot()
        output = "\n".join(node.text or "" for node in xml.findall("system-out"))
        # The frozen interop test silently returns without KADB_JVM_PAIRING_PORT.
        # Its JUnit success is not execution proof. Dedicated mandatory CLI
        # consumers now provide separate, explicit interoperability reports.
        known_optional = any(name in xml.attrib.get("name", "") for name in
                             ("JvmPairingInteropTest", "RealDeviceSmokeTest"))
        opt_in_missing = known_optional or "SKIP:" in output or "Skipping" in output
        cases = xml.findall("testcase")
        failed = sum(case.find("failure") is not None or case.find("error") is not None for case in cases)
        skipped = sum(case.find("skipped") is not None for case in cases)
        suites.append({
            "file": str(path.relative_to(root)),
            "suite": xml.attrib.get("name"),
            "cases": len(cases),
            "failed": failed,
            "skipped": skipped,
            "opt_in_not_executed": opt_in_missing,
            "executed": 0 if opt_in_missing else len(cases) - skipped,
        })
    return {"suites": suites, "executed": sum(s["executed"] for s in suites),
            "failed": sum(s["failed"] for s in suites),
            "device_coverage": "Not established by this summary; requires explicit device evidence."}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--require", action="append", default=[], help="Required XML path substring")
    args = parser.parse_args()
    result = summarize(args.root)
    missing = [item for item in args.require
               if not any(item in s["file"] and s["executed"] > 0 for s in result["suites"])]
    result["missing_required_test_groups"] = missing
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({key: value for key, value in result.items() if key != "suites"}, indent=2))
    raise SystemExit(1 if result["failed"] or not result["executed"] or missing else 0)
