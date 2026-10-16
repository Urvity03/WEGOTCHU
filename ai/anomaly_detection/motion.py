"""Motion feature extraction and kinematic anomaly detection for WEGOTCHU."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
import math
from typing import Sequence

import numpy as np

# Standard Earth gravitational acceleration constant (m/s^2)
STANDARD_GRAVITY_MPS2: float = 9.80665

# Minimum time difference in seconds to prevent division-by-zero or derivative explosion
MIN_DT_SECONDS: float = 1e-4
# Maximum interval in seconds to compute a localized instantaneous jerk derivative
MAX_JERK_DT_SECONDS: float = 2.0

# Provisional heuristic thresholds (uncalibrated baseline, pending crisis benchmark dataset)
# Mean dynamic acceleration |a| - g thresholds (m/s^2)
STATIONARY_DYNAMIC_ACCEL_THRESHOLD: float = 0.5
RUNNING_DYNAMIC_ACCEL_THRESHOLD: float = 4.0

# Provisional jerk threshold for abrupt kinematic impulse (m/s^3)
# Note: Abrupt motion may arise from phone drops, sudden stops, stumbles, or impacts.
# It denotes kinematic divergence from smooth locomotion, NOT verified fall or struggle detection.
ABRUPT_JERK_THRESHOLD: float = 30.0


@dataclass(frozen=True)
class MotionSample:
    """
    A single discrete timestamped 3-axis motion observation.

    Matches mobile telemetry contract (Contract 1, Version 0.1):
      - accelerometer: x, y, z in m/s^2 (required)
      - gyroscope: x, y, z in rad/s (optional)
      - speed_mps: optional GPS/fused speed in m/s
    """

    timestamp: datetime
    accel_x: float
    accel_y: float
    accel_z: float
    gyro_x: float | None = None
    gyro_y: float | None = None
    gyro_z: float | None = None
    speed_mps: float | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.timestamp, datetime):
            raise TypeError(
                f"timestamp must be a datetime instance, got {type(self.timestamp).__name__}"
            )
        for name, val in [
            ("accel_x", self.accel_x),
            ("accel_y", self.accel_y),
            ("accel_z", self.accel_z),
        ]:
            if not isinstance(val, (int, float)) or not math.isfinite(val):
                raise ValueError(f"{name} must be a finite float, got {val}")

        for name, val in [
            ("gyro_x", self.gyro_x),
            ("gyro_y", self.gyro_y),
            ("gyro_z", self.gyro_z),
            ("speed_mps", self.speed_mps),
        ]:
            if val is not None:
                if not isinstance(val, (int, float)) or not math.isfinite(val):
                    raise ValueError(
                        f"{name} must be None or a finite float, got {val}"
                    )
                if name == "speed_mps" and val < 0.0:
                    raise ValueError(f"speed_mps must be non-negative, got {val}")


@dataclass(frozen=True)
class MotionFeatures:
    """Extracted time-domain kinematic features from a motion window."""

    sample_count: int
    duration_seconds: float
    mean_accel_magnitude: float
    std_accel_magnitude: float
    max_accel_magnitude: float
    mean_dynamic_accel: float
    max_dynamic_accel: float
    mean_jerk: float
    max_jerk: float
    mean_gyro_magnitude: float | None
    max_gyro_magnitude: float | None


@dataclass(frozen=True)
class MotionAnomalyResult:
    """
    Result of evaluating kinematic motion telemetry.

    Attributes:
        status: Evaluation status ("SUCCESS", "INSUFFICIENT_DATA", "INVALID_DATA").
        motion_anomaly_score: Bounded anomaly indicator in [0.0, 1.0], or None if insufficient/invalid.
                              IMPORTANT: This represents kinematic unusualness relative to baseline
                              locomotion thresholds, NOT a calibrated probability of danger.
        confidence: Confidence score in [0.0, 1.0] reflecting observation density and signal validity.
        motion_state: Inferred activity class ("still", "walking", "running", "abrupt_motion", "unknown").
        features: Computed kinematic features, or None if evaluation failed.
        metadata: Diagnostic details (e.g., sample count, sampling interval).
    """

    status: str
    motion_anomaly_score: float | None
    confidence: float
    motion_state: str
    features: MotionFeatures | None = None
    metadata: dict[str, float | str] = field(default_factory=dict)


class MotionAnomalyDetector:
    """
    Lightweight rule-anchored kinematic anomaly detector.

    Computes acceleration magnitude ||a||, dynamic acceleration (||a|| - g),
    and kinematic jerk ||da/dt|| across temporal observations.

    NOTE: The scoring formula uses sigmoid-bounded mapping over dynamic acceleration
    and jerk metrics. Parameters are provisional baseline defaults and will be replaced
    or calibrated once empirical crisis/fall benchmark datasets (e.g. MobiFall) are integrated.
    """

    def __init__(
        self,
        min_samples: int = 2,
        max_valid_accel_magnitude: float = 100.0,  # ~10g maximum plausible smartphone range
        dynamic_accel_scale: float = 5.0,
        jerk_scale: float = 20.0,
    ) -> None:
        if min_samples < 2:
            raise ValueError(
                "min_samples must be at least 2 to compute time differences."
            )
        if dynamic_accel_scale <= 0.0 or jerk_scale <= 0.0:
            raise ValueError("Scale parameters must be strictly positive.")

        self.min_samples = min_samples
        self.max_valid_accel_magnitude = max_valid_accel_magnitude
        self.dynamic_accel_scale = dynamic_accel_scale
        self.jerk_scale = jerk_scale

    def extract_features(self, samples: Sequence[MotionSample]) -> MotionFeatures:
        """Extract kinematic metrics from an ordered sequence of MotionSamples."""
        if len(samples) < self.min_samples:
            raise ValueError(
                f"At least {self.min_samples} samples required, got {len(samples)}"
            )

        # Sort chronologically to preserve physical derivative validity
        sorted_samples = sorted(samples, key=lambda s: s.timestamp)

        accel_mags: list[float] = []
        dyn_accels: list[float] = []
        gyro_mags: list[float] = []
        has_gyro = True

        for s in sorted_samples:
            mag = math.sqrt(s.accel_x**2 + s.accel_y**2 + s.accel_z**2)
            accel_mags.append(mag)
            # Dynamic acceleration magnitude: | ||a|| - g |
            dyn = abs(mag - STANDARD_GRAVITY_MPS2)
            dyn_accels.append(dyn)

            if s.gyro_x is not None and s.gyro_y is not None and s.gyro_z is not None:
                g_mag = math.sqrt(s.gyro_x**2 + s.gyro_y**2 + s.gyro_z**2)
                gyro_mags.append(g_mag)
            else:
                has_gyro = False

        # Compute jerk across consecutive observations
        jerks: list[float] = []
        for i in range(1, len(sorted_samples)):
            dt = (
                sorted_samples[i].timestamp - sorted_samples[i - 1].timestamp
            ).total_seconds()
            if dt < 0.0:
                raise ValueError("Timestamps must be non-decreasing after sorting.")
            if dt < MIN_DT_SECONDS:
                # Sub-millisecond or duplicate timestamp: skip rate computation
                # to prevent synthetic derivative explosion from clock discretization
                continue
            if dt > MAX_JERK_DT_SECONDS:
                # Sampling gap too wide for continuous instantaneous jerk derivative
                continue

            da_x = sorted_samples[i].accel_x - sorted_samples[i - 1].accel_x
            da_y = sorted_samples[i].accel_y - sorted_samples[i - 1].accel_y
            da_z = sorted_samples[i].accel_z - sorted_samples[i - 1].accel_z
            jerk_mag = math.sqrt(da_x**2 + da_y**2 + da_z**2) / dt
            jerks.append(jerk_mag)

        total_duration = (
            sorted_samples[-1].timestamp - sorted_samples[0].timestamp
        ).total_seconds()

        mean_accel = float(np.mean(accel_mags))
        std_accel = float(np.std(accel_mags))
        max_accel = float(np.max(accel_mags))
        mean_dyn = float(np.mean(dyn_accels))
        max_dyn = float(np.max(dyn_accels))
        mean_jerk = float(np.mean(jerks)) if jerks else 0.0
        max_jerk = float(np.max(jerks)) if jerks else 0.0

        mean_gyro = float(np.mean(gyro_mags)) if has_gyro and gyro_mags else None
        max_gyro = float(np.max(gyro_mags)) if has_gyro and gyro_mags else None

        return MotionFeatures(
            sample_count=len(samples),
            duration_seconds=max(total_duration, 0.0),
            mean_accel_magnitude=mean_accel,
            std_accel_magnitude=std_accel,
            max_accel_magnitude=max_accel,
            mean_dynamic_accel=mean_dyn,
            max_dynamic_accel=max_dyn,
            mean_jerk=mean_jerk,
            max_jerk=max_jerk,
            mean_gyro_magnitude=mean_gyro,
            max_gyro_magnitude=max_gyro,
        )

    def evaluate_window(
        self, samples: Sequence[MotionSample] | None
    ) -> MotionAnomalyResult:
        """
        Evaluate a window of motion samples.

        Returns a structured MotionAnomalyResult conforming to WEGOTCHU principles:
          - Missing/empty input produces status="INSUFFICIENT_DATA" with score=None.
          - Plausibility-violating readings produce status="INVALID_DATA" with score=None.
          - Valid windows produce a score in [0.0, 1.0] and an interpretable motion state.
        """
        if samples is None or len(samples) == 0:
            return MotionAnomalyResult(
                status="INSUFFICIENT_DATA",
                motion_anomaly_score=None,
                confidence=0.0,
                motion_state="unknown",
                metadata={"reason": "no_samples_provided"},
            )

        if len(samples) < self.min_samples:
            return MotionAnomalyResult(
                status="INSUFFICIENT_DATA",
                motion_anomaly_score=None,
                confidence=float(len(samples) / self.min_samples * 0.5),
                motion_state="unknown",
                metadata={
                    "reason": "insufficient_samples",
                    "provided_count": len(samples),
                    "required_count": self.min_samples,
                },
            )

        # Check for sensor-quality violations / saturation limits
        for s in samples:
            mag = math.sqrt(s.accel_x**2 + s.accel_y**2 + s.accel_z**2)
            if mag > self.max_valid_accel_magnitude:
                return MotionAnomalyResult(
                    status="INVALID_DATA",
                    motion_anomaly_score=None,
                    confidence=0.0,
                    motion_state="unknown",
                    metadata={
                        "reason": "sensor_saturation_or_quality_limit_exceeded",
                        "observed_magnitude": mag,
                        "max_allowed": self.max_valid_accel_magnitude,
                    },
                )

        try:
            feats = self.extract_features(samples)
        except Exception as err:
            return MotionAnomalyResult(
                status="INVALID_DATA",
                motion_anomaly_score=None,
                confidence=0.0,
                motion_state="unknown",
                metadata={"reason": "feature_extraction_failure", "error": str(err)},
            )

        if feats.duration_seconds <= 0.0:
            return MotionAnomalyResult(
                status="INVALID_DATA",
                motion_anomaly_score=None,
                confidence=0.0,
                motion_state="unknown",
                metadata={"reason": "zero_window_duration"},
            )

        # Classify qualitative motion state
        if feats.max_jerk >= ABRUPT_JERK_THRESHOLD or feats.max_dynamic_accel >= 8.0:
            motion_state = "abrupt_motion"
        elif feats.mean_dynamic_accel < STATIONARY_DYNAMIC_ACCEL_THRESHOLD:
            motion_state = "still"
        elif feats.mean_dynamic_accel < RUNNING_DYNAMIC_ACCEL_THRESHOLD:
            motion_state = "walking"
        else:
            motion_state = "running"

        # Bounded anomaly score in [0.0, 1.0]
        # Combines dynamic acceleration variance and sudden jerk intensity
        dyn_component = feats.max_dynamic_accel / self.dynamic_accel_scale
        jerk_component = feats.max_jerk / self.jerk_scale

        combined_raw = 0.5 * dyn_component + 0.5 * jerk_component
        # Hyperbolic tangent bounding ensures smooth asymptotic mapping to [0.0, 1.0]
        score = float(np.clip(math.tanh(combined_raw), 0.0, 1.0))

        # Confidence is higher with more observations across the window
        # Target density is 10+ samples per window
        confidence = float(np.clip(feats.sample_count / 10.0, 0.2, 1.0))

        return MotionAnomalyResult(
            status="SUCCESS",
            motion_anomaly_score=score,
            confidence=confidence,
            motion_state=motion_state,
            features=feats,
            metadata={
                "mean_dynamic_accel": feats.mean_dynamic_accel,
                "max_jerk": feats.max_jerk,
            },
        )
