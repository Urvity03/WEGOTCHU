from pathlib import Path

import numpy as np
import pytest
import soundfile as sf

from perception.edge.src.benchmark import benchmark_audio_inference


def create_test_audio(path: Path) -> None:
    sample_rate = 16000
    duration = 1.0
    t = np.arange(int(sample_rate * duration), dtype=np.float32) / sample_rate
    audio = (0.1 * np.sin(2 * np.pi * 440 * t)).astype(np.float32)
    sf.write(path, audio, sample_rate)


def test_benchmark_audio_inference(tmp_path):
    audio_path = tmp_path / "test_audio.wav"
    create_test_audio(audio_path)

    result = benchmark_audio_inference(
        file_path=audio_path,
        warmup_runs=1,
        measured_runs=2,
    )

    assert result["average_latency_ms"] >= 0
    assert result["peak_latency_ms"] >= result["average_latency_ms"]
    assert result["memory_usage_mb"] > 0
    assert result["measured_runs"] == 2
    assert result["model_version"] == "audio-baseline-v2"


def test_benchmark_rejects_invalid_runs(tmp_path):
    audio_path = tmp_path / "test_audio.wav"
    create_test_audio(audio_path)

    with pytest.raises(ValueError, match="measured_runs"):
        benchmark_audio_inference(
            file_path=audio_path,
            measured_runs=0,
        )
