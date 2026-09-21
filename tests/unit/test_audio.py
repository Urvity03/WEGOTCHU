import numpy as np

from perception.audio.src.features import aggregate_mfcc, extract_mfcc
from perception.audio.src.preprocessing import normalize_audio


def test_normalize_audio():
    audio = np.array([-2.0, 0.0, 1.0, 2.0], dtype=np.float32)

    normalized = normalize_audio(audio)

    assert np.max(np.abs(normalized)) == 1.0
    assert normalized.dtype == np.float32


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