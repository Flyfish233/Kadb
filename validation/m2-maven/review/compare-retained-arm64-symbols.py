#!/usr/bin/env python3
"""Read-only symbol evidence for two retained iOS Simulator ARM64 static archives.

This deliberately limited reader accepts BSD ar containing thin little-endian
ARM64 MH_OBJECT files. It is not a Mach-O linker or a general ABI checker. The
complete migrated output is checked against the actual Apple `nm -gU` log.
"""

import argparse
from collections import Counter
import gzip
import hashlib
import json
from pathlib import Path
import re
import struct
import subprocess
import zipfile


BASELINE_SHA = "49a88b14e9b731e4c086c920eb74664450c79d9f"
MIGRATED_SHA = "677a39e74ef568ac91bec6db2885929003cc709e"
FRAMEWORK = "kadb/build/bin/iosSimulatorArm64/debugFramework/Kadb.framework/"
ARCHIVE_HASHES = {
    "baseline": "d2c0b7733739d97b4291e7d9eaddc4bcb485c1a600ada8cde5c3baffaf60b684",
    "migrated": "0c210932ea3e0cc86af7ed281b7e7b1644a6b10b1703e78148870f165d95af5c",
}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def span(data, start, length):
    require(start >= 0 and length >= 0 and start + length <= len(data), "range outside input")
    return data[start:start + length]


def cstring(data, offset):
    require(0 <= offset < len(data), "string offset outside table")
    end = data.find(b"\0", offset)
    require(end >= offset, "unterminated symbol string")
    return data[offset:end].decode("utf-8")


def parse_object(data, member):
    header = struct.unpack("<8I", span(data, 0, 32))
    magic, cpu, subtype, kind, commands, commands_size, flags, reserved = header
    require(magic == 0xFEEDFACF and cpu == 0x0100000C and kind == 1,
            "expected thin little-endian ARM64 MH_OBJECT: " + member)
    span(data, 32, commands_size)
    offset, tables, sections = 32, [], [None]
    for _ in range(commands):
        command, size = struct.unpack("<II", span(data, offset, 8))
        require(size >= 8 and offset + size <= 32 + commands_size, "invalid load command")
        command_data = span(data, offset, size)
        if command == 2:  # LC_SYMTAB
            require(size == 24, "unexpected LC_SYMTAB size")
            tables.append(struct.unpack("<6I", command_data)[2:])
        elif command == 0x19:  # LC_SEGMENT_64
            span(command_data, 0, 72)
            count = struct.unpack_from("<I", command_data, 64)[0]
            require(size == 72 + count * 80, "invalid section table")
            for index in range(count):
                section = span(command_data, 72 + index * 80, 80)
                section_name = section[:16].split(b"\0", 1)[0].decode("ascii")
                segment_name = section[16:32].split(b"\0", 1)[0].decode("ascii")
                sections.append(segment_name + "," + section_name)
        offset += size
    require(offset == 32 + commands_size and len(tables) == 1, "load-command/table count mismatch")
    symbol_offset, count, string_offset, string_size = tables[0]
    symbol_data = span(data, symbol_offset, count * 16)
    strings = span(data, string_offset, string_size)
    result = []
    for index in range(count):
        name_index, symbol_type, section, descriptor, value = struct.unpack_from(
            "<IBBHQ", symbol_data, index * 16)
        if symbol_type & 0xE0 or not symbol_type & 1:  # N_STAB, N_EXT
            continue
        basic_type = symbol_type & 0x0E
        # nm -U retains common definitions (N_UNDF with nonzero n_value).
        if basic_type in (0, 0x0C) and not (basic_type == 0 and value != 0):
            continue
        require(basic_type in (0, 2, 0x0A, 0x0E), "unsupported external definition type")
        require(section < len(sections), "invalid symbol section")
        name = cstring(strings, name_index)
        require(bool(name), "empty defined external symbol")
        result.append({"member": member, "name": name, "n_type": symbol_type,
                       "n_desc": descriptor, "section": sections[section], "value": value})
    return result


def parse_archive(data):
    require(data[:8] == b"!<arch>\n", "expected BSD ar archive")
    offset, members, indexes, symbols = 8, 0, 0, []
    while offset < len(data):
        header = span(data, offset, 60)
        require(header[58:60] == b"`\n", "invalid ar member header")
        length = int(header[48:58])
        name = header[:16].decode("ascii").strip()
        payload = span(data, offset + 60, length)
        if name.startswith("#1/"):
            name_length = int(name[3:])
            name = span(payload, 0, name_length).rstrip(b"\0").decode("utf-8")
            payload = payload[name_length:]
        else:
            name = name.rstrip("/")
        if name in ("__.SYMDEF", "__.SYMDEF SORTED"):
            indexes += 1
        else:
            symbols.extend(parse_object(payload, name))
            members += 1
        offset += 60 + length + length % 2
    require(offset == len(data) and indexes == 1, "ar extent/index mismatch")
    return symbols, members


