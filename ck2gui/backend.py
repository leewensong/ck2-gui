"""Small, UI-independent batch runner for the local CorridorKey GUI."""
from __future__ import annotations

import json
import os
import queue
import shutil
import signal
import subprocess
import sys
import threading
from dataclasses import asdict, dataclass
from pathlib import Path

from .i18n import tr, translate_error

# The GUI project lives in its own folder.  In a development checkout that is
# <CorridorKey2.0>/ck2-gui/; in the portable bundle the same package is copied
# to the bundle root next to infer.py, weights/ and runtime/.
PACKAGE_DIR = Path(__file__).resolve().parent
PROJECT_DIR = PACKAGE_DIR.parent


def find_ck2_root() -> Path | None:
    """Locate the CorridorKey 2.0 root that contains infer.py/corridorkey."""
    candidates: list[Path] = []
    override = os.environ.get('CORRIDORKEY_ROOT')
    if override:
        candidates.append(Path(override).expanduser())
    candidates.extend((PROJECT_DIR, PROJECT_DIR.parent))
    for candidate in candidates:
        try:
            candidate = candidate.resolve()
        except OSError:
            continue
        if (candidate / 'infer.py').is_file() and (candidate / 'corridorkey').is_dir():
            return candidate
    return None


def current_root() -> Path | None:
    """Return the cached root, falling back to a fresh lookup."""
    return ROOT if ROOT is not None else find_ck2_root()


def require_ck2_root() -> Path:
    root = current_root()
    if root is None:
        raise RuntimeError(
            '未找到 CorridorKey 2.0 根目录（需要包含 infer.py 和 corridorkey/）。'
            '请将 ck2-gui 文件夹放进 CorridorKey 2.0 根目录，或设置 CORRIDORKEY_ROOT 环境变量。')
    return root


def portable_root() -> Path | None:
    """Return the bundle root when a bundled Python runtime is present."""
    for candidate in (PROJECT_DIR, current_root()):
        if candidate is not None and (candidate / 'runtime' / 'python.exe').is_file():
            return candidate
    return None


ROOT = find_ck2_root()
STATE_DIR = Path(os.environ.get(
    'CORRIDORKEY_CONFIG_DIR',
    str(PROJECT_DIR / 'data' if (PROJECT_DIR / 'runtime').is_dir() else PROJECT_DIR)))
SETTINGS_PATH = STATE_DIR / '.corridorkey_gui.json'
VIDEO_EXTENSIONS = {'.mp4', '.mov', '.mkv', '.avi', '.webm', '.mxf', '.m4v', '.mts', '.m2ts', '.mpg', '.mpeg', '.wmv'}
OUTPUTS = ('alpha', 'fg', 'checker', 'cutout')
MEMORY_MODES = ('auto', 'low')
WINDOW_SIZES = (1, 2, 4, 8, 24, 48, 80)


@dataclass(frozen=True)
class Settings:
    output_root: str = ''
    outputs: tuple[str, ...] = OUTPUTS
    memory_mode: str = 'auto'
    window_size: int = 8
    frame_limit: int = 0
    model_scale: float = 1.0
    auto_hint: bool = True
    language: str = 'zh'

    def validate(self) -> None:
        if not isinstance(self.output_root, str):
            raise ValueError('输出目录必须是文本路径。')
        if not isinstance(self.outputs, (tuple, list)) or not self.outputs or any(x not in OUTPUTS for x in self.outputs):
            raise ValueError('请至少选择一种有效的输出内容。')
        if len(set(self.outputs)) != len(self.outputs):
            raise ValueError('输出内容不能重复。')
        if self.memory_mode not in MEMORY_MODES:
            raise ValueError('显存模式无效。')
        if type(self.window_size) is not int or self.window_size not in WINDOW_SIZES:
            raise ValueError('窗口帧数无效。')
        if type(self.frame_limit) is not int or self.frame_limit < 0:
            raise ValueError('帧数上限必须是非负整数，0 表示全部。')
        if type(self.model_scale) not in (float, int) or self.model_scale not in (1.0, 0.75, 0.5):
            raise ValueError('处理缩放只能是 1.0、0.75 或 0.5。')
        if self.language not in ('zh', 'en'):
            raise ValueError('语言设置无效。')
        if type(self.auto_hint) is not bool:
            raise ValueError('自动提示设置无效。')


