#!/usr/bin/env python3
"""Inspect the actual Mach-O/archive deployment stamps; never infer an OS runtime test."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import subprocess


def version(value):
    parts = tuple(map(int, value.split('.')))
    return parts + (0,) * (3 - len(parts))


def inspect(args, report):
    artifact = args.artifact.resolve(strict=True)
    with artifact.open('rb') as source:
        report['sha256'] = hashlib.file_digest(source, 'sha256').hexdigest()
    report['bytes'] = artifact.stat().st_size
    report['file'] = subprocess.check_output(['file', str(artifact)], text=True).strip()
    architectures = subprocess.check_output(['xcrun', 'lipo', '-archs', str(artifact)], text=True).strip()
    report['architectures'] = architectures.split()
    if report['architectures'] != [args.architecture]:
        raise RuntimeError('Unexpected architecture(s): ' + architectures)
    load_commands = subprocess.check_output(['xcrun', 'otool', '-l', str(artifact)], text=True)
    args.output.with_suffix('.otool.log').write_text(load_commands)
    records = Counter()
    aliases = {'1': 'macos', 'MACOS': 'macos', 'MACOSX': 'macos',
               '2': 'ios', 'IOS': 'ios', '7': 'ios-simulator', 'IOSSIMULATOR': 'ios-simulator'}
    for block in re.split(r'(?m)^Load command \d+\s*$', load_commands):
        command = re.search(r'(?m)^\s*cmd (LC_BUILD_VERSION|LC_VERSION_MIN_MACOSX|LC_VERSION_MIN_IPHONEOS)\s*$', block)
        if not command:
            continue
        kind = command.group(1)
        if kind == 'LC_BUILD_VERSION':
            platform = re.search(r'(?m)^\s*platform (\S+)\s*$', block)
            minimum = re.search(r'(?m)^\s*minos ([\d.]+)\s*$', block)
            if not platform or not minimum:
                raise RuntimeError('Incomplete LC_BUILD_VERSION record')
            platform_name = aliases.get(platform.group(1).upper(), platform.group(1))
        else:
            minimum = re.search(r'(?m)^\s*version ([\d.]+)\s*$', block)
            if not minimum:
                raise RuntimeError('Incomplete legacy deployment-version record')
            platform_name = 'macos' if kind == 'LC_VERSION_MIN_MACOSX' else 'ios'
        records[(platform_name, minimum.group(1), kind)] += 1
    report['deployment_records'] = [dict(platform=p, minimum_os=v, command=k, count=n)
                                    for (p, v, k), n in sorted(records.items())]
    if not records:
        raise RuntimeError('No actual deployment-version records found')
    if any(p != args.platform for p, _, _ in records):
        raise RuntimeError('Archive includes an unexpected platform stamp')
    if any(version(v) > version(args.maximum_minimum_os) for _, v, _ in records):
        raise RuntimeError('An object requires an OS newer than the declared deployment target')
    report['declared_deployment_target'] = args.maximum_minimum_os
    report['scope'] = {'actual_artifact_inspected': True, 'oldest_os_runtime_executed': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--artifact', required=True, type=Path)
    parser.add_argument('--architecture', choices=['arm64', 'x86_64'], required=True)
    parser.add_argument('--platform', choices=['macos', 'ios', 'ios-simulator'], required=True)
    parser.add_argument('--maximum-minimum-os', required=True)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    report = {'schema': 1, 'status': 'failed', 'artifact': str(args.artifact)}
    try:
        inspect(args, report)
        report['status'] = 'passed'
    except Exception as error:
        report['error'] = str(error)
    args.output.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report))
    return 0 if report['status'] == 'passed' else 1


if __name__ == '__main__':
    raise SystemExit(main())
