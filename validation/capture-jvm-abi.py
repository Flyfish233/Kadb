#!/usr/bin/env python3
"""Capture the JVM/Android bytecode surface independently of source layout.

This intentionally includes Kotlin internal declarations visible to Java. It
is a conservative bytecode inventory, complementary to Kotlin ABI validation
and the precompiled consumer tests, not a source-compatibility proof.
"""
import argparse
import io
from pathlib import Path
import subprocess
import tempfile
import zipfile


def dump(archive: Path) -> str:
    data = archive.read_bytes()
    if archive.suffix == ".aar":
        with zipfile.ZipFile(io.BytesIO(data)) as aar:
            data = aar.read("classes.jar")
    with tempfile.TemporaryDirectory(prefix="kadb-abi-") as folder:
        jar = Path(folder) / "classes.jar"
        jar.write_bytes(data)
        with zipfile.ZipFile(jar) as contents:
            classes = sorted(name[:-6].replace("/", ".") for name in contents.namelist()
                             if name.startswith("com/flyfishxu/kadb/") and name.endswith(".class"))
        if not classes:
            raise RuntimeError(f"No Kadb classes in {archive}")
        parts = []
        for offset in range(0, len(classes), 100):
            raw = subprocess.check_output(["javap", "-classpath", str(jar), "-protected", "-s", "-constants",
                                           *classes[offset:offset + 100]], text=True)
            parts.extend(line.rstrip() for line in raw.splitlines() if not line.startswith("Compiled from "))
        return "\n".join(parts) + "\n"


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("archive", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    result = dump(args.archive)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(result)
    print(f"Captured {len(result.splitlines())} ABI lines from {args.archive.name}")
