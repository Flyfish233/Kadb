#!/usr/bin/env python3
"""Collect fixed Native and validation Android runtime sources; never publish.

Python 3.11+ standard library only. The bundle is an engineering source inventory,
not a legal certification, a general Android application bundle, or a toolchain image.
"""

from __future__ import annotations

import argparse
import datetime
import gzip
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import posixpath
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import tomllib
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
import zipfile


ROOT = Path(__file__).resolve().parent.parent
SUPPORT = (Path(__file__).resolve().parent if (Path(__file__).resolve().parent / "dependencies.lock.json").is_file()
           else ROOT / "validation/source-bundle")
CHUNK = 1024 * 1024
NOTICE_LIMIT = 16 * CHUNK
HEX_SHA = re.compile(r"[0-9a-f]{64}\Z")
ANDROID_SCOPE = "experimental-native-and-android-validation-runtime"


def digest(path: Path) -> str:
    result = hashlib.sha256()
    with path.open("rb") as source:
        while block := source.read(CHUNK):
            result.update(block)
    return result.hexdigest()


def json_bytes(value) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode()


def relative_name(name: str) -> str:
    path = PurePosixPath(name)
    if not name or path.is_absolute() or ".." in path.parts or "\\" in name:
        raise ValueError(f"Unsafe archive-relative path: {name!r}")
    return path.as_posix()


def git(repo: Path, *arguments: str) -> bytes:
    return subprocess.check_output(["git", "-C", str(repo), *arguments], stderr=subprocess.PIPE)


def check_project(repo: Path, revision: str, lock: dict) -> tuple[str, int]:
    commit = git(repo, "rev-parse", "--verify", revision + "^{commit}").decode().strip()
    if not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise ValueError("Expected an immutable Git SHA-1 commit")
    catalog = tomllib.loads(git(repo, "show", commit + ":gradle/libs.versions.toml").decode())
    version_keys = ["kotlin", "kotlinxCoroutinesCore", "okio"]
    if lock["scope"] == ANDROID_SCOPE:
        version_keys += ["bc", "documentfile", "hiddenapibypass"]
        check_android_project_sources(repo, commit, lock)
    for key in version_keys:
        if catalog["versions"][key] != lock["versions"][key]:
            raise ValueError(f"Source lock does not cover project version {key}={catalog['versions'][key]}")
    native = git(repo, "show", commit + ":kadb/gradle/ios-native.gradle.kts").decode()
    boring = next(entry for entry in lock["entries"] if entry["id"] == "boringssl")
    if lock["boringssl_revision"] not in native or boring["sha256"] not in native:
        raise ValueError("Source lock does not match the project's BoringSSL revision/checksum")
    spake = git(repo, "show", commit + ":third-party/spake2/UPSTREAM_COMMIT").decode().strip()
    if spake != lock["spake2_revision"]:
        raise ValueError("Source lock does not match the vendored Legacy revision")
    epoch = int(git(repo, "show", "-s", "--format=%ct", commit).decode())
    return commit, epoch


def check_android_project_sources(repo: Path, commit: str, lock: dict) -> None:
    required = lock["android_runtime"]["required_project_files"]
    if not required:
        raise ValueError("Android source scope requires the consumer's project files")
    for name in required:
        relative_name(name)
        try:
            content = git(repo, "show", commit + ":" + name)
        except subprocess.CalledProcessError as error:
            raise ValueError(f"Android consumer source is absent from {commit}: {name}") from error
        if not content:
            raise ValueError(f"Android consumer source is empty in {commit}: {name}")


def checked_file(path: Path, entry: dict) -> None:
    if not path.is_file() or path.stat().st_size != entry["size"] or digest(path) != entry["sha256"]:
        raise ValueError(f"Size/SHA-256 mismatch: {entry['id']}")


