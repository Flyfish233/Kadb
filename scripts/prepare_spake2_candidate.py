#!/usr/bin/env python3
"""Restore the committed fixed Maven candidate without network access.

--output names the parent directory; the Maven repository is OUTPUT/maven.
On success stdout contains only that repository's absolute path. Existing
repositories must match every locked file and are never repaired or overwritten.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import sys
import tarfile
import tempfile

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = ROOT / "validation/maven-candidate/manifest.json"
VERSION = "0.1.0-dev.59105290820b"
REVISION = "59105290820bcbfd4e0336a2e7713006a461527f"
ORIGINAL_ARTIFACT_SHA256 = "29fe208f315ea08c9643d4388df8d832b984b04270fd39e55d00328ed4746ac3"


class CandidateError(ValueError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise CandidateError(message)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def unique_object(pairs: list[tuple[str, object]]) -> dict:
    result = {}
    for key, value in pairs:
        require(key not in result, f"Duplicate manifest key: {key}")
        result[key] = value
    return result


def safe_relative(value: str) -> str:
    require(isinstance(value, str) and value and "\\" not in value and "\x00" not in value,
            f"Invalid candidate path: {value!r}")
    path = PurePosixPath(value)
    require(not path.is_absolute() and ".." not in path.parts and path.as_posix() == value
            and path.parts and path.parts[0] != ".", f"Unsafe candidate path: {value!r}")
    return value


def load_manifest(path: Path) -> tuple[dict, dict[str, dict]]:
    manifest = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=unique_object)
    require(isinstance(manifest, dict), "Candidate manifest must be an object")
    require(manifest.get("schemaVersion") == 1, "Unsupported candidate manifest schema")
    require(manifest.get("version") == VERSION and manifest.get("revision") == REVISION,
            "Wrong fixed candidate version or source revision")
    require(manifest.get("sourceGitHubArtifactSha256") == ORIGINAL_ARTIFACT_SHA256
            and manifest.get("sourceGitHubArtifactId") == 12682137388
            and manifest.get("sourceGitHubRunId") == 40388080222,
            "Wrong fixed GitHub candidate identity")
    require(re.fullmatch(r"[0-9a-f]{64}", str(manifest.get("sha256", ""))) is not None,
            "Invalid candidate archive digest")
    archive_name = safe_relative(manifest.get("archive", ""))
    require("/" not in archive_name, "Archive filename must be a basename")
    files = manifest.get("files")
    require(isinstance(files, list) and len(files) == manifest.get("fileCount") == 219,
            "The complete fixed Maven candidate must contain exactly 219 files")
    inventory = {}
    for item in files:
        require(isinstance(item, dict), "Invalid candidate file entry")
        name = safe_relative(item.get("path", ""))
        require(name not in inventory, f"Duplicate candidate file: {name}")
        require(isinstance(item.get("size"), int) and not isinstance(item["size"], bool)
                and item["size"] >= 0, f"Invalid file size: {name}")
        require(re.fullmatch(r"[0-9a-f]{64}", str(item.get("sha256", ""))) is not None,
                f"Invalid file digest: {name}")
        inventory[name] = item
    require(sum(item["size"] for item in inventory.values()) == manifest.get("totalFileBytes"),
            "Candidate aggregate file size mismatch")
    summary = manifest.get("publicationValidation", {})
    require(summary.get("status") == "passed" and summary.get("publicationCount") == 33
            and summary.get("androidIncluded") is True and summary.get("revision") == REVISION
            and summary.get("version") == VERSION,
            "Missing complete fixed-candidate publication validation identity")
    return manifest, inventory


def verify_archive(archive: Path, manifest: dict, inventory: dict[str, dict]) -> bytes:
    require(archive.is_file() and not archive.is_symlink(), "Candidate archive must be a regular file")
    require(archive.stat().st_size == manifest.get("size"), "Candidate archive size mismatch")
    raw = archive.read_bytes()
    require(hashlib.sha256(raw).hexdigest() == manifest["sha256"], "Candidate archive SHA-256 mismatch")
    seen = set()
    with tarfile.open(fileobj=io.BytesIO(raw), mode="r:xz") as source:
        for member in source:
            name = safe_relative(member.name)
            require(member.isfile(), f"Non-regular archive member prohibited: {name}")
            require(name.startswith("maven/"), f"Wrong archive root: {name}")
            relative = name[len("maven/"):]
            require(relative in inventory, f"Unexpected candidate archive file: {name}")
            require(relative not in seen, f"Duplicate candidate archive file: {name}")
            seen.add(relative)
            locked = inventory[relative]
            require(member.size == locked["size"], f"Candidate file size mismatch: {relative}")
            require(member.uid == member.gid == member.mtime == 0 and member.mode == 0o644
                    and member.uname == member.gname == "", f"Noncanonical archive metadata: {name}")
            stream = source.extractfile(member)
            require(stream is not None, f"Unreadable candidate archive file: {name}")
            digest = hashlib.sha256(stream.read()).hexdigest()
            require(digest == locked["sha256"], f"Candidate file SHA-256 mismatch: {relative}")
    require(seen == set(inventory), f"Incomplete candidate archive: missing {sorted(set(inventory)-seen)}")
    return raw


def check_no_symlink_parents(path: Path) -> None:
    for part in (path, *path.parents):
        require(not part.is_symlink(), f"Symlink output path prohibited: {part}")


def verify_repository(repository: Path, inventory: dict[str, dict]) -> None:
    require(repository.is_dir() and not repository.is_symlink(),
            f"Existing candidate output is not a real directory: {repository}")
    expected_dirs = {parent.as_posix() for name in inventory for parent in PurePosixPath(name).parents
                     if parent.as_posix() != "."}
    found = set()
    for directory, directories, files in os.walk(repository, followlinks=False):
        for name in directories:
            path = Path(directory) / name
            relative = path.relative_to(repository).as_posix()
            require(not path.is_symlink() and relative in expected_dirs,
                    f"Unexpected directory or symlink in existing candidate: {relative}")
        for name in files:
            path = Path(directory) / name
            relative = path.relative_to(repository).as_posix()
            require(not path.is_symlink() and path.is_file() and relative in inventory,
                    f"Unexpected file or symlink in existing candidate: {relative}")
            locked = inventory[relative]
            require(path.stat().st_size == locked["size"] and sha256(path) == locked["sha256"],
                    f"Existing candidate differs; refusing overwrite: {relative}")
            found.add(relative)
    require(found == set(inventory), "Existing candidate is incomplete; refusing overwrite")


def prepare(manifest_path: Path, archive: Path | None, output: Path) -> Path:
    manifest, inventory = load_manifest(manifest_path)
    archive = archive if archive is not None else manifest_path.parent / manifest["archive"]
    raw = verify_archive(archive, manifest, inventory)
    output = Path(os.path.abspath(output))
    check_no_symlink_parents(output)
    repository = output / "maven"
    if os.path.lexists(repository):
        verify_repository(repository, inventory)
        return repository
    output.mkdir(parents=True, exist_ok=True)
    lock = output / ".prepare-spake2-candidate.lock"
    try:
        descriptor = os.open(lock, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError as error:
        raise CandidateError(f"Candidate preparation already in progress: {lock}") from error
    try:
        os.close(descriptor)
        # Recheck under the preparation lock before writing a new directory.
        if os.path.lexists(repository):
            verify_repository(repository, inventory)
            return repository
        with tempfile.TemporaryDirectory(prefix=".spake2-candidate-", dir=output) as temporary:
            temporary = Path(temporary)
            with tarfile.open(fileobj=io.BytesIO(raw), mode="r:xz") as source:
                for member in source:
                    # This immutable byte snapshot was verified above. No extractall(),
                    # links, special files, or tar-provided ownership is used.
                    path = temporary / member.name
                    path.parent.mkdir(parents=True, exist_ok=True)
                    with path.open("xb") as target:
                        target.write(source.extractfile(member).read())
                    path.chmod(0o644)
            verify_repository(temporary / "maven", inventory)
            require(not os.path.lexists(repository), "Candidate output appeared concurrently; refusing overwrite")
            os.rename(temporary / "maven", repository)
    finally:
        lock.unlink()
    return repository


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--archive", type=Path)
    parser.add_argument("--output", type=Path, default=ROOT / "build/spake2-candidate",
                        help="Parent directory; the verified Maven repository will be OUTPUT/maven")
    args = parser.parse_args()
    try:
        repository = prepare(args.manifest, args.archive, args.output)
    except (CandidateError, OSError, ValueError, tarfile.TarError) as error:
        print(f"SPAKE2 candidate preparation failed: {error}", file=sys.stderr)
        return 1
    print(repository)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
