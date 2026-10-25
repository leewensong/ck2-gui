"""Create a new hotfix stage without recopying immutable multi-GB assets."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CK2_ROOT = ROOT.parent
parser = argparse.ArgumentParser()
parser.add_argument('--base', type=Path, default=ROOT / 'dist/CorridorKey2.0-Portable-v1.1.0')
parser.add_argument('--stage', type=Path, default=ROOT / 'dist/CorridorKey2.0-Portable-v1.1.1')
args = parser.parse_args()
base = args.base.resolve()
stage = args.stage.resolve()
if stage.exists():
    raise FileExistsError(f'Refusing to overwrite stage: {stage}')
manifest = json.loads((base / 'BUILD_MANIFEST.json').read_text(encoding='utf-8'))
stage.mkdir(parents=True)
linked = copied = 0
for name, entry in manifest['files'].items():
    relative = Path(name)
    source = (base / relative).resolve()
    target = (stage / relative).resolve()
    if not source.is_relative_to(base) or not target.is_relative_to(stage):
        raise ValueError(f'Invalid manifest path: {name}')
    if relative.parts[0] == 'data' and relative.as_posix() != 'data/README.txt':
        continue
    assert source.is_file() and source.stat().st_size == entry['size'], source
    target.parent.mkdir(parents=True, exist_ok=True)
    # These assets are never edited by the app. ZIP members are real file data,
    # not hardlinks; this only reduces build-host staging I/O and disk usage.
    if entry['size'] >= 50 * 1024 * 1024 and source.suffix.lower() in ('.dll', '.safetensors', '.npz', '.pt', '.exe'):
        try:
            os.link(source, target)
            linked += 1
            continue
        except OSError:
            pass
    shutil.copy2(source, target)
    copied += 1

updates = [
    (ROOT / 'ck2gui/__init__.py', 'ck2gui/__init__.py'),
    (ROOT / 'ck2gui/__main__.py', 'ck2gui/__main__.py'),
    (ROOT / 'ck2gui/app.py', 'ck2gui/app.py'),
    (ROOT / 'ck2gui/backend.py', 'ck2gui/backend.py'),
    (ROOT / 'ck2gui/i18n.py', 'ck2gui/i18n.py'),
    (ROOT / 'bootstrap.py', 'bootstrap.py'),
    (ROOT / 'runtime_check.py', 'runtime_check.py'),
    (ROOT / 'requirements-gui.txt', 'requirements-gui.txt'),
    (ROOT / 'packaging/CorridorKey.exe', 'CorridorKey.exe'),
    (ROOT / 'packaging/app.ico', 'app.ico'),
    (ROOT / 'packaging/HOTFIX_1.1.1.md', 'HOTFIX_1.1.1.md'),
    (ROOT / 'packaging/PORTABLE_README.md', 'README.md'),
    (CK2_ROOT / 'infer.py', 'infer.py'),
    (CK2_ROOT / 'LICENSE', 'LICENSE'),
    (CK2_ROOT / 'THIRD_PARTY_NOTICES.md', 'THIRD_PARTY_NOTICES.md'),
    (CK2_ROOT / 'corridorkey/runtime.py', 'corridorkey/runtime.py'),
    (CK2_ROOT / 'corridorkey/video_io.py', 'corridorkey/video_io.py'),
]
for source, target_name in updates:
    target = stage / target_name
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)
    manifest['files'][target_name] = {'size': target.stat().st_size, 'sha256': hashlib.sha256(target.read_bytes()).hexdigest()}
manifest['version'] = '1.1.1'
manifest['total_bytes'] = sum(entry['size'] for entry in manifest['files'].values())
(stage / 'BUILD_MANIFEST.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps({'stage': str(stage), 'files': len(manifest['files']), 'linked_immutable_assets': linked, 'copied_files': copied, 'bytes': manifest['total_bytes']}, indent=2), flush=True)