def fetch(entry: dict, cache: Path, offline: bool, boring_archive: Path | None, emit) -> Path:
    name = entry["sha256"] + "-" + PurePosixPath(entry["path"]).name
    cached = cache / name
    if cached.exists():
        # Do not silently replace a corrupt cache entry and hide the integrity failure.
        checked_file(cached, entry)
        emit("cache_verified", component=entry["id"], bytes=entry["size"])
        return cached
    if entry["id"] == "boringssl" and boring_archive is not None:
        checked_file(boring_archive, entry)
        shutil.copyfile(boring_archive, cached)
        emit("build_archive_verified", component=entry["id"], bytes=entry["size"])
        return cached
    if offline:
        raise FileNotFoundError(f"Offline source cache is missing {entry['id']}")
    if not entry["url"].startswith("https://"):
        raise ValueError("Only HTTPS sources are supported")
    temporary = cached.with_name(cached.name + f".download-{os.getpid()}")
    for attempt in range(1, 4):
        try:
            request = urllib.request.Request(entry["url"], headers={"User-Agent": "Kadb-source-bundle/1"})
            with urllib.request.urlopen(request, timeout=30) as response, temporary.open("wb") as output:
                if not response.geturl().startswith("https://"):
                    raise ValueError("Source download redirected away from HTTPS")
                received = 0
                while block := response.read(CHUNK):
                    received += len(block)
                    if received > entry["size"]:
                        raise ValueError(f"Download exceeds locked size: {entry['id']}")
                    output.write(block)
            checked_file(temporary, entry)
            temporary.replace(cached)
            emit("download_verified", component=entry["id"], bytes=entry["size"], sha256=entry["sha256"])
            return cached
        except urllib.error.HTTPError as error:
            if attempt == 3 or error.code not in (408, 429, 500, 502, 503, 504):
                raise
            emit("download_retry", component=entry["id"], attempt=attempt, error=str(error))
        except (urllib.error.URLError, TimeoutError) as error:
            if attempt == 3:
                raise
            emit("download_retry", component=entry["id"], attempt=attempt, error=str(error))
        finally:
            temporary.unlink(missing_ok=True)
    raise AssertionError("Unreachable download retry state")


def is_notice(name: str) -> bool:
    path = PurePosixPath(name)
    if any(part.lower() in ("license", "licenses", "licence", "licences", "notices") for part in path.parts):
        return True
    return path.name.lower().startswith(("license", "licence", "notice", "copying", "copyright", "authors"))


def inspect_archive(archive: Path, component: str, destination: Path, required: list[str], *,
                    strip_root: bool = True, require_notice: bool = True) -> dict:
    seen = set()
    notices = []
    sources = 0
    native_runtime_sources = 0
    with tarfile.open(archive, "r|*") as source:
        for member in source:
            name = relative_name(member.name)
            # Upstream GitHub archives and the Kadb Git archive have one root directory.
            relative = name.partition("/")[2] if strip_root else name
            if member.isfile():
                if relative in seen:
                    raise ValueError(f"Duplicate archive member in {component}: {relative}")
                seen.add(relative)
                if relative.endswith((".kt", ".java", ".cpp", ".cc", ".c", ".h", ".hpp")):
                    sources += 1
                    if relative.startswith("kotlin-native/runtime/") and relative.endswith((".cpp", ".cc", ".c", ".h")):
                        native_runtime_sources += 1
                if is_notice(relative):
                    if member.size > NOTICE_LIMIT:
                        raise ValueError(f"Notice exceeds safety limit; review it explicitly: {name}")
                    content = source.extractfile(member).read()
                    target = destination / "notices" / component / relative_name(relative)
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(content)
                    notices.append({"archive_member": name, "bundle_path": target.relative_to(destination).as_posix(),
                                    "sha256": hashlib.sha256(content).hexdigest(), "size": len(content)})
            # Keep the streaming tar reader's metadata memory bounded for the Kotlin repository.
            source.members.clear()
    missing = set(required) - seen
    if missing or not sources or (require_notice and not notices):
        raise ValueError(f"Incomplete {component} source archive: missing={sorted(missing)}, sources={sources}, notices={len(notices)}")
    if component == "kotlin" and native_runtime_sources == 0:
        raise ValueError("Kotlin archive lacks Native C/C++ runtime sources")
    return {"component": component, "source_files": sources, "native_runtime_source_files": native_runtime_sources,
            "notices": notices}


