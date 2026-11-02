#!/usr/bin/env python3
"""Retain text/XML evidence from a digest-verified Actions artifact without copying binaries."""
from __future__ import annotations

import argparse
import datetime
import gzip
import hashlib
import json
from pathlib import Path, PurePosixPath
import zipfile


def digest(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def collect(archive: Path, metadata: dict, output: Path) -> dict:
    expected = metadata.get("digest", "")
    actual = "sha256:" + digest(archive)
    if expected != actual:
        raise ValueError(f"Artifact digest mismatch: expected {expected}, received {actual}")
    output.mkdir(parents=True, exist_ok=False)
    files = []
    omitted = []
    with zipfile.ZipFile(archive) as zipped:
        for item in zipped.infolist():
            path = PurePosixPath(item.filename)
            if path.is_absolute() or ".." in path.parts or "\\" in item.filename:
                raise ValueError(f"Unsafe artifact member: {item.filename}")
            if item.is_dir():
                continue
            in_evidence = path.parts[0] == "evidence"
            test_xml = "/build/test-results/" in item.filename and path.suffix == ".xml"
            resolution = item.filename.endswith("/reports/spake2-maven-resolution.json")
            public_header = "/Kadb.framework/" in item.filename and "/Headers/" in item.filename and path.suffix == ".h"
            text_file = path.suffix.lower() in {
                ".json", ".jsonl", ".log", ".txt", ".xml", ".properties",
                ".toml", ".api", ".abi", ".diff", ".h",
            }
            if not ((in_evidence and text_file) or test_xml or resolution or public_header):
                omitted.append({"path": item.filename, "bytes": item.file_size})
                continue
            data = zipped.read(item)
            # Preserve byte-identical originals. Large raw logs are losslessly
            # compressed to keep repeatable evidence suitable for Git.
            compressed = len(data) > 256 * 1024 and path.suffix in {".log", ".txt", ".jsonl"}
            destination = output.joinpath(*path.parts)
            if compressed:
                destination = destination.with_name(destination.name + ".gz")
            if destination.exists():
                raise ValueError(f"Duplicate retained artifact path: {item.filename}")
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(gzip.compress(data, mtime=0) if compressed else data)
            files.append({"archive_path": item.filename,
                          "retained_path": destination.relative_to(output).as_posix(),
                          "original_bytes": len(data), "original_sha256": hashlib.sha256(data).hexdigest(),
                          "storage": "gzip" if compressed else "original bytes",
                          "stored_sha256": digest(destination)})
    report = {
        "schema": 1, "collected_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "artifact": {key: value for key, value in metadata.items()
                     if key in {"id", "name", "size_in_bytes", "digest", "created_at", "expires_at", "workflow_run"}},
        "downloaded_zip_bytes": archive.stat().st_size,
        "downloaded_zip_sha256": actual.removeprefix("sha256:"),
        "artifact_digest_verified": True, "retained_files": files, "omitted_binary_or_archive_files": omitted,
        "scope": "Original text/XML evidence is retained. Large binaries and corresponding-source archives remain in the identified CI artifact.",
    }
    (output / "artifact-custody.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--metadata", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = collect(args.archive, json.loads(args.metadata.read_text()), args.output)
    print(json.dumps({"artifact_id": report["artifact"]["id"],
                      "sha256": report["downloaded_zip_sha256"],
                      "retained_files": len(report["retained_files"]),
                      "output": str(args.output)}))


if __name__ == "__main__":
    main()
