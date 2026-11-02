#!/usr/bin/env python3
"""Identify the installed, unmodified official SDK target without rooting it."""
import argparse
import hashlib
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    properties = dict(line.split("=", 1) for line in (args.image_dir / "source.properties").read_text().splitlines()
                      if "=" in line and not line.startswith("#"))
    assert properties["Pkg.Revision"] == "9", "SDK revision changed; review the recorded official package before use"
    assert properties["AndroidVersion.ApiLevel"] == "35"
    assert properties["SystemImage.TagId"] == "google_apis_playstore"
    assert properties["SystemImage.Abi"] == "x86_64"
    files = []
    for name in ("system.img", "vendor.img", "ramdisk.img", "kernel-ranchu", "source.properties", "package.xml"):
        path = args.image_dir / name
        assert path.is_file(), f"Missing official SDK image component: {name}"
        with path.open("rb") as handle:
            digest = hashlib.file_digest(handle, "sha256").hexdigest()
        files.append({"file": name, "bytes": path.stat().st_size, "sha256": digest})
    report = {"schema": 1, "sdk_package": "system-images;android-35;google_apis_playstore;x86_64",
              "properties": properties, "files": files, "modified": False,
              "scope": "Hashes identify installed official SDK platform inputs. No claim that AOSP reference tag is exact source of Google Play binaries.",
              "runtime_adbd_elf_hash": "Unavailable to unprivileged shell on this user image; no root or permissions change attempted."}
    args.output.write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    main()
