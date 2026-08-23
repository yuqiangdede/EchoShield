# EchoShield

EchoShield 是一个面向**音频识别鲁棒性测试**的本地工具：输入 MP4，保留原视频流，仅对音频执行可配置的测试变换，并重新封装为 MP4，同时生成质量评估报告。

> 本项目定位为自有/授权音频与识别系统的鲁棒性验证，不包含针对第三方版权检测服务的自动绕过优化。

## MVP 功能

- 输入 `MP4`，输出仍为 `MP4`
- 视频流 `stream copy`，不重新编码
- 音频提取为 PCM WAV 后执行测试变换
- 内置 `mild` / `codec` / `resample` 三种测试 profile
- 输出音频质量指标：时长、RMS、峰值、SNR、频谱距离
- 生成 `report.json` 和单文件 `report.html`
- `fast` 模式只处理前 60 秒，并输出 60 秒预览 MP4，便于快速开发验证

## 环境

- Python 3.10+
- FFmpeg / ffprobe（需要在 `PATH` 中）

## 安装

```bash
python -m venv .venv
# Windows
.venv\\Scripts\\activate
# Linux/macOS
# source .venv/bin/activate

pip install -e .
```

确认 FFmpeg：

```bash
ffmpeg -version
ffprobe -version
```

## 使用

```bash
echoshield input.mp4 -o output.mp4 --profile mild
```

快速模式：

```bash
echoshield input.mp4 -o output.mp4 --profile mild --fast
```

输出目录默认与输出 MP4 同级：

```text
output.mp4
output_report.json
output_report.html
```

保留中间 WAV 便于调试：

```bash
echoshield input.mp4 -o output.mp4 --profile codec --keep-workdir
```

## Profile

### `mild`

轻量链路扰动，用于验证识别/处理链对常见轻微信号变化的稳定性。

### `codec`

执行一次 AAC 编解码回环，再恢复到 PCM，模拟常见平台转码链路。

### `resample`

执行采样率往返变换，模拟音频经过不同设备/服务后的重采样链路。

## 目录结构

```text
echoshield/
├── __init__.py
├── __main__.py
├── cli.py
├── media.py
├── transforms.py
├── metrics.py
└── report.py

tests/
└── test_metrics.py
```

## 设计原则

1. **视频不动**：最终封装使用 FFmpeg `-c:v copy`。
2. **音频独立处理**：解码成 PCM，完成实验后重新编码 AAC。
3. **可复现**：报告记录输入信息、profile、FFmpeg 命令结果和质量指标。
4. **先做闭环**：MVP 先保证 `MP4 -> 音频测试 -> MP4 + 报告` 跑通，再扩展更多 detector/metric 插件。

## 后续计划

- Detector 插件接口：对接自有 fingerprint / embedding 服务
- 滑动窗口鲁棒性评估（5s/10s/30s）
- ViSQOL 等感知质量指标
- Pareto 报告（识别稳定性 vs 感知质量）
- Web UI / 批量目录测试

## License

MIT
