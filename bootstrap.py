"""Relocatable entry point for the local GUI and the portable runtime.

In the portable bundle this file sits next to ``infer.py``, ``runtime/``,
``weights/`` and ``ck2gui/``.  In a development checkout it can also be run
from ``ck2-gui/``; the CorridorKey 2.0 root is then the parent folder.
"""
from __future__ import annotations

import os
import runpy
import sys
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent


def find_ck2_root() -> Path:
    """Find the folder that owns infer.py and corridorkey/."""
    override = os.environ.get('CORRIDORKEY_ROOT')
    candidates = ([Path(override).expanduser()] if override else [])
    candidates.extend((PROJECT_DIR, PROJECT_DIR.parent))
    for candidate in candidates:
        try:
            candidate = candidate.resolve()
        except OSError:
            continue
        if (candidate / 'infer.py').is_file() and (candidate / 'corridorkey').is_dir():
            return candidate
    return PROJECT_DIR


ROOT = find_ck2_root()
sys.path.insert(0, str(PROJECT_DIR))
os.chdir(ROOT)
for stream in (sys.stdout, sys.stderr):
    if stream is not None and hasattr(stream, 'reconfigure'):
        stream.reconfigure(encoding='utf-8', errors='backslashreplace')
for name in ('PYTHONHOME', 'PYTHONPATH', 'VIRTUAL_ENV'):
    os.environ.pop(name, None)
os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
os.environ['PATH'] = os.pathsep.join((
    str(PROJECT_DIR / 'bin'),
    str(PROJECT_DIR / 'runtime'),
    str(PROJECT_DIR / 'runtime' / 'DLLs'),
    str(ROOT / 'bin'),
    os.environ.get('PATH', ''),
))
os.environ.setdefault('HF_HUB_OFFLINE', '1')
os.environ.setdefault('TRANSFORMERS_OFFLINE', '1')

if len(sys.argv) > 1 and sys.argv[1] == '--infer':
    del sys.argv[1]
    runpy.run_path(str(ROOT / 'infer.py'), run_name='__main__')
elif len(sys.argv) > 1 and sys.argv[1] == '--check':
    del sys.argv[1]
    runpy.run_path(str(PROJECT_DIR / 'runtime_check.py'), run_name='__main__')
else:
    from ck2gui.app import run
    run()
