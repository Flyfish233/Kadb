#!/usr/bin/env python3
"""Compare the fixed candidate's complete-source ZIPs with immutable Git blobs.

Usage: python3 verify_candidate_source.py MAVEN_REPOSITORY SPAKE2_GIT_CHECKOUT OUTPUT
The producer's distribution intentionally excludes only .gitignore at this revision.
"""
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
import hashlib
import io
import json
import subprocess
import sys
import tarfile
import zipfile

REVISION = "59105290820bcbfd4e0336a2e7713006a461527f"
VERSION = "0.1.0-dev.59105290820b"
MODULES = ("spake2", "spake2-legacy", "spake2-primitives")


def verify(repository: Path, checkout: Path) -> dict:
    git_archive = subprocess.check_output(["git", "-C", str(checkout), "archive", REVISION])
    with tarfile.open(fileobj=io.BytesIO(git_archive)) as source:
        git_files = {member.name: source.extractfile(member).read()
                     for member in source.getmembers() if member.isfile()}
    expected = set(git_files) - {".gitignore"}
    archives = []
    previous_hash = None
    for module in MODULES:
        relative = Path("io/github/flyfish233") / module / VERSION / f"{module}-{VERSION}-source-distribution.zip"
        raw = (repository / relative).read_bytes()
        sha256 = hashlib.sha256(raw).hexdigest()
        with zipfile.ZipFile(io.BytesIO(raw)) as source:
            members = [member for member in source.infolist() if not member.is_dir()]
            names = [member.filename for member in members]
            if len(set(names)) != len(names):
                raise ValueError(f"Duplicate source paths: {relative}")
            if set(names) != expected:
                raise ValueError(f"Wrong source inventory: {relative}; missing={sorted(expected-set(names))}, extra={sorted(set(names)-expected)}")
            for member in members:
                name = member.filename
                if PurePosixPath(name).is_absolute() or ".." in PurePosixPath(name).parts:
                    raise ValueError(f"Unsafe source member: {name}")
                if source.read(member) != git_files[name]:
                    raise ValueError(f"Source differs from fixed Git blob: {relative}: {name}")
        archives.append({"archive": relative.as_posix(), "sha256": sha256,
                         "comparedFiles": len(names), "mismatches": [],
                         "untrackedExtras": [], "sameBytesAsPreviousArchive": previous_hash == sha256 if previous_hash else None})
        previous_hash = sha256
    return {"schemaVersion": 1, "status": "PASS", "executedAtUtc": datetime.now(timezone.utc).isoformat(),
            "sourceRevision": REVISION, "version": VERSION,
            "comparison": "ZIP member bytes independently compared against git archive of the immutable source commit",
            "gitTrackedFiles": len(git_files), "excludedTrackedFiles": [".gitignore"],
            "archives": archives,
            "limitations": "Source identity and archive completeness only; not a new binary reproducibility, compiler, or cryptographic audit."}


if __name__ == "__main__":
    if len(sys.argv) != 4:
        raise SystemExit(__doc__)
    result = verify(Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve())
    Path(sys.argv[3]).write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(f"PASS: {len(result['archives'])} complete-source ZIPs; {result['archives'][0]['comparedFiles']} Git-matching files per archive")
