from datetime import datetime, timezone
from pathlib import Path

from features import aggregate_mfcc, extract_mfcc
from model import AudioBaselineModel
from preprocessing import preprocess_audio


def run_audio_inference(
    file_path: str | Path,
    sample_rate: int = 16000,
) -> dict:
    """
    Run the complete audio perception pipeline.

    Returns a structured signal for downstream multimodal fusion.
    """
    audio, sr = preprocess_audio(
        file_path=file_path,
        sample_rate=sample_rate,
    )

    mfcc = extract_mfcc(
        audio=audio,
        sample_rate=sr,
        n_mfcc=40,
    )

    features = aggregate_mfcc(mfcc)

    model = AudioBaselineModel()
    result = model.predict_score(features)

    return {
        "audio_score": result.audio_score,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "model_version": result.model_version,
    }