def inspect_maven(entry: dict, path: Path, destination: Path | None = None) -> dict:
    with zipfile.ZipFile(path) as source:
        if source.testzip() is not None:
            raise ValueError(f"Damaged sources jar: {entry['id']}")
        names = [relative_name(info.filename) for info in source.infolist() if not info.is_dir()]
        if len(names) != len(set(names)):
            raise ValueError(f"Duplicate sources jar member: {entry['id']}")
        count = sum(name.endswith((".kt", ".java", ".c", ".h", ".cpp")) for name in names)
        if count != entry["source_entries"] or not count:
            raise ValueError(f"Unexpected source inventory: {entry['id']}")
        notices = []
        if destination is not None:
            for name in names:
                if not is_notice(name):
                    continue
                if source.getinfo(name).file_size > NOTICE_LIMIT:
                    raise ValueError(f"Maven notice exceeds safety limit: {name}")
                content = source.read(name)
                target = destination / "notices" / entry["path"] / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(content)
                notices.append({"archive_member": name, "bundle_path": target.relative_to(destination).as_posix(),
                                "sha256": hashlib.sha256(content).hexdigest(), "size": len(content)})
        return {"coordinate": entry["coordinate"], "path": entry["path"], "source_files": count,
                "source_sets": entry["source_sets"], "notices": notices,
                "metadata_verification": entry.get("metadata_verification", "gradle-module")}


def verify_module_sources(lock: dict, bundle: Path) -> None:
    by_path = {entry["path"]: entry for entry in lock["entries"]}
    published_sources = set()
    pom_coordinates = set()

    def coordinate(component: dict) -> str:
        return ":".join(component[key] for key in ("group", "module", "version"))

    def relative_artifact(base: str, reference: str) -> str:
        # Gradle's KMP metadata legitimately uses ../../ links between sibling
        # modules. Resolve only within the already locked local inventory.
        if ":" in reference or reference.startswith("/") or "\\" in reference:
            raise ValueError("Maven metadata contains a non-relative artifact URL")
        return relative_name(posixpath.normpath(posixpath.join(posixpath.dirname(base), reference)))

    for entry in lock["entries"]:
        if not entry["path"].endswith(".module"):
            continue
        module = json.loads((bundle / entry["path"]).read_text())
        component = module["component"]
        if coordinate(component) != entry["coordinate"]:
            # Native target metadata identifies its owning common component,
            # rather than repeating the target module's Maven coordinates.
            owner_path = relative_artifact(entry["path"], component.get("url", ""))
            owner_entry = by_path.get(owner_path)
            if owner_entry is None or owner_entry["coordinate"] != coordinate(component):
                raise ValueError(f"Maven component identity mismatch: {entry['id']}")
            owner = json.loads((bundle / owner_path).read_text())
            published_targets = [variant["available-at"] for variant in owner["variants"] if "available-at" in variant]
            if not any(coordinate(target) == entry["coordinate"] and
                       relative_artifact(owner_path, target["url"]) == entry["path"] for target in published_targets):
                raise ValueError(f"Maven owning component does not publish this target: {entry['id']}")
        for variant in module["variants"]:
            if "source" not in variant["name"].lower():
                continue
            for published in variant.get("files", []):
                key = relative_artifact(entry["path"], published["url"])
                recorded = by_path.get(key)
                if recorded is None or recorded["sha256"] != published["sha256"] or recorded["size"] != published["size"]:
                    raise ValueError(f"Published source artifact is absent or mismatched: {key}")
                published_sources.add(key)

    for entry in lock["entries"]:
        if not entry["path"].endswith(".pom"):
            continue
        project = ET.parse(bundle / entry["path"]).getroot()
        def field(node, name):
            if node is None:
                return ""
            return next(((child.text or "").strip() for child in node
                         if child.tag.rsplit("}", 1)[-1] == name), "")
        parent = next((child for child in project if child.tag.rsplit("}", 1)[-1] == "parent"), None)
        identity = ":".join((field(project, "groupId") or field(parent, "groupId"),
                             field(project, "artifactId"),
                             field(project, "version") or field(parent, "version")))
        if identity != entry["coordinate"]:
            raise ValueError(f"Maven POM identity mismatch: {entry['id']}")
        pom_coordinates.add(identity)
    for entry in lock["entries"]:
        mode = entry.get("metadata_verification")
        if mode is None:
            continue
        if mode not in ("gradle-module", "pom-and-fixed-hash") or entry["coordinate"] not in pom_coordinates:
            raise ValueError(f"Source artifact lacks its verified POM: {entry['id']}")
        if mode == "gradle-module" and entry["path"] not in published_sources:
            raise ValueError(f"Source artifact is not published by locked module metadata: {entry['id']}")


