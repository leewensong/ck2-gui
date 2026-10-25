"""Build the local, relocatable Windows runtime; optionally create a ZIP64 archive.

This project is an overlay for a CorridorKey 2.0 checkout.  The expected
development layout is:

    CorridorKey2.0/
      corridorkey/  infer.py  weights/  vfms/  third_party/
      ck2-gui/      <- this project

The portable bundle copies the GUI package plus the upstream runtime and
weights into one self-contained folder.  Large assets are never stored in this
repository; they are taken from the sibling CorridorKey checkout at build time.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import os
import shutil
import subprocess
import sys
import time
import tempfile
import zipfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parents[1]
CK2_ROOT = PROJECT_DIR.parent
VERSION = '1.1.1'
DEFAULT_STAGE = PROJECT_DIR / 'dist' / f'CorridorKey2.0-Portable-v{VERSION}'


def require_ck2_root() -> None:
    if not (CK2_ROOT / 'infer.py').is_file() or not (CK2_ROOT / 'corridorkey').is_dir():
        raise FileNotFoundError(
            f'CorridorKey 2.0 checkout not found at {CK2_ROOT}. '
            'Place this project inside the CorridorKey 2.0 root before building.')


def ignore_files(directory, names):
    ignored = {name for name in names if name in {'.git', '.cache', '__pycache__', '_virtualenv.pth', '_virtualenv.py', 'pyvenv.cfg'} or name.endswith(('.pyc', '.pyo'))}
    return ignored


def copy_tree(source, target):
    print(f'Copy: {source} -> {target}', flush=True)
    shutil.copytree(source, target, ignore=ignore_files, dirs_exist_ok=False)


def sha256(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def stage_runtime(stage):
    require_ck2_root()
    if stage.exists():
        raise FileExistsError(f'Refusing to overwrite an existing runtime: {stage}')
    if not (PROJECT_DIR / 'packaging' / 'CorridorKey.exe').is_file():
        raise FileNotFoundError('Compile packaging/launcher.c first (see packaging/BUILD.md).')
    stage.mkdir(parents=True)
    runtime = stage / 'runtime'
    runtime.mkdir()
    base = Path(sys.base_prefix)
    for name in ('python.exe', 'pythonw.exe', 'python312.dll', 'python3.dll', 'vcruntime140.dll', 'vcruntime140_1.dll', 'LICENSE.txt'):
        shutil.copy2(base / name, runtime / name)
    for name in ('DLLs', 'tcl'):
        copy_tree(base / name, runtime / name)
    # Do not copy a virtualenv or its absolute pyvenv.cfg. Merge its packages into
    # a full standalone CPython layout, leaving the copied base install untouched.
    shutil.copytree(base / 'Lib', runtime / 'Lib', ignore=lambda d, names: ignore_files(d, names) | ({'site-packages'} if Path(d) == base / 'Lib' else set()))
    tasks = [(Path(sys.prefix) / 'Lib/site-packages', runtime / 'Lib/site-packages')]
    tasks += [(PROJECT_DIR / 'ck2gui', stage / 'ck2gui')]
    tasks += [(CK2_ROOT / name, stage / name) for name in ('corridorkey', 'third_party', 'weights', 'vfms')]
    with ThreadPoolExecutor(max_workers=3) as pool:
        list(pool.map(lambda task: copy_tree(*task), tasks))
    # Ship the Microsoft release CRT app-locally, never copying system DLLs or
    # installing a global redistributable. The native launcher itself uses /MT.
    redist = Path(r'C:\Program Files\Microsoft Visual Studio\18\Community\VC\Redist\MSVC\14.51.36231\x64\Microsoft.VC145.CRT')
    if not redist.is_dir():
        raise FileNotFoundError('Set the MSVC release CRT path in the build script for this build host.')
    for dll in redist.glob('*.dll'):
        shutil.copy2(dll, runtime / dll.name)
    for name in ('bootstrap.py', 'runtime_check.py', 'requirements-gui.txt'):
        shutil.copy2(PROJECT_DIR / name, stage / name)
    for name in ('infer.py', 'LICENSE', 'THIRD_PARTY_NOTICES.md', 'requirements.txt'):
        shutil.copy2(CK2_ROOT / name, stage / name)
    shutil.copy2(PROJECT_DIR / 'packaging/PORTABLE_README.md', stage / 'README.md')
    shutil.copy2(CK2_ROOT / 'README.md', stage / 'UPSTREAM_README.md')
    shutil.copy2(PROJECT_DIR / 'packaging/CorridorKey.exe', stage / 'CorridorKey.exe')
    shutil.copy2(PROJECT_DIR / 'packaging/app.ico', stage / 'app.ico')
    (stage / 'scripts').mkdir()
    shutil.copy2(CK2_ROOT / 'scripts/download_weights.py', stage / 'scripts/download_weights.py')
    (stage / 'bin').mkdir()
    for name in ('ffmpeg', 'ffprobe'):
        source = shutil.which(name)
        if not source:
            raise FileNotFoundError(name)
        shutil.copy2(source, stage / 'bin' / f'{name}.exe')
    (stage / 'samples').mkdir()
    sample = CK2_ROOT / 'tmp/smoke_test/input.mp4'
    if not sample.is_file():
        raise FileNotFoundError(f'Build-host smoke-test clip not found: {sample}')
    shutil.copy2(sample, stage / 'samples/quick-test.mp4')
    (stage / 'data').mkdir()
    (stage / 'data/README.txt').write_text('Portable preferences and runtime diagnostics are saved here.\n', encoding='utf-8')
    (stage / 'Start.cmd').write_text('@echo off\r\ncd /d "%~dp0"\r\nstart "" "%~dp0CorridorKey.exe" %*\r\n', encoding='ascii')
    (stage / 'Check_runtime.cmd').write_text('@echo off\r\ncd /d "%~dp0"\r\n"runtime\\python.exe" -I -B "bootstrap.py" --check\r\necho.\r\necho Diagnostic report: data\\runtime-check.json\r\npause\r\n', encoding='ascii')
    packages = sorted(({'name': d.metadata.get('Name', ''), 'version': d.version, 'license': d.metadata.get('License-Expression') or d.metadata.get('License', '')} for d in importlib.metadata.distributions()), key=lambda d: d['name'].lower())
    (stage / 'BUNDLED_PACKAGES.json').write_text(json.dumps(packages, ensure_ascii=False, indent=2), encoding='utf-8')
    ffmpeg_info = subprocess.check_output([str(stage / 'bin/ffmpeg.exe'), '-version'], text=True, encoding='utf-8', errors='replace')
    (stage / 'bin/FFMPEG_BUILD.txt').write_text(ffmpeg_info + '\nSource build provider: https://www.gyan.dev/ffmpeg/builds/\nFFmpeg upstream source: https://github.com/FFmpeg/FFmpeg\nLicense: GPL version 3 or later; see licenses/FFMPEG_GPLv3.txt.\n', encoding='utf-8')
    licenses = stage / 'licenses'
    licenses.mkdir()
    for name in ('FFMPEG_GPLv3.txt', 'NVIDIA_OPEN_MODEL_LICENSE.pdf'):
        asset = PROJECT_DIR / 'packaging' / name
        if asset.is_file():
            shutil.copy2(asset, licenses / name)
    shutil.copy2(base / 'LICENSE.txt', licenses / 'PYTHON_LICENSE.txt')
    shutil.copy2(PROJECT_DIR / 'packaging/launcher.c', licenses / 'LOCAL_LAUNCHER_SOURCE.c')
    (licenses / 'NOTICE.txt').write_text('Original CorridorKey license and third-party notices are in the package root.\nPython and dependency licenses are retained in runtime/LICENSE.txt and runtime/Lib/site-packages/*.dist-info/.\nMSVC release CRT is included app-locally from the build host licensed Visual Studio redistribution directory.\nNo debug CRT, system DLLs, user credentials, user preferences, or model download caches are bundled.\nThis is a local modified frontend, not the official commercial plugin. No publication or redistribution is performed by this build.\nReview upstream licensing and obtain permission before sharing this bundle.\n', encoding='utf-8')
    print('Hashing staged runtime…', flush=True)
    files = sorted(p for p in stage.rglob('*') if p.is_file())
    def entry(path):
        return path.relative_to(stage).as_posix(), {'size': path.stat().st_size, 'sha256': sha256(path)}
    with ThreadPoolExecutor(max_workers=3) as pool:
        manifest = dict(pool.map(entry, files))
    total = sum(e['size'] for e in manifest.values())
    info = {'version': VERSION, 'format': 'portable-win-x64', 'python': sys.version, 'files': manifest, 'total_bytes': total}
    (stage / 'BUILD_MANIFEST.json').write_text(json.dumps(info, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'Staged {len(manifest)} files, {total / 2**30:.2f} GiB: {stage}', flush=True)


def create_zip(stage):
    archive = stage.parent / (stage.name + '.zip')
    temporary = archive.with_suffix('.zip.partial')
    if archive.exists() or temporary.exists():
        raise FileExistsError(f'Refusing to overwrite: {archive} or {temporary}')
    files = sorted(p for p in stage.rglob('*') if p.is_file() and p.relative_to(stage).parts[0] != 'data')
    # Do not package test results/preferences. Include only the data folder note.
    files.append(stage / 'data/README.txt')
    total = sum(p.stat().st_size for p in files)
    processed = 0
    last_report = 0
    seven_zip = Path(shutil.which('7za') or PROJECT_DIR / 'tmp/build_tools/7zip/extra/x64/7za.exe')
    if not seven_zip.is_file():
        seven_zip = CK2_ROOT / 'tmp/build_tools/7zip/extra/x64/7za.exe'
    if seven_zip.is_file():
        # ZIP64 with multiple independent deflate workers, no bundled test data.
        tmp_dir = PROJECT_DIR / 'tmp'
        tmp_dir.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='zip_list_', dir=tmp_dir) as folder:
            listing = Path(folder) / 'files.txt'
            listing.write_text(''.join(str(Path(stage.name) / p.relative_to(stage)) + '\n' for p in files), encoding='utf-8')
            subprocess.run([str(seven_zip), 'a', '-tzip', '-mx=1', '-mmt=8', '-scsUTF-8', '-bsp0', str(temporary), '@' + str(listing)], cwd=stage.parent, check=True)
    else:
        with zipfile.ZipFile(temporary, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=1, allowZip64=True, strict_timestamps=False) as z:
            for path in files:
                relative = Path(stage.name) / path.relative_to(stage)
                z.write(path, relative.as_posix())
                processed += path.stat().st_size
                if processed - last_report > 256 * 1024 * 1024:
                    print(f'ZIP: {processed / total:.0%}, {processed / 2**30:.2f}/{total / 2**30:.2f} GiB', flush=True)
                    last_report = processed
    temporary.replace(archive)
    print('Verifying all ZIP CRCs…', flush=True)
    with zipfile.ZipFile(archive) as z:
        bad = z.testzip()
        if bad:
            raise RuntimeError(f'ZIP CRC failure: {bad}')
    checksum = sha256(archive)
    archive.with_suffix('.zip.sha256').write_text(f'{checksum}  {archive.name}\n', encoding='ascii')
    print(json.dumps({'archive': str(archive), 'bytes': archive.stat().st_size, 'sha256': checksum}, indent=2), flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--stage', type=Path, default=DEFAULT_STAGE)
    parser.add_argument('--zip-only', action='store_true')
    parser.add_argument('--zip', action='store_true')
    args = parser.parse_args()
    stage = args.stage.resolve()
    if not args.zip_only:
        stage_runtime(stage)
    if args.zip or args.zip_only:
        create_zip(stage)


if __name__ == '__main__':
    main()
