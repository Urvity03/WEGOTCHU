"""
Risk Evaluation Service for WEGOTCHU.

Coordinates:
  1. Telemetry adaptation via Telemetry Adapter (motion samples and candidate trajectory).
  2. Kinematic motion anomaly detection via MotionAnomalyDetector.
  3. Personalized route-deviation evaluation via build_reference_set and score_route_deviation.
  4. Structured risk assessment synthesis via RiskEngine complying with Contract 4.

Guiding Principles:
  - Pure orchestration: does not perform direct database queries or HTTP handling.
  - Fail-safe semantics: missing or invalid signals remain None in the RiskVector;
    they are NEVER substituted with 0.0 or converted into a fabricated NORMAL assessment.
  - Strict privacy: pseudonymous user identifiers are required; raw device IDs cannot be used.
  - Cold-start preservation: INSUFFICIENT_HISTORY is explicitly preserved without global fallbacks.
"""

from __future__ import annotations

import math
from typing import Any, Sequence

from ai.anomaly_detection.motion import MotionAnomalyDetector, MotionAnomalyResult
from ai.risk_engine.engine import RiskEngine
from ai.risk_engine.models import RiskAssessment
from ai.route_deviation.loader import Trajectory
from ai.route_deviation.reference import (
    MIN_HISTORICAL_TRAJECTORIES,
    build_reference_set,
)
from ai.route_deviation.scoring import RouteDeviationResult, score_route_deviation
from backend.app.services.telemetry_adapter import (
    _get_val,
    records_to_candidate_trajectory,
    records_to_motion_samples,
)


class RiskServiceError(Exception):
    """Base exception for RiskService failures."""


