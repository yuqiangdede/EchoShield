from __future__ import annotations

from pathlib import Path

import numpy as np

from .metrics import read_pcm16_wav


def _mono(path: Path) -> tuple[np.ndarray, int]:
    audio, sample_rate = read_pcm16_wav(path)
    return audio.mean(axis=1), sample_rate


def _band_signature(
    signal: np.ndarray,
    sample_rate: int,
    *,
    frame_size: int = 4096,
    bands: int = 32,
    max_frames: int = 96,
) -> np.ndarray:
    if len(signal) < 256:
        return np.zeros(bands * 2, dtype=np.float64)
    frame_size = min(frame_size, 2 ** int(np.floor(np.log2(len(signal)))))
    frame_size = max(256, frame_size)
    if len(signal) < frame_size:
        signal = np.pad(signal, (0, frame_size - len(signal)))

    max_start = max(0, len(signal) - frame_size)
    count = min(max_frames, max(1, len(signal) // max(1, frame_size // 2)))
    starts = np.linspace(0, max_start, num=count, dtype=int)
    window = np.hanning(frame_size)
    freqs = np.fft.rfftfreq(frame_size, 1.0 / sample_rate)
    low = 80.0
    high = min(8000.0, sample_rate / 2.0 - 1.0)
    if high <= low:
        high = sample_rate / 2.0
    edges = np.geomspace(low, max(low + 1.0, high), bands + 1)

    vectors: list[np.ndarray] = []
    for start in starts:
        frame = signal[start:start + frame_size]
        spectrum = np.log1p(np.abs(np.fft.rfft(frame * window)))
        vals = np.zeros(bands, dtype=np.float64)
        for idx in range(bands):
            mask = (freqs >= edges[idx]) & (freqs < edges[idx + 1])
            if np.any(mask):
                vals[idx] = float(np.mean(spectrum[mask]))
        vectors.append(vals)

    matrix = np.vstack(vectors)
    signature = np.concatenate([matrix.mean(axis=0), matrix.std(axis=0)])
    norm = float(np.linalg.norm(signature))
    return signature / norm if norm > 1e-12 else signature


def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    denom = float(np.linalg.norm(a) * np.linalg.norm(b))
    if denom <= 1e-12:
        return 1.0 if np.allclose(a, b) else 0.0
    return float(np.clip(np.dot(a, b) / denom, 0.0, 1.0))


def analyze_similarity(
    original: Path,
    candidate: Path,
    *,
    window_seconds: float = 10.0,
    step_seconds: float = 5.0,
    match_threshold: float = 0.90,
) -> dict[str, object]:
    a, rate_a = _mono(original)
    b, rate_b = _mono(candidate)
    if rate_a != rate_b:
        raise ValueError(f"Detector expects equal sample rates, got {rate_a} and {rate_b}")
    if window_seconds <= 0 or step_seconds <= 0:
        raise ValueError("window_seconds and step_seconds must be positive")
    if not 0.0 <= match_threshold <= 1.0:
        raise ValueError("match_threshold must be between 0 and 1")

    n = min(len(a), len(b))
    a = a[:n]
    b = b[:n]
    global_similarity = _cosine_similarity(
        _band_signature(a, rate_a), _band_signature(b, rate_a)
    )

    window_samples = max(1, int(round(window_seconds * rate_a)))
    step_samples = max(1, int(round(step_seconds * rate_a)))
    windows: list[dict[str, float | bool]] = []

    if n <= window_samples:
        starts = [0]
        window_samples = n
    else:
        starts = list(range(0, n - window_samples + 1, step_samples))
        final_start = n - window_samples
        if starts[-1] != final_start:
            starts.append(final_start)

    for start in starts:
        end = min(n, start + window_samples)
        score = _cosine_similarity(
            _band_signature(a[start:end], rate_a, max_frames=32),
            _band_signature(b[start:end], rate_a, max_frames=32),
        )
        windows.append({
            "start_s": round(start / rate_a, 3),
            "end_s": round(end / rate_a, 3),
            "similarity": round(score, 6),
            "matched": bool(score >= match_threshold),
        })

    scores = [float(item["similarity"]) for item in windows]
    matched = sum(bool(item["matched"]) for item in windows)
    return {
        "name": "local_spectral_signature_v1",
        "description": "Local aligned spectral-signature similarity for robustness testing",
        "global_similarity": round(global_similarity, 6),
        "window_seconds": window_seconds,
        "step_seconds": step_seconds,
        "match_threshold": match_threshold,
        "window_count": len(windows),
        "window_similarity_avg": round(float(np.mean(scores)), 6),
        "window_similarity_min": round(float(np.min(scores)), 6),
        "window_similarity_max": round(float(np.max(scores)), 6),
        "matched_window_ratio": round(matched / len(windows), 6),
        "windows": windows,
    }
