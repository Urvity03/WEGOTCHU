import librosa
import numpy as np


def extract_mfcc(
    audio: np.ndarray,
    sample_rate: int,
    n_mfcc: int = 40,
) -> np.ndarray:
    """
    Extract MFCC features from an audio waveform.
    """
    if audio.size == 0:
        raise ValueError("Audio array is empty.")

    mfcc = librosa.feature.mfcc(
        y=audio,
        sr=sample_rate,
        n_mfcc=n_mfcc,
    )

    return mfcc.astype(np.float32)


def aggregate_mfcc(mfcc: np.ndarray) -> np.ndarray:
    """
    Convert frame-level MFCC features into a fixed-length vector.

    Uses mean and standard deviation for each MFCC coefficient.
    """
    if mfcc.size == 0:
        raise ValueError("MFCC feature array is empty.")

    mean_features = np.mean(mfcc, axis=1)
    std_features = np.std(mfcc, axis=1)

    return np.concatenate(
        [mean_features, std_features]
    ).astype(np.float32)