class RiskService:
    """
    Coordinates telemetry adaptation, anomaly detection, and risk evaluation.

    Encapsulates the full pipeline from raw telemetry observations to a Contract 4
    RiskAssessment, enforcing same-user history, strict chronological precedence,
    and fail-safe handling of missing or corrupted data.
    """

    def __init__(
        self,
        motion_detector: MotionAnomalyDetector | None = None,
        risk_engine: RiskEngine | None = None,
        min_historical_trajectories: int = MIN_HISTORICAL_TRAJECTORIES,
        raise_on_detector_error: bool = False,
        enforce_pseudonymous_id: bool = True,
    ) -> None:
        """
        Initialize RiskService.

        Args:
            motion_detector: Optional configured MotionAnomalyDetector instance.
            risk_engine: Optional configured RiskEngine instance.
            min_historical_trajectories: Minimum historical trajectories required for
                route deviation (default: 5).
            raise_on_detector_error: If True, raises RiskServiceError when an unexpected
                detector exception occurs. If False, records the failure as an invalid/error
                detector status so RiskEngine can conservatively assess risk without crashing.
            enforce_pseudonymous_id: If True, verifies user_id does not equal raw device_id
                found in the telemetry records.
        """
        self.motion_detector = motion_detector or MotionAnomalyDetector()
        self.risk_engine = risk_engine or RiskEngine()
        self.min_historical_trajectories = min_historical_trajectories
        self.raise_on_detector_error = raise_on_detector_error
        self.enforce_pseudonymous_id = enforce_pseudonymous_id

    def evaluate_telemetry(
        self,
        user_id: str,
        records: Sequence[Any],
        trajectory_id: str | None = None,
        historical_trajectories: Sequence[Trajectory] | None = None,
    ) -> RiskAssessment:
        """
        Evaluate a sequence of telemetry records and produce a structured RiskAssessment.

        Pipeline Stages:
          1. Validation: Verifies user_id is non-empty and does not leak raw device_id.
          2. Motion Adaptation & Evaluation:
             - Converts records to chronologically ordered, deduplicated MotionSamples.
             - Evaluates motion window using MotionAnomalyDetector.
             - If samples are fewer than min_samples, returns INSUFFICIENT_DATA with score=None.
          3. Route Adaptation & Evaluation:
             - If trajectory_id is provided, converts records to candidate Trajectory.
             - If candidate trajectory has >= 2 valid points, builds reference set from
               historical_trajectories enforcing same-user and strict chronological precedence.
             - Scores route deviation against the reference set.
             - If fewer than min_history eligible trajectories exist, status is
               INSUFFICIENT_HISTORY with score=None (location_status remains "available").
             - If trajectory_id is None or < 2 valid points exist, route_result is None
               (location_status becomes "unavailable").
          4. Risk Synthesis:
             - Invokes RiskEngine.evaluate() to compute final risk_level, confidence,
               recommended_action, and telemetry summary.

        Args:
            user_id: Stable pseudonymous identifier of the user.
            records: Sequence of TelemetryRecord objects or compatible mappings.
            trajectory_id: Explicit trajectory identifier for the candidate trip segment.
                If None, route deviation is omitted (e.g. stationary / motion-only window).
            historical_trajectories: Optional pool of historical Trajectory objects belonging
                to the user. If None or insufficient, INSUFFICIENT_HISTORY is reported.

        Returns:
            RiskAssessment conforming to Contract 4 (Version 0.1).

        Raises:
            TypeError: If user_id is not a string.
            ValueError: If user_id is empty, whitespace-only, or equals a raw device_id.
            RiskServiceError: If raise_on_detector_error is True and a detector crashes.
        """
        # --- Stage 1: User Identity & Privacy Validation ---
        if not isinstance(user_id, str):
            raise TypeError(f"user_id must be a string, got {type(user_id).__name__}")
        if not user_id.strip():
            raise ValueError("user_id cannot be empty or whitespace-only")

        if self.enforce_pseudonymous_id and records:
            for rec in records:
                dev_id = _get_val(rec, "device_id")
                if dev_id and dev_id == user_id:
                    raise ValueError(
                        "Raw device identifier cannot be used as user_id. "
                        "Use pseudonymize_identifier() to derive a stable pseudonymous user_id."
                    )

        # --- Stage 2: Motion Telemetry Evaluation ---
        motion_samples = records_to_motion_samples(records, deduplicate_timestamps=True)
        motion_result: MotionAnomalyResult | None = None

        try:
            motion_result = self.motion_detector.evaluate_window(motion_samples)
        except Exception as err:
            if self.raise_on_detector_error:
                raise RiskServiceError(
                    f"Motion anomaly evaluation failed: {err}"
                ) from err
            motion_result = MotionAnomalyResult(
                status="INVALID_DATA",
                motion_anomaly_score=None,
                confidence=0.0,
                motion_state="unknown",
                metadata={"reason": "detector_exception", "error": str(err)},
            )

        # --- Stage 3: Speed Extraction ---
        speed_mps: float | None = None
        for s in reversed(motion_samples):
            if s.speed_mps is not None:
                speed_mps = s.speed_mps
                break

        if speed_mps is None and records:
            for r in reversed(records):
                raw_sp = _get_val(r, "speed_mps")
                if (
                    raw_sp is not None
                    and isinstance(raw_sp, (int, float))
                    and not isinstance(raw_sp, bool)
                    and math.isfinite(raw_sp)
                    and raw_sp >= 0.0
                ):
                    speed_mps = float(raw_sp)
                    break

        # --- Stage 4: Route Deviation Evaluation ---
        route_result: RouteDeviationResult | None = None

        if trajectory_id is not None:
            candidate_traj = records_to_candidate_trajectory(
                records=records,
                user_id=user_id,
                trajectory_id=trajectory_id,
            )

            if candidate_traj is not None:
                try:
                    ref_set = build_reference_set(
                        trajectories=historical_trajectories or [],
                        candidate_trajectory=candidate_traj,
                        min_history=self.min_historical_trajectories,
                    )
                    route_result = score_route_deviation(
                        candidate_trajectory=candidate_traj,
                        reference_set=ref_set,
                    )
                except Exception as err:
                    if self.raise_on_detector_error:
                        raise RiskServiceError(
                            f"Route deviation evaluation failed: {err}"
                        ) from err
                    route_result = RouteDeviationResult(
                        user_id=user_id,
                        trajectory_id=candidate_traj.trajectory_id,
                        status="COMPUTATION_ERROR",
                        raw_distance_meters=None,
                        route_deviation_score=None,
                        reference_trajectory_count=len(historical_trajectories or []),
                        closest_reference_id=None,
                    )

        # --- Stage 5: Structured Risk Synthesis ---
        return self.risk_engine.evaluate(
            user_id=user_id,
            route_result=route_result,
            motion_result=motion_result,
            speed_mps=speed_mps,
        )
