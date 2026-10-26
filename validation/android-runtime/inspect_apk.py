#!/usr/bin/env python3
"""Require actual DEX class definitions for the external Android runtime consumer."""

import argparse
import hashlib
import json
from pathlib import Path
import re
import struct
import zipfile

REQUIRED_CLASSES = {
    "Lcom/flyfishxu/kadb/validation/runtime/RuntimeInstrumentation;",
    "Lcom/flyfishxu/kadb/Kadb;",
    "Lcom/flyfishxu/kadb/cert/KadbCert;",
    "Lio/github/flyfish233/spake2/legacy/LegacySpake25519;",
}


def dex_classes(data: bytes) -> set[str]:
    if len(data) < 112 or not re.fullmatch(rb"dex\n0[0-9]{2}\x00", data[:8]):
        raise ValueError("Expected a standard Android DEX file")
    if struct.unpack_from("<I", data, 40)[0] != 0x12345678:
        raise ValueError("Unsupported DEX byte order")
    string_count, string_offset = struct.unpack_from("<II", data, 56)
    type_count, type_offset = struct.unpack_from("<II", data, 64)
    class_count, class_offset = struct.unpack_from("<II", data, 96)
    if (string_offset + string_count * 4 > len(data) or type_offset + type_count * 4 > len(data)
            or class_offset + class_count * 32 > len(data)):
        raise ValueError("DEX index table exceeds file bounds")
    result = set()
    for index in range(class_count):
        type_index = struct.unpack_from("<I", data, class_offset + index * 32)[0]
        if type_index >= type_count:
            raise ValueError("DEX class has invalid type index")
        string_index = struct.unpack_from("<I", data, type_offset + type_index * 4)[0]
        if string_index >= string_count:
            raise ValueError("DEX type has invalid string index")
        offset = struct.unpack_from("<I", data, string_offset + string_index * 4)[0]
        for _ in range(5):
            if offset >= len(data):
                raise ValueError("Truncated DEX string length")
            current = data[offset]
            offset += 1
            if current < 128:
                break
        else:
            raise ValueError("Invalid DEX string length")
        end = data.find(b"\0", offset)
        if end < 0:
            raise ValueError("Unterminated DEX class descriptor")
        # Required descriptors are ASCII. Other valid MUTF-8 names need not be
        # decoded semantically for this presence/inventory check.
        result.add(data[offset:end].decode("utf-8", "replace"))
    return result


def inspect_apk(path: Path) -> dict:
    classes = set()
    files = []
    with zipfile.ZipFile(path) as apk:
        bad = apk.testzip()
        if bad:
            raise ValueError(f"APK member failed CRC: {bad}")
        for name in sorted(apk.namelist()):
            if not re.fullmatch(r"classes(?:[2-9]|[1-9][0-9]+)?\.dex", name):
                continue
            data = apk.read(name)
            definitions = dex_classes(data)
            duplicate = classes & definitions
            if duplicate:
                raise ValueError("Duplicate class definitions across APK DEX files")
            classes.update(definitions)
            files.append({"name": name, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest(),
                          "class_definitions": len(definitions)})
    if not REQUIRED_CLASSES <= classes:
        raise ValueError(f"APK lacks actual DEX class definitions: {sorted(REQUIRED_CLASSES - classes)}")
    if any(name.startswith("Lorg/conscrypt/") or name.startswith("Lcom/flyfish233/crypto/spake2/") for name in classes):
        raise ValueError("Host-only Conscrypt or historical SPAKE oracle was packaged in the Android APK")
    return {"status": "verified", "apk_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "apk_bytes": path.stat().st_size, "dex_files": files,
            "required_class_definitions": sorted(REQUIRED_CLASSES),
            "host_oracle_classes_present": False,
            "scope": "APK/DEX packaging only; Android execution is a separate mandatory gate"}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("apk", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args()
    result = inspect_apk(arguments.apk)
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result))
