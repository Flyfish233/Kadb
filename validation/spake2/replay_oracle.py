#!/usr/bin/env python3
"""Re-execute immutable historical fixtures with an external pinned C oracle.

This executes a test-only binary built from legacy_oracle.cc, not any Kotlin
implementation. A nonzero exit code or any byte mismatch is a failing check.
"""
import argparse
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
EXPECTED_FIXTURE_SHA256 = "94ed5b9c564794eac6d2494966ff3ae479d872171f6a70286f504cbe4bfe8d94"


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--oracle", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--reference-source", type=Path, required=True)
    parser.add_argument("--reference-commit", required=True)
    parser.add_argument("--libcrypto", type=Path, required=True)
    parser.add_argument("--prefix", default="KADB_BSSL")
    parser.add_argument("--cxx", default="c++")
    args = parser.parse_args()
    source = args.reference_source.resolve()
    build_command = [args.cxx, "-std=c++17", "-O2", f"-DBORINGSSL_PREFIX={args.prefix}",
                     f"-I{source}", f"-I{source / 'include'}", str(ROOT / "legacy_oracle.cc"),
                     str(args.libcrypto.resolve()), "-lpthread", "-o", str(args.oracle.resolve())]
    subprocess.run(build_command, check=True, timeout=60)
    fixture = ROOT / "boringssl-spake2-vectors.json"
    if sha256(fixture) != EXPECTED_FIXTURE_SHA256:
        raise SystemExit("Refusing an altered independent fixture")
    corpus = json.loads(fixture.read_text())
    requests, expected, names = [], [], []
    for exchange in corpus["exchanges"]:
        for role, peer_role in (("alice", "bob"), ("bob", "alice")):
            endpoint, peer = exchange[role], exchange[peer_role]
            generated = endpoint["generate"]
            result = exchange[role + "Process"]
            requests.append("|".join([
                role, endpoint["myNameHex"], endpoint["theirNameHex"],
                endpoint["passwordHex"], generated["privateInput64Hex"],
                str(int(endpoint["disablePasswordScalarHack"])), peer["generate"]["messageHex"]
            ]))
            expected.append([
                generated["messageHex"], generated["privateScalarHex"],
                generated["passwordScalarHex"], generated["passwordHashHex"],
                str(int(result["success"])), result["keyHex"]
            ])
            names.append(f"{exchange['id']}/{role}")
    normal = corpus["exchanges"][0]["alice"]
    generated = normal["generate"]
    for case in corpus["processCases"]:
        requests.append("|".join([
            "alice", normal["myNameHex"], normal["theirNameHex"], normal["passwordHex"],
            generated["privateInput64Hex"], "0", case["process"]["theirMessageHex"]
        ]))
        expected.append([
            generated["messageHex"], generated["privateScalarHex"],
            generated["passwordScalarHex"], generated["passwordHashHex"],
            str(int(case["process"]["success"])), case["process"]["keyHex"]
        ])
        names.append(case["id"])
    completed = subprocess.run([str(args.oracle.resolve())], input="\n".join(requests) + "\n",
                               text=True, capture_output=True, check=True, timeout=60)
    actual = [line.split("|") for line in completed.stdout.splitlines()]
    if len(actual) != len(expected):
        raise SystemExit(f"Oracle result count differs: {len(actual)} != {len(expected)}")
    for name, observed, wanted in zip(names, actual, expected):
        if observed != wanted:
            raise SystemExit(f"Independent C oracle differs from fixture: {name}")
    report = {
        "executed_at_utc": datetime.now(timezone.utc).isoformat(),
        "result": "PASS: every observed C-oracle byte matched the immutable external fixture",
        "scope": "C reference reexecution; Kotlin consumer tests are recorded separately",
        "fixture_reference_commit": corpus["boringsslCommit"],
        "executed_reference_commit": args.reference_commit,
        "reference_spake_source_sha256": sha256(source / "crypto/curve25519/spake25519.cc"),
        "reference_crypto_archive_sha256": sha256(args.libcrypto),
        "build_command": build_command,
        "fixture_sha256": sha256(fixture),
        "harness_sha256": sha256(ROOT / "legacy_oracle.cc"),
        "executable_sha256": sha256(args.oracle),
        "exchanges": len(corpus["exchanges"]),
        "endpoint_exchange_results": len(corpus["exchanges"]) * 2,
        "peer_input_cases": len(corpus["processCases"]),
        "oracle_exit_code": completed.returncode,
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
