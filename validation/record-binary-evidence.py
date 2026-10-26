#!/usr/bin/env python3
"""Associate actual CI artifacts with the successfully uploaded source package."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess


def sha256(path):
    with path.open('rb') as source:
        return hashlib.file_digest(source, 'sha256').hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-url', required=True)
    parser.add_argument('--source-sha256', required=True)
    parser.add_argument('--source-lock-sha256', required=True)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip()
    if commit != os.environ['GITHUB_SHA']:
        raise RuntimeError('Binary job checkout differs from the declared CI source commit')
    if subprocess.check_output(['git', 'status', '--porcelain', '--untracked-files=no'], text=True).strip():
        raise RuntimeError('Tracked source files changed during the binary job')
    source_lock = Path('validation/source-bundle/dependencies.lock.json')
    if sha256(source_lock) != args.source_lock_sha256:
        raise RuntimeError('Binary job dependency-source lock differs from the source job')
    if not re.fullmatch(r'[a-f0-9]{64}', args.source_sha256):
        raise RuntimeError('Missing actual source package checksum')
    repository = os.environ['GITHUB_REPOSITORY']
    run_id = os.environ['GITHUB_RUN_ID']
    run_url = f"{os.environ['GITHUB_SERVER_URL']}/{repository}/actions/runs/{run_id}"
    if not args.source_url.startswith(run_url + '/artifacts/'):
        raise RuntimeError('Source upload URL must identify an actual artifact from this exact run')
    candidates = set()
    for pattern in (
        'kadb/build/bin/**/*.kexe', 'kadb-mdns/build/bin/**/*.kexe',
        'kadb/build/bin/**/Kadb.framework/Kadb',
        'validation/native-adbd/build/bin/**/*.kexe',
        'kadb/build/outputs/aar/*.aar', 'kadb-mdns/build/outputs/aar/*.aar',
        'validation/android-fixture/build/outputs/apk/**/*.apk',
        'kadb/build/classes/kotlin/**/*.klib', 'evidence/swift-consumer',
    ):
        candidates.update(path for path in Path('.').glob(pattern) if path.is_file())
    artifacts = [{'path': path.as_posix(), 'bytes': path.stat().st_size, 'sha256': sha256(path)}
                 for path in sorted(candidates)]
    report = {'schema': 1, 'commit': commit, 'run_url': run_url,
              'source_artifact_url': args.source_url,
              'source_package_sha256': args.source_sha256,
              'source_lock_sha256': args.source_lock_sha256,
              'binary_artifacts': artifacts,
              'scope': 'Commit/lock and actual artifact association. Build/test status is in the job logs and reports; hashes alone do not prove compilation or reproducible binaries.'}
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / 'binary-source-association.json').write_text(json.dumps(report, indent=2) + '\n')
    (args.output / 'SOURCE_LOCATION.txt').write_text(
        f'Exact source commit: {commit}\nActual source artifact: {args.source_url}\n'
        f'Source artifact name: corresponding-source-{commit}\n'
        f'Source package SHA-256: {args.source_sha256}\n'
        f'Dependency-source lock SHA-256: {args.source_lock_sha256}\n'
        f'CI run and execution evidence: {run_url}\n'
        'The source artifact contains actual pinned library source archives and notices.\n'
        'Keep it alongside any copied binaries; this CI bundle is not a final distribution-license certification.\n'
    )
    print(json.dumps({'commit': commit, 'binary_artifacts_recorded': len(artifacts), 'source_artifact_url': args.source_url}))


if __name__ == '__main__':
    main()
