from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class MediaError(RuntimeError):
    pass


@dataclass(frozen=True)
class AudioInfo:
    codec: str
    sample_rate: int
    channels: int
    bit_rate: int | None
    duration: float | None


def _run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    proc = subprocess.run(cmd, text=True, capture_output=True)
    if proc.returncode != 0:
        raise MediaError(
            f"Command failed ({proc.returncode}): {' '.join(cmd)}\n{proc.stderr.strip()}"
        )
    return proc


def check_ffmpeg() -> None:
    missing = [tool for tool in ("ffmpeg", "ffprobe") if shutil.which(tool) is None]
    if missing:
        raise MediaError(f"Missing required tool(s): {', '.join(missing)}")


def probe(path: Path) -> dict[str, Any]:
    proc = _run([
        "ffprobe", "-v", "error", "-show_streams", "-show_format",
        "-of", "json", str(path),
    ])
    return json.loads(proc.stdout)


def get_audio_info(probe_data: dict[str, Any]) -> AudioInfo:
    for stream in probe_data.get("streams", []):
        if stream.get("codec_type") == "audio":
            bit_rate = stream.get("bit_rate")
            duration = stream.get("duration") or probe_data.get("format", {}).get("duration")
            return AudioInfo(
                codec=str(stream.get("codec_name") or "unknown"),
                sample_rate=int(stream.get("sample_rate") or 48000),
                channels=int(stream.get("channels") or 2),
                bit_rate=int(bit_rate) if bit_rate else None,
                duration=float(duration) if duration else None,
            )
    raise MediaError("Input MP4 has no audio stream")


def extract_audio_wav(input_path: Path, output_wav: Path, *, limit_seconds: float | None = None) -> None:
    cmd = ["ffmpeg", "-y", "-v", "error", "-i", str(input_path), "-map", "0:a:0"]
    if limit_seconds is not None:
        cmd += ["-t", f"{limit_seconds:.3f}"]
    cmd += ["-vn", "-c:a", "pcm_s16le", str(output_wav)]
    _run(cmd)


def mux_processed_audio(
    input_mp4: Path,
    processed_wav: Path,
    output_mp4: Path,
    *,
    audio_bitrate: str = "192k",
    limit_seconds: float | None = None,
) -> None:
    output_mp4.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg", "-y", "-v", "error",
        "-i", str(input_mp4),
        "-i", str(processed_wav),
        "-map", "0:v:0?",
        "-map", "1:a:0",
        "-map_metadata", "0",
        "-c:v", "copy",
        "-c:a", "aac",
        "-b:a", audio_bitrate,
    ]
    if limit_seconds is not None:
        cmd += ["-t", f"{limit_seconds:.3f}"]
    cmd += ["-shortest", "-movflags", "+faststart", str(output_mp4)]
    _run(cmd)
