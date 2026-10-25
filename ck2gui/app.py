#!/usr/bin/env python3
"""Native drag-and-drop frontend. No model imports on the UI thread."""
from __future__ import annotations

import ctypes
import os
import queue
import subprocess
import sys
import tkinter as tk
import uuid
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from .backend import (PROJECT_DIR, STATE_DIR, VIDEO_EXTENSIONS,
                      WINDOW_SIZES, BatchRunner, Job, Settings, load_settings,
                      save_settings)
from .i18n import tr, translate_error, translate_widgets
from dataclasses import replace

try:
    from tkinterdnd2 import COPY, DND_FILES, REFUSE_DROP, TkinterDnD
except ImportError:
    root = tk.Tk()
    root.withdraw()
    messagebox.showerror(
        '缺少 GUI 组件',
        '请先安装 GUI 依赖：\n'
        f'"{sys.executable}" -m pip install -r requirements-gui.txt\n\n'
        'requirements-gui.txt 位于本程序目录。')
    root.destroy()
    raise SystemExit(1)

STATUS_TEXT = {'pending': '待运行', 'running': '运行中', 'done': '已完成', 'failed': '失败', 'cancelled': '已停止'}
OUTPUT_LABELS = {'alpha': 'Alpha 遮罩', 'fg': '前景 RGB', 'checker': '棋盘格预览', 'cutout': '透明视频 (ProRes MOV)'}


