"""Local diagnostic for the portable runtime; optionally runs two GPU test clips."""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import traceback
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--smoke', action='store_true')
    parser.add_argument('--report')
    args = parser.parse_args()
    root = Path(__file__).resolve().parent
    report_path = Path(args.report) if args.report else root / 'data' / 'runtime-check.json'
    report = {'status': 'running', 'root': str(root)}
    try:
        import torch
        import torchvision
        import tkinter
        from tkinterdnd2 import TkinterDnD
        from ck2gui.backend import preflight, worker_python
        assert Path(sys.prefix).resolve() == (root / 'runtime').resolve(), sys.prefix
        assert Path(torch.__file__).is_relative_to(root / 'runtime'), torch.__file__
        assert worker_python().resolve() == (root / 'runtime' / 'python.exe').resolve()
        assert Path(shutil.which('ffmpeg')).parent.resolve() == (root / 'bin').resolve()
        assert Path(shutil.which('ffprobe')).parent.resolve() == (root / 'bin').resolve()
        preflight()
        tk_root = TkinterDnD.Tk()
        tk_root.withdraw()
        report['tk'] = tk_root.tk.call('info', 'patchlevel')
        report['tkdnd'] = tk_root.tk.call('package', 'require', 'tkdnd')
        tk_root.update_idletasks()
        tk_root.update()
        tk_root.destroy()
        assert torch.cuda.is_available(), 'A compatible NVIDIA GPU and driver are required.'
        tensor = torch.randn(64, 64, device='cuda', dtype=torch.bfloat16)
        assert bool(torch.isfinite(tensor @ tensor.T).all())
        del tensor
        torch.cuda.empty_cache()
        report.update(python=sys.version, prefix=sys.prefix, sys_path=sys.path, torch=torch.__version__, torchvision=torchvision.__version__, gpu=torch.cuda.get_device_name(0), ffmpeg=shutil.which('ffmpeg'))
        if args.smoke:
            # This uses the real GUI queue and the bundled inference subprocess.
            from unittest.mock import patch
            from ck2gui.backend import Settings
            from ck2gui.app import CorridorKeyApp, SettingsDialog
            base = root / 'data' / 'self_test'
            base.mkdir(parents=True, exist_ok=True)
            files = [base / '测试 片段一.mp4', base / 'second clip.mp4']
            for source in files:
                shutil.copy2(root / 'samples' / 'quick-test.mp4', source)
            with patch('ck2gui.app.load_settings', return_value=Settings(language='zh')), patch('ck2gui.app.save_settings'):
                app = CorridorKeyApp()
                app.withdraw()
                try:
                    app.tk.setvar('test_drop', tuple(str(path) for path in files))
                    app.on_drop(type('Drop', (), {'data': app.tk.eval('set test_drop')})())
                    app.toggle_language()
                    assert app.run_button['text'] == 'Run'
                    assert app.table.heading('status')['text'] == 'Status'
                    dialog = SettingsDialog(app, app.settings, app.apply_settings)
                    dialog.withdraw()
                    assert dialog.memory.get() == 'Automatic (recommended)'
                    dialog.destroy()
                    app.toggle_language()
                    assert app.run_button['text'] == '运行'
                    app.settings = Settings(output_root=str(base / 'results'), frame_limit=8, language='en')
                    app.apply_language()
                    app.run_batch()
                    deadline = time.monotonic() + 300
                    while app.busy and time.monotonic() < deadline:
                        app.update()
                        time.sleep(0.04)
                    assert not app.busy, 'GPU batch timed out'
                    report['jobs'] = []
                    for job in app.jobs.values():
                        assert job.status == 'done', (job.source, job.status)
                        videos = sorted(job.output.glob('*.mp4')) + sorted(job.output.glob('*.mov'))
                        assert len(videos) == 4
                        for video in videos:
                            data = json.loads(subprocess.check_output(['ffprobe', '-v', 'error', '-count_frames', '-select_streams', 'v:0', '-show_entries', 'stream=width,height,nb_read_frames,pix_fmt', '-of', 'json', str(video)], text=True))['streams'][0]
                            assert (data['width'], data['height'], int(data['nb_read_frames'])) == (512, 384, 8), data
                            subprocess.run(['ffmpeg', '-v', 'error', '-i', str(video), '-f', 'null', '-'], check=True, capture_output=True)
                        report['jobs'].append({'source': str(job.source), 'status': job.status, 'output': str(job.output), 'outputs': len(videos)})
                finally:
                    if app.busy:
                        app.runner.stop()
                        app.runner.thread.join(20)
                    app.destroy()
        report['status'] = 'passed'
    except Exception:
        report['status'] = 'failed'
        report['error'] = traceback.format_exc()
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    if sys.stdout:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report['status'] == 'passed' else 1


if __name__ == '__main__':
    raise SystemExit(main())
