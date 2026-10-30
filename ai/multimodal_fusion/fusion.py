"""
Multimodal Late-Fusion Engine for synthesizing perception and anomaly streams.

STATUS: EXPERIMENTAL / RESEARCH PROTOTYPE.
This standalone utility explores dynamic confidence-weighted late fusion across heterogeneous
sensor streams. It is NOT connected to the active production RiskService or RiskEngine pipeline
in feat/telemetry-ai-adapter. Production risk arbitration is currently governed by the
deterministic rule engine in ai/risk_engine/engine.py.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import math
from typing import Sequence


class ModalityStatus(str, Enum):
    """Execution status for an individual sensor modality."""

    AVAILABLE = "AVAILABLE"
    MISSING = "MISSING"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"
    FAILED = "FAILED"


@dataclass(frozen=True)
class ModalitySignal:
    """An individual modality observation."""

    name: str
    score: float | None
    status: ModalityStatus
    confidence: float = 0.0
    threshold: float = 0.50

    @property
    def is_valid(self) -> bool:
        return (
            self.status == ModalityStatus.AVAILABLE
            and self.score is not None
            and math.isfinite(self.score)
            and 0.0 <= self.score <= 1.0
        )

    @property
    def is_anomalous(self) -> bool:
        return self.is_valid and self.score is not None and self.score >= self.threshold


@dataclass(frozen=True)
class FusedMultimodalState:
    """Unified situational assessment produced by multimodal late fusion."""

    fused_score: float | None
    overall_confidence: float
    active_signals: tuple[str, ...]
    available_modalities: tuple[str, ...]
    missing_modalities: tuple[str, ...]
    co_occurring_anomaly: bool


class MultimodalFusionEngine:
    """
    Synthesizes heterogeneous, asynchronous perception streams into a coherent risk state.

    Guiding Principles:
      1. Missing Modalities Remain Missing: Unobserved modalities are represented explicitly
         as None in scores; they are NEVER imputed as 0.0 (which would falsely imply normal safety).
      2. No Synthetic Confidence Inflation: Confidence reflects the real evidence available;
         it is penalized when modalities are unobserved or degraded.
      3. Deterministic Late Fusion: Normalized anomaly scores are aggregated using
         proportional weight allocation across verified available modalities.
    """

    def __init__(
        self,
        nominal_weights: dict[str, float] | None = None,
    ) -> None:
        self.nominal_weights = nominal_weights or {
            "route_deviation": 0.40,
            "kinematic_motion": 0.40,
            "acoustic_distress": 0.20,
        }

    def fuse(self, modality_signals: Sequence[ModalitySignal]) -> FusedMultimodalState:
        """Fuse incoming modality signals into a consolidated multimodal state."""
        valid_signals = [sig for sig in modality_signals if sig.is_valid]
        available_names: list[str] = []
        missing_names: list[str] = []
        active_signals: list[str] = []

        for sig in modality_signals:
            if sig.is_valid:
                available_names.append(sig.name)
                if sig.is_anomalous:
                    active_signals.append(sig.name)
            else:
                missing_names.append(sig.name)

        co_occurring = len(active_signals) >= 2

        if not valid_signals:
            # All modalities missing or uncalibrated
            return FusedMultimodalState(
                fused_score=None,
                overall_confidence=0.20,
                active_signals=(),
                available_modalities=(),
                missing_modalities=tuple(missing_names),
                co_occurring_anomaly=False,
            )

        # Allocate weights dynamically across available valid modalities
        total_nominal_weight = sum(
            self.nominal_weights.get(sig.name, 0.33) for sig in valid_signals
        )
        if total_nominal_weight <= 0:
            total_nominal_weight = 1.0

        weighted_score_sum = 0.0
        weighted_conf_sum = 0.0

        for sig in valid_signals:
            norm_weight = (
                self.nominal_weights.get(sig.name, 0.33) / total_nominal_weight
            )
            weighted_score_sum += (sig.score or 0.0) * norm_weight
            weighted_conf_sum += max(0.0, min(1.0, sig.confidence)) * norm_weight

        # Penalize confidence if critical modalities are missing
        availability_ratio = len(valid_signals) / max(1, len(modality_signals))
        overall_conf = float(
            round(
                min(
                    0.95,
                    max(0.15, weighted_conf_sum * (0.60 + 0.40 * availability_ratio)),
                ),
                4,
            )
        )

        return FusedMultimodalState(
            fused_score=float(round(weighted_score_sum, 4)),
            overall_confidence=overall_conf,
            active_signals=tuple(active_signals),
            available_modalities=tuple(available_names),
            missing_modalities=tuple(missing_names),
            co_occurring_anomaly=co_occurring,
        )