def parse_nm(text):
    result, member = Counter(), None
    for line in text.splitlines():
        if not line:
            continue
        if line.endswith(":"):
            member = line[:-1]
            continue
        match = re.fullmatch(r"([0-9a-fA-F]+) ([A-Za-z?]) (.+)", line)
        require(member is not None and match is not None, "unexpected Apple nm output")
        result[(member, match[3], int(match[1], 16))] += 1
    return result


def symbol_attributes(symbols):
    result = {}
    for symbol in symbols:
        if symbol["n_type"] & 0x10:  # N_PEXT is private external.
            continue
        name = symbol["name"]
        result.setdefault(name, []).append(
            {key: symbol[key] for key in ("member", "n_type", "n_desc", "section")})
    for entries in result.values():
        entries.sort(key=lambda item: json.dumps(item, sort_keys=True))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline-zip", type=Path, required=True)
    parser.add_argument("--migrated-zip", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    repo = Path(__file__).resolve().parents[3]
    inputs, all_symbols, headers = {}, {}, {}
    nm_bytes = None
    for label, path in (("baseline", args.baseline_zip), ("migrated", args.migrated_zip)):
        with path.open("rb") as stream:
            archive_hash = hashlib.file_digest(stream, "sha256").hexdigest()
        require(archive_hash == ARCHIVE_HASHES[label], label + " artifact hash mismatch")
        with zipfile.ZipFile(path) as archive:
            binary = archive.read(FRAMEWORK + "Kadb")
            headers[label] = archive.read(FRAMEWORK + "Headers/Kadb.h")
            if label == "migrated":
                nm_bytes = archive.read("evidence/framework-symbols.log")
        symbols, members = parse_archive(binary)
        all_symbols[label] = symbols
        inputs[label] = {"source_sha": BASELINE_SHA if label == "baseline" else MIGRATED_SHA,
                         "artifact_id": 12655313986 if label == "baseline" else 13128890597,
                         "run_id": 40331404006 if label == "baseline" else 41415836057,
                         "zip_bytes": path.stat().st_size, "zip_sha256": archive_hash,
                         "framework_archive_member": FRAMEWORK + "Kadb",
                         "framework_bytes": len(binary), "framework_sha256": sha(binary),
                         "header_sha256": sha(headers[label]), "arm64_object_members": members,
                         "nm_external_definition_entries": len(symbols)}
    nm_path = repo / "validation/m2-maven/runs/41415836057/iosSimulatorArm64/evidence/framework-symbols.log.gz"
    compressed_nm = nm_path.read_bytes()
    require(gzip.decompress(compressed_nm) == nm_bytes, "retained nm log differs from original artifact")
    reference_nm = parse_nm(nm_bytes.decode("utf-8"))
    parsed_nm = Counter((item["member"], item["name"], item["value"])
                        for item in all_symbols["migrated"])
    require(reference_nm == parsed_nm, "parser does not reproduce actual Apple nm entries")
    require(headers["baseline"] == headers["migrated"], "framework headers differ")
    frozen_header = repo / "validation/m2-maven/baseline/darwin-arm-40331404006/Kadb-iosSimulatorArm64.h"
    require(frozen_header.read_bytes() == headers["baseline"], "frozen baseline header mismatch")
    header_text = headers["baseline"].decode("utf-8")
    classes = sorted(re.findall(r"^@interface\s+(\w+)(?:<[^\n]+>)?\s*:", header_text, re.M))
    expected_objc = {f"_{prefix}_$_{name}" for name in classes
                     for prefix in ("OBJC_CLASS", "OBJC_METACLASS")}
    c_headers, expected_c = [], set()
    for header in ("kadb_crypto.h", "kadb_transport.h"):
        path = "kadb/src/nativeInterop/cinterop/" + header
        original = subprocess.check_output(["git", "show", BASELINE_SHA + ":" + path], cwd=repo)
        migrated = subprocess.check_output(["git", "show", MIGRATED_SHA + ":" + path], cwd=repo)
        require(original == migrated, "C bridge declaration header changed")
        declarations = set(re.findall(r"\b(kadb_[A-Za-z0-9_]+)\s*\(", original.decode("utf-8")))
        expected_c.update("_" + name for name in declarations)
        c_headers.append({"path": path, "sha256": sha(original), "function_declarations": len(declarations)})
    public = {label: symbol_attributes(symbols) for label, symbols in all_symbols.items()}
    original_names, migrated_names = set(public["baseline"]), set(public["migrated"])
    removed, added = sorted(original_names - migrated_names), sorted(migrated_names - original_names)
    changed = sorted(name for name in original_names & migrated_names
                     if public["baseline"][name] != public["migrated"][name])
    require(not removed and not added and not changed, "non-private symbol ABI evidence differs")
    require(expected_c <= original_names and expected_c <= migrated_names, "C bridge definition missing")
    historical_absence = sorted(expected_objc - original_names)
    require(expected_objc - migrated_names == set(historical_absence), "new ObjC definition absence")
    all_original = {item["name"] for item in all_symbols["baseline"]}
    all_migrated = {item["name"] for item in all_symbols["migrated"]}
    report = {
        "schema": 1, "verdict": "PASS", "scope": "iOS Simulator ARM64 static archive external symbol preservation",
        "inputs": inputs,
        "parser_crosscheck": {"reference_command": "xcrun nm -gU <actual migrated framework>",
                              "nm_log_sha256": sha(nm_bytes), "retained_gzip_sha256": sha(compressed_nm),
                              "entries_compared": sum(reference_nm.values()),
                              "compared_fields": ["archive member", "symbol name", "n_value"],
                              "exact_multiset_match": True, "includes_private_external_and_common": True},
        "non_private_external_definitions": {
            "baseline_entries": sum(len(entries) for entries in public["baseline"].values()),
            "migrated_entries": sum(len(entries) for entries in public["migrated"].values()),
            "baseline_unique_names": len(original_names), "migrated_unique_names": len(migrated_names),
            "removed": removed, "added": added, "attribute_changes": changed,
            "attributes_compared": ["archive member", "n_type", "n_desc", "segment and section names"],
            "identical_name_list_sha256": sha(("\n".join(sorted(original_names)) + "\n").encode())},
        "framework_header": {"byte_identical": True, "declared_classes_excluding_categories": len(classes),
                             "expected_class_and_metaclass_names": len(expected_objc),
                             "present_in_both": len(expected_objc & original_names & migrated_names),
                             "absent_in_both_original_and_migrated": historical_absence,
                             "new_missing_symbols": [], "framework_c_function_declarations": 0,
                             "framework_c_declaration_check": "manual inspection of actual Kadb.h; this script is not a C declaration parser"},
        "c_bridge": {"declaration_headers": c_headers, "declared_functions": len(expected_c),
                     "present_in_both": len(expected_c & original_names & migrated_names),
                     "classification": "Native C bridge; not separately exposed as a C API in framework Kadb.h"},
        "all_external_names_including_private": {"baseline_unique": len(all_original),
                                                  "migrated_unique": len(all_migrated),
                                                  "removed": sorted(all_original - all_migrated),
                                                  "added_count": len(all_migrated - all_original)},
        "non_private_symbol_inventory": [{"name": name, "definitions": public["baseline"][name],
                                          "category": ("framework-header-objc" if name in expected_objc else
                                                       "native-c-bridge" if name in expected_c else "runtime")}
                                         for name in sorted(original_names)],
        "reproducer_sha256": sha(Path(__file__).read_bytes()),
        "format_references": [
            "https://github.com/apple-oss-distributions/xnu/blob/main/EXTERNAL_HEADERS/mach-o/nlist.h",
            "https://github.com/apple-oss-distributions/xnu/blob/main/EXTERNAL_HEADERS/mach-o/loader.h"],
        "limitations": [
            "This is a comparison of static archive object symbols, not a dynamic library export-trie or install-name check.",
            "No claim of arbitrary ABI compatibility: Objective-C method encodings, runtime layouts, calling conventions, and old precompiled consumer relinking were not independently checked.",
            "The framework header declares KadbNumber but its class and metaclass definitions are absent from both compared archives; no new loss is observed.",
            "Only exact original and migrated iOS Simulator ARM64 archives are compared here; no x64 historical binary baseline is asserted.",
            "Symbol addresses are expected to vary; values are checked only to validate the parser against the same migrated artifact's Apple nm output.",
            "Framework header equality and existing macOS Swift consumer execution are separate evidence; this script runs no Apple compilation or execution."],
    }
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"verdict": report["verdict"], "nm_entries": sum(reference_nm.values()),
                      "unchanged_non_private_entries": report["non_private_external_definitions"]["baseline_entries"],
                      "unchanged_non_private_unique_names": len(original_names),
                      "header_objc_symbols": len(expected_objc & original_names),
                      "c_bridge_symbols": len(expected_c), "historical_absence": historical_absence}))


if __name__ == "__main__":
    main()
