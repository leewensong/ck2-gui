# CorridorKey 2.0 绿色版 / Portable GUI

## 中文

1. 将 ZIP 完整解压到一个可写目录，建议使用较短的路径（例如 D:\Apps\CorridorKey）。
2. 双击 CorridorKey.exe（或 Start.cmd）。不要直接在压缩包预览中运行。
3. 将多个视频拖入列表。右上角“中 / E”切换中英文并记住选择。
4. 点击“设置”选择输出内容、目录和显存模式，再点击“运行”。
5. 双击列表中的已处理项目或点击“打开输出”查看结果。

本包内置 Python 3.12、CUDA 版 PyTorch、ffmpeg/ffprobe 及所有模型。
不需要安装 Python、CUDA Toolkit 或 pip 依赖；仍需要兼容的 NVIDIA 显卡和驱动。
硬件要求请参考随附原项目文档。本机验证设备为 RTX 5090 Laptop GPU。
模型与依赖占用约 10 GB；请为解压和视频输出预留足够空间。

程序不需要管理员权限，不写注册表、不创建系统服务、不修改系统 PATH。
设置和启动错误日志位于本目录 data 文件夹；移动整个文件夹即可搬迁。
GUI 推理缓存位于每个输出目录下的 .corridorkey_cache，完成后自动清理任务文件。
开始前会检查临时磁盘空间；长片 / 8K 的低显存路径可能需要数百 GB 缓存。视频输出保存在所选目录。
删除整个文件夹即可移除本绿色版；已经导出到其他位置的视频不会被删除。

默认每个素材旁创建 out_素材名；如目录已存在，会另建 _2、_3 后缀目录，不覆盖结果。
停止推理可能留下不完整输出；已完成项目不会自动重跑，移除并重新添加可重跑。
模型和 ffmpeg 的原始日志保持英文，不随界面语言翻译。

故障排查：双击 Check_runtime.cmd，报告生成于 data\runtime-check.json。
此诊断会检查内置 runtime、GPU 和拖放组件，不会运行真实素材。
也可在命令行执行：runtime\python.exe -I -B bootstrap.py --check --smoke
它会用附带的合成视频执行两个短任务；这只验证推理链路，不代表真实抠像质量。

这是基于原仓库的本地桌面界面，不是 Corridor 官方商业插件。
保留原作者、LICENSE、THIRD_PARTY_NOTICES.md 和依赖许可。
本绿色版本体不随源码仓库发布；构建方式见 ck2-gui 仓库的 packaging/BUILD.md。
对外分发、再打包和商业使用前请确认原项目许可或取得授权。
原项目：https://github.com/nikopueringer/CorridorKey2.0
界面项目：https://github.com/leewensong/ck2-gui

## English

Extract the entire ZIP to a writable folder and double-click CorridorKey.exe.
Drop videos into the list, adjust Settings, and click Run. The top-right 中 / E
button switches Chinese/English and remembers the selection.

Python, CUDA-enabled PyTorch, ffmpeg/ffprobe and all model weights are included.
A compatible NVIDIA GPU and driver are still required. No Python or CUDA Toolkit
installation, administrator privileges, registry entries, services, or system PATH
changes are required. Keep all files together when relocating the application.

Settings and crash reports are stored in the local data folder. Inference may use
the output disk for its temporary feature cache. Disk space is checked before
processing; long 8K clips may need hundreds of GB. Outputs are saved where configured and never
silently overwritten. Model and ffmpeg logs remain in their original language.

Use Check_runtime.cmd for diagnostics. Read LICENSE and THIRD_PARTY_NOTICES.md
before use or sharing. This is a locally modified frontend, not the official plugin.
The portable bundle itself is not published with the source repository; build it
with ck2-gui/packaging/BUILD.md. Confirm upstream permissions before
redistributing, repackaging, or commercial integration.
