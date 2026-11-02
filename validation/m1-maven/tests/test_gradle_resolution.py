"""Exercise the real Gradle resolution gate with the pinned Maven binaries.

Run with KADB_RUN_GRADLE_GATE_TESTS=1 after preparing the candidate. These small
consumers use only Gradle's built-in plugins; they are not Kadb compilation,
platform integration, or pairing tests. KADB_GRADLE_EXECUTABLE can select an
already unpacked Gradle 9.6.0 executable instead of the repository wrapper.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[3]
VERSION = "0.1.0-dev.59105290820b"
ENABLED = os.environ.get("KADB_RUN_GRADLE_GATE_TESTS") == "1"


@unittest.skipUnless(ENABLED, "set KADB_RUN_GRADLE_GATE_TESTS=1 for real Gradle cases")
class GradleResolutionGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.repository = ROOT / "build/spake2-candidate/maven"
        if not cls.repository.is_dir():
            raise RuntimeError("Run python3 scripts/prepare_spake2_candidate.py first")
        cls.executable = os.environ.get("KADB_GRADLE_EXECUTABLE", str(ROOT / "gradlew"))
        cls.output = ROOT / "build/reports/spake2-gradle-gate-tests"
        cls.output.mkdir(parents=True, exist_ok=True)

    def run_case(self, name, *, changes="", expected=None, wrong_source=False,
                 corrupt=False, extra_configuration=False):
        with tempfile.TemporaryDirectory(prefix=f"spake2-gate-{name}-") as temporary:
            fixture = Path(temporary)
            repository = fixture / "candidate"
            shutil.copytree(self.repository, repository)
            used_repository = repository
            if wrong_source:
                used_repository = fixture / "different-repository"
                shutil.copytree(repository, used_repository)
            if corrupt:
                binary = next(repository.rglob(f"spake2-legacy-jvm-{VERSION}.jar"))
                binary.write_bytes(binary.read_bytes() + b"changed")
            lock = fixture / "validation/source-bundle/dependencies.lock.json"
            lock.parent.mkdir(parents=True)
            shutil.copyfile(ROOT / "validation/source-bundle/dependencies.lock.json", lock)
            (fixture / "settings.gradle").write_text("rootProject.name = 'spake2-gate-fixture'\ninclude ':replacement'\n")
            replacement = fixture / "replacement"
            replacement.mkdir()
            (replacement / "build.gradle").write_text("plugins { id 'java-library' }\n")
            # Keep the expected repository configured behind the wrong one. This
            # checks actual selection provenance, not merely missing configuration.
            additional_repository = (
                f"maven {{ name = 'fixedCandidate'; url = uri({json.dumps(str(repository))}); "
                "metadataSources { gradleMetadata(); mavenPom() } }"
                if wrong_source else "")
            # Ignore Kotlin stdlib only in this fixture: the test is about the exact
            # SPAKE2 graph and bytes, without resolving unrelated remote libraries.
            build = f"""
import org.gradle.api.attributes.Attribute
import org.gradle.api.attributes.Usage
import org.gradle.api.attributes.Category
repositories {{
    maven {{
        name = 'fixtureCandidate'
        url = uri({json.dumps(str(used_repository))})
        metadataSources {{ gradleMetadata(); mavenPom() }}
    }}
    {additional_repository}
}}
def configureCandidate = {{ c, platform, usage ->
    c.canBeResolved = true
    c.canBeConsumed = false
    c.attributes {{
        attribute(Usage.USAGE_ATTRIBUTE, objects.named(Usage, usage))
        attribute(Category.CATEGORY_ATTRIBUTE, objects.named(Category, 'library'))
        attribute(Attribute.of('org.jetbrains.kotlin.platform.type', String), platform)
        if (platform == 'native') {{
            attribute(Attribute.of('org.jetbrains.kotlin.native.target', String), 'linux_x64')
        }}
    }}
    c.exclude(group: 'org.jetbrains.kotlin')
}}
def consumer = configurations.create('candidateConsumer')
configureCandidate(consumer, 'jvm', 'java-api')
def android = configurations.create('candidateAndroid')
configureCandidate(android, 'androidJvm', 'java-runtime')
def nativeConsumer = configurations.create('candidateNative')
configureCandidate(nativeConsumer, 'native', 'kotlin-api')
['candidateConsumer', 'candidateAndroid', 'candidateNative'].each {{ name ->
    dependencies.add(name, 'io.github.flyfish233:spake2-legacy:{VERSION}')
}}
{changes}
apply from: {json.dumps(str(ROOT / 'gradle/spake2-maven.gradle'))}
"""
            if extra_configuration:
                build += f"""
