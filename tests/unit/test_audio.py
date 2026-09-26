import numpy as np
import pytest

from perception.audio.src.features import aggregate_mfcc, extract_mfcc
from perception.audio.src.inference import run_audio_inference
from perception.audio.src.model import AudioBaselineModel
from perception.audio.src.preprocessing import normalize_audio


def test_normalize_audio():
    audio = np.array([-2.0, 0.0, 1.0, 2.0], dtype=np.float32)

    normalized = normalize_audio(audio)

    assert np.max(np.abs(normalized)) == 1.0
    assert normalized.dtype == np.float32


def test_normalize_audio_rejects_non_finite_values():
    audio = np.array([0.0, np.nan, 1.0], dtype=np.float32)

    with pytest.raises(ValueError, match="NaN or Inf"):
        normalize_audio(audio)


def test_extract_mfcc():
    sample_rate = 16000
    duration = 1.0

    t = np.linspace(
        0,
        duration,
        int(sample_rate * duration),
        endpoint=False,
    )

    audio = np.sin(2 * np.pi * 440 * t).astype(np.float32)

    mfcc = extract_mfcc(
        audio=audio,
        sample_rate=sample_rate,
        n_mfcc=40,
    )

    assert mfcc.shape[0] == 40
    assert mfcc.dtype == np.float32


def test_aggregate_mfcc():
    mfcc = np.random.rand(40, 63).astype(np.float32)

    features = aggregate_mfcc(mfcc)

    assert features.shape == (80,)
    assert features.dtype == np.float32


def test_predict_score():
    model = AudioBaselineModel()

    audio = np.ones(16000, dtype=np.float32) * 0.5
    features = np.ones(80, dtype=np.float32)

    result = model.predict_score(
        audio=audio,
        features=features,
    )

    assert 0.0 <= result.audio_distress_score <= 1.0
    assert 0.0 <= result.confidence <= 1.0
    assert result.detected_class == "acoustic_activity"
    assert result.model_version == "audio-baseline-v2"


def test_predict_score_rejects_non_finite_audio():
    model = AudioBaselineModel()

    audio = np.array([0.0, np.inf, 1.0], dtype=np.float32)
    features = np.ones(80, dtype=np.float32)

    with pytest.raises(ValueError, match="NaN or Inf"):
        model.predict_score(
            audio=audio,
            features=features,
        )


def test_predict_score_rejects_empty_features():
    model = AudioBaselineModel()

    audio = np.ones(16000, dtype=np.float32)
    features = np.array([], dtype=np.float32)

    with pytest.raises(ValueError, match="Feature vector is empty"):
        model.predict_score(
            audio=audio,
            features=features,
        )


def test_run_audio_inference(tmp_path):
    sample_rate = 16000
    duration = 1.0

    t = np.linspace(
        0,
        duration,
        int(sample_rate * duration),
        endpoint=False,
    )

    audio = (0.5 * np.sin(2 * np.pi * 440 * t)).astype(np.float32)

    audio_path = tmp_path / "test_audio.wav"

    import soundfile as sf

    sf.write(audio_path, audio, sample_rate)

    result = run_audio_inference(audio_path)

    assert "audio_distress_score" in result
    assert "confidence" in result
    assert "detected_class" in result
    assert "window_duration_seconds" in result
    assert "timestamp" in result
    assert "model_version" in result

    assert 0.0 <= result["audio_distress_score"] <= 1.0
    assert 0.0 <= result["confidence"] <= 1.0
    assert result["window_duration_seconds"] == pytest.approx(1.0)
    assert result["model_version"] == "audio-baseline-v2"


def test_run_audio_inference_rejects_short_audio(tmp_path):
    sample_rate = 16000

    audio = np.zeros(1000, dtype=np.float32)

    audio_path = tmp_path / "short_audio.wav"

    import soundfile as sf

    sf.write(audio_path, audio, sample_rate)

    with pytest.raises(ValueError, match="too short"):
        run_audio_inference(audio_path)