def verify_source_context(entry: dict, bundle: Path, required: list[str]) -> dict:
    """Verify a small upstream module subtree without claiming its parent build system."""
    report = inspect_archive(bundle / entry["path"], entry["component"], bundle, required,
                             strip_root=False, require_notice=False)
    with zipfile.ZipFile(bundle / entry["published_sources"]) as published:
        license_bytes = published.read(entry["license_member"])
        if not license_bytes or not is_notice(entry["license_member"]):
            raise ValueError("Module source context lacks its referenced license")
        expected = {name: published.read(name) for name in published.namelist() if name.endswith(".java")}
    matched = set()
    with tarfile.open(bundle / entry["path"], "r|*") as archive:
        for member in archive:
            name = relative_name(member.name)
            if member.isfile() and name.startswith("src/main/java/"):
                relative = name.removeprefix("src/main/java/")
                if relative.endswith(".java"):
                    if relative not in expected or archive.extractfile(member).read() != expected[relative]:
                        raise ValueError(f"Module source context differs from published sources: {relative}")
                    matched.add(relative)
            archive.members.clear()
    if matched != set(expected) or not matched:
        raise ValueError("Module source context does not cover all published Java files")
    return {**report, "scope": "module subtree; parent build system not included",
            "published_sources": entry["published_sources"], "matched_java_files": len(matched),
            "license_member": entry["license_member"]}


def write_vendored_context(repo: Path, commit: str, entry: dict, destination: Path) -> None:
    """Archive the reviewed small module tree, without Gitiles' request-time tar metadata."""
    root = relative_name(entry["vendored_root"])
    sources = {}
    for record in entry["vendored_files"]:
        name = relative_name(record["path"])
        if name in sources:
            raise ValueError(f"Duplicate vendored source path: {name}")
        try:
            data = git(repo, "show", commit + ":" + root + "/" + name)
        except subprocess.CalledProcessError as error:
            raise ValueError(f"Vendored source is absent from {commit}: {name}") from error
        blob = hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data, usedforsecurity=False).hexdigest()
        if (len(data), hashlib.sha256(data).hexdigest(), blob) != (record["size"], record["sha256"], record["git_blob"]):
            raise ValueError(f"Vendored source hash/blob mismatch: {name}")
        sources[name] = data
    if not sources:
        raise ValueError("Vendored source context is empty")
    # Plain USTAR has no gzip compressor variance or PAX request-time fields.
    # Explicit headers exclude filesystem/checkout timestamps and owner names.
    with tarfile.open(destination, "w", format=tarfile.USTAR_FORMAT) as archive:
        for name, data in sorted(sources.items()):
            info = tarfile.TarInfo(name)
            info.size = len(data)
            info.mode = 0o644
            info.mtime = 0
            archive.addfile(info, io.BytesIO(data))
    checked_file(destination, entry)


