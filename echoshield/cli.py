from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

from . import __version__
from .detector import analyze_similarity
from .media import check_ffmpeg, extract_audio_wav, get_audio_info, mux_processed_audio, probe
from .metrics import compare_wavs
from .report import write_html_report, write_json_report
from .transforms import PROFILES, apply_profile


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="echoshield",
        description="MP4 audio robustness testing toolkit",
    )
    parser.add_argument("input", type=Path, help="Input MP4")
    parser.add_argument("-o", "--output", type=Path, help="Output MP4")
    parser.add_argument("--profile", choices=PROFILES, default="mild")
    parser.add_argument("--audio-bitrate", default="192k", help="Output AAC bitrate")
    parser.add_argument("--fast", action="store_true", help="Preview mode: process first 60 seconds only")
    parser.add_argument("--keep-workdir", action="store_true", help="Keep intermediate WAV/M4A files")
    parser.add_argument("--no-detector", action="store_true", help="Skip local spectral similarity detector")
    parser.add_argument("--window-seconds", type=float, default=10.0, help="Detector window length")
    parser.add_argument("--step-seconds", type=float, default=5.0, help="Detector window step")
    parser.add_argument("--match-threshold", type=float, default=0.90, help="Window match threshold 0..1")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return parser


def _default_output(input_path: Path) -> Path:
    return input_path.with_name(f"{input_path.stem}_echoshield.mp4")


def run(args: argparse.Namespace) -> dict[str, object]:
    check_ffmpeg()
    input_path = args.input.expanduser().resolve()
    if not input_path.exists():
        raise FileNotFoundError(input_path)
    if input_path.suffix.lower() != ".mp4":
        raise ValueError("EchoShield currently accepts MP4 input only")

    output_path = (args.output or _default_output(input_path)).expanduser().resolve()
    if output_path == input_path:
        raise ValueError("Output path must be different from input path")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    probe_data = probe(input_path)
    audio = get_audio_info(probe_data)
    limit_seconds = 60.0 if args.fast else None

    persistent_workdir = output_path.with_name(f"{output_path.stem}_work")
    temp_ctx = None
    if args.keep_workdir:
        persistent_workdir.mkdir(parents=True, exist_ok=True)
        workdir = persistent_workdir
    else:
        temp_ctx = tempfile.TemporaryDirectory(prefix="echoshield-")
        workdir = Path(temp_ctx.name)

    try:
        original_wav = workdir / "original.wav"
        candidate_wav = workdir / "candidate.wav"
        final_wav = workdir / "final_mp4_audio.wav"
        extract_audio_wav(input_path, original_wav, limit_seconds=limit_seconds)
        transform = apply_profile(
            args.profile,
            original_wav,
            candidate_wav,
            sample_rate=audio.sample_rate,
            channels=audio.channels,
            workdir=workdir,
        )
        pre_metrics = compare_wavs(original_wav, candidate_wav)

        mux_processed_audio(
            input_path,
            candidate_wav,
            output_path,
            audio_bitrate=args.audio_bitrate,
            limit_seconds=limit_seconds,
        )
        output_probe = probe(output_path)
        output_audio = get_audio_info(output_probe)
        extract_audio_wav(output_path, final_wav)
        final_metrics = compare_wavs(original_wav, final_wav)

        detector = None
        if not args.no_detector:
            detector = analyze_similarity(
                original_wav,
                final_wav,
                window_seconds=args.window_seconds,
                step_seconds=args.step_seconds,
                match_threshold=args.match_threshold,
            )

        report: dict[str, object] = {
            "echoshield_version": __version__,
            "profile": args.profile,
            "preview_mode": bool(args.fast),
            "input": {
                "path": str(input_path),
                "audio": {
                    "codec": audio.codec,
                    "sample_rate": audio.sample_rate,
                    "channels": audio.channels,
                    "bit_rate": audio.bit_rate,
                    "duration": audio.duration,
                },
            },
            "output": {
                "path": str(output_path),
                "audio_bitrate": args.audio_bitrate,
                "audio": {
                    "codec": output_audio.codec,
                    "sample_rate": output_audio.sample_rate,
                    "channels": output_audio.channels,
                    "bit_rate": output_audio.bit_rate,
                    "duration": output_audio.duration,
                },
            },
            "transform": transform,
            "metrics": {"pre_mux": pre_metrics, "final_mp4": final_metrics},
            "detector": detector,
        }
        json_path = output_path.with_name(f"{output_path.stem}_report.json")
        html_path = output_path.with_name(f"{output_path.stem}_report.html")
        report["report_json"] = str(json_path)
        report["report_html"] = str(html_path)
        if args.keep_workdir:
            report["workdir"] = str(workdir)
        write_json_report(json_path, report)
        write_html_report(html_path, report)
        return report
    finally:
        if temp_ctx is not None:
            temp_ctx.cleanup()


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        result = run(args)
    except Exception as exc:
        print(f"EchoShield error: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0
