from __future__ import annotations

import os
import queue
import sys
import tempfile
import time
import unittest
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ck2gui.backend import (BatchRunner, Job, Settings, build_command, find_hint,
                         load_settings, reserve_output_dir, save_settings)


class BackendTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='corridorkey_gui_')
        self.root = Path(self.temp.name)
        self.source = self.root / '中文 素材.mp4'
        self.source.touch()

    def tearDown(self):
        self.temp.cleanup()

    def test_settings_roundtrip_and_validation(self):
        path = self.root / 'data' / 'settings.json'
        settings = Settings(output_root=str(self.root), outputs=('alpha', 'cutout'), memory_mode='low', frame_limit=8, language='en')
        save_settings(settings, path)
        self.assertEqual(load_settings(path), settings)
        for changes in ({'outputs': ()}, {'outputs': ('alpha', 'alpha')}, {'frame_limit': -1}, {'frame_limit': 1.5}, {'memory_mode': 'bad'}, {'model_scale': 0.1}, {'window_size': 0}, {'auto_hint': 'yes'}, {'language': 'fr'}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                replace(settings, **changes).validate()
        path.write_text('{ broken', encoding='utf-8')
        with self.assertRaises(ValueError):
            load_settings(path)

    def test_command_options_and_unicode_paths(self):
        output = self.root / '输出 文件夹'
        default = build_command(self.source, output, Settings())
        self.assertNotIn('--low_vram', default)
        self.assertEqual(default[default.index('--temp_dir') + 1], str(output / '.corridorkey_cache'))
        self.assertNotIn('--hann_chunk', default)
        self.assertEqual(default[default.index('--input') + 1], str(self.source))
        settings = Settings(outputs=('alpha',), memory_mode='low', window_size=4, frame_limit=8, model_scale=0.5)
        command = build_command(self.source, output, settings)
        for flag, value in (('--hann_chunk', '4'), ('--hann_stride', '2'), ('--num_frames', '8'), ('--model_scale', '0.5')):
            self.assertEqual(command[command.index(flag) + 1], value)
        self.assertIn('--low_vram', command)

    def test_portable_command_uses_bundled_interpreter_and_isolated_bootstrap(self):
        from ck2gui.backend import worker_python
        portable = self.root / 'runtime'
        portable.mkdir()
        executable = portable / 'python.exe'
        executable.touch()
        with patch('ck2gui.backend.ROOT', self.root):
            self.assertEqual(worker_python(), executable)
            command = build_command(self.source, self.root / 'output', Settings())
        self.assertEqual(command[0], str(executable))
        self.assertIn('-I', command)
        self.assertIn('-B', command)
        self.assertIn(str(self.root / 'bootstrap.py'), command)
        self.assertIn('--infer', command)
        self.assertNotIn(str(ROOT / 'venv' / 'Scripts' / 'python.exe'), command)

    def test_hint_selection_and_disabled_hint(self):
        image = self.root / '中文 素材FrameHint.png'
        image.touch()
        self.assertEqual(find_hint(self.source), ('--hint_first_frame', image))
        video = self.root / '中文 素材_AlphaHint.mp4'
        video.touch()
        self.assertEqual(find_hint(self.source), ('--hint_video', video))
        self.assertNotIn('--hint_video', build_command(self.source, self.root, Settings(auto_hint=False)))
        # Similar clip names must not accidentally use each other's hints.
        self.source = self.root / '中文.mp4'
        self.assertIsNone(find_hint(self.source))

    def test_output_reservation_never_overwrites(self):
        first = reserve_output_dir(self.source, Settings())
        (first / 'keep.txt').write_text('keep', encoding='utf-8')
        second = reserve_output_dir(self.source, Settings())
        self.assertNotEqual(first, second)
        self.assertEqual((first / 'keep.txt').read_text(), 'keep')
        other = self.root / 'same_name' / self.source.name
        other.parent.mkdir()
        other.touch()
        shared = Settings(output_root=str(self.root / 'central'))
        a = reserve_output_dir(self.source, shared)
        b = reserve_output_dir(other, shared)
        self.assertNotEqual(a, b)

    def collect(self, events):
        result = []
        while not events.empty():
            result.append(events.get_nowait())
        return result

    def test_failure_does_not_stop_next_file(self):
        source2 = self.root / 'second.mp4'
        source2.touch()
        events = queue.Queue()
        runner = BatchRunner(events)
        def command(source, _output, _settings):
            return [sys.executable, '-u', '-c', "import sys; print('unicode 输出', flush=True); sys.exit(" + ('2' if source == self.source else '0') + ')']
        with patch('ck2gui.backend.preflight'), patch('ck2gui.backend.build_command', side_effect=command):
            runner.start([Job('a', self.source), Job('b', source2)], Settings())
            runner.thread.join(15)
        self.assertFalse(runner.thread.is_alive())
        result = self.collect(events)
        statuses = [(e['id'], e['status']) for kind, e in result if kind == 'job']
        self.assertIn(('a', 'failed'), statuses)
        self.assertIn(('b', 'done'), statuses)
        self.assertEqual(next(e for kind, e in result if kind == 'finished')['completed'], 1)
        self.assertEqual(len(list(self.root.glob('out_*/corridorkey.log'))), 2)

    def test_stop_terminates_current_child_and_leaves_next_unstarted(self):
        source2 = self.root / 'second.mp4'
        source2.touch()
        events = queue.Queue()
        runner = BatchRunner(events)
        command = [sys.executable, '-u', '-c', "import time; print('CHILD_READY', flush=True); time.sleep(60)"]
        with patch('ck2gui.backend.preflight'), patch('ck2gui.backend.build_command', return_value=command):
            runner.start([Job('a', self.source), Job('b', source2)], Settings())
            deadline = time.monotonic() + 10
            while time.monotonic() < deadline:
                kind, event = events.get(timeout=5)
                if kind == 'log' and 'CHILD_READY' in event['text']:
                    break
            else:
                self.fail('child did not start')
            runner.stop()
            runner.thread.join(15)
        self.assertFalse(runner.thread.is_alive())
        result = self.collect(events)
        self.assertIn(('a', 'cancelled'), [(e['id'], e['status']) for kind, e in result if kind == 'job'])
        self.assertFalse(any(e.get('id') == 'b' for kind, e in result if kind == 'job'))
        self.assertTrue(next(e for kind, e in result if kind == 'finished')['stopped'])

    def test_preflight_failure_emits_error_and_finishes(self):
        events = queue.Queue()
        runner = BatchRunner(events)
        with patch('ck2gui.backend.preflight', side_effect=RuntimeError('missing weights')):
            runner.start([Job('a', self.source)], Settings())
            runner.thread.join(5)
        kinds = [kind for kind, _ in self.collect(events)]
        self.assertEqual(kinds, ['error', 'finished'])


class WidgetTests(unittest.TestCase):
    def test_language_toggle_translates_controls_statuses_and_settings(self):
        from ck2gui.app import CorridorKeyApp, SettingsDialog
        with tempfile.TemporaryDirectory() as folder, patch('ck2gui.app.load_settings', return_value=Settings()), patch('ck2gui.app.save_settings') as save:
            source = Path(folder) / 'sample.mp4'
            source.touch()
            app = CorridorKeyApp([source])
            app.withdraw()
            try:
                identifier = next(iter(app.jobs))
                app.toggle_language()
                self.assertEqual(app.settings.language, 'en')
                self.assertEqual(app.settings_button['text'], 'Settings')
                self.assertEqual(app.run_button['text'], 'Run')
                self.assertEqual(app.table.heading('status')['text'], 'Status')
                self.assertEqual(app.table.item(identifier)['values'][1], 'Queued')
                self.assertEqual(app.count_var.get(), '1 file')
                self.assertIn('Added 1 file', app.status_var.get())
                dialog = SettingsDialog(app, app.settings, app.apply_settings)
                dialog.withdraw()
                self.assertEqual(dialog.title(), 'Settings · CorridorKey 2.0')
                self.assertEqual(dialog.memory.get(), 'Automatic (recommended)')
                dialog.memory.set('Low VRAM')
                dialog.update_memory()
                self.assertEqual(str(dialog.window_combo['state']), 'readonly')
                dialog.save()
                self.assertEqual(app.settings.language, 'en')
                self.assertEqual(app.settings.memory_mode, 'low')
                app.set_status('{state} · 完成 {completed} / {total} · 失败 {failed}', state='本批次结束', completed=1, total=1, failed=0)
                self.assertIn('Batch finished', app.status_var.get())
                app.toggle_language()
                self.assertEqual(app.settings.language, 'zh')
                self.assertEqual(app.run_button['text'], '运行')
                self.assertEqual(app.table.item(identifier)['values'][1], '待运行')
                self.assertIn('本批次结束', app.status_var.get())
                self.assertEqual(save.call_args.args[0].language, 'zh')
            finally:
                app.destroy()

    def test_drag_drop_dedup_settings_and_queue_controls(self):
        from ck2gui.app import COPY, REFUSE_DROP, CorridorKeyApp, SettingsDialog
        with tempfile.TemporaryDirectory(prefix='corridorkey_widgets_') as folder, patch('ck2gui.app.load_settings', return_value=Settings()):
            root = Path(folder)
            files = (root / '中文 素材一.mp4', root / 'second clip.MOV')
            for path in files:
                path.touch()
            app = CorridorKeyApp()
            app.withdraw()
            try:
                # Generate a real Tcl list, as Explorer's native drop callback does.
                app.tk.setvar('test_drop', tuple(str(p) for p in files))
                data = app.tk.eval('set test_drop')
                self.assertEqual(app.on_drop(SimpleNamespace(data=data)), COPY)
                app.add_paths([str(files[0]), str(root / 'missing.mp4')])
                self.assertEqual(len(app.jobs), 2)
                self.assertEqual(len(app.table.get_children()), 2)
                app.set_busy(True)
                self.assertEqual(app.on_drop(SimpleNamespace(data=data)), REFUSE_DROP)
                self.assertEqual(str(app.settings_button['state']), 'disabled')
                app.set_busy(False)
                dialog = SettingsDialog(app, Settings(), app.apply_settings)
                dialog.withdraw()
                dialog.memory.set('低显存')
                dialog.update_memory()
                self.assertEqual(str(dialog.window_combo['state']), 'readonly')
                dialog.frames.set('8')
                with patch('ck2gui.app.save_settings') as save:
                    dialog.save()
                self.assertEqual(app.settings.frame_limit, 8)
                self.assertEqual(app.settings.memory_mode, 'low')
                save.assert_called_once()
                app.table.selection_set(next(iter(app.jobs)))
                app.remove_selected()
                self.assertEqual(len(app.jobs), 1)
                app.clear()
                app.clear()
                self.assertEqual(len(app.jobs), 0)
            finally:
                app.destroy()


if __name__ == '__main__':
    unittest.main(verbosity=2)