def android_inventory(lock: dict) -> dict:
    if lock.get("scope") != ANDROID_SCOPE:
        raise ValueError("Source lock does not cover the Android validation runtime")
    inventory = lock["android_runtime"]
    records = inventory["external_modules"]
    if not records or len({record["coordinate"] for record in records}) != len(records):
        raise ValueError("Android runtime source inventory is empty or duplicated")
    by_path = {entry["path"]: entry for entry in lock["entries"]}
    pom_coordinates = {entry.get("coordinate") for entry in lock["entries"] if entry["path"].endswith(".pom")}
    external_components = {component for component in inventory["resolved_components"] if not component.startswith("project ")}
    if not external_components.issubset(pom_coordinates):
        raise ValueError("Android runtime component graph lacks locked POM metadata")
    for record in records:
        if not HEX_SHA.fullmatch(record["sha256"]) or record["bytes"] <= 0:
            raise ValueError(f"Invalid Android runtime binary hash/size: {record['coordinate']}")
        if not record["source_paths"]:
            raise ValueError(f"Android runtime module lacks source: {record['coordinate']}")
        for path in record["source_paths"]:
            source = by_path.get(path)
            if source is None or source["kind"] != "maven-source" or source["coordinate"] != record["coordinate"]:
                raise ValueError(f"Android runtime source mapping is invalid: {record['coordinate']}")
            if source.get("metadata_verification") not in ("gradle-module", "pom-and-fixed-hash"):
                raise ValueError(f"Android runtime source has no explicit metadata check: {record['coordinate']}")
    return inventory


def verify_android_runtime(lock_path: Path, report_path: Path) -> dict:
    lock = json.loads(lock_path.read_text())
    inventory = android_inventory(lock)
    report = json.loads(report_path.read_text())
    if (report.get("schema"), report.get("project"), report.get("configuration")) != (
            1, inventory["project"], inventory["configuration"]):
        raise ValueError("Unexpected Android runtime report schema/project/configuration")
    expected = {record["coordinate"]: record for record in inventory["external_modules"]}
    actual = report["external_modules"]
    actual_coordinates = [record["coordinate"] for record in actual]
    if len(actual_coordinates) != len(set(actual_coordinates)):
        raise ValueError("Android runtime report contains duplicate external modules")
    if set(actual_coordinates) != set(expected):
        raise ValueError(f"Android runtime module set differs: missing={sorted(set(expected) - set(actual_coordinates))}, "
                         f"unknown={sorted(set(actual_coordinates) - set(expected))}")
    if sorted(report["resolved_components"]) != inventory["resolved_components"]:
        raise ValueError("Android runtime resolved component graph differs from the source lock")
    projects = report["project_artifacts"]
    if sorted(record["component"] for record in projects) != inventory["project_components"]:
        raise ValueError("Android runtime project artifact set differs from the source lock")
    verified = []
    for records, kind in ((actual, "external-module"), (projects, "project")):
        for record in records:
            if record["kind"] != kind:
                raise ValueError("Android runtime artifact has an unexpected component kind")
            path = Path(record["file"])
            if (not path.is_file() or path.stat().st_size != record["bytes"] or digest(path) != record["sha256"]):
                raise ValueError(f"Android runtime artifact no longer matches its report: {record['component']}")
            if kind == "external-module":
                fixed = expected[record["coordinate"]]
                if ((path.name, record["bytes"], record["sha256"]) !=
                        (fixed["file_name"], fixed["bytes"], fixed["sha256"])):
                    raise ValueError(f"Android runtime binary differs from the source lock: {record['coordinate']}")
            verified.append({key: record[key] for key in ("component", "bytes", "sha256")})
    return {"status": "verified", "scope": lock["scope"], "source_lock_sha256": digest(lock_path),
            "runtime_report_sha256": digest(report_path), "external_modules": len(actual),
            "project_artifacts": len(projects), "verified_artifacts": verified,
            "legal_certification": False}


def write_git_archive(repo: Path, commit: str, destination: Path) -> None:
    with tempfile.TemporaryFile() as raw:
        subprocess.run(["git", "-C", str(repo), "archive", "--format=tar", "--prefix=kadb/", commit],
                       stdout=raw, stderr=subprocess.PIPE, check=True)
        raw.seek(0)
        with destination.open("wb") as output, gzip.GzipFile(filename="", fileobj=output, mode="wb", mtime=0) as compressed:
            shutil.copyfileobj(raw, compressed, CHUNK)


