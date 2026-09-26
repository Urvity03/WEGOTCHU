from dataclasses import dataclass

import numpy as np


@dataclass
class AudioSignal:
    """
    Structured output from the audio perception layer.
    """

    audio_distress_score: float
    confidence: float
    detected_class: str
    model_version: str = "audio-baseline-v2"


class AudioBaselineModel:
    """
    Lightweight development baseline for converting acoustic
    activity into an audio perception signal.

    This is not a trained safety or distress classifier.
    """

    def __init__(self, model_version: str = "audio-baseline-v2"):
        self.model_version = model_version

    def predict_score(
        self,
        audio: np.ndarray,
        features: np.ndarray,
    ) -> AudioSignal:
        """
        Produce a bounded audio perception signal.

        Audio activity is estimated from waveform RMS energy.
        MFCC features are retained as part of the perception
        pipeline but are not treated as a calibrated probability.
        """
        audio = np.asarray(audio, dtype=np.float32)
        features = np.asarray(features, dtype=np.float32)

        if audio.size == 0:
            raise ValueError("Audio array is empty.")

        if features.size == 0:
            raise ValueError("Feature vector is empty.")

        if not np.all(np.isfinite(audio)):
            raise ValueError("Audio array contains NaN or Inf values.")

        if not np.all(np.isfinite(features)):
            raise ValueError("Feature vector contains NaN or Inf values.")

        rms = float(np.sqrt(np.mean(np.square(audio))))

        # Map waveform activity into a bounded development signal.
        score = rms / (1.0 + rms)
        score = float(np.clip(score, 0.0, 1.0))

        if rms < 0.01:
            detected_class = "ambient"
        else:
            detected_class = "acoustic_activity"

        confidence = float(np.clip(abs(score - 0.5) * 2.0, 0.0, 1.0))

        return AudioSignal(
            audio_distress_score=score,
            confidence=confidence,
            detected_class=detected_class,
            model_version=self.model_version,
        )
