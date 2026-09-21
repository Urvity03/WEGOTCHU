from dataclasses import dataclass

import numpy as np


@dataclass
class AudioSignal:
    """
    Structured output from the audio perception layer.
    """

    audio_score: float
    model_version: str = "audio-baseline-v1"


class AudioBaselineModel:
    """
    Lightweight baseline model for converting acoustic features
    into an audio signal.

    This is a development baseline, not a trained safety classifier.
    """

    def __init__(self, model_version: str = "audio-baseline-v1"):
        self.model_version = model_version

    def predict_score(self, features: np.ndarray) -> AudioSignal:
        """
        Produce a bounded audio score from extracted features.

        The score is a perception signal for downstream fusion;
        it does not determine whether an unsafe event occurred.
        """
        features = np.asarray(features, dtype=np.float32)

        if features.size == 0:
            raise ValueError("Feature vector is empty.")

        # Baseline signal derived from feature magnitude.
        magnitude = float(np.mean(np.abs(features)))

        # Bound the signal to [0, 1].
        score = magnitude / (1.0 + magnitude)
        score = float(np.clip(score, 0.0, 1.0))

        return AudioSignal(
            audio_score=score,
            model_version=self.model_version,
        )
