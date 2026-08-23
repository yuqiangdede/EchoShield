import wave
from pathlib import Path

import numpy as np

from echoshield.detector import analyze_similarity


def _write(path: Path, data: np.ndarray, rate: int = 16000) -> None:
    data = np.clip(data, -1.0, 1.0)
    pcm = (data * 32767).astype("<i2")
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(pcm.tobytes())


def test_detector_identical(tmp_path: Path):
    rate = 16000
    t = np.arange(rate * 3) / rate
    x = 0.4 * np.sin(2 * np.pi * 440 * t) + 0.2 * np.sin(2 * np.pi * 660 * t)
    a = tmp_path / "a.wav"
    b = tmp_path / "b.wav"
    _write(a, x)
    _write(b, x)
    result = analyze_similarity(a, b, window_seconds=1, step_seconds=0.5)
    assert result["global_similarity"] > 0.9999
    assert result["matched_window_ratio"] == 1.0


def test_detector_noise_reduces_similarity(tmp_path: Path):
    rng = np.random.default_rng(7)
    rate = 16000
    t = np.arange(rate * 3) / rate
    x = 0.4 * np.sin(2 * np.pi * 440 * t) + 0.2 * np.sin(2 * np.pi * 660 * t)
    y = x + 0.15 * rng.normal(size=x.shape)
    a = tmp_path / "a.wav"
    b = tmp_path / "b.wav"
    _write(a, x)
    _write(b, y)
    result = analyze_similarity(a, b, window_seconds=1, step_seconds=0.5)
    assert result["global_similarity"] < 0.999
