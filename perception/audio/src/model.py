from dataclasses import dataclass

import numpy as np


@dataclass
class AudioSignal:
    """Structured output from the audio perception layer."""

    audio_distress_score: float
    confidence: float
    detected_class: str
    model_version: str = "audio-baseline-v2"


class AudioBaselineModel:
    """
    Lightweight development baseline based on waveform RMS energy.

    IMPORTANT:
    The score represents acoustic activity, not a validated probability
    of distress. This baseline is not a trained safety classifier.
    """

    def __init__(self, model_version: str = "audio-baseline-v2"):
        self.model_version = model_version

    def predict_score(
        self,
        audio: np.ndarray,
        features: np.ndarray,
    ) -> AudioSignal:
        """Return a bounded acoustic-activity signal."""
        audio = np.asarray(audio, dtype=np.float32)
        features = np.asarray(features, dtype=np.float32)

        if audio.ndim != 1:
            raise ValueError("Audio must be a one-dimensional mono waveform.")

        if audio.size == 0:
            raise ValueError("Audio array is empty.")

        if features.ndim != 1:
            raise ValueError("Feature vector must be one-dimensional.")

        if features.size == 0:
            raise ValueError("Feature vector is empty.")

        if not np.all(np.isfinite(audio)):
            raise ValueError("Audio array contains NaN or Inf values.")

        if not np.all(np.isfinite(features)):
            raise ValueError("Feature vector contains NaN or Inf values.")

        rms = float(np.sqrt(np.mean(np.square(audio), dtype=np.float64)))

        # Bounded activity score; not a calibrated distress probability.
        score = float(np.clip(rms / (1.0 + rms), 0.0, 1.0))

        detected_class = "ambient" if rms < 0.01 else "acoustic_activity"

        # This is a heuristic score derived from the activity score,
        # not a calibrated estimate of model correctness.
        confidence = float(np.clip(abs(score - 0.5) * 2.0, 0.0, 1.0))

        return AudioSignal(
            audio_distress_score=score,
            confidence=confidence,
            detected_class=detected_class,
            model_version=self.model_version,
        )
