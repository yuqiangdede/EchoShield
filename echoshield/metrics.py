from __future__ import annotations

import math
import wave
from pathlib import Path

import numpy as np


def read_pcm16_wav(path: Path) -> tuple[np.ndarray, int]:
    with wave.open(str(path), "rb") as wav:
        channels = wav.getnchannels()
        sample_rate = wav.getframerate()
        sample_width = wav.getsampwidth()
        frames = wav.readframes(wav.getnframes())
    if sample_width != 2:
        raise ValueError(f"Expected PCM16 WAV, got sample width {sample_width}")
    audio = np.frombuffer(frames, dtype="<i2").astype(np.float32) / 32768.0
    if channels > 1:
        audio = audio.reshape(-1, channels)
    else:
        audio = audio.reshape(-1, 1)
    return audio, sample_rate


def _aligned_mono(a: np.ndarray, b: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    n = min(len(a), len(b))
    if n == 0:
        raise ValueError("Cannot compare empty audio")
    return a[:n].mean(axis=1), b[:n].mean(axis=1)


def _rms(x: np.ndarray) -> float:
    return float(np.sqrt(np.mean(np.square(x), dtype=np.float64)))


def _spectral_distance(a: np.ndarray, b: np.ndarray, frame_size: int = 4096, max_frames: int = 160) -> float:
    n = min(len(a), len(b))
    if n < frame_size:
        frame_size = max(256, 2 ** int(math.floor(math.log2(max(256, n)))))
    if n < frame_size:
        return 0.0

    starts = np.linspace(0, n - frame_size, num=min(max_frames, max(1, n // frame_size)), dtype=int)
    window = np.hanning(frame_size).astype(np.float32)
    diffs: list[float] = []
    for start in starts:
        fa = np.fft.rfft(a[start:start + frame_size] * window)
        fb = np.fft.rfft(b[start:start + frame_size] * window)
        la = np.log1p(np.abs(fa))
        lb = np.log1p(np.abs(fb))
        denom = float(np.sqrt(np.mean(np.square(la))) + 1e-12)
        diffs.append(float(np.sqrt(np.mean(np.square(la - lb))) / denom))
    return float(np.mean(diffs))


def compare_wavs(original: Path, candidate: Path) -> dict[str, float]:
    a, rate_a = read_pcm16_wav(original)
    b, rate_b = read_pcm16_wav(candidate)
    mono_a, mono_b = _aligned_mono(a, b)

    err = mono_a - mono_b
    rms_a = _rms(mono_a)
    rms_b = _rms(mono_b)
    rms_err = _rms(err)
    snr_db = 120.0 if rms_err < 1e-12 else 20.0 * math.log10(max(rms_a, 1e-12) / rms_err)

    if np.std(mono_a) < 1e-12 or np.std(mono_b) < 1e-12:
        correlation = 1.0 if np.allclose(mono_a, mono_b) else 0.0
    else:
        correlation = float(np.corrcoef(mono_a, mono_b)[0, 1])

    duration_a = len(a) / rate_a
    duration_b = len(b) / rate_b

    return {
        "original_duration_s": round(duration_a, 6),
        "candidate_duration_s": round(duration_b, 6),
        "duration_delta_ms": round((duration_b - duration_a) * 1000.0, 3),
        "original_rms": round(rms_a, 8),
        "candidate_rms": round(rms_b, 8),
        "rms_delta_db": round(20.0 * math.log10(max(rms_b, 1e-12) / max(rms_a, 1e-12)), 4),
        "peak_delta": round(float(np.max(np.abs(mono_b)) - np.max(np.abs(mono_a))), 8),
        "snr_db": round(snr_db, 4),
        "correlation": round(correlation, 8),
        "spectral_distance": round(_spectral_distance(mono_a, mono_b), 8),
    }
