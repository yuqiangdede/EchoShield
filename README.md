# EchoShield

EchoShield 是一个面向**音频识别鲁棒性测试**的本地工具：输入 MP4，对音频执行可配置的测试变换并重新封装为 MP4，同时对最终 MP4 的音频重新解码后做质量与相似度评估。

> 本项目定位为自有/授权音频与识别系统的鲁棒性验证，不包含针对第三方版权检测服务的自动绕过优化。

## 当前可直接测试

- 输入 `MP4`，输出仍为 `MP4`
- 默认模式视频流 `stream copy`，不重新编码
- 音频提取为 PCM WAV 后执行测试变换
- 内置 `mild` / `codec` / `resample` 三种测试 profile
- `--padding-test`：前后加入可复现的低电平测试音，并同步延长首尾画面
- 输出 MP4 重新解码后再做最终质量检测
- 本地频谱签名相似度检测器
- 10 秒窗口 / 5 秒步长的滑动窗口检测，可自定义
- 质量指标：时长、RMS、峰值、SNR、相关系数、频谱距离
- 生成 `report.json` 和单文件 `report.html`
- HTML 报告带固定目录、媒体信息、编码前/编码后指标、窗口结果
- `--fast` 只处理前 60 秒并输出预览 MP4
- `echoshield-doctor` 环境检查
- `echoshield-demo` 自动生成测试 MP4 并跑完整链路
- GitHub Actions 会实际生成、处理、验证 MP4，而不只是跑单元测试

## 环境

- Python 3.10+
- FFmpeg / ffprobe，需要在 `PATH` 中

## Windows：最短上手流程

克隆仓库后进入项目目录：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\setup_windows.ps1
```

如果电脑没有 FFmpeg：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\setup_windows.ps1 -InstallFFmpeg
```

重新打开 PowerShell 后检查：

```powershell
.\.venv\Scripts\echoshield-doctor.exe
```

先不放自己的文件，直接运行内置 Demo：

```powershell
.\.venv\Scripts\echoshield-demo.exe
```

测试 padding 模式：

```powershell
.\.venv\Scripts\echoshield-demo.exe --padding-test --padding-seconds 3
```

成功后会生成：

```text
demo_output/
├── demo_input.mp4
├── demo_output.mp4
├── demo_output_report.json
└── demo_output_report.html
```

打开 `demo_output_report.html` 即可查看完整结果。

## Linux/macOS

```bash
bash scripts/setup_linux.sh
echoshield-demo
```

如果系统没有 FFmpeg，请先通过系统包管理器安装。

## 用自己的 MP4 测试

最常用：

```bash
echoshield input.mp4 -o output.mp4 --profile codec
```

Windows 虚拟环境直接执行：

```powershell
.\.venv\Scripts\echoshield.exe input.mp4 -o output.mp4 --profile codec
```

运行后得到：

```text
output.mp4
output_report.json
output_report.html
```

### 前后加入测试音

默认前后各 3 秒：

```powershell
.\.venv\Scripts\echoshield.exe input.mp4 `
  -o output.mp4 `
  --profile codec `
  --padding-test `
  --padding-seconds 3 `
  --keep-workdir
```

该模式的行为：

- 前置和后置各加入指定时长的低电平粉红噪声测试段。
- 使用固定随机种子，因此同一版本每次结果可复现，不会自动搜索参数。
- 默认测试音幅度为 `0.0025`，随机种子为 `20260823`；尾部使用下一个种子。
- `--padding-seconds` 允许范围为 `0.25` 到 `10` 秒。
- 为保证音视频时长一致，首帧和尾帧会分别冻结相同时长。
- 只有 padding 模式需要对视频执行 H.264 重新编码；普通模式仍然是视频 `stream copy`。
- 最终音质指标会先跳过前置 padding，再截取原内容长度进行比较，避免把时间偏移误判成音质损坏。
- 本地检测器仍对完整输出文件进行测试，因此可以观察检测器面对前后 padding 时的鲁棒性。

启用 `--keep-workdir` 后会额外看到：

```text
output_work/
├── original.wav
├── candidate.wav
├── candidate_padded.wav
├── padding_intro.wav
├── padding_outro.wav
├── final_mp4_audio.wav
└── final_mp4_content_aligned.wav
```

其中：

- `final_mp4_audio.wav`：最终 MP4 的完整音频，包含前后测试段。
- `final_mp4_content_aligned.wav`：去掉前置测试段后重新对齐的原内容，用于最终音质比较。

### 快速测试前 60 秒

```bash
echoshield input.mp4 -o output.mp4 --profile codec --fast
```

也可以和 padding 一起使用：

```powershell
.\.venv\Scripts\echoshield.exe input.mp4 `
  -o output.mp4 `
  --profile codec `
  --fast `
  --padding-test `
  --padding-seconds 3
```

### 调整滑动窗口

```bash
echoshield input.mp4 -o output.mp4 \
  --profile codec \
  --window-seconds 10 \
  --step-seconds 5 \
  --match-threshold 0.90
```

### 不运行本地检测器

```bash
echoshield input.mp4 -o output.mp4 --no-detector
```

### 保留中间文件

```bash
echoshield input.mp4 -o output.mp4 --profile codec --keep-workdir
```

## Profile

### `mild`

轻量链路变化：很小的音量变化 + 保持原采样率重采样，用于建立基础鲁棒性基线。

### `codec`

先执行一次 AAC 编解码回环，再重新封装最终 MP4。适合模拟常见音视频平台、服务链路中的转码过程。

### `resample`

执行采样率往返变换，再回到原采样率。适合验证不同采集设备、服务或中间链路带来的重采样影响。

## 本地检测器

当前内置：

```text
local_spectral_signature_v1
```

工作方式：

1. 输入音频与最终 MP4 音频转单声道。
2. 计算多个对数频带的频谱统计签名。
3. 计算整段全局相似度。
4. 按时间窗口做对齐比较。
5. 输出窗口平均、最低、最高相似度和达到阈值的窗口比例。

它是一个**本地可复现的基线检测器**，用于观察音频处理前后的机器特征稳定程度，不代表任何具体第三方识别服务。

## 报告重点看什么

`output_report.html` 建议重点看：

- `最终 MP4 音频（AAC 编码后）`：真正交付文件的质量变化
- `global_similarity`：全局频谱签名相似度
- `window_similarity_min`：变化最明显的局部窗口
- `matched_window_ratio`：达到配置阈值的窗口比例
- 滑动窗口明细：定位具体时间段

`report.json` 保存相同数据，方便后续批量统计或接入其他系统。

## 目录结构

```text
echoshield/
├── __init__.py
├── __main__.py
├── cli.py
├── demo.py
├── detector.py
├── doctor.py
├── media.py
├── metrics.py
├── report.py
└── transforms.py

scripts/
├── setup_windows.ps1
└── setup_linux.sh

tests/
├── test_metrics.py
└── test_detector.py
```

## 开发验证

```bash
pytest -q
echoshield-doctor
echoshield-demo --output-dir demo_output --duration 6 --profile codec --padding-test --padding-seconds 1
```

CI 会实际生成 MP4、执行 padding、重新封装，并使用 ffprobe 确认输出文件同时包含视频流和 AAC 音频流，同时检查输出时长确实增长。

## 后续计划

- Detector 插件接口：接入自有 fingerprint / embedding 检测器
- ViSQOL 等感知质量指标
- 多 Profile 批量对比报告
- 目录批处理
- Web UI

## License

MIT