class SettingsDialog(tk.Toplevel):
    def __init__(self, parent, settings: Settings, on_save):
        super().__init__(parent)
        self.t = parent.t
        self.language = parent.settings.language
        self.title(self.t('设置 · CorridorKey 2.0'))
        self.resizable(False, False)
        self.transient(parent)
        self.on_save = on_save
        self.output_root = tk.StringVar(value=settings.output_root)
        self.outputs = {name: tk.BooleanVar(value=name in settings.outputs) for name in OUTPUT_LABELS}
        self.memory = tk.StringVar(value=self.t('自动（推荐）') if settings.memory_mode == 'auto' else self.t('低显存'))
        self.window = tk.StringVar(value=str(settings.window_size))
        self.frames = tk.StringVar(value=str(settings.frame_limit))
        self.scale = tk.StringVar(value=str(settings.model_scale))
        self.hint = tk.BooleanVar(value=settings.auto_hint)
        body = ttk.Frame(self, padding=24)
        body.grid(sticky='nsew')
        body.columnconfigure(1, weight=1)
        ttk.Label(body, text='输出位置', style='Section.TLabel').grid(row=0, column=0, sticky='w', pady=(0, 8))
        ttk.Label(body, text='留空：每个素材旁新建 out_素材名 文件夹', style='Muted.TLabel').grid(row=1, column=0, columnspan=3, sticky='w')
        ttk.Entry(body, textvariable=self.output_root, width=53).grid(row=2, column=0, columnspan=2, sticky='ew', pady=(8, 20))
        ttk.Button(body, text='浏览…', command=self.browse).grid(row=2, column=2, padx=(8, 0), pady=(8, 20))
        ttk.Label(body, text='导出内容', style='Section.TLabel').grid(row=3, column=0, sticky='w', pady=(0, 8))
        for index, (name, label) in enumerate(OUTPUT_LABELS.items()):
            ttk.Checkbutton(body, text=label, variable=self.outputs[name]).grid(row=4 + index // 2, column=index % 2, sticky='w', pady=5)
        ttk.Label(body, text='显存模式').grid(row=6, column=0, sticky='w', pady=(22, 6))
        memory_combo = ttk.Combobox(body, textvariable=self.memory, state='readonly', values=(self.t('自动（推荐）'), self.t('低显存')), width=24)
        memory_combo.grid(row=6, column=1, columnspan=2, sticky='ew', pady=(22, 6))
        memory_combo.bind('<<ComboboxSelected>>', self.update_memory)
        ttk.Label(body, text='低显存窗口（帧）').grid(row=7, column=0, sticky='w', pady=6)
        self.window_combo = ttk.Combobox(body, textvariable=self.window, values=WINDOW_SIZES, state='readonly', width=24)
        self.window_combo.grid(row=7, column=1, columnspan=2, sticky='ew', pady=6)
        ttk.Label(body, text='处理缩放').grid(row=8, column=0, sticky='w', pady=6)
        ttk.Combobox(body, textvariable=self.scale, values=('1.0', '0.75', '0.5'), state='readonly', width=24).grid(row=8, column=1, columnspan=2, sticky='ew', pady=6)
        ttk.Label(body, text='1.0 保留原始分辨率；较小值会降低输出分辨率。', style='Muted.TLabel').grid(row=9, column=0, columnspan=3, sticky='w', pady=(0, 10))
        ttk.Label(body, text='帧数上限（0 = 全部）').grid(row=10, column=0, sticky='w', pady=6)
        ttk.Entry(body, textvariable=self.frames, width=25).grid(row=10, column=1, columnspan=2, sticky='ew', pady=6)
        ttk.Checkbutton(body, text='自动查找同名 FrameHint 图片 / _AlphaHint 视频', variable=self.hint).grid(row=11, column=0, columnspan=3, sticky='w', pady=(14, 4))
        ttk.Label(body, text='所有文件使用相同设置，按顺序运行；已存在的输出不会被覆盖。', style='Muted.TLabel').grid(row=12, column=0, columnspan=3, sticky='w', pady=(14, 20))
        buttons = ttk.Frame(body)
        buttons.grid(row=13, column=0, columnspan=3, sticky='e')
        ttk.Button(buttons, text='取消', command=self.destroy).pack(side='left', padx=8)
        ttk.Button(buttons, text='保存', style='Accent.TButton', command=self.save).pack(side='left')
        self.bind('<Escape>', lambda _: self.destroy())
        translate_widgets(self, self.language)
        self.update_memory()
        self.update_idletasks()
        self.geometry(f'+{max(0, parent.winfo_rootx() + (parent.winfo_width() - self.winfo_width()) // 2)}+{max(0, parent.winfo_rooty() + 70)}')
        self.grab_set()

    def update_memory(self, _event=None):
        self.window_combo.configure(state='readonly' if self.memory.get() == self.t('低显存') else 'disabled')

    def browse(self):
        path = filedialog.askdirectory(parent=self, title=self.t('选择统一输出目录（每个素材会另建子文件夹）'))
        if path:
            self.output_root.set(path)

    def save(self):
        try:
            settings = Settings(output_root=self.output_root.get().strip(), outputs=tuple(name for name, var in self.outputs.items() if var.get()), memory_mode='low' if self.memory.get() == self.t('低显存') else 'auto', window_size=int(self.window.get()), frame_limit=int(self.frames.get()), model_scale=float(self.scale.get()), auto_hint=self.hint.get(), language=self.language)
            settings.validate()
            save_settings(settings)
        except (ValueError, OSError) as exc:
            messagebox.showerror(self.t('设置未保存'), translate_error(exc, self.language), parent=self)
            return
        self.on_save(settings)
        self.destroy()


class CorridorKeyApp(TkinterDnD.Tk):
    def __init__(self, initial_files=()):
        super().__init__()
        self.title('CorridorKey 2.0 · 批量抠像')
        icon = PROJECT_DIR / 'app.ico'
        if not icon.is_file():
            icon = PROJECT_DIR / 'packaging' / 'app.ico'
        if icon.is_file():
            self.iconbitmap(str(icon))
            self.iconbitmap(default=str(icon))
        self.geometry('1080x800')
        self.minsize(840, 680)
        self.configure(background='#f4f6fa')
        self.events = queue.Queue()
        self.runner = BatchRunner(self.events)
        self.jobs: dict[str, Job] = {}
        self.busy = False
        self.closing = False
        self.settings_dialog = None
        self.last_output = None
        self._poll_id = None
        settings_warning = ''
        try:
            self.settings = load_settings()
        except (OSError, ValueError, TypeError) as exc:
            self.settings = Settings()
            settings_warning = str(exc)
        self._style()
        self._build()
        self._status = ('就绪', {})
        self.apply_language()
        self.protocol('WM_DELETE_WINDOW', self.close)
        self.append_log(self.t('就绪。将多个视频拖入列表，点击“运行”。双击已处理文件可打开输出文件夹。\n'))
        if settings_warning:
            self.append_log(self.t('设置读取失败，已使用默认设置：{error}\n', error=translate_error(settings_warning, self.settings.language)))
        if initial_files:
            self.add_paths(initial_files)
        self._poll_id = self.after(80, self.poll_events)

    def t(self, source, **values):
        return tr(source, self.settings.language, **values)

    def set_status(self, source, **values):
        self._status = (source, values)
        self.render_status()

    def render_status(self):
        source, values = self._status
        if source == '__added__':
            text = self.t('已添加 {count} 个文件', count=values['count'])
            if values['duplicates']:
                text += self.t(' · {count} 个重复已忽略', count=values['duplicates'])
            if values['skipped']:
                text += self.t(' · {count} 个无效项目已忽略', count=values['skipped'])
        else:
            values = dict(values)
            if 'state' in values:
                values['state'] = self.t(values['state'])
            text = self.t(source, **values)
        self.status_var.set(text)

    def apply_language(self):
        self.title(self.t('CorridorKey 2.0 · 批量抠像'))
        translate_widgets(self, self.settings.language)
        for name, title in [('name', '文件名'), ('status', '状态'), ('path', '文件路径')]:
            self.table.heading(name, text=self.t(title))
        for job in self.jobs.values():
            self.table.item(job.id, values=(job.source.name, self.t(STATUS_TEXT[job.status]), str(job.source)))
        self.count_var.set(self.t('{count} 个文件', count=len(self.jobs)))
        self.render_status()

    def toggle_language(self):
        self.settings = replace(self.settings, language='en' if self.settings.language == 'zh' else 'zh')
        self.apply_language()
        try:
            save_settings(self.settings)
        except OSError as exc:
            self.append_log(self.t('语言切换后无法保存设置：{error}\n', error=str(exc)))

    def _style(self):
        style = ttk.Style(self)
        style.theme_use('clam')
        style.configure('.', font=('Microsoft YaHei UI', 10), background='#f4f6fa', foreground='#243248')
        style.configure('TFrame', background='#f4f6fa')
        style.configure('TLabel', background='#f4f6fa')
        style.configure('Title.TLabel', font=('Microsoft YaHei UI', 22, 'bold'))
        style.configure('Section.TLabel', font=('Microsoft YaHei UI', 11, 'bold'))
        style.configure('Muted.TLabel', foreground='#67768a')
        style.configure('TButton', padding=(14, 8), background='#ffffff', bordercolor='#d8e0ea')
        style.map('TButton', background=[('active', '#e9eef6')])
        style.configure('Accent.TButton', background='#277360', foreground='white', font=('Microsoft YaHei UI', 10, 'bold'))
        style.map('Accent.TButton', background=[('disabled', '#a9bab5'), ('active', '#1b5f4e')], foreground=[('disabled', '#f2f5f4')])
        style.configure('Treeview', background='white', fieldbackground='white', rowheight=36, borderwidth=0)
        style.configure('Treeview.Heading', padding=(8, 10), font=('Microsoft YaHei UI', 10, 'bold'), background='#e9edf4')
        style.map('Treeview', background=[('selected', '#dcebe6')], foreground=[('selected', '#154f40')])
        style.configure('TProgressbar', troughcolor='#e0e6ee', background='#277360', borderwidth=0, thickness=7)

    def _build(self):
        main = ttk.Frame(self, padding=(26, 20))
        main.pack(fill='both', expand=True)
        main.columnconfigure(0, weight=1)
        main.rowconfigure(3, weight=3, minsize=125)
        main.rowconfigure(7, weight=2, minsize=145)
        header = ttk.Frame(main)
        header.grid(row=0, column=0, sticky='ew')
        ttk.Label(header, text='CorridorKey 2.0', style='Title.TLabel').pack(side='left')
        self.language_button = ttk.Button(header, text='中 / E', width=7, command=self.toggle_language)
        self.language_button.pack(side='right', padx=(8, 0))
        self.settings_button = ttk.Button(header, text='设置', command=self.show_settings)
        self.settings_button.pack(side='right')
        ttk.Label(main, text='批量视频抠像  /  本地 GPU 运行', style='Muted.TLabel').grid(row=1, column=0, sticky='w', pady=(2, 16))
        self.drop_area = tk.Label(main, text='将多个视频文件拖到这里或下方列表\n也可以点击“添加文件” · 支持 MP4 / MOV / MKV 等', font=('Microsoft YaHei UI', 11), foreground='#277360', background='#e8f1ed', padx=18, pady=20, relief='solid', borderwidth=1, highlightthickness=0)
        self.drop_area.grid(row=2, column=0, sticky='ew', pady=(0, 14))
        table_frame = ttk.Frame(main)
        table_frame.grid(row=3, column=0, sticky='nsew')
        table_frame.rowconfigure(0, weight=1)
        table_frame.columnconfigure(0, weight=1)
        self.table = ttk.Treeview(table_frame, columns=('name', 'status', 'path'), show='headings', selectmode='extended', height=6)
        for name, title, width in [('name', '文件名', 260), ('status', '状态', 100), ('path', '文件路径', 540)]:
            self.table.heading(name, text=title, anchor='w')
            self.table.column(name, width=width, minwidth=70, anchor='w', stretch=name != 'status')
        self.table.grid(row=0, column=0, sticky='nsew')
        scroll = ttk.Scrollbar(table_frame, orient='vertical', command=self.table.yview)
        scroll.grid(row=0, column=1, sticky='ns')
        horizontal = ttk.Scrollbar(table_frame, orient='horizontal', command=self.table.xview)
        horizontal.grid(row=1, column=0, sticky='ew')
        self.table.configure(yscrollcommand=scroll.set, xscrollcommand=horizontal.set)
        self.table.tag_configure('done', foreground='#26745a')
        self.table.tag_configure('failed', foreground='#b43737')
        self.table.tag_configure('running', foreground='#215a9f')
        self.table.bind('<Delete>', lambda _: self.remove_selected())
        self.table.bind('<Double-1>', lambda _: self.open_output())
        for widget in (self.drop_area, self.table, self):
            widget.drop_target_register(DND_FILES)
            widget.dnd_bind('<<Drop>>', self.on_drop)
        toolbar = ttk.Frame(main)
        toolbar.grid(row=4, column=0, sticky='ew', pady=(12, 10))
        self.add_button = ttk.Button(toolbar, text='添加文件', command=self.choose_files)
        self.add_button.pack(side='left')
        self.remove_button = ttk.Button(toolbar, text='移除选中', command=self.remove_selected)
        self.remove_button.pack(side='left', padx=8)
        self.clear_button = ttk.Button(toolbar, text='清空', command=self.clear)
        self.clear_button.pack(side='left')
        self.run_button = ttk.Button(toolbar, text='运行', style='Accent.TButton', command=self.run_batch)
        self.run_button.pack(side='right')
        self.stop_button = ttk.Button(toolbar, text='停止', command=self.stop_batch, state='disabled')
        self.stop_button.pack(side='right', padx=8)
        self.count_var = tk.StringVar(value='0 个文件')
        ttk.Label(toolbar, textvariable=self.count_var, style='Muted.TLabel').pack(side='right', padx=16)
        self.status_var = tk.StringVar(value='就绪')
        ttk.Label(main, textvariable=self.status_var, wraplength=980).grid(row=5, column=0, sticky='ew', pady=(2, 8))
        self.progress = ttk.Progressbar(main, mode='determinate', maximum=1)
        self.progress.grid(row=6, column=0, sticky='ew', pady=(0, 16))
        log_frame = ttk.Frame(main)
        log_frame.grid(row=7, column=0, sticky='nsew')
        log_frame.rowconfigure(1, weight=1)
        log_frame.columnconfigure(0, weight=1)
        log_header = ttk.Frame(log_frame)
        log_header.grid(row=0, column=0, columnspan=2, sticky='ew', pady=(0, 6))
        ttk.Label(log_header, text='运行日志', style='Section.TLabel').pack(side='left')
        ttk.Button(log_header, text='打开输出', command=self.open_output).pack(side='right')
        self.log = tk.Text(log_frame, height=8, wrap='word', background='#172534', foreground='#d6e4f0', insertbackground='white', font=('Consolas', 10), relief='flat', padx=12, pady=10, state='disabled')
        self.log.grid(row=1, column=0, sticky='nsew')
        log_scroll = ttk.Scrollbar(log_frame, orient='vertical', command=self.log.yview)
        log_scroll.grid(row=1, column=1, sticky='ns')
        self.log.configure(yscrollcommand=log_scroll.set)

    def append_log(self, text):
        self.log.configure(state='normal')
        self.log.insert('end', text)
        lines = int(self.log.index('end-1c').split('.')[0])
        if lines > 1600:
            self.log.delete('1.0', f'{lines - 1200}.0')
        self.log.see('end')
        self.log.configure(state='disabled')

    def choose_files(self):
        files = filedialog.askopenfilenames(parent=self, title=self.t('选择视频文件（可多选）'), filetypes=[(self.t('视频文件'), ' '.join('*' + extension for extension in sorted(VIDEO_EXTENSIONS))), (self.t('所有文件'), '*.*')])
        self.add_paths(files)

    def on_drop(self, event):
        if self.busy:
            self.set_status('正在运行，请在本批次结束后添加文件。')
            return REFUSE_DROP
        try:
            self.add_paths(self.tk.splitlist(event.data))
        except tk.TclError as exc:
            self.append_log(self.t('拖放数据读取失败：{error}\n', error=str(exc)))
            return REFUSE_DROP
        return COPY

    def add_paths(self, paths):
        if self.busy:
            return
        known = {os.path.normcase(str(job.source)) for job in self.jobs.values()}
        added = duplicate = skipped = 0
        for raw in paths:
            try:
                path = Path(raw).expanduser().resolve()
                candidates = sorted(path.iterdir()) if path.is_dir() else [path]
                for source in candidates:
                    if not source.is_file() or source.suffix.lower() not in VIDEO_EXTENSIONS:
                        skipped += 1
                        continue
                    if not path.is_file() and source.stem.lower().endswith('_alphahint'):
                        continue
                    key = os.path.normcase(str(source))
                    if key in known:
                        duplicate += 1
                        continue
                    identifier = uuid.uuid4().hex
                    self.jobs[identifier] = Job(identifier, source)
                    self.table.insert('', 'end', iid=identifier, values=(source.name, self.t(STATUS_TEXT['pending']), str(source)))
                    known.add(key)
                    added += 1
            except (OSError, ValueError) as exc:
                skipped += 1
                self.append_log(self.t('无法添加 {path}：{error}\n', path=raw, error=str(exc)))
        self.count_var.set(self.t('{count} 个文件', count=len(self.jobs)))
        self.set_status('__added__', count=added, duplicates=duplicate, skipped=skipped)

    def remove_selected(self):
        if self.busy:
            return
        for identifier in self.table.selection():
            self.table.delete(identifier)
            self.jobs.pop(identifier, None)
        self.count_var.set(self.t('{count} 个文件', count=len(self.jobs)))

    def clear(self):
        if not self.busy:
            self.table.delete(*self.table.get_children())
            self.jobs.clear()
            self.count_var.set(self.t('{count} 个文件', count=0))
            self.set_status('就绪')
            self.progress['value'] = 0

    def show_settings(self):
        if self.busy:
            return
        if self.settings_dialog and self.settings_dialog.winfo_exists():
            self.settings_dialog.lift()
            return
        self.settings_dialog = SettingsDialog(self, self.settings, self.apply_settings)

    def apply_settings(self, settings):
        self.settings = settings
        self.append_log(self.t('设置已保存：{outputs} · {memory}\n', outputs=' / '.join(self.t(OUTPUT_LABELS[name]) for name in settings.outputs), memory=self.t('自动显存') if settings.memory_mode == 'auto' else self.t('低显存 {frames} 帧窗口', frames=settings.window_size)))

    def set_busy(self, busy):
        self.busy = busy
        for button in (self.add_button, self.remove_button, self.clear_button, self.settings_button, self.run_button):
            button.configure(state='disabled' if busy else 'normal')
        self.stop_button.configure(state='normal' if busy else 'disabled')

    def run_batch(self):
        if self.busy:
            return
        pending = [job for job in self.jobs.values() if job.status != 'done']
        if not pending:
            messagebox.showinfo(self.t('没有待运行文件'), self.t('请添加视频文件。已完成的项目不会重复处理；如需重跑，请移除后重新添加。'), parent=self)
            return
        for job in pending:
            job.status = 'pending'
            self.table.item(job.id, values=(job.source.name, self.t(STATUS_TEXT['pending']), str(job.source)), tags=())
        self.progress.configure(value=0, maximum=len(pending))
        self.set_busy(True)
        self.set_status('准备运行 {count} 个文件 · 文件计数进度（单文件详细进度见日志）', count=len(pending))
        try:
            self.runner.start(pending, self.settings)
        except Exception as exc:
            self.set_busy(False)
            messagebox.showerror(self.t('无法启动'), translate_error(exc, self.settings.language), parent=self)

    def stop_batch(self):
        if self.busy:
            self.runner.stop()
            self.stop_button.configure(state='disabled')
            self.set_status('正在停止当前推理；已完成的输出保留，未开始的文件不受影响…')

    def poll_events(self):
        try:
            for _ in range(300):
                kind, event = self.events.get_nowait()
                if kind == 'log':
                    self.append_log(event['text'])
                elif kind == 'job':
                    job = self.jobs[event['id']]
                    job.status = event['status']
                    if 'output' in event:
                        job.output = event['output']
                        self.last_output = job.output
                    self.table.item(job.id, values=(job.source.name, self.t(STATUS_TEXT[job.status]), str(job.source)), tags=(job.status,))
                    self.table.see(job.id)
                    if job.status == 'running':
                        self.set_status('正在处理：{name} · 详细进度见下方日志', name=job.source.name)
                elif kind == 'progress':
                    self.progress['value'] = event['current']
                elif kind == 'error':
                    self.append_log(self.t('无法运行：{error}\n', error=translate_error(event['text'], self.settings.language)))
                elif kind == 'finished':
                    self.set_status('{state} · 完成 {completed} / {total} · 失败 {failed}', state='已停止' if event['stopped'] else '本批次结束', completed=event['completed'], total=event['total'], failed=event['failed'])
                    self.append_log(self.status_var.get() + '\n')
                    self.set_busy(False)
                    if self.closing:
                        self.destroy()
                        return
        except queue.Empty:
            pass
        self._poll_id = self.after(80, self.poll_events)

    def open_output(self):
        selected = self.table.selection()
        path = self.jobs[selected[0]].output if selected else self.last_output
        if not path or not path.is_dir():
            messagebox.showinfo(self.t('尚无输出'), self.t('选择已运行的文件，或先运行一批文件。'), parent=self)
            return
        try:
            if os.name == 'nt':
                os.startfile(str(path))
            elif sys.platform == 'darwin':
                subprocess.Popen(['open', str(path)])
            else:
                subprocess.Popen(['xdg-open', str(path)])
        except OSError as exc:
            messagebox.showerror(self.t('无法打开目录'), str(exc), parent=self)

    def close(self):
        if self.busy:
            if not messagebox.askyesno(self.t('正在运行'), self.t('停止当前推理并退出？已生成的结果会保留。'), parent=self):
                return
            self.closing = True
            self.stop_batch()
        else:
            self.destroy()

    def destroy(self):
        if self._poll_id is not None:
            try:
                self.after_cancel(self._poll_id)
            except tk.TclError:
                pass
            self._poll_id = None
        super().destroy()


def main():
    if os.name == 'nt':
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('CorridorKey.BatchGUI.2')
        except (AttributeError, OSError):
            pass
    app = CorridorKeyApp(sys.argv[1:])
    app.mainloop()


def run():
    """Entry point shared by ``python -m ck2gui`` and the portable bootstrap."""
    try:
        main()
    except Exception:
        import traceback
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        error_path = STATE_DIR / 'corridorkey_gui_error.log'
        error_path.write_text(traceback.format_exc(), encoding='utf-8')
        if os.name == 'nt':
            ctypes.windll.user32.MessageBoxW(None, f'GUI 启动失败，请查看：\n{error_path}', 'CorridorKey', 0x10)
        raise


if __name__ == '__main__':
    run()