def incomplete = configurations.create('incompleteConsumer')
configureCandidate(incomplete, 'jvm', 'java-api')
incomplete.exclude(group: 'io.github.flyfish233', module: 'spake2-primitives')
dependencies.add('incompleteConsumer', 'io.github.flyfish233:spake2-legacy:{VERSION}')
"""
            (fixture / "build.gradle").write_text(build)
            report = fixture / "build/reports/spake2-maven-resolution.json"
            report.parent.mkdir(parents=True)
            report.write_text('{"status":"stale success must be removed"}\n')
            configurations = "candidateConsumer,candidateAndroid,candidateNative"
            if extra_configuration:
                configurations += ",incompleteConsumer"
            command = [self.executable, "--offline", "--no-daemon", "--console=plain",
                       "--no-configuration-cache", "--max-workers=2", "-p", str(fixture),
                       "-Dorg.gradle.java.installations.auto-download=false",
                       f"-Pspake2Repository={repository}",
                       f"-Pspake2Configurations={configurations}",
                       "verifySpake2MavenResolution"]
            result = subprocess.run(command, text=True, stdout=subprocess.PIPE,
                                    stderr=subprocess.STDOUT, timeout=180)
            (self.output / f"{name}.log").write_text(result.stdout)
            if expected is None:
                self.assertEqual(result.returncode, 0, result.stdout[-12000:])
                evidence = json.loads(report.read_text())
                self.assertEqual(evidence["version"], VERSION)
                self.assertEqual(evidence["origin_binding"],
                                 "gradle-9.6-repository-name-to-unique-descriptor")
                self.assertTrue(evidence["repository_id"])
                self.assertEqual(evidence["repository_name"], "fixtureCandidate")
                for item in evidence["artifacts"] + evidence["resolved_components"]:
                    self.assertEqual(item["repository_id"], evidence["repository_id"])
                    self.assertEqual(item["repository_name"], evidence["repository_name"])
                for configuration, suffix in [("candidateConsumer", "-jvm"),
                                              ("candidateAndroid", "-android"),
                                              ("candidateNative", "-linuxx64")]:
                    coordinates = {a["coordinate"] for a in evidence["artifacts"]
                                   if a["configuration"] == configuration}
                    self.assertEqual(coordinates, {
                        f"io.github.flyfish233:spake2-{module}{suffix}:{VERSION}"
                        for module in ("legacy", "primitives")})
                (self.output / "positive-resolution.json").write_text(
                    json.dumps(evidence, indent=2) + "\n")
            else:
                self.assertNotEqual(result.returncode, 0, result.stdout)
                self.assertIn(expected, result.stdout)
                self.assertFalse(report.exists(), "failed gate left a stale success report")

    def test_real_pinned_platform_binaries(self):
        self.run_case("positive-platforms")

    def test_wrong_requested_version_forced_to_candidate(self):
        self.run_case("wrong-version", changes=f"""
consumer.dependencies.clear()
dependencies.add('candidateConsumer', 'io.github.flyfish233:spake2-legacy:99.0.0')
consumer.resolutionStrategy.force('io.github.flyfish233:spake2-legacy:{VERSION}')
""", expected="SPAKE2 request is not the fixed candidate")

    def test_missing_primitives_in_one_configuration(self):
        self.run_case("missing-primitives", extra_configuration=True,
                      expected="Required transitive Maven component missing in incompleteConsumer: spake2-primitives")

    def test_illegal_project_substitution(self):
        self.run_case("project-substitution", changes="""
consumer.resolutionStrategy.dependencySubstitution {
    substitute module('io.github.flyfish233:spake2-legacy') using project(':replacement')
}
""", expected="SPAKE2 project substitution rejected")

    def test_identical_bytes_from_different_repository(self):
        self.run_case("wrong-repository", wrong_source=True,
                      expected="SPAKE2 artifact came from a different repository")

    def test_modified_candidate_binary(self):
        self.run_case("modified-binary", corrupt=True,
                      expected="Fixed Maven candidate is missing or changed")


if __name__ == "__main__":
    unittest.main()
