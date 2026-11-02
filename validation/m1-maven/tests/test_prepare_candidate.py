"""Bounded restoration checks against the actual retained candidate."""
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import tarfile
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[3]
SPEC = importlib.util.spec_from_file_location("prepare_candidate", ROOT / "scripts/prepare_spake2_candidate.py")
PREPARE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PREPARE)
MANIFEST = ROOT / "validation/maven-candidate/manifest.json"
LOCK = json.loads(MANIFEST.read_text())
ARCHIVE = MANIFEST.parent / LOCK["archive"]


class PrepareCandidateTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)

    def tearDown(self):
        self.temporary.cleanup()

    def rewritten_archive(self, mutate):
        """Rehash transport metadata so deeper member checks are exercised."""
        archive = self.root / "mutated.tar.xz"
        with tarfile.open(ARCHIVE, "r:xz") as original, tarfile.open(archive, "w:xz") as changed:
            for member in original:
                raw = original.extractfile(member).read()
                member, raw = mutate(member, raw)
                if member is not None:
                    changed.addfile(member, io.BytesIO(raw))
        manifest = dict(LOCK)
        manifest.update(archive=archive.name, size=archive.stat().st_size,
                        sha256=hashlib.sha256(archive.read_bytes()).hexdigest())
        path = self.root / "manifest.json"
        path.write_text(json.dumps(manifest))
        return path

    def test_real_candidate_restores_and_second_run_is_read_only(self):
        repository = PREPARE.prepare(MANIFEST, None, self.root / "output")
        before = {p.relative_to(repository).as_posix(): (p.stat().st_mtime_ns, p.read_bytes())
                  for p in repository.rglob("*") if p.is_file()}
        self.assertEqual(len(before), 219)
        self.assertEqual(repository, PREPARE.prepare(MANIFEST, None, self.root / "output"))
        after = {p.relative_to(repository).as_posix(): (p.stat().st_mtime_ns, p.read_bytes())
                 for p in repository.rglob("*") if p.is_file()}
        self.assertEqual(before, after)

    def test_corrupt_archive_digest_rejected_without_output(self):
        raw = bytearray(ARCHIVE.read_bytes())
        raw[len(raw) // 2] ^= 1
        archive = self.root / "corrupt.tar.xz"
        archive.write_bytes(raw)
        with self.assertRaisesRegex(PREPARE.CandidateError, "SHA-256 mismatch"):
            PREPARE.prepare(MANIFEST, archive, self.root / "output")
        self.assertFalse((self.root / "output").exists())

    def test_missing_primitives_rejected_even_with_updated_transport_digest(self):
        manifest = self.rewritten_archive(lambda member, raw: (None, raw)
            if "/spake2-primitives/" in member.name else (member, raw))
        with self.assertRaisesRegex(PREPARE.CandidateError, "Incomplete candidate archive"):
            PREPARE.prepare(manifest, None, self.root / "output")
        self.assertFalse((self.root / "output").exists())

    def test_path_traversal_rejected_before_writing(self):
        changed = False
        def mutate(member, raw):
            nonlocal changed
            if not changed:
                member.name = "maven/../../escaped"
                changed = True
            return member, raw
        manifest = self.rewritten_archive(mutate)
        with self.assertRaisesRegex(PREPARE.CandidateError, "Unsafe candidate path"):
            PREPARE.prepare(manifest, None, self.root / "output")
        self.assertFalse((self.root / "output").exists())
        self.assertFalse((self.root / "escaped").exists())

    def test_existing_modified_output_is_preserved_and_rejected(self):
        repository = PREPARE.prepare(MANIFEST, None, self.root / "output")
        selected = repository / LOCK["files"][0]["path"]
        selected.write_bytes(b"preserve this local change")
        with self.assertRaisesRegex(PREPARE.CandidateError, "refusing overwrite"):
            PREPARE.prepare(MANIFEST, None, self.root / "output")
        self.assertEqual(selected.read_bytes(), b"preserve this local change")

    def test_existing_symlink_is_preserved_and_rejected(self):
        output = self.root / "output"
        output.mkdir()
        target = self.root / "untouched"
        target.mkdir()
        (output / "maven").symlink_to(target, target_is_directory=True)
        with self.assertRaisesRegex(PREPARE.CandidateError, "not a real directory"):
            PREPARE.prepare(MANIFEST, None, output)
        self.assertTrue((output / "maven").is_symlink())
        self.assertEqual(list(target.iterdir()), [])


if __name__ == "__main__":
    unittest.main()