def load_settings(path: Path = SETTINGS_PATH) -> Settings:
    if not path.exists():
        return Settings()
    data = json.loads(path.read_text(encoding='utf-8-sig'))
    if not isinstance(data, dict):
        raise ValueError('设置文件格式无效。')
    if 'outputs' in data:
        if not isinstance(data['outputs'], list):
            raise ValueError('设置中的输出列表无效。')
        data['outputs'] = tuple(data['outputs'])
    settings = Settings(**data)
    settings.validate()
    return settings


def save_settings(settings: Settings, path: Path = SETTINGS_PATH) -> None:
    settings.validate()
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(asdict(settings), ensure_ascii=False, indent=2), encoding='utf-8')
    temporary.replace(path)


def worker_python() -> Path:
    portable = portable_root()
    if portable is not None:
        return portable / 'runtime' / 'python.exe'
    root = current_root()
    if root is not None:
        bundled = root / 'venv' / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
        if bundled.is_file():
            return bundled
    executable = Path(sys.executable)
    if executable.name.lower() == 'pythonw.exe':
        executable = executable.with_name('python.exe')
    return executable


def find_hint(path: Path) -> tuple[str, Path] | None:
    """Prefer a full-video hint, then a first-frame hint; do not guess prefixes."""
    try:
        candidates = sorted((p for p in path.parent.iterdir() if p.is_file()), key=lambda p: p.name.lower())
    except OSError:
        return None
    base = path.stem.lower()
    for candidate in candidates:
        if candidate.stem.lower() == f'{base}_alphahint' and candidate.suffix.lower() in VIDEO_EXTENSIONS:
            return '--hint_video', candidate
    for marker in ('framehint', 'alphahint'):
        for candidate in candidates:
            if candidate.suffix.lower() not in {'.png', '.jpg', '.jpeg', '.exr'}:
                continue
            stem = candidate.stem.lower()
            if stem.startswith(base) and stem[len(base):].lstrip('_- ') == marker:
                return '--hint_first_frame', candidate
    return None


def reserve_output_dir(source: Path, settings: Settings) -> Path:
    """Create a unique directory atomically; never overwrite an earlier run."""
    parent = Path(settings.output_root).expanduser().resolve() if settings.output_root else source.parent
    parent.mkdir(parents=True, exist_ok=True)
    for number in range(1, 100000):
        suffix = '' if number == 1 else f'_{number}'
        target = parent / f'out_{source.stem}{suffix}'
        try:
            target.mkdir()
            return target
        except FileExistsError:
            continue
    raise OSError('无法创建不重名的输出目录。')


