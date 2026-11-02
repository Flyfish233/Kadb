#!/usr/bin/env python3
"""Retain observed Darwin phase outcomes; never turn a skipped execution into PASS."""
from __future__ import annotations

import argparse
import datetime
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import platform
import subprocess

ROOT = Path(__file__).resolve().parents[3]


def tests(target: str) -> tuple[dict, int]:
    spec = importlib.util.spec_from_file_location("existing_test_summary", ROOT / "validation/summarize-tests.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    result = module.summarize(ROOT)
    required = [f"{project}/build/test-results/{target}Test/" for project in ("kadb", "kadb-mdns")]
    result["suites"] = [suite for suite in result["suites"] if any(group in suite["file"] for group in required)]
    result["target"] = target
    result["executed"] = sum(suite["executed"] for suite in result["suites"])
    result["failed"] = sum(suite["failed"] for suite in result["suites"])
    result["skipped"] = sum(suite["skipped"] for suite in result["suites"] if not suite["opt_in_not_executed"])
    result["missing_required_test_groups"] = [group for group in required if not any(
        group in suite["file"] and suite["executed"] > 0 for suite in result["suites"])]
    failed = bool(result["failed"] or result["skipped"] or result["missing_required_test_groups"])
    result["verdict"] = "FAIL" if failed else "PASS"
    result["scope"] = "Executed product regressions only; optional baseline interop/device suites do not count."
    return result, int(failed)


def verdict() -> tuple[dict, int]:
    steps = json.loads(os.environ["M2_STEPS_JSON"])
    target = os.environ["M2_TARGET"]
    required = ["candidate", "environment", "compile", "link", "tests", "test_evidence", "protocol", "api", "framework", "source"]
    required += ["simulator"] if os.environ["M2_PLATFORM"] == "ios-simulator" else ["swift"]
    if target == "iosSimulatorArm64":
        required.append("ios_device_framework")
    phases = {name: {"outcome": steps.get(name, {}).get("outcome", "not_run"),
                     "verdict": {"success": "PASS", "failure": "FAIL"}.get(
                         steps.get(name, {}).get("outcome"), "NOT VERIFIED")} for name in required}
    binaries = []
    for project in ("kadb", "kadb-mdns", "validation/native-adbd"):
        folder = ROOT / project / "build/bin" / target
        for path in sorted(folder.rglob("*")):
            if path.is_file() and not path.is_symlink():
                with path.open("rb") as stream:
                    digest = hashlib.file_digest(stream, "sha256").hexdigest()
                binaries.append({"path": str(path.relative_to(ROOT)), "bytes": path.stat().st_size, "sha256": digest})
    statuses = {phase["verdict"] for phase in phases.values()}
    result = {"schema": 1, "recorded_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
              "head_sha": os.environ.get("GITHUB_SHA"), "run_id": os.environ.get("GITHUB_RUN_ID"),
              "run_attempt": os.environ.get("GITHUB_RUN_ATTEMPT"), "target": target,
              "runner_label": os.environ["M2_RUNNER"], "host_machine": platform.machine(),
              "expected_architecture": os.environ["M2_ARCHITECTURE"], "host_platform": platform.platform(),
              "image_os": os.environ.get("ImageOS"), "image_version": os.environ.get("ImageVersion"),
              "candidate_version": "0.1.0-dev.59105290820b", "phases": phases, "binaries": binaries,
              "verdict": "FAIL" if "FAIL" in statuses else "NOT VERIFIED" if "NOT VERIFIED" in statuses else "PASS",
              "failure_attribution": "Observed stage outcome only. Migration regression attribution requires baseline comparison.",
              "scope": {"real_device": False, "external_adbd_matrix": False}}
    summary = ROOT / "evidence/test-summary.json"
    if summary.is_file():
        result["test_summary"] = json.loads(summary.read_text())
    result["tracked_worktree_changes"] = subprocess.run(
        ["git", "status", "--porcelain=v1", "--untracked-files=no"], cwd=ROOT,
        text=True, capture_output=True, check=True).stdout
    return result, 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("tests", "verdict"))
    parser.add_argument("--target")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.mode == "tests" and not args.target:
        parser.error("tests requires --target")
    result, code = tests(args.target) if args.mode == "tests" else verdict()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({key: result[key] for key in ("target", "verdict", "executed", "failed", "skipped") if key in result}))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
