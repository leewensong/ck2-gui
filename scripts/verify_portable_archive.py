"""Extract a built ZIP elsewhere, verify every manifest hash, then run GPU checks."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import time
import zipfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def digest(path):
    sha = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b''):
            sha.update(chunk)
    return sha.hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('archive', type=Path)
    parser.add_argument('--destination', type=Path, default=ROOT / 'tmp' / '绿色版 解压验证')
    args = parser.parse_args()
    target = args.destination.resolve()
    if target.exists():
        raise FileExistsError(f'Refusing to overwrite existing verification directory: {target}')
    target.mkdir(parents=True)
    archive = args.archive.resolve()
    print(f'Extracting to: {target}', flush=True)
    with zipfile.ZipFile(archive) as z:
        for item in z.infolist():
            resolved = (target / item.filename).resolve()
            if not resolved.is_relative_to(target):
                raise ValueError(f'Unsafe ZIP entry: {item.filename}')
        top_levels = {Path(item.filename).parts[0] for item in z.infolist()}
        assert len(top_levels) == 1, top_levels
        z.extractall(target)
    package = target / next(iter(top_levels))
    manifest = json.loads((package / 'BUILD_MANIFEST.json').read_text(encoding='utf-8'))
    print(f"Verifying SHA-256 for {len(manifest['files'])} extracted files…", flush=True)
    def verify(item):
        relative, expected = item
        path = package / relative
        assert path.is_file(), str(path)
        assert path.stat().st_size == expected['size'], str(path)
        assert digest(path) == expected['sha256'], str(path)
    with ThreadPoolExecutor(max_workers=3) as pool:
        list(pool.map(verify, manifest['files'].items()))
    environment = dict(os.environ)
    environment['PATH'] = str(Path(os.environ['SystemRoot']) / 'System32') + os.pathsep + os.environ['SystemRoot']
    environment['PYTHONHOME'] = r'C:\missing-python-home'
    environment['PYTHONPATH'] = r'C:\missing-python-path'
    report = ROOT / 'out_setup' / 'portable-extracted-test.json'
    options = {'creationflags': subprocess.CREATE_NO_WINDOW} if os.name == 'nt' else {}
    print('Running relocated GUI/language/drag-and-drop/GPU batch checks with a clean PATH…', flush=True)
    command = [str(package / 'runtime/python.exe'), '-I', '-B', str(package / 'bootstrap.py'), '--check', '--smoke', '--report', str(report)]
    result = subprocess.run(command, cwd=target.parent, env=environment, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=360, **options)
    print(result.stdout, flush=True)
    if result.stderr:
        print(result.stderr, flush=True)
    assert result.returncode == 0, result.returncode
    data = json.loads(report.read_text(encoding='utf-8'))
    assert data['status'] == 'passed'
    # Exercise the real native .exe with a quoted, spaced output path as well.
    native_report = ROOT / 'out_setup' / 'native launcher check.json'
    assert not native_report.exists(), native_report
    subprocess.run([str(package / 'CorridorKey.exe'), '--check', '--report', str(native_report)], cwd=target.parent, env=environment, timeout=20, check=True, **options)
    deadline = time.monotonic() + 60
    while not native_report.exists() and time.monotonic() < deadline:
        time.sleep(0.25)
    native = json.loads(native_report.read_text(encoding='utf-8'))
    assert native['status'] == 'passed', native
    summary = {'status': 'passed', 'archive': str(archive), 'archive_sha256': digest(archive), 'extracted_root': str(package), 'manifest_files_verified': len(manifest['files']), 'gpu_jobs': len(data['jobs']), 'outputs_verified': sum(job['outputs'] for job in data['jobs']), 'native_launcher': 'passed'}
    (ROOT / 'out_setup').mkdir(parents=True, exist_ok=True)
    (ROOT / 'out_setup' / 'portable-release-verification.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(summary, ensure_ascii=False, indent=2), flush=True)


if __name__ == '__main__':
    main()
