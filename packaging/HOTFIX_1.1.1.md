# 1.1.1 本地修复 / Local hotfix

> 说明：下面的运行时修复位于同级的 CorridorKey 2.0 代码目录
> （`corridorkey/runtime.py`、`corridorkey/video_io.py`），不在本 GUI 仓库中。
> 绿色版构建脚本会从同级 CK2 目录复制带修复的运行时；单独克隆本仓库时，
> GUI 仍可配合上游 CorridorKey 2.0 使用。
>
> Note: the runtime fixes below live in the sibling CorridorKey 2.0 checkout,
> not in this GUI repository. The portable builder copies that checkout. The GUI
> itself also works with an unmodified upstream CorridorKey 2.0 checkout.


- 修复容器帧数高于实际可解码帧数时的片尾读取失败。对整段视频先用实际读取所用的同一解码器核实帧数；只处理可解码帧，不复制/填充尾帧。读取限制帧数且从片头开始时，只验证需要的帧数，避免全片预扫描。
- 对 RVM、基础模型、stage 1 和 stage 2 的内存映射添加显式关闭，异常 traceback 保留引用时也能在 Windows 上删除临时文件。
- 每次推理使用独立的临时任务子目录，避免多个窗口或同名素材相互覆盖缓存。
- 清理操作会尝试释放所有写出器和缓存；清理失败不再盖住原始推理错误。
- RVM / 基础模型预处理阶段新增帧数进度日志。
- 保留 FXG CK 图标、中英文切换和现有模型。原素材不被修改。

When container metadata overstates the frame count, the source is now verified with
the same decoder used by inference. All decodable frames are processed; no tail
frames are invented or duplicated. Memory-mapped feature files are explicitly
closed on every exit path, including live-exception traceback paths on Windows.
Each inference uses its own cache directory. Cleanup never replaces the original
inference exception. RVM/foundation prepasses now report frame progress.

- GUI 的临时缓存现在随输出目录，避免大分辨率长片挤满系统 TEMP；运行前按实际尺寸/帧数估算缓存并检查空闲磁盘空间。该 861 帧 8192×4096 素材在低显存模式下预计缓存约 163 GiB，另需安全余量和输出视频空间。
