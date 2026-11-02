"""Integrity regressions for the source collector; no network or Gradle required."""

import hashlib
import copy
import importlib.util
import json
from pathlib import Path
import subprocess
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

    def pom_source(self, mode="pom-and-fixed-hash"):
        pom = self.root / "example.pom"
        # Maven permits group/version inheritance from a parent. The actual
        # ListenableFuture POM uses this group inheritance.
        pom.write_text('<project xmlns="http://maven.apache.org/POM/4.0.0">'
                       '<parent><groupId>example</groupId><version>1</version></parent>'
                       '<artifactId>core</artifactId></project>')
        return {"entries": [
            {"id": "pom", "path": pom.name, "coordinate": "example:core:1"},
            {"id": "source", "kind": "maven-source", "path": "example-sources.jar",
             "coordinate": "example:core:1", "metadata_verification": mode}]}, pom

    def test_pom_only_source_is_explicitly_supported_without_fabricated_module(self):
        lock, _ = self.pom_source()
        bundle.verify_module_sources(lock, self.root)
        self.assertFalse(any(self.root.glob("*.module")))

    def test_pom_only_source_requires_matching_pom_identity(self):
        lock, pom = self.pom_source()
        pom.write_text(pom.read_text().replace("<artifactId>core", "<artifactId>different"))
        with self.assertRaisesRegex(ValueError, "POM identity mismatch"):
            bundle.verify_module_sources(lock, self.root)

    def test_pom_only_source_requires_pom_in_lock(self):
        lock, _ = self.pom_source()
        lock["entries"].pop(0)
        with self.assertRaisesRegex(ValueError, "lacks its verified POM"):
            bundle.verify_module_sources(lock, self.root)

    def test_pom_cannot_masquerade_as_gradle_source_metadata(self):
        lock, _ = self.pom_source("gradle-module")
        with self.assertRaisesRegex(ValueError, "not published by locked module"):
            bundle.verify_module_sources(lock, self.root)

    def test_android_scope_uses_committed_consumer_sources(self):
        name = "validation/android-runtime/RuntimeInstrumentation.java"
        local = self.root / name
        local.parent.mkdir(parents=True)
        local.write_text("// Present only in the working tree, not in the selected commit.")
        lock = {"android_runtime": {"required_project_files": [name]}}
        missing = subprocess.CalledProcessError(128, "git show")
        with mock.patch.object(bundle, "git", side_effect=missing) as read:
            with self.assertRaisesRegex(ValueError, "consumer source is absent"):
                bundle.check_android_project_sources(self.root, "a" * 40, lock)
            read.assert_called_once_with(self.root, "show", "a" * 40 + ":" + name)

    def test_android_scope_rejects_empty_consumer_source(self):
        lock = {"android_runtime": {"required_project_files": ["build.gradle.kts"]}}
        with mock.patch.object(bundle, "git", return_value=b""):
            with self.assertRaisesRegex(ValueError, "consumer source is empty"):
                bundle.check_android_project_sources(self.root, "a" * 40, lock)

    def runtime_fixture(self):
        external = self.root / "example-1.jar"
        external.write_bytes(b"external archive bytes")
        project = self.root / "classes.jar"
        project.write_bytes(b"current project bytes")
        coordinate = "example:core:1"
        project_name = "project ':kadb'"
        def record(path, component, kind):
            return {"kind": kind, "component": component,
                    "coordinate": component if kind == "external-module" else None,
                    "file": str(path), "bytes": path.stat().st_size, "sha256": bundle.digest(path)}
        artifact = record(external, coordinate, "external-module")
        inventory = {"project": ":validation-android-runtime", "configuration": "debugRuntimeClasspath",
                     "resolved_components": [coordinate, project_name], "project_components": [project_name],
                     "external_modules": [{"coordinate": coordinate, "file_name": external.name,
                         "bytes": artifact["bytes"], "sha256": artifact["sha256"],
                         "source_paths": ["example-sources.jar"]}]}
        lock = {"scope": bundle.ANDROID_SCOPE, "android_runtime": inventory, "entries": [
            {"kind": "maven-source", "path": "example-sources.jar", "coordinate": coordinate,
             "metadata_verification": "pom-and-fixed-hash"},
            {"kind": "maven-metadata", "path": "example.pom", "coordinate": coordinate}]}
        report = {"schema": 1, "project": inventory["project"], "configuration": inventory["configuration"],
                  "external_modules": [artifact], "project_artifacts": [record(project, project_name, "project")],
                  "resolved_components": inventory["resolved_components"][:]}
        return lock, report, external, project

    def verify_runtime_fixture(self, lock, report):
        lock_path, report_path = self.root / "lock.json", self.root / "report.json"
        lock_path.write_bytes(bundle.json_bytes(lock))
        report_path.write_bytes(bundle.json_bytes(report))
        return bundle.verify_android_runtime(lock_path, report_path)

    def test_android_runtime_verifies_current_files_and_does_not_pin_project_hash(self):
        lock, report, _, project = self.runtime_fixture()
        self.assertEqual("verified", self.verify_runtime_fixture(lock, report)["status"])
        project.write_bytes(b"a newer consumer commit")
        report["project_artifacts"][0].update(bytes=project.stat().st_size, sha256=bundle.digest(project))
        self.assertEqual(1, self.verify_runtime_fixture(lock, report)["project_artifacts"])

    def test_android_runtime_missing_unknown_and_duplicate_modules_fail(self):
        lock, report, _, _ = self.runtime_fixture()
        original = report["external_modules"][0]
        for records, message in (([], "module set differs"),
                                 ([dict(original, coordinate="example:unknown:1")], "module set differs"),
                                 ([original, original], "duplicate external")):
            with self.subTest(message=message, count=len(records)):
                report["external_modules"] = records
                with self.assertRaisesRegex(ValueError, message):
                    self.verify_runtime_fixture(lock, report)

    def test_android_runtime_publisher_binary_replacement_fails_even_with_fresh_report(self):
        lock, report, external, _ = self.runtime_fixture()
        external.write_bytes(b"replacement at same coordinate")
        report["external_modules"][0].update(bytes=external.stat().st_size, sha256=bundle.digest(external))
        with self.assertRaisesRegex(ValueError, "binary differs from the source lock"):
            self.verify_runtime_fixture(lock, report)

    def test_android_runtime_stale_report_cannot_hide_mutated_files(self):
        lock, report, external, _ = self.runtime_fixture()
        external.write_bytes(b"x" * external.stat().st_size)
        with self.assertRaisesRegex(ValueError, "no longer matches its report"):
            self.verify_runtime_fixture(lock, report)

    def test_android_runtime_metadata_graph_and_project_set_must_match(self):
        lock, report, _, _ = self.runtime_fixture()
        report["resolved_components"].append("example:new-bom:1")
        with self.assertRaisesRegex(ValueError, "component graph differs"):
            self.verify_runtime_fixture(lock, report)
        report["resolved_components"].pop()
        report["project_artifacts"] = []
        with self.assertRaisesRegex(ValueError, "project artifact set differs"):
            self.verify_runtime_fixture(lock, report)

    def test_android_runtime_requires_locked_sources_and_poms(self):
        lock, report, _, _ = self.runtime_fixture()
        source = lock["entries"].pop(0)
        with self.assertRaisesRegex(ValueError, "source mapping is invalid"):
            self.verify_runtime_fixture(lock, report)
        lock["entries"] = [source]
        with self.assertRaisesRegex(ValueError, "lacks locked POM"):
            self.verify_runtime_fixture(lock, report)

    def test_flat_module_context_requires_byte_identical_sources_and_license(self):
        jar = self.root / "sources.jar"
        with zipfile.ZipFile(jar, "w") as output:
            output.writestr("example/Code.java", b"class Code {}")
            output.writestr("META-INF/LICENSE.txt", b"original license")
        tree = self.root / "module"
        java = tree / "src/main/java/example/Code.java"
        java.parent.mkdir(parents=True)
        java.write_bytes(b"class Code {}")
        (tree / "build.gradle").write_text("// upstream build script")
        archive = self.root / "module.tar.gz"
        def pack():
            with tarfile.open(archive, "w:gz") as output:
                for path in sorted(tree.rglob("*")):
                    output.add(path, arcname=path.relative_to(tree).as_posix(), recursive=False)
        entry = {"path": archive.name, "component": "module", "published_sources": jar.name,
                 "license_member": "META-INF/LICENSE.txt"}
        pack()
        result = bundle.verify_source_context(entry, self.root, ["build.gradle"])
        self.assertEqual(1, result["matched_java_files"])
        java.write_bytes(b"class Changed {}")
        pack()
        with self.assertRaisesRegex(ValueError, "differs from published sources"):
            bundle.verify_source_context(entry, self.root, ["build.gradle"])

    def vendored_context_fixture(self):
        files = {"Example.java": b"class Example {}\n", "build.gradle": b"// fixed build context\n"}
        entry = {"id": "context", "vendored_root": "third-party/context/upstream", "size": 10240,
                 "sha256": "eea29b61c2ff2716d77504dbdf2640e5511d1fe776d701cd1271bece29687691",
                 "vendored_files": [{"path": name, "size": len(data),
                     "sha256": hashlib.sha256(data).hexdigest(),
                     "git_blob": hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data,
                                              usedforsecurity=False).hexdigest()}
                     for name, data in files.items()]}
        def committed_file(repo, operation, path):
            self.assertEqual("show", operation)
            return files[path.split("/upstream/", 1)[1]]
        return entry, files, committed_file

    def test_vendored_context_has_stable_headers_and_reads_the_requested_commit(self):
        entry, _, read = self.vendored_context_fixture()
        first, second = self.root / "one.tar", self.root / "two.tar"
        with mock.patch.object(bundle, "git", side_effect=read) as git:
            bundle.write_vendored_context(self.root, "a" * 40, entry, first)
            bundle.write_vendored_context(self.root, "b" * 40, entry, second)
            self.assertEqual(["a" * 40] * 2 + ["b" * 40] * 2,
                             [call.args[2].split(":", 1)[0] for call in git.call_args_list])
        self.assertEqual(first.read_bytes(), second.read_bytes())
        with tarfile.open(first) as archive:
            self.assertEqual(["Example.java", "build.gradle"], archive.getnames())
            for member in archive:
                self.assertEqual((0, 0, 0, "", "", 0o644, {}),
                                 (member.mtime, member.uid, member.gid, member.uname,
                                  member.gname, member.mode, member.pax_headers))

    def test_vendored_context_rejects_committed_source_or_blob_changes(self):
        entry, files, read = self.vendored_context_fixture()
        with mock.patch.object(bundle, "git", side_effect=read):
            files["Example.java"] = b"class Modified {}\n"
            with self.assertRaisesRegex(ValueError, "source hash/blob mismatch"):
                bundle.write_vendored_context(self.root, "a" * 40, entry, self.root / "out.tar")
            files["Example.java"] = b"class Example {}\n"
            entry["vendored_files"][0]["git_blob"] = "0" * 40
            with self.assertRaisesRegex(ValueError, "source hash/blob mismatch"):
                bundle.write_vendored_context(self.root, "a" * 40, entry, self.root / "out.tar")

    def test_vendored_context_cannot_fall_back_to_uncommitted_files(self):
        entry, files, _ = self.vendored_context_fixture()
        for name, data in files.items():
            path = self.root / entry["vendored_root"] / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        with mock.patch.object(bundle, "git", side_effect=subprocess.CalledProcessError(128, "git show")):
            with self.assertRaisesRegex(ValueError, "Vendored source is absent"):
                bundle.write_vendored_context(self.root, "a" * 40, entry, self.root / "out.tar")

    def test_vendored_context_keeps_the_whole_archive_hash_gate(self):
        entry, _, read = self.vendored_context_fixture()
        entry["sha256"] = "0" * 64
        with mock.patch.object(bundle, "git", side_effect=read):
            with self.assertRaisesRegex(ValueError, "Size/SHA-256 mismatch"):
                bundle.write_vendored_context(self.root, "a" * 40, entry, self.root / "out.tar")