def build_command(source: Path, output: Path, settings: Settings) -> list[str]:
    settings.validate()
    portable = portable_root()
    if portable is not None:
        entry = ['-I', '-B', str(portable / 'bootstrap.py'), '--infer']
    else:
        entry = [str(require_ck2_root() / 'infer.py')]
    command = [str(worker_python()), '-u', *entry, '--input', str(source), '--output_dir', str(output), '--outputs', *settings.outputs]
    # Keep potentially huge 8K feature caches off the default system TEMP disk.
    command += ['--temp_dir', str(output / '.corridorkey_cache')]
    if settings.memory_mode == 'low':
        command += ['--low_vram', '--hann_chunk', str(settings.window_size), '--hann_stride', str(max(1, settings.window_size // 2))]
    if settings.frame_limit:
        command += ['--num_frames', str(settings.frame_limit)]
    if settings.model_scale != 1.0:
        command += ['--model_scale', str(settings.model_scale)]
    if settings.auto_hint:
        hint = find_hint(source)
        if hint:
            command += [hint[0], str(hint[1])]
    return command


def preflight() -> None:
    if not shutil.which('ffmpeg'):
        raise RuntimeError('找不到 ffmpeg，请将其加入 PATH 后重启 GUI。')
    root = require_ck2_root()
    if not worker_python().is_file():
        raise RuntimeError('找不到可用的 Python 环境。')
    required = ('weights/corridorkey_v2.safetensors', 'weights/foundation_stats.safetensors', 'vfms/moge/model.pt', 'vfms/cradio/C-RADIOv4-SO400M/model.safetensors', 'vfms/cradio/C-RADIOv4-SO400M/config.json', 'vfms/rvm/pretrain_rvm_small16_256_204031069.npz')
    missing = [name for name in required if not (root / name).is_file()]
    if missing:
        raise RuntimeError('缺少模型文件，请在 CorridorKey 2.0 根目录运行 scripts/download_weights.py：\n' + '\n'.join(missing))


@dataclass
class Job:
    id: str
    source: Path
    status: str = 'pending'
    output: Path | None = None


class BatchRunner:
    """One inference child at a time. Tk is never called from this thread."""

    def __init__(self, events: queue.Queue):
        self.events = events
        self.stop_event = threading.Event()
        self._process_lock = threading.Lock()
        self._process: subprocess.Popen | None = None
        self.thread: threading.Thread | None = None

    def emit(self, kind: str, **payload) -> None:
        self.events.put((kind, payload))

    def start(self, jobs: list[Job], settings: Settings) -> None:
        if self.thread and self.thread.is_alive():
            raise RuntimeError('已有任务正在运行。')
        settings.validate()
        self.stop_event.clear()
        self.thread = threading.Thread(target=self._run, args=(tuple(jobs), settings), daemon=True, name='CorridorKeyBatch')
        self.thread.start()

    def stop(self) -> None:
        self.stop_event.set()
        threading.Thread(target=self._terminate, daemon=True, name='CorridorKeyStop').start()

    def _terminate(self) -> None:
        # This PID belongs exclusively to our current inference subprocess.
        with self._process_lock:
            proc = self._process
            if proc is None or proc.poll() is not None:
                return
            if os.name == 'nt':
                subprocess.run(['taskkill', '/PID', str(proc.pid), '/T', '/F'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=subprocess.CREATE_NO_WINDOW, check=False)
            else:
                try:
                    os.killpg(proc.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
            if proc.poll() is None:
                proc.kill()

    def _run(self, jobs: tuple[Job, ...], settings: Settings) -> None:
        completed = failed = attempted = 0
        t = lambda source, **values: tr(source, settings.language, **values)
        try:
            preflight()
            for job in jobs:
                if self.stop_event.is_set():
                    break
                attempted += 1
                try:
                    if not job.source.is_file():
                        raise FileNotFoundError(t('输入文件不存在：{path}', path=job.source))
                    output = reserve_output_dir(job.source, settings)
                    command = build_command(job.source, output, settings)
                    self.emit('job', id=job.id, status='running', output=output)
                    self.emit('log', text=t('\n--- [{current}/{total}] {name} ---\n输出：{output}\n命令：{command}\n', current=attempted, total=len(jobs), name=job.source.name, output=output, command=subprocess.list2cmdline(command)))
                    environment = dict(os.environ, PYTHONUNBUFFERED='1', PYTHONIOENCODING='utf-8')
                    options = {'creationflags': subprocess.CREATE_NO_WINDOW} if os.name == 'nt' else {'start_new_session': True}
                    with (output / 'corridorkey.log').open('w', encoding='utf-8') as log:
                        log.write(subprocess.list2cmdline(command) + '\n')
                        with self._process_lock:
                            if self.stop_event.is_set():
                                self.emit('job', id=job.id, status='cancelled')
                                break
                            proc = subprocess.Popen(command, cwd=str(ROOT or PROJECT_DIR), env=environment, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL, text=True, encoding='utf-8', errors='replace', bufsize=1, **options)
                            self._process = proc
                        try:
                            assert proc.stdout is not None
                            with proc.stdout:
                                for line in proc.stdout:
                                    log.write(line)
                                    log.flush()
                                    self.emit('log', text=line)
                            code = proc.wait()
                        finally:
                            if proc.poll() is None:
                                self._terminate()
                                proc.wait()
                            with self._process_lock:
                                self._process = None
                    if self.stop_event.is_set():
                        self.emit('job', id=job.id, status='cancelled')
                        self.emit('log', text=t('任务已停止；部分输出可能未完成，已保留供检查。\n'))
                        break
                    if code:
                        failed += 1
                        self.emit('job', id=job.id, status='failed')
                        self.emit('log', text=t('处理失败（退出码 {code}），详见上方日志。继续下一文件。\n', code=code))
                    else:
                        completed += 1
                        self.emit('job', id=job.id, status='done')
                except Exception as exc:
                    if self.stop_event.is_set():
                        self.emit('job', id=job.id, status='cancelled')
                        break
                    failed += 1
                    self.emit('job', id=job.id, status='failed')
                    self.emit('log', text=t('处理失败：{error}\n', error=translate_error(exc, settings.language)))
                self.emit('progress', current=completed + failed, total=len(jobs))
        except Exception as exc:
            self.emit('error', text=translate_error(exc, settings.language))
        finally:
            self.emit('finished', completed=completed, failed=failed, total=len(jobs), stopped=self.stop_event.is_set())
