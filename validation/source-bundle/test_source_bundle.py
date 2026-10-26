"""Integrity regressions for the source collector; no network or Gradle required."""

import hashlib
import importlib.util
import json
from pathlib import Path
import tarfile
import tempfile
import unittest
from unittest import mock
import zipfile


SPEC = importlib.util.spec_from_file_location(
    "source_bundle", Path(__file__).resolve().parents[2] / "scripts/source_bundle.py")
bundle = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(bundle)


class SourceBundleIntegrityTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)

    def source_archive(self, files):
        tree = self.root / "upstream"
        tree.mkdir()
        for name, content in files.items():
            path = tree / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content)
        archive = self.root / "upstream.tar.gz"
        with tarfile.open(archive, "w:gz") as output:
            output.add(tree, arcname="project-revision")
        return archive

    def small_bundle(self):
        tree = self.root / "bundle"
        tree.mkdir()
        source = tree / "source.kt"
        source.write_text("// source bytes\n")
        files = {source.name: {"size": source.stat().st_size, "sha256": bundle.digest(source)}}
        manifest = tree / "MANIFEST.json"
        manifest.write_bytes(bundle.json_bytes({
            "kadb_commit": "a" * 40, "binary_artifacts": [], "files": files}))
        (tree / "SHA256SUMS").write_text(
            f"{bundle.digest(manifest)}  MANIFEST.json\n"
            f"{bundle.digest(source)}  source.kt\n")
        return tree

    def test_corrupt_cache_fails_without_refetch(self):
        entry = {"id": "example", "path": "source.jar", "size": 4,
                 "sha256": hashlib.sha256(b"good").hexdigest()}
        (self.root / (entry["sha256"] + "-source.jar")).write_bytes(b"evil")
        with mock.patch.object(bundle.urllib.request, "urlopen") as request:
            with self.assertRaisesRegex(ValueError, "mismatch"):
                bundle.fetch(entry, self.root, False, None, lambda *args, **kwargs: None)
            request.assert_not_called()

    def test_offline_cache_miss_is_failure(self):
        entry = {"id": "example", "path": "source.jar", "sha256": "a" * 64}
        with self.assertRaisesRegex(FileNotFoundError, "Offline source cache"):
            bundle.fetch(entry, self.root, True, None, lambda *args, **kwargs: None)

    def test_class_only_jar_is_not_source(self):
        archive = self.root / "empty-sources.jar"
        with zipfile.ZipFile(archive, "w") as output:
            output.writestr("Example.class", b"not source")
        with self.assertRaisesRegex(ValueError, "Unexpected source inventory"):
            bundle.inspect_maven({"id": "example", "source_entries": 1}, archive)

    def test_kotlin_source_archive_must_include_native_runtime(self):
        archive = self.source_archive({"LICENSE.txt": "notice", "Source.kt": "// Kotlin only"})
        with self.assertRaisesRegex(ValueError, "Native C/C\\+\\+ runtime"):
            bundle.inspect_archive(archive, "kotlin", self.root / "out", ["LICENSE.txt"])

    def test_missing_required_build_source_is_failure(self):
        archive = self.source_archive({"LICENSE": "notice", "runtime.c": "// source"})
        with self.assertRaisesRegex(ValueError, "Incomplete.*CMakeLists"):
            bundle.inspect_archive(archive, "test", self.root / "out", ["CMakeLists.txt"])

    def test_bundle_round_trip_is_deterministic(self):
        tree = self.small_bundle()
        first, second = self.root / "first.tar.gz", self.root / "second.tar.gz"
        bundle.write_tar(tree, first, 1_700_000_000)
        bundle.write_tar(tree, second, 1_700_000_000)
        self.assertEqual(bundle.digest(first), bundle.digest(second))
        result = bundle.verify_bundle(first, bundle.digest(second))
        self.assertEqual("verified", result["status"])
        self.assertEqual(3, result["files"])
        self.assertEqual(0, result["binary_associations"])

    def test_changed_or_unlisted_member_is_rejected(self):
        tree = self.small_bundle()
        (tree / "source.kt").write_text("// changed bytes\n")
        packed = self.root / "changed.tar.gz"
        bundle.write_tar(tree, packed, 1_700_000_000)
        with self.assertRaisesRegex(ValueError, "checksum mismatch"):
            bundle.verify_bundle(packed)
        (tree / "extra.kt").write_text("// unlisted source\n")
        bundle.write_tar(tree, packed, 1_700_000_000)
        with self.assertRaisesRegex(ValueError, "inventory is incomplete"):
            bundle.verify_bundle(packed)

    def test_path_traversal_and_outer_hash_mismatch_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "Unsafe archive-relative path"):
            bundle.relative_name("native-source-bundle/../outside")
        tree = self.small_bundle()
        packed = self.root / "bundle.tar.gz"
        bundle.write_tar(tree, packed, 1_700_000_000)
        with self.assertRaisesRegex(ValueError, "Bundle SHA-256 mismatch"):
            bundle.verify_bundle(packed, "0" * 64)

    def maven_metadata(self):
        parent = "maven/example/core/1/core-1.module"
        target = "maven/example/core-linuxx64/1/core-linuxx64-1.module"
        source = "maven/example/core-linuxx64/1/core-linuxx64-1-sources.jar"
        module = {"component": {"group": "example", "module": "core", "version": "1"},
                  "variants": [{"name": "linuxX64ApiElements", "available-at": {
                      "group": "example", "module": "core-linuxx64", "version": "1",
                      "url": "../../core-linuxx64/1/core-linuxx64-1.module"}}]}
        child = {"component": {**module["component"], "url": "../../core/1/core-1.module"},
                 "variants": [{"name": "linuxX64SourcesElements", "files": [{
                     "url": "core-linuxx64-1-sources.jar", "size": 4, "sha256": "a" * 64}]}]}
        for path, content in ((parent, module), (target, child)):
            destination = self.root / path
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(json.dumps(content))
        lock = {"entries": [
            {"id": "root", "path": parent, "coordinate": "example:core:1"},
            {"id": "target", "path": target, "coordinate": "example:core-linuxx64:1"},
            {"id": "sources", "path": source, "size": 4, "sha256": "a" * 64}]}
        return lock, self.root / parent

    def test_native_metadata_owner_requires_published_target_backlink(self):
        lock, parent = self.maven_metadata()
        bundle.verify_module_sources(lock, self.root)
        module = json.loads(parent.read_text())
        module["variants"] = []
        parent.write_text(json.dumps(module))
        with self.assertRaisesRegex(ValueError, "does not publish this target"):
            bundle.verify_module_sources(lock, self.root)

    def test_published_source_hash_must_match_lock(self):
        lock, _ = self.maven_metadata()
        lock["entries"][-1]["sha256"] = "b" * 64
        with self.assertRaisesRegex(ValueError, "source artifact is absent or mismatched"):
            bundle.verify_module_sources(lock, self.root)


if __name__ == "__main__":
    unittest.main()
