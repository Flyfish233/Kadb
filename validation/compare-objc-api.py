#!/usr/bin/env python3
"""Reject removed/changed Objective-C declarations in an exported framework.

Ignore generated comments/order and allow additions. This covers the actual
exported class/protocol, selector, property and Swift-name declarations; it is
complementary to the separately compiled and executed Swift consumer.
"""
import argparse
import json
from pathlib import Path
import re


def declarations(path):
    owner = None
    result = set()
    in_comment = False
    pending_attributes = []
    for raw in path.read_text().splitlines():
        line = raw.strip()
        if in_comment:
            if "*/" in line: in_comment = False
            continue
        if line.startswith("/*"):
            in_comment = "*/" not in line
            continue
        if not line or line.startswith("//"): continue
        if line.startswith("__attribute__") and owner is None:
            pending_attributes.append(line)
        elif line.startswith(("@interface ", "@protocol ")):
            owner = re.split(r"[ :<]", line.split(" ", 1)[1])[0]
            result.add((owner, line))
            result.update((owner, attribute) for attribute in pending_attributes)
            pending_attributes = []
        elif line == "@end":
            owner = None
        elif owner and line.startswith(("- (", "+ (", "@property")):
            result.add((owner, line))
        elif owner is None:
            pending_attributes = []
    if len(result) < 50:
        raise RuntimeError(f"Unexpectedly small exported API: {path}")
    return result


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("baseline", type=Path)
    p.add_argument("current", type=Path)
    p.add_argument("--report", type=Path, required=True)
    args = p.parse_args()
    before, after = declarations(args.baseline), declarations(args.current)
    missing, additions = sorted(before - after), sorted(after - before)
    report = {"baseline_declarations": len(before), "current_declarations": len(after),
              "removed_or_changed": missing, "additions": additions,
              "result": "FAIL" if missing else "PASS"}
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({k: v for k, v in report.items() if k not in ("removed_or_changed", "additions")}, indent=2))
    if missing:
        for owner, declaration in missing: print(owner, declaration)
        raise SystemExit(1)
