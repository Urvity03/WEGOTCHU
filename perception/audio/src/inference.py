from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from .features import aggregate_mfcc, extract_mfcc
from .model import AudioBaselineModel
from .preprocessing import preprocess_audio


def run_audio_inference(
    file_path: str | Path,
    sample_rate: int = 16000,
) -> dict:
    """
    Run the complete audio perception pipeline.

    Returns a structured perception signal for downstream
    multimodal fusion.
    """
    audio, sr = preprocess_audio(
        file_path=file_path,
        sample_rate=sample_rate,
    )

    if audio.size == 0:
        raise ValueError("Audio array is empty.")

    if not np.all(np.isfinite(audio)):
        raise ValueError("Audio array contains NaN or Inf values.")

    window_duration_seconds = float(audio.size / sr)

    mfcc = extract_mfcc(
        audio=audio,
        sample_rate=sr,
        n_mfcc=40,
    )

    features = aggregate_mfcc(mfcc)

    model = AudioBaselineModel()
    result = model.predict_score(
        audio=audio,
        features=features,
    )

    return {
        "audio_distress_score": result.audio_distress_score,
        "confidence": result.confidence,
        "detected_class": result.detected_class,
        "window_duration_seconds": window_duration_seconds,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "model_version": result.model_version,
    }
