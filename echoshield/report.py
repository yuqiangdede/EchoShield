from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Any


def write_json_report(path: Path, data: dict[str, Any]) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _table_rows(values: dict[str, Any]) -> str:
    return "".join(
        f"<tr><td>{html.escape(str(k))}</td><td>{html.escape(str(v))}</td></tr>"
        for k, v in values.items()
    )


def write_html_report(path: Path, data: dict[str, Any]) -> None:
    metrics = data["metrics"]
    detector = data.get("detector")
    transform = data["transform"]
    input_info = data["input"]
    output_info = data["output"]

    detector_summary = "<p>未启用本地检测器。</p>"
    window_rows = ""
    if detector:
        detector_summary = f"""
        <div class=\"cards\">
          <div class=\"card\"><span>全局相似度</span><b>{detector['global_similarity']}</b></div>
          <div class=\"card\"><span>窗口平均</span><b>{detector['window_similarity_avg']}</b></div>
          <div class=\"card\"><span>最低窗口</span><b>{detector['window_similarity_min']}</b></div>
          <div class=\"card\"><span>匹配窗口比例</span><b>{float(detector['matched_window_ratio']) * 100:.1f}%</b></div>
        </div>"""
        window_rows = "".join(
            f"<tr><td>{w['start_s']}</td><td>{w['end_s']}</td><td>{w['similarity']}</td><td>{'是' if w['matched'] else '否'}</td></tr>"
            for w in detector["windows"]
        )

    document = f"""<!doctype html>
<html lang=\"zh-CN\">
<head>
<meta charset=\"utf-8\">
<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">
<title>EchoShield Report</title>
<style>
*{{box-sizing:border-box}} body{{font-family:system-ui,-apple-system,Segoe UI,sans-serif;margin:0;background:#f6f7f9;color:#1f2937}}
header{{position:sticky;top:0;background:#111827;color:white;padding:14px 22px;z-index:20}}
.layout{{display:grid;grid-template-columns:210px minmax(0,980px);gap:22px;max-width:1230px;margin:20px auto;padding:0 16px}}
nav{{position:sticky;top:68px;height:max-content;background:white;border:1px solid #e5e7eb;border-radius:10px;padding:14px}}
nav a{{display:block;color:#374151;text-decoration:none;padding:7px 4px}} nav a:hover{{color:#111827;font-weight:600}}
main{{min-width:0}} section{{background:white;border:1px solid #e5e7eb;border-radius:10px;padding:20px;margin-bottom:16px;scroll-margin-top:70px}}
h1,h2{{margin-top:0}} table{{border-collapse:collapse;width:100%;font-size:14px}} td,th{{padding:9px;border-bottom:1px solid #eee;text-align:left}}
td:first-child{{font-weight:600}} code{{background:#f3f4f6;padding:2px 5px;border-radius:4px;word-break:break-all}}
.cards{{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin:12px 0}} .card{{border:1px solid #e5e7eb;border-radius:8px;padding:12px}} .card span{{display:block;color:#6b7280;font-size:12px}} .card b{{display:block;font-size:22px;margin-top:5px}}
.note{{background:#fff7ed;border-left:4px solid #f59e0b}}
@media(max-width:800px){{.layout{{grid-template-columns:1fr}}nav{{position:static}}.cards{{grid-template-columns:repeat(2,1fr)}}}}
</style>
</head>
<body>
<header><strong>EchoShield · 音频鲁棒性测试报告</strong></header>
<div class=\"layout\">
<nav><b>目录</b><a href=\"#summary\">任务概览</a><a href=\"#media\">媒体信息</a><a href=\"#transform\">变换参数</a><a href=\"#quality\">质量指标</a><a href=\"#detector\">本地检测</a><a href=\"#windows\">滑动窗口</a><a href=\"#notes\">说明</a></nav>
<main>
<section id=\"summary\"><h2>任务概览</h2><p><b>输入：</b><code>{html.escape(input_info['path'])}</code></p><p><b>输出：</b><code>{html.escape(output_info['path'])}</code></p><p><b>Profile：</b><code>{html.escape(data['profile'])}</code>　<b>快速模式：</b>{'是' if data['preview_mode'] else '否'}</p></section>
<section id=\"media\"><h2>媒体信息</h2><table><tr><th>项目</th><th>输入</th><th>输出</th></tr><tr><td>Codec</td><td>{html.escape(str(input_info['audio']['codec']))}</td><td>{html.escape(str(output_info['audio']['codec']))}</td></tr><tr><td>Sample Rate</td><td>{input_info['audio']['sample_rate']} Hz</td><td>{output_info['audio']['sample_rate']} Hz</td></tr><tr><td>Channels</td><td>{input_info['audio']['channels']}</td><td>{output_info['audio']['channels']}</td></tr><tr><td>Duration</td><td>{html.escape(str(input_info['audio']['duration']))} s</td><td>{html.escape(str(output_info['audio']['duration']))} s</td></tr></table></section>
<section id=\"transform\"><h2>变换参数</h2><table>{_table_rows(transform)}</table></section>
<section id=\"quality\"><h2>质量指标</h2><h3>处理后 PCM（编码前）</h3><table>{_table_rows(metrics['pre_mux'])}</table><h3>最终 MP4 音频（AAC 编码后）</h3><table>{_table_rows(metrics['final_mp4'])}</table></section>
<section id=\"detector\"><h2>本地检测</h2>{detector_summary}</section>
<section id=\"windows\"><h2>滑动窗口</h2>{'<table><tr><th>开始(s)</th><th>结束(s)</th><th>相似度</th><th>达到阈值</th></tr>' + window_rows + '</table>' if window_rows else '<p>无窗口数据。</p>'}</section>
<section id=\"notes\" class=\"note\"><h2>说明</h2><p>内置检测器是本地、可复现的频谱签名相似度基线，用于衡量常见转码、重采样和轻微信号变化后的鲁棒性。它不是任何第三方版权系统的等价实现，也不会自动搜索规避参数。</p></section>
</main></div></body></html>"""
    path.write_text(document, encoding="utf-8")
