from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Any


def write_json_report(path: Path, data: dict[str, Any]) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def write_html_report(path: Path, data: dict[str, Any]) -> None:
    metrics = data["metrics"]
    transform = data["transform"]
    input_info = data["input"]

    metric_rows = "".join(
        f"<tr><td>{html.escape(str(k))}</td><td>{html.escape(str(v))}</td></tr>"
        for k, v in metrics.items()
    )
    transform_rows = "".join(
        f"<tr><td>{html.escape(str(k))}</td><td>{html.escape(str(v))}</td></tr>"
        for k, v in transform.items()
    )

    document = f"""<!doctype html>
<html lang=\"zh-CN\">
<head>
<meta charset=\"utf-8\">
<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">
<title>EchoShield Report</title>
<style>
body{{font-family:system-ui,-apple-system,Segoe UI,sans-serif;margin:0;background:#f6f7f9;color:#1f2937}}
header{{position:sticky;top:0;background:#111827;color:white;padding:16px 24px;z-index:10}}
main{{max-width:980px;margin:24px auto;padding:0 16px}}
section{{background:white;border:1px solid #e5e7eb;border-radius:10px;padding:20px;margin-bottom:16px}}
h1,h2{{margin-top:0}} table{{border-collapse:collapse;width:100%}} td{{padding:9px;border-bottom:1px solid #eee}}
td:first-child{{font-weight:600;width:45%}} code{{background:#f3f4f6;padding:2px 5px;border-radius:4px}}
.note{{background:#fff7ed;border-left:4px solid #f59e0b;padding:12px}}
</style>
</head>
<body>
<header><strong>EchoShield · 音频鲁棒性测试报告</strong></header>
<main>
<section><h2>任务</h2><p><b>输入：</b><code>{html.escape(input_info['path'])}</code></p><p><b>输出：</b><code>{html.escape(data['output']['path'])}</code></p><p><b>Profile：</b><code>{html.escape(data['profile'])}</code></p></section>
<section><h2>音频信息</h2><table><tr><td>Codec</td><td>{html.escape(str(input_info['audio']['codec']))}</td></tr><tr><td>Sample Rate</td><td>{input_info['audio']['sample_rate']} Hz</td></tr><tr><td>Channels</td><td>{input_info['audio']['channels']}</td></tr><tr><td>Duration</td><td>{html.escape(str(input_info['audio']['duration']))} s</td></tr></table></section>
<section><h2>变换参数</h2><table>{transform_rows}</table></section>
<section><h2>质量指标</h2><table>{metric_rows}</table></section>
<section class=\"note\"><b>说明：</b>这些指标用于衡量普通转码/重采样/轻微信号变化后的质量差异；MVP 不会自动针对第三方检测服务搜索规避参数。</section>
</main></body></html>"""
    path.write_text(document, encoding="utf-8")
