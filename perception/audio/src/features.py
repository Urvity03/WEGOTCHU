import librosa
import numpy as np


def extract_mfcc(
    audio: np.ndarray,
    sample_rate: int,
    n_mfcc: int = 40,
) -> np.ndarray:
    """
    Extract MFCC features from a valid mono audio waveform.
    """
    audio = np.asarray(audio, dtype=np.float32)

    if audio.ndim != 1:
        raise ValueError("Audio must be a one-dimensional mono waveform.")

    if audio.size == 0:
        raise ValueError("Audio array is empty.")

    if sample_rate <= 0:
        raise ValueError("Sample rate must be greater than zero.")

    if n_mfcc <= 0:
        raise ValueError("n_mfcc must be greater than zero.")

    if not np.all(np.isfinite(audio)):
        raise ValueError("Audio array contains NaN or Inf values.")

    mfcc = librosa.feature.mfcc(
        y=audio,
        sr=sample_rate,
        n_mfcc=n_mfcc,
    )

    if mfcc.size == 0 or not np.all(np.isfinite(mfcc)):
        raise ValueError("MFCC extraction produced invalid features.")

    return mfcc.astype(np.float32)


def aggregate_mfcc(mfcc: np.ndarray) -> np.ndarray:
    """
    Convert frame-level MFCC features into a fixed-length vector
    using the mean and standard deviation of each coefficient.
    """
    mfcc = np.asarray(mfcc, dtype=np.float32)

    if mfcc.ndim != 2:
        raise ValueError("MFCC input must be a two-dimensional array.")

    if mfcc.size == 0:
        raise ValueError("MFCC feature array is empty.")

    if not np.all(np.isfinite(mfcc)):
        raise ValueError("MFCC features contain NaN or Inf values.")

    mean_features = np.mean(mfcc, axis=1)
    std_features = np.std(mfcc, axis=1)

    features = np.concatenate([mean_features, std_features])

    if not np.all(np.isfinite(features)):
        raise ValueError("Aggregated MFCC features contain NaN or Inf values.")

    return features.astype(np.float32)