def binary_inventory(arguments: list[str]) -> list[dict]:
    result = []
    labels = set()
    for value in arguments:
        label, separator, value_path = value.partition("=")
        if not separator or label in labels:
            raise ValueError("Each --binary must be a unique LABEL=PATH")
        relative_name(label)
        path = Path(value_path)
        if not path.is_file():
            raise FileNotFoundError(f"Binary artifact is missing: {label}")
        with path.open("rb") as source:
            magic = source.read(8)
        if magic.startswith(b"\x7fELF"):
            kind = "ELF"
        elif magic == b"!<arch>\n":
            kind = "static-archive"
        elif magic[:4] in (b"\xfe\xed\xfa\xce", b"\xce\xfa\xed\xfe", b"\xfe\xed\xfa\xcf", b"\xcf\xfa\xed\xfe",
                            b"\xca\xfe\xba\xbe", b"\xbe\xba\xfe\xca", b"\xca\xfe\xba\xbf", b"\xbf\xba\xfe\xca"):
            kind = "Mach-O-or-fat"
        elif path.suffix == ".klib" and zipfile.is_zipfile(path):
            kind = "KLIB"
        else:
            raise ValueError(f"Unsupported Native artifact format: {label}")
        result.append({"label": label, "kind": kind, "size": path.stat().st_size, "sha256": digest(path)})
        labels.add(label)
    return sorted(result, key=lambda item: item["label"])


def write_tar(bundle: Path, destination: Path, epoch: int) -> None:
    with destination.open("wb") as output, gzip.GzipFile(filename="", fileobj=output, mode="wb", mtime=0, compresslevel=1) as compressed:
        with tarfile.open(fileobj=compressed, mode="w|", format=tarfile.PAX_FORMAT) as archive:
            for path in sorted(bundle.rglob("*")):
                if not path.is_file():
                    continue
                name = "native-source-bundle/" + path.relative_to(bundle).as_posix()
                info = tarfile.TarInfo(name)
                info.size = path.stat().st_size
                info.mtime = epoch
                info.mode = 0o644
                with path.open("rb") as source:
                    archive.addfile(info, source)


def verify_bundle(path: Path, expected_sha256: str | None = None) -> dict:
    actual = digest(path)
    if expected_sha256 is not None and actual != expected_sha256:
        raise ValueError("Bundle SHA-256 mismatch")
    found = {}
    metadata = {}
    with tarfile.open(path, "r|gz") as archive:
        for member in archive:
            full = relative_name(member.name)
            if not full.startswith("native-source-bundle/") or not member.isfile():
                raise ValueError(f"Unexpected bundle member: {full}")
            name = full.removeprefix("native-source-bundle/")
            if name in found:
                raise ValueError(f"Duplicate bundle member: {name}")
            source = archive.extractfile(member)
            sha = hashlib.sha256()
            retained = bytearray()
            while block := source.read(CHUNK):
                sha.update(block)
                if name in ("MANIFEST.json", "SHA256SUMS"):
                    retained.extend(block)
                    if len(retained) > 16 * CHUNK:
                        raise ValueError("Bundle metadata exceeds safety limit")
            found[name] = {"sha256": sha.hexdigest(), "size": member.size}
            if retained:
                metadata[name] = bytes(retained)
            archive.members.clear()
    lines = metadata["SHA256SUMS"].decode().splitlines()
    expected = {}
    for line in lines:
        sha, separator, name = line.partition("  ")
        if not separator or not HEX_SHA.fullmatch(sha) or name in expected:
            raise ValueError("Invalid or duplicate checksum entry")
        expected[relative_name(name)] = sha
    if set(expected) != set(found) - {"SHA256SUMS"}:
        raise ValueError("Bundle checksum inventory is incomplete")
    for name, sha in expected.items():
        if found[name]["sha256"] != sha:
            raise ValueError(f"Bundle member checksum mismatch: {name}")
    manifest = json.loads(metadata["MANIFEST.json"])
    if manifest["files"] != {name: info for name, info in sorted(found.items()) if name not in ("SHA256SUMS", "MANIFEST.json")}:
        raise ValueError("Bundle manifest inventory differs from its actual contents")
    return {"status": "verified", "sha256": actual, "kadb_commit": manifest["kadb_commit"],
            "files": len(found), "binary_associations": len(manifest["binary_artifacts"]),
            "legal_certification": False}


