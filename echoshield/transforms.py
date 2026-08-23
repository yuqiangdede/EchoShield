from __future__ import annotations

import subprocess
from pathlib import Path

from .media import MediaError


PROFILES = ("mild", "codec", "resample")


def _run(cmd: list[str]) -> None:
    proc = subprocess.run(cmd, text=True, capture_output=True)
    if proc.returncode != 0:
        raise MediaError(
            f"Transform failed ({proc.returncode}): {' '.join(cmd)}\n{proc.stderr.strip()}"
        )


def apply_profile(
    profile: str,
    source_wav: Path,
    output_wav: Path,
    *,
    sample_rate: int,
    channels: int,
    workdir: Path,
) -> dict[str, object]:
    if profile not in PROFILES:
        raise ValueError(f"Unknown profile: {profile}")

    if profile == "mild":
        # Ordinary signal-chain perturbations for robustness testing.
        # No automatic third-party detector targeting/optimization is performed.
        _run([
            "ffmpeg", "-y", "-v", "error", "-i", str(source_wav),
            "-af", f"volume=0.995,aresample={sample_rate}",
            "-ar", str(sample_rate), "-ac", str(channels),
            "-c:a", "pcm_s16le", str(output_wav),
        ])
        return {"profile": profile, "volume": 0.995, "sample_rate": sample_rate}

    if profile == "resample":
        intermediate_rate = 32000 if sample_rate != 32000 else 44100
        intermediate = workdir / "resampled_intermediate.wav"
        _run([
            "ffmpeg", "-y", "-v", "error", "-i", str(source_wav),
            "-ar", str(intermediate_rate), "-ac", str(channels),
            "-c:a", "pcm_s16le", str(intermediate),
        ])
        _run([
            "ffmpeg", "-y", "-v", "error", "-i", str(intermediate),
            "-ar", str(sample_rate), "-ac", str(channels),
            "-c:a", "pcm_s16le", str(output_wav),
        ])
        return {
            "profile": profile,
            "original_rate": sample_rate,
            "intermediate_rate": intermediate_rate,
        }

    encoded = workdir / "codec_roundtrip.m4a"
    _run([
        "ffmpeg", "-y", "-v", "error", "-i", str(source_wav),
        "-c:a", "aac", "-b:a", "160k", str(encoded),
    ])
    _run([
        "ffmpeg", "-y", "-v", "error", "-i", str(encoded),
        "-ar", str(sample_rate), "-ac", str(channels),
        "-c:a", "pcm_s16le", str(output_wav),
    ])
    return {"profile": profile, "codec": "AAC", "bitrate": "160k"}
