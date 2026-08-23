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


def extract_audio_wav(
    input_path: Path,
    output_wav: Path,
    *,
    limit_seconds: float | None = None,
    start_seconds: float | None = None,
) -> None:
    cmd = ["ffmpeg", "-y", "-v", "error"]
    if start_seconds is not None and start_seconds > 0:
        cmd += ["-ss", f"{start_seconds:.6f}"]
    cmd += ["-i", str(input_path), "-map", "0:a:0"]
    if limit_seconds is not None:
        cmd += ["-t", f"{limit_seconds:.6f}"]
    cmd += ["-vn", "-c:a", "pcm_s16le", str(output_wav)]
    _run(cmd)


def create_padded_test_audio(
    source_wav: Path,
    output_wav: Path,
    *,
    sample_rate: int,
    channels: int,
    padding_seconds: float,
    workdir: Path,
    seed: int = 20260823,
    amplitude: float = 0.0025,
) -> dict[str, object]:
    """Add deterministic, low-level pink-noise test segments before/after audio."""
    if not 0.25 <= padding_seconds <= 10.0:
        raise ValueError("padding_seconds must be between 0.25 and 10.0")
    if channels < 1:
        raise ValueError("channels must be >= 1")

    intro = workdir / "padding_intro.wav"
    outro = workdir / "padding_outro.wav"

    def make_noise(path: Path, noise_seed: int) -> None:
        source = (
            f"anoisesrc=color=pink:amplitude={amplitude}:sample_rate={sample_rate}:"
            f"duration={padding_seconds:.6f}:seed={noise_seed}"
        )
        _run([
            "ffmpeg", "-y", "-v", "error",
            "-f", "lavfi", "-i", source,
            "-ar", str(sample_rate),
            "-ac", str(channels),
            "-c:a", "pcm_s16le",
            str(path),
        ])

    make_noise(intro, seed)
    make_noise(outro, seed + 1)

    _run([
        "ffmpeg", "-y", "-v", "error",
        "-i", str(intro),
        "-i", str(source_wav),
        "-i", str(outro),
        "-filter_complex", "[0:a][1:a][2:a]concat=n=3:v=0:a=1[out]",
        "-map", "[out]",
        "-ar", str(sample_rate),
        "-ac", str(channels),
        "-c:a", "pcm_s16le",
        str(output_wav),
    ])

    return {
        "enabled": True,
        "intro_seconds": round(padding_seconds, 3),
        "outro_seconds": round(padding_seconds, 3),
        "signal": "low_level_pink_noise",
        "seed": seed,
        "amplitude": amplitude,
    }


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
        "-map_chapters", "0",
        "-c:v", "copy",
        "-c:a", "aac",
        "-b:a", audio_bitrate,
    ]
    if limit_seconds is not None:
        cmd += ["-t", f"{limit_seconds:.3f}"]
    cmd += ["-shortest", "-movflags", "+faststart", str(output_mp4)]
    _run(cmd)
    if not output_mp4.exists() or output_mp4.stat().st_size == 0:
        raise MediaError("FFmpeg finished but output MP4 was not created")


def mux_processed_audio_with_padding(
    input_mp4: Path,
    padded_wav: Path,
    output_mp4: Path,
    *,
    content_duration: float,
    padding_seconds: float,
    audio_bitrate: str = "192k",
) -> None:
    """Mux padded audio and clone first/last video frames for matching duration.

    Padding requires video filtering, so this mode re-encodes video instead of stream-copying it.
    """
    output_mp4.parent.mkdir(parents=True, exist_ok=True)
    video_filter = (
        f"[0:v:0]trim=duration={content_duration:.6f},setpts=PTS-STARTPTS,"
        f"tpad=start_mode=clone:start_duration={padding_seconds:.6f}s:"
        f"stop_mode=clone:stop_duration={padding_seconds:.6f}s[v]"
    )
    cmd = [
        "ffmpeg", "-y", "-v", "error",
        "-i", str(input_mp4),
        "-i", str(padded_wav),
        "-filter_complex", video_filter,
        "-map", "[v]",
        "-map", "1:a:0",
        "-map_metadata", "0",
        "-map_chapters", "0",
        "-c:v", "libx264",
        "-preset", "medium",
        "-crf", "18",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", audio_bitrate,
        "-shortest",
        "-movflags", "+faststart",
        str(output_mp4),
    ]
    _run(cmd)
    if not output_mp4.exists() or output_mp4.stat().st_size == 0:
        raise MediaError("FFmpeg finished but padded output MP4 was not created")