def create(arguments) -> dict:
    lock_path = SUPPORT / "dependencies.lock.json"
    lock = json.loads(lock_path.read_text())
    if lock["schema"] != 1 or lock["scope"] not in ("experimental-native-runtime", ANDROID_SCOPE):
        raise ValueError("Unknown source lock schema/scope")
    if len({entry["path"] for entry in lock["entries"]}) != len(lock["entries"]):
        raise ValueError("Duplicate source lock output paths")
    for entry in lock["entries"]:
        relative_name(entry["path"])
        if not HEX_SHA.fullmatch(entry["sha256"]) or entry["size"] <= 0:
            raise ValueError("Invalid locked source hash/size")
        if entry["kind"] not in ("source-archive", "source-context-archive", "maven-source", "maven-metadata"):
            raise ValueError(f"Unknown source lock entry kind: {entry['kind']}")
    android = android_inventory(lock) if lock["scope"] == ANDROID_SCOPE else None
    commit, epoch = check_project(arguments.repo, arguments.ref, lock)
    binary_files = binary_inventory(arguments.binary)
    arguments.output.mkdir(parents=True, exist_ok=True)
    arguments.cache.mkdir(parents=True, exist_ok=True)
    final = arguments.output / f"native-source-bundle-{commit}.tar.gz"
    log_path = arguments.output / "source-bundle-execution.jsonl"
    if final.exists() or log_path.exists():
        raise FileExistsError("Choose a new output directory; existing execution evidence is never overwritten")
    with log_path.open("x") as log:
        def emit(event, **details):
            record = {"event": event, "utc": datetime.datetime.now(datetime.timezone.utc).isoformat(), **details}
            line = json.dumps(record, sort_keys=True)
            log.write(line + "\n")
            log.flush()
            print(line, flush=True)

        try:
            emit("started", kadb_commit=commit, native_targets=lock["native_targets"],
                 binary_associations=len(binary_files), python=sys.version.split()[0])
            with tempfile.TemporaryDirectory(prefix="source-bundle-", dir=arguments.output) as temporary:
                bundle = Path(temporary)
                (bundle / "upstream").mkdir()
                kadb_archive = bundle / "upstream" / f"kadb-{commit}.tar.gz"
                write_git_archive(arguments.repo, commit, kadb_archive)
                required_kadb = ["LICENSE", "gradlew", "gradle/libs.versions.toml", "third-party/spake2/upstream/LICENSE"]
                if android is not None:
                    required_kadb += android["required_project_files"]
                source_reports = [inspect_archive(kadb_archive, "kadb", bundle, required_kadb)]
                maven_reports = []
                for entry in lock["entries"]:
                    output = bundle / entry["path"]
                    output.parent.mkdir(parents=True, exist_ok=True)
                    if "vendored_root" in entry:
                        write_vendored_context(arguments.repo, commit, entry, output)
                        emit("vendored_source_verified", component=entry["id"], commit=commit,
                             files=len(entry["vendored_files"]), bytes=entry["size"], sha256=entry["sha256"])
                    else:
                        cached = fetch(entry, arguments.cache, arguments.offline, arguments.boringssl_archive, emit)
                        shutil.copyfile(cached, output)
                    if entry["kind"] == "source-archive":
                        report = inspect_archive(output, entry["component"], bundle,
                            lock["required_archive_files"][entry["component"]])
                        source_reports.append(report)
                        emit("archive_inventory_verified", component=entry["component"],
                             source_files=report["source_files"], notices=len(report["notices"]))
                    elif entry["kind"] == "maven-source":
                        maven_reports.append(inspect_maven(entry, output, bundle))
                verify_module_sources(lock, bundle)
                context_reports = [verify_source_context(entry, bundle,
                    lock["required_archive_files"][entry["component"]]) for entry in lock["entries"]
                    if entry["kind"] == "source-context-archive"]
                support = bundle / "assembly"
                support.mkdir()
                support_files = [Path(__file__).resolve(), lock_path, SUPPORT / "upstream-ref-resolution.json", SUPPORT / "BUNDLE_README.md"]
                if android is not None:
                    support_files.append(SUPPORT / "android-source-provenance.json")
                for path in support_files:
                    shutil.copyfile(path, support / path.name)
                (bundle / "README.md").write_text((SUPPORT / "BUNDLE_README.md").read_text().replace("@KADB_COMMIT@", commit))
                files = {path.relative_to(bundle).as_posix(): {"sha256": digest(path), "size": path.stat().st_size}
                         for path in sorted(bundle.rglob("*")) if path.is_file()}
                manifest = {"schema": 1, "scope": lock["scope"], "legal_certification": False,
                            "kadb_commit": commit, "kadb_archive": kadb_archive.relative_to(bundle).as_posix(),
                            "source_lock_sha256": digest(lock_path), "versions": lock["versions"],
                            "native_targets": lock["native_targets"], "binary_artifacts": binary_files,
                            "binary_association_scope": "caller-supplied artifact hashes" if binary_files else "source inventory only; no binary association",
                            "source_archives": source_reports, "source_contexts": context_reports,
                            "maven_sources": maven_reports, "android_runtime": android, "files": files}
                manifest_path = bundle / "MANIFEST.json"
                manifest_path.write_bytes(json_bytes(manifest))
                checksums = {**{name: info["sha256"] for name, info in files.items()}, "MANIFEST.json": digest(manifest_path)}
                (bundle / "SHA256SUMS").write_text("".join(f"{sha}  {name}\n" for name, sha in sorted(checksums.items())))
                packed = arguments.output / (final.name + ".partial")
                write_tar(bundle, packed, epoch)
                verified = verify_bundle(packed)
                packed.replace(final)
                (arguments.output / "source-bundle-manifest.json").write_bytes(json_bytes(manifest))
                (arguments.output / (final.name + ".sha256")).write_text(f"{verified['sha256']}  {final.name}\n")
                result = {**verified, "bundle": final.name, "bytes": final.stat().st_size,
                          "source_archives": len(source_reports), "published_source_jars": len(maven_reports)}
                (arguments.output / "source-bundle-result.json").write_bytes(json_bytes(result))
                emit("completed", **result)
                return result
        except BaseException as error:
            emit("failed", error_type=type(error).__name__, error=str(error))
            raise


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    collect = subparsers.add_parser("create", help="Collect verified source bytes into a deterministic bundle")
    collect.add_argument("--repo", type=Path, default=ROOT)
    collect.add_argument("--ref", required=True, help="Git revision of the corresponding Kadb binary source")
    collect.add_argument("--output", type=Path, required=True)
    collect.add_argument("--cache", type=Path, required=True)
    collect.add_argument("--offline", action="store_true", help="Require all fixed sources in the verified local cache")
    collect.add_argument("--boringssl-archive", type=Path, help="Reuse the Native build's archive only after verifying its fixed hash")
    collect.add_argument("--binary", action="append", default=[], metavar="LABEL=PATH", help="Associate a compiled Native artifact by hash; repeat as needed")
    verify = subparsers.add_parser("verify", help="Verify every bundle member against its inventory without extracting files")
    verify.add_argument("bundle", type=Path)
    verify.add_argument("--sha256")
    android = subparsers.add_parser("verify-android-runtime", help="Match actual Android runtime archives to the source lock")
    android.add_argument("--lock", type=Path, default=SUPPORT / "dependencies.lock.json")
    android.add_argument("--runtime-report", type=Path, required=True)
    android.add_argument("--output", type=Path, help="Save successful verification as a new JSON evidence file")
    arguments = parser.parse_args()
    try:
        if arguments.command == "create":
            result = create(arguments)
        elif arguments.command == "verify":
            result = verify_bundle(arguments.bundle, arguments.sha256)
        else:
            result = verify_android_runtime(arguments.lock, arguments.runtime_report)
            if arguments.output is not None:
                arguments.output.parent.mkdir(parents=True, exist_ok=True)
                with arguments.output.open("xb") as output:
                    output.write(json_bytes(result))
        print(json.dumps(result, sort_keys=True))
        return 0
    except Exception as error:
        print(f"SOURCE_BUNDLE_FAILED {type(error).__name__}: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