class MavenCandidateSourceTest(unittest.TestCase):
    """Mutate the retained CI candidate, rather than inventing matching source/binary fixtures."""

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        project = Path(__file__).resolve().parents[2]
        self.lock_path = project / "validation/source-bundle/dependencies.lock.json"
        self.lock = json.loads(self.lock_path.read_text())
        candidate = self.lock["spake2_maven"]
        archive = project / candidate["source"]["recovery_archive"]
        self.assertEqual(candidate["source"]["recovery_archive_sha256"], bundle.digest(archive))
        with tarfile.open(archive) as source:
            for member in source:
                name = bundle.relative_name(member.name)
                if member.isdir():
                    continue
                self.assertTrue(member.isfile() and name.startswith("maven/"))
                target = self.root / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(source.extractfile(member).read())
        self.repo = self.root / "maven"
        # Synthetic origin IDs are only fixture data; production reports obtain them
        # from the actual Gradle resolved component and repository descriptor.
        origin = {"repository_id": "unit-test-candidate-repository-id", "repository_name": "spake2ValidatedCandidate"}
        self.report = {"schema": 1, "repository": str(self.repo), "version": candidate["version"], **origin,
                       "revision": candidate["revision"], "source_lock_sha256": bundle.digest(self.lock_path),
                       "resolved_components": [], "artifacts": []}
        for module in ("spake2-legacy-android", "spake2-primitives-android"):
            coordinate = f"io.github.flyfish233:{module}:{candidate['version']}"
            fixed = next(item for item in candidate["inventory"] if item["coordinate"] == coordinate and item["path"].endswith(".aar"))
            path = self.repo / fixed["path"]
            metadata = json.loads(path.with_suffix(".module").read_text())
            variant = next(item for item in metadata["variants"] if item["attributes"].get("org.gradle.usage") == "java-api")
            self.report["resolved_components"].append({"kind": "external-module", "coordinate": coordinate, **origin,
                                                       "configuration": "androidCompileClasspath"})
            self.report["artifacts"].append({"kind": "external-module", "coordinate": coordinate, **origin,
                "component": coordinate, "configuration": "androidCompileClasspath", "file": str(path),
                "repository_path": fixed["path"], "bytes": fixed["size"], "sha256": fixed["sha256"],
                "variant": variant["name"], "attributes": {key: str(value) for key, value in variant["attributes"].items()}})

    def verify(self):
        path = self.root / "resolution.json"
        path.write_text(json.dumps(self.report))
        return bundle.verify_spake2_maven(self.lock, self.repo, path)

    def test_actual_candidate_sources_and_external_variants_are_verified(self):
        result = self.verify()
        self.assertEqual("verified", result["resolution_status"])
        self.assertEqual(22, result["publications"])
        self.assertEqual(2, len(result["source_distributions"]))
        self.assertEqual(2, len(result["verified_artifacts"]))

    def test_missing_or_mismatched_resolved_repository_origin_is_rejected(self):
        original = copy.deepcopy(self.report)
        self.report.pop("repository_id")
        with self.assertRaisesRegex(ValueError, "lacks the actual repository origin"):
            self.verify()
        for section in ("resolved_components", "artifacts"):
            for field in ("repository_id", "repository_name"):
                self.report = copy.deepcopy(original)
                self.report[section][0][field] = "untrusted-repository"
                with self.subTest(section=section, field=field), self.assertRaisesRegex(ValueError, "repository origin differs"):
                    self.verify()

    def test_stale_or_missing_source_lock_identity_is_rejected(self):
        for digest in (None, "0" * 64):
            self.report["source_lock_sha256"] = digest
            with self.subTest(digest=digest), self.assertRaisesRegex(ValueError, "source lock is missing, stale or mismatched"):
                self.verify()

    def test_wrong_version_and_old_vendored_lock_are_rejected(self):
        self.report["version"] = "0.1.0-dev.wrong"
        with self.assertRaisesRegex(ValueError, "version/revision/repository mismatch"):
            self.verify()
        self.lock.pop("spake2_maven")
        with self.assertRaisesRegex(ValueError, "lacks the Maven SPAKE2"):
            self.verify()

    def test_missing_primitives_binary_is_rejected(self):
        Path(self.report["artifacts"][1]["file"]).unlink()
        with self.assertRaisesRegex(ValueError, "Size/SHA-256 mismatch"):
            self.verify()

    def test_missing_transitive_resolution_is_rejected(self):
        self.report["artifacts"].pop()
        with self.assertRaisesRegex(ValueError, "omits Legacy or its same-version Primitives"):
            self.verify()

    def test_project_substitution_is_rejected_even_with_correct_candidate_bytes(self):
        self.report["artifacts"][0]["kind"] = "project"
        with self.assertRaisesRegex(ValueError, "substituted"):
            self.verify()
        self.report["artifacts"][0]["kind"] = "external-module"
        self.report["resolved_components"][0].update(kind="project", coordinate="project ':spake2-legacy'")
        with self.assertRaisesRegex(ValueError, "substituted"):
            self.verify()

    def test_wrong_selected_variant_and_platform_attributes_are_rejected(self):
        artifact = self.report["artifacts"][0]
        original = copy.deepcopy(artifact)
        artifact["variant"] = "jvmApiElements-published"
        with self.assertRaisesRegex(ValueError, "variant/attributes"):
            self.verify()
        artifact.update(original)
        artifact["attributes"]["org.jetbrains.kotlin.platform.type"] = "jvm"
        with self.assertRaisesRegex(ValueError, "variant/attributes"):
            self.verify()

    def test_stale_resolution_report_cannot_hide_changed_cached_binary(self):
        artifact = self.report["artifacts"][0]
        cached = self.root / "cached.aar"
        cached.write_bytes(Path(artifact["file"]).read_bytes() + b"changed")
        artifact["file"] = str(cached)
        with self.assertRaisesRegex(ValueError, "Size/SHA-256 mismatch"):
            self.verify()

    def test_sources_cannot_masquerade_as_selected_library_binaries(self):
        artifact = self.report["artifacts"][0]
        fixed = next(item for item in self.lock["spake2_maven"]["inventory"] if
                     item["coordinate"] == artifact["coordinate"] and item["path"].endswith("-sources.jar"))
        metadata_path = next(item["path"] for item in self.lock["spake2_maven"]["inventory"] if
                             item["coordinate"] == artifact["coordinate"] and item["path"].endswith(".module"))
        metadata = json.loads((self.repo / metadata_path).read_text())
        variant = next(item for item in metadata["variants"] if item["attributes"].get("org.gradle.docstype") == "sources")
        artifact.update(repository_path=fixed["path"], file=str(self.repo / fixed["path"]),
                        bytes=fixed["size"], sha256=fixed["sha256"], variant=variant["name"],
                        attributes={key: str(value) for key, value in variant["attributes"].items()})
        with self.assertRaisesRegex(ValueError, "not a library binary"):
            self.verify()

    def test_source_collection_cannot_omit_full_distribution_or_license_companion(self):
        for kind in ("spake2-source-distribution", "spake2-license-companion"):
            lock = copy.deepcopy(self.lock)
            entry = next(item for item in lock["entries"] if item["kind"] == kind)
            lock["entries"].remove(entry)
            with self.subTest(kind=kind), self.assertRaisesRegex(ValueError, "omits or duplicates"):
                bundle.verify_spake2_maven(lock, self.repo)

    def test_full_source_zip_requires_wrapper_build_scripts_and_original_license(self):
        original = next(item for item in self.lock["entries"] if item["kind"] == "spake2-source-distribution")
        for missing in ("gradle/wrapper/gradle-wrapper.jar", "build.gradle.kts", "LICENSE"):
            path = self.root / (missing.replace("/", "-") + ".zip")
            with zipfile.ZipFile(self.repo / original["candidate_path"]) as source, zipfile.ZipFile(path, "w") as target:
                for member in source.infolist():
                    if member.filename != missing:
                        target.writestr(member, source.read(member.filename))
            entry = {**original, "size": path.stat().st_size, "sha256": bundle.digest(path)}
            with self.subTest(missing=missing), self.assertRaisesRegex(ValueError, "required build sources or license"):
                bundle.inspect_spake2_zip(entry, path)

    def test_repository_identity_and_full_revision_must_match(self):
        self.report["repository"] = str(self.root / "other")
        with self.assertRaisesRegex(ValueError, "repository mismatch"):
            self.verify()
        self.report["repository"] = str(self.repo)
        self.report["revision"] = "0" * 40
        with self.assertRaisesRegex(ValueError, "version/revision/repository mismatch"):
            self.verify()


if __name__ == "__main__":
    unittest.main()
