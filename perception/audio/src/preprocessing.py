from pathlib import Path

import librosa
import numpy as np

DEFAULT_SAMPLE_RATE = 16000
MIN_AUDIO_SAMPLES = 2048


def load_audio(
    file_path: str | Path,
    sample_rate: int = DEFAULT_SAMPLE_RATE,
) -> tuple[np.ndarray, int]:
    """
    Load an audio file as mono waveform.
    """
    file_path = Path(file_path)

    if not file_path.exists():
        raise FileNotFoundError(f"Audio file not found: {file_path}")

    audio, sr = librosa.load(
        file_path,
        sr=sample_rate,
        mono=True,
    )

    if audio.size == 0:
        raise ValueError("Audio file contains no samples.")

    if not np.all(np.isfinite(audio)):
        raise ValueError("Audio file contains NaN or Inf values.")

    if audio.size < MIN_AUDIO_SAMPLES:
        raise ValueError(
            f"Audio is too short. Minimum required samples: " f"{MIN_AUDIO_SAMPLES}."
        )

    return audio.astype(np.float32), sr


def normalize_audio(audio: np.ndarray) -> np.ndarray:
    """
    Normalize waveform amplitude to the range [-1, 1].
    """
    audio = np.asarray(audio, dtype=np.float32)

    if audio.size == 0:
        raise ValueError("Audio array is empty.")

    if not np.all(np.isfinite(audio)):
        raise ValueError("Audio array contains NaN or Inf values.")

    peak = np.max(np.abs(audio))

    if peak == 0:
        return audio

    return audio / peak


def preprocess_audio(
    file_path: str | Path,
    sample_rate: int = DEFAULT_SAMPLE_RATE,
) -> tuple[np.ndarray, int]:
    """
    Complete preprocessing pipeline.

    Steps:
    1. Load audio.
    2. Convert to mono.
    3. Resample to target sample rate.
    4. Validate waveform.
    5. Normalize amplitude.
    """
    audio, sr = load_audio(
        file_path=file_path,
        sample_rate=sample_rate,
    )

    audio = normalize_audio(audio)

    return audio, sr
