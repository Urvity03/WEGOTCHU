"""
Temporal sequence modeling and anomaly persistence estimation across sliding windows.

STATUS: EXPERIMENTAL / RESEARCH PROTOTYPE.
This standalone utility models duration-weighted anomaly persistence across temporal windows.
It is NOT connected to the active production RiskService or RiskEngine pipeline in
feat/telemetry-ai-adapter. Production risk arbitration is currently governed by the
deterministic rule engine in ai/risk_engine/engine.py.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import math
from typing import Sequence


@dataclass(frozen=True)
class TemporalObservation:
    """A discrete observation with UTC timestamp and anomaly indication."""

    timestamp: datetime
    score: float
    is_anomalous: bool

    def __post_init__(self) -> None:
        if not isinstance(self.timestamp, datetime):
            raise TypeError("timestamp must be a datetime instance")
        if self.timestamp.tzinfo is None:
            raise ValueError("timestamp must be timezone-aware")
        if not math.isfinite(self.score):
            raise ValueError("score must be a finite float")


@dataclass(frozen=True)
class TemporalPersistenceResult:
    """Outcome of temporal trend and persistence evaluation."""

    persistence_ratio: float
    window_duration_seconds: float
    sample_count: int
    is_sustained: bool
    is_transient: bool
    max_gap_seconds: float


class TemporalPersistenceEstimator:
    """
    Estimates whether safety anomalies represent transient spikes or sustained temporal trends.

    Guiding Principles:
      1. Irregular Sampling Invariant: Observations are weighted by their duration intervals,
         not unweighted sample counts, preventing high-frequency bursts from skewing trend analysis.
      2. Gap Awareness: Large temporal gaps (> max_allowed_gap_seconds) segment sequence continuity.
      3. Minimum Window Duration: Windows shorter than min_duration_seconds report zero persistence
         to avoid hasty escalation on initial frames.
    """

    def __init__(
        self,
        min_duration_seconds: float = 30.0,
        min_sustained_seconds: float = 20.0,
        min_persistence_ratio: float = 0.60,
        max_allowed_gap_seconds: float = 15.0,
    ) -> None:
        self.min_duration_seconds = min_duration_seconds
        self.min_sustained_seconds = min_sustained_seconds
        self.min_persistence_ratio = min_persistence_ratio
        self.max_allowed_gap_seconds = max_allowed_gap_seconds

    def evaluate_persistence(
        self,
        observations: Sequence[TemporalObservation],
    ) -> TemporalPersistenceResult:
        """Evaluate the temporal persistence of anomalous indicators in a chronological window."""
        if not observations or len(observations) < 2:
            return TemporalPersistenceResult(
                persistence_ratio=0.0,
                window_duration_seconds=0.0,
                sample_count=len(observations),
                is_sustained=False,
                is_transient=False,
                max_gap_seconds=0.0,
            )

        # Ensure strict chronological ordering
        sorted_obs = sorted(observations, key=lambda o: o.timestamp)
        total_duration = (
            sorted_obs[-1].timestamp - sorted_obs[0].timestamp
        ).total_seconds()

        if total_duration < self.min_duration_seconds:
            # Below minimum duration threshold for trend inference
            any_anomalous = any(o.is_anomalous for o in sorted_obs)
            return TemporalPersistenceResult(
                persistence_ratio=0.0,
                window_duration_seconds=total_duration,
                sample_count=len(sorted_obs),
                is_sustained=False,
                is_transient=any_anomalous,
                max_gap_seconds=0.0,
            )

        anomalous_duration = 0.0
        max_gap = 0.0

        for i in range(len(sorted_obs) - 1):
            curr = sorted_obs[i]
            nxt = sorted_obs[i + 1]
            dt = (nxt.timestamp - curr.timestamp).total_seconds()
            if dt > max_gap:
                max_gap = dt

            # Only count interval if gap is within acceptable limits
            if dt <= self.max_allowed_gap_seconds:
                if curr.is_anomalous:
                    anomalous_duration += dt

        persistence_ratio = float(
            round(min(1.0, max(0.0, anomalous_duration / max(1e-6, total_duration))), 4)
        )
        is_sustained = (
            anomalous_duration >= self.min_sustained_seconds
            and persistence_ratio >= self.min_persistence_ratio
        )
        is_transient = (anomalous_duration > 0.0) and not is_sustained

        return TemporalPersistenceResult(
            persistence_ratio=persistence_ratio,
            window_duration_seconds=float(round(total_duration, 2)),
            sample_count=len(sorted_obs),
            is_sustained=is_sustained,
            is_transient=is_transient,
            max_gap_seconds=float(round(max_gap, 2)),
        )
