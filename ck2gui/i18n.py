"""Chinese/English UI strings. Model/ffmpeg logs remain in their original language."""
from __future__ import annotations

TRANSLATIONS = {
    '设置': 'Settings',
    '设置 · CorridorKey 2.0': 'Settings · CorridorKey 2.0',
    'CorridorKey 2.0 · 批量抠像': 'CorridorKey 2.0 · Batch Keyer',
    '批量视频抠像  /  本地 GPU 运行': 'Batch video keying  /  Local GPU processing',
    '将多个视频文件拖到这里或下方列表\n也可以点击“添加文件” · 支持 MP4 / MOV / MKV 等': 'Drop multiple videos here or into the list below\nOr choose Add files · MP4 / MOV / MKV and more',
    '文件名': 'File name', '状态': 'Status', '文件路径': 'File path',
    '添加文件': 'Add files', '移除选中': 'Remove selected', '清空': 'Clear',
    '运行': 'Run', '停止': 'Stop', '运行日志': 'Activity log', '打开输出': 'Open output',
    '待运行': 'Queued', '运行中': 'Running', '已完成': 'Done', '失败': 'Failed', '已停止': 'Stopped',
    '就绪': 'Ready', '{count} 个文件': '{count} files',
    '输出位置': 'Output location',
    '留空：每个素材旁新建 out_素材名 文件夹': 'Leave blank to create out_<clip> beside each source file.',
    '浏览…': 'Browse…', '导出内容': 'Outputs',
    'Alpha 遮罩': 'Alpha matte', '前景 RGB': 'Foreground RGB',
    '棋盘格预览': 'Checkerboard preview', '透明视频 (ProRes MOV)': 'Transparent video (ProRes MOV)',
    '显存模式': 'GPU memory mode', '自动（推荐）': 'Automatic (recommended)', '低显存': 'Low VRAM',
    '低显存窗口（帧）': 'Low-VRAM window (frames)', '处理缩放': 'Processing scale',
    '1.0 保留原始分辨率；较小值会降低输出分辨率。': '1.0 keeps native resolution; smaller values reduce output resolution.',
    '帧数上限（0 = 全部）': 'Frame limit (0 = all)',
    '自动查找同名 FrameHint 图片 / _AlphaHint 视频': 'Find companion FrameHint images / _AlphaHint videos automatically',
    '所有文件使用相同设置，按顺序运行；已存在的输出不会被覆盖。': 'Files run sequentially with the same settings. Existing output is never overwritten.',
    '取消': 'Cancel', '保存': 'Save',
    '选择统一输出目录（每个素材会另建子文件夹）': 'Choose output folder (a subfolder will be created for each clip)',
    '设置未保存': 'Settings not saved', '设置读取失败，已使用默认设置：{error}\n': 'Could not load settings; using defaults: {error}\n',
    '就绪。将多个视频拖入列表，点击“运行”。双击已处理文件可打开输出文件夹。\n': 'Ready. Drop videos into the list and click Run. Double-click a processed file to open its output folder.\n',
    '选择视频文件（可多选）': 'Select videos (multiple selection supported)',
    '视频文件': 'Video files', '所有文件': 'All files',
    '正在运行，请在本批次结束后添加文件。': 'Processing. Add more files after this batch finishes.',
    '拖放数据读取失败：{error}\n': 'Could not read dropped files: {error}\n',
    '无法添加 {path}：{error}\n': 'Could not add {path}: {error}\n',
    '已添加 {count} 个文件': 'Added {count} files',
    ' · {count} 个重复已忽略': ' · {count} duplicates skipped',
    ' · {count} 个无效项目已忽略': ' · {count} unsupported items skipped',
    '设置已保存：{outputs} · {memory}\n': 'Settings saved: {outputs} · {memory}\n',
    '自动显存': 'Automatic VRAM', '低显存 {frames} 帧窗口': 'Low VRAM, {frames}-frame window',
    '没有待运行文件': 'No queued files',
    '请添加视频文件。已完成的项目不会重复处理；如需重跑，请移除后重新添加。': 'Add some video files. Completed items are skipped; remove and re-add them to run again.',
    '准备运行 {count} 个文件 · 文件计数进度（单文件详细进度见日志）': 'Preparing {count} files · Progress counts files; see the log for per-file details.',
    '无法启动': 'Unable to start',
    '正在停止当前推理；已完成的输出保留，未开始的文件不受影响…': 'Stopping inference. Completed output and unstarted files will be kept…',
    '正在处理：{name} · 详细进度见下方日志': 'Processing: {name} · See the activity log for details.',
    '无法运行：{error}\n': 'Unable to run: {error}\n',
    '本批次结束': 'Batch finished',
    '{state} · 完成 {completed} / {total} · 失败 {failed}': '{state} · Done {completed} / {total} · Failed {failed}',
    '尚无输出': 'No output yet',
    '选择已运行的文件，或先运行一批文件。': 'Select a processed file, or run a batch first.',
    '无法打开目录': 'Could not open folder',
    '正在运行': 'Processing',
    '停止当前推理并退出？已生成的结果会保留。': 'Stop the current inference and exit? Existing output will be kept.',
    '语言切换后无法保存设置：{error}\n': 'Language changed, but settings could not be saved: {error}\n',
    '输出目录必须是文本路径。': 'The output folder must be a text path.',
    '请至少选择一种有效的输出内容。': 'Select at least one valid output.',
    '输出内容不能重复。': 'Outputs must not be repeated.',
    '显存模式无效。': 'Invalid GPU memory mode.', '窗口帧数无效。': 'Invalid window size.',
    '帧数上限必须是非负整数，0 表示全部。': 'The frame limit must be an integer of zero or greater (0 means all).',
    '处理缩放只能是 1.0、0.75 或 0.5。': 'Processing scale must be 1.0, 0.75, or 0.5.',
    '自动提示设置无效。': 'Invalid automatic hint setting.', '语言设置无效。': 'Invalid language setting.',
    '设置文件格式无效。': 'Invalid settings file format.', '设置中的输出列表无效。': 'Invalid output list in settings.',
    '无法创建不重名的输出目录。': 'Could not create a unique output folder.',
    '找不到 ffmpeg，请将其加入 PATH 后重启 GUI。': 'ffmpeg was not found. Check the bundled bin folder or add ffmpeg to PATH.',
    '找不到可用的 Python 环境。': 'No usable Python runtime was found.',
    '未找到 CorridorKey 2.0 根目录（需要包含 infer.py 和 corridorkey/）。请将 ck2-gui 文件夹放进 CorridorKey 2.0 根目录，或设置 CORRIDORKEY_ROOT 环境变量。': 'Could not find the CorridorKey 2.0 root (it must contain infer.py and corridorkey/). Place the ck2-gui folder inside a CorridorKey 2.0 checkout, or set the CORRIDORKEY_ROOT environment variable.',
    '缺少模型文件，请在 CorridorKey 2.0 根目录运行 scripts/download_weights.py：\n': 'Missing model files. Run scripts/download_weights.py from the CorridorKey 2.0 root:\n',
    '已有任务正在运行。': 'A batch is already running.',
    '输入文件不存在：{path}': 'Input file does not exist: {path}',
    '\n--- [{current}/{total}] {name} ---\n输出：{output}\n命令：{command}\n': '\n--- [{current}/{total}] {name} ---\nOutput: {output}\nCommand: {command}\n',
    '任务已停止；部分输出可能未完成，已保留供检查。\n': 'Stopped. Partial output has been kept and may be incomplete.\n',
    '处理失败（退出码 {code}），详见上方日志。继续下一文件。\n': 'Failed (exit code {code}); see the log above. Continuing to the next file.\n',
    '处理失败：{error}\n': 'Failed: {error}\n',
}


def tr(source: str, language: str = 'zh', **values) -> str:
    result = TRANSLATIONS.get(source, source) if language == 'en' else source
    if language == 'en' and values.get('count') == 1:
        result = result.replace('{count} files', '{count} file').replace('{count} duplicates', '{count} duplicate').replace('{count} unsupported items', '{count} unsupported item')
    return result.format(**values) if values else result


def translate_error(error, language: str) -> str:
    text = str(error)
    if language == 'en':
        for source in sorted(TRANSLATIONS, key=len, reverse=True):
            if '{' not in source and source in text:
                text = text.replace(source, TRANSLATIONS[source])
    return text


def translate_widgets(widget, language: str) -> None:
    """Keep the canonical text on each widget so switching is lossless."""
    keys = widget.keys()
    if 'text' in keys and not ('textvariable' in keys and str(widget.cget('textvariable'))):
        source = getattr(widget, '_translation_source', None)
        if source is None:
            source = str(widget.cget('text'))
            widget._translation_source = source
        widget.configure(text=tr(source, language))
    for child in widget.winfo_children():
        translate_widgets(child, language)
