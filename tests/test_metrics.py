from __future__ import annotations

import wave
from pathlib import Path

import numpy as np

from echoshield.metrics import compare_wavs


def write_wav(path: Path, samples: np.ndarray, sample_rate: int = 16000) -> None:
    pcm = np.clip(samples, -1.0, 1.0)
    pcm = (pcm * 32767.0).astype("<i2")
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        wav.writeframes(pcm.tobytes())


def test_identical_audio(tmp_path: Path) -> None:
    t = np.arange(16000, dtype=np.float32) / 16000.0
    tone = 0.2 * np.sin(2.0 * np.pi * 440.0 * t)
    a = tmp_path / "a.wav"
    b = tmp_path / "b.wav"
    write_wav(a, tone)
    write_wav(b, tone)

    metrics = compare_wavs(a, b)
    assert metrics["correlation"] > 0.99999
    assert metrics["snr_db"] >= 100.0
    assert metrics["spectral_distance"] < 1e-8


def test_quieter_audio_has_expected_delta(tmp_path: Path) -> None:
    t = np.arange(16000, dtype=np.float32) / 16000.0
    tone = 0.2 * np.sin(2.0 * np.pi * 440.0 * t)
    a = tmp_path / "a.wav"
    b = tmp_path / "b.wav"
    write_wav(a, tone)
    write_wav(b, tone * 0.9)

    metrics = compare_wavs(a, b)
    assert metrics["correlation"] > 0.999
    assert metrics["rms_delta_db"] < 0
    assert metrics["snr_db"] > 10
