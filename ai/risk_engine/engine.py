"""Deterministic safety risk estimation engine for WEGOTCHU."""

from __future__ import annotations

import math
from typing import Optional

from ai.anomaly_detection.motion import MotionAnomalyResult
from ai.risk_engine.models import (
    CalibrationMetadata,
    RecommendedAction,
    RiskAssessment,
    RiskLevel,
    RiskVector,
    TelemetrySummary,
)
from ai.route_deviation.scoring import RouteDeviationResult

# Signal identifier constants.
#
# Authoritative source: docs/architecture/ai-architecture.md §3 Validation Constraints (line 126):
#   signals: Array of validated signal identifiers
#   (e.g., "route_deviation", "unusual_motion", "acoustic_distress", ...)
#
# The Contract 4 illustrative JSON in docs/architecture/data-flow.md (line 139) shows
# "abnormal_motion", but that example also has risk_level:"HIGH" paired with
# recommended_action:"USER_CHECK" — a mutually inconsistent combination that confirms
# the JSON block is a draft illustration, not a normative definition.
# The normative validation text in ai-architecture.md §3 is authoritative.
# "unusual_motion" is therefore the required signal identifier for motion anomalies.
SIGNAL_ROUTE_DEVIATION: str = "route_deviation"
SIGNAL_UNUSUAL_MOTION: str = "unusual_motion"

# Provisional anomaly threshold definitions.
# These denote statistical departure from personal baseline, not confirmed danger.
ROUTE_ANOMALY_THRESHOLD: float = 0.50
MOTION_ANOMALY_THRESHOLD: float = 0.50


class RiskEngine:
    """
    Synthesizes incoming perception and anomaly signals into a structured RiskAssessment.

    Guiding Principles (from docs/safety/ai-safety-policy.md and docs/architecture/ai-architecture.md):

      1. Deterministic & Explainable: The mapping from signal inputs to risk levels is rule-anchored.
         No stochastic elements; identical inputs always produce identical outputs.

      2. Unavailable Scores are Never Coerced: A missing or invalid signal is represented as None
         in the risk_vector. It is NEVER substituted with 0.0, which would falsely imply a
         validated normal observation.

      3. Graduated Escalation (initial v0.1 policy):
         - Both validated signals within threshold -> NORMAL (NONE).
         - One validated signal anomalous -> UNUSUAL (MONITOR). Silent logging, no user interruption.
         - Both validated signals anomalous -> ELEVATED (USER_CHECK). Triggers discreet check-in.
         - HIGH / PRE_ALERT: requires unacknowledged ELEVATED check-in or multi-signal distress
           (e.g. acoustic); handled by the Deterministic Policy Engine, not this class.
         - EMERGENCY / DISPATCH_EMERGENCY: countdown expiry, manual SOS, or confirmed crisis;
           handled by the Deterministic Policy Engine, not this class.

      4. Partial Availability (one signal available, other unavailable/cold-start):
         - If the available validated signal is normal and the unavailable signal is
           cleanly missing or cold-start (INSUFFICIENT_HISTORY or INSUFFICIENT_DATA),
           the assessment is NORMAL with reduced confidence (0.65), reflecting genuine
           uncertainty from the missing modality.
         - If the available validated signal is anomalous, the assessment escalates to UNUSUAL
           (MONITOR) based on that single modality.
         - This is not the same as all-signals-missing, which is treated separately below.

      5. All Signals Missing: If both route and motion are unavailable (neither produced a
         validated score), the assessment is UNUSUAL (MONITOR) with very low confidence (0.20).
         This avoids the silent false assurance that absence of evidence is evidence of safety,
         while not triggering a user-visible check-in (consistent with Principle 4 of the policy:
         Active Mitigation of False Alarms).

      6. Detector Failure / Corrupted Input: If a detector reports a computational error,
         corrupted data, or failure (e.g. INVALID_DATA, COMPUTATION_ERROR), the engine NEVER
         converts the evaluation into a NORMAL assessment, even if the other signal is normal.
         It escalates conservatively to UNUSUAL (MONITOR) with degraded confidence (0.35)
         and preserves the explicit detector error status in telemetry_summary.
    """

    def __init__(
        self,
        route_threshold: float = ROUTE_ANOMALY_THRESHOLD,
        motion_threshold: float = MOTION_ANOMALY_THRESHOLD,
    ) -> None:
        if not (0.0 < route_threshold < 1.0):
            raise ValueError("route_threshold must be strictly within (0.0, 1.0)")
        if not (0.0 < motion_threshold < 1.0):
            raise ValueError("motion_threshold must be strictly within (0.0, 1.0)")

        self.route_threshold = route_threshold
        self.motion_threshold = motion_threshold

    def evaluate(
        self,
        user_id: str,
        route_result: Optional[RouteDeviationResult] = None,
        motion_result: Optional[MotionAnomalyResult] = None,
        speed_mps: Optional[float] = None,
    ) -> RiskAssessment:
        """
        Evaluate route-deviation and motion-anomaly signals.

        Args:
            user_id: Identifier of the user under evaluation.
            route_result: RouteDeviationResult from ai/route_deviation/scoring.py (or None).
            motion_result: MotionAnomalyResult from ai/anomaly_detection/motion.py (or None).
            speed_mps: Optional current speed in m/s for telemetry summary.

        Returns:
            RiskAssessment complying with Contract 4 (Version 0.1).
        """
        if not user_id:
            raise ValueError("user_id must be a non-empty string.")

        # Extract normalized scores; None indicates missing/cold-start signal
        route_score = (
            route_result.route_deviation_score
            if route_result and route_result.status == "SUCCESS"
            else None
        )
        motion_score = (
            motion_result.motion_anomaly_score
            if motion_result and motion_result.status == "SUCCESS"
            else None
        )

        # Validate that extracted scores are finite numbers in [0.0, 1.0]
        route_invalid = False
        if route_score is not None:
            if (
                not isinstance(route_score, (int, float))
                or isinstance(route_score, bool)
                or not math.isfinite(route_score)
                or not (0.0 <= float(route_score) <= 1.0)
            ):
                route_score = None
                route_invalid = True
            else:
                route_score = float(route_score)

        motion_invalid = False
        if motion_score is not None:
            if (
                not isinstance(motion_score, (int, float))
                or isinstance(motion_score, bool)
                or not math.isfinite(motion_score)
                or not (0.0 <= float(motion_score) <= 1.0)
            ):
                motion_score = None
                motion_invalid = True
            else:
                motion_score = float(motion_score)

        # Sanitize speed_mps
        if speed_mps is not None and (
            not isinstance(speed_mps, (int, float))
            or isinstance(speed_mps, bool)
            or not math.isfinite(speed_mps)
            or speed_mps < 0.0
        ):
            speed_mps = None

        # Determine active validated signals
        active_signals: list[str] = []
        is_route_anomalous = False
        is_motion_anomalous = False

        if route_score is not None and route_score >= self.route_threshold:
            active_signals.append(SIGNAL_ROUTE_DEVIATION)
            is_route_anomalous = True

        if motion_score is not None and motion_score >= self.motion_threshold:
            active_signals.append(SIGNAL_UNUSUAL_MOTION)
            is_motion_anomalous = True

        # Formulate RiskVector
        risk_vector = RiskVector(
            kinematic_anomaly=motion_score,
            route_anomaly=route_score,
            acoustic_anomaly=None,
            temporal_persistence=None,
        )

        # Formulate TelemetrySummary
        if route_result and route_result.status in ("SUCCESS", "INSUFFICIENT_HISTORY"):
            location_status = "available"
        else:
            location_status = "unavailable"

        corridor_dev_meters = (
            route_result.raw_distance_meters
            if route_result and route_result.status == "SUCCESS"
            else None
        )
        motion_state = motion_result.motion_state if motion_result else "unknown"

        telemetry_summary = TelemetrySummary(
            speed_mps=speed_mps,
            corridor_deviation_meters=corridor_dev_meters,
            motion_state=motion_state,
            acoustic_anomaly_score=None,
            motion_status=(
                motion_result.status if motion_result is not None else "UNAVAILABLE"
            ),
            route_status=(
                route_result.status if route_result is not None else "UNAVAILABLE"
            ),
        )

        # Deterministic Risk & Action Policy Logic
        has_route = route_score is not None
        has_motion = motion_score is not None

        # Check for detector failures or corrupted inputs
        route_failure = (
            route_invalid
            or (
                route_result is not None
                and route_result.status in ("COMPUTATION_ERROR", "INVALID_INPUT", "ERROR", "FAILED")
            )
        )
        motion_failure = (
            motion_invalid
            or (
                motion_result is not None
                and motion_result.status in ("INVALID_DATA", "ERROR", "FAILED")
            )
        )
        has_detector_failure = route_failure or motion_failure

        if not has_route and not has_motion:
            # Both signals are missing or insufficient (e.g. cold start + no sensors).
            # Safety Principle: Never assume unmonitored user is NORMAL (safe).
            # Escalate conservatively to UNUSUAL with MONITOR to reflect telemetry deficit.
            # Do NOT infer safety solely from missing data, nor invent numerical scores.
            risk_level = RiskLevel.UNUSUAL
            action = RecommendedAction.MONITOR
            confidence = 0.20  # Low confidence reflecting telemetry deficit
            raw_score: float | None = None
            calibrated_score: float | None = None

        elif is_route_anomalous and is_motion_anomalous:
            # Co-occurring anomalies: simultaneous route deviation and unusual motion.
            # Escalate to ELEVATED and trigger gentle haptic user check-in.
            # IMPORTANT: Statistical anomaly scores alone NEVER trigger HIGH or EMERGENCY.
            risk_level = RiskLevel.ELEVATED
            action = RecommendedAction.USER_CHECK
            # Route deviation has no detector-level confidence field; assume a nominal
            # baseline weight of 0.85 when a validated route anomaly is observed.
            # Incorporate motion detector confidence explicitly rather than clamping
            # with an artificial 0.70 floor.
            if motion_result is None or motion_result.confidence is None:
                motion_conf = 0.80
            elif not math.isfinite(motion_result.confidence):
                motion_conf = 0.0
            else:
                motion_conf = float(max(0.0, min(1.0, motion_result.confidence)))

            confidence = float(min(0.95, max(0.0, (0.85 + motion_conf) / 2.0)))
            raw_score = (route_score + motion_score) / 2.0
            calibrated_score = float(min(1.0, raw_score + 0.15))

        elif is_route_anomalous or is_motion_anomalous:
            # Single anomaly divergence: unfamiliar street OR unusual motion spike.
            # Escalate to UNUSUAL with MONITOR (increase polling rate / silent logging).
            risk_level = RiskLevel.UNUSUAL
            action = RecommendedAction.MONITOR
            active_score = route_score if is_route_anomalous else motion_score
            if is_motion_anomalous and not is_route_anomalous:
                # When motion is the anomalous modality, scale confidence with motion detector confidence
                if motion_result is None or motion_result.confidence is None:
                    motion_conf = 0.75
                elif not math.isfinite(motion_result.confidence):
                    motion_conf = 0.0
                else:
                    motion_conf = float(max(0.0, min(1.0, motion_result.confidence)))

                confidence = float(min(0.90, max(0.0, motion_conf)))
            else:
                # Route anomaly is active (either motion is normal or motion is unavailable).
                # Route deviation does not provide a detector-level confidence; assign nominal 0.75.
                confidence = 0.75
            raw_score = active_score
            calibrated_score = active_score

        elif has_detector_failure:
            # A detector reported a computational error, corrupted input, or crash.
            # Safety Principle: Never manufacture a NORMAL assessment when a detector failed.
            # Escalate conservatively to UNUSUAL with MONITOR and degraded confidence.
            risk_level = RiskLevel.UNUSUAL
            action = RecommendedAction.MONITOR
            confidence = 0.35  # Degraded confidence reflecting detector failure
            available_scores = [s for s in (route_score, motion_score) if s is not None]
            raw_score = float(max(available_scores)) if available_scores else None
            calibrated_score = raw_score

        else:
            # At least one signal observed, no detector failure, and neither exceeded threshold.
            risk_level = RiskLevel.NORMAL
            action = RecommendedAction.NONE
            # High confidence when both modalities observed normal; reduced when partial
            confidence = 0.88 if (has_route and has_motion) else 0.65
            available_scores = [s for s in (route_score, motion_score) if s is not None]
            raw_score = float(max(available_scores)) if available_scores else None
            calibrated_score = raw_score

        calibration_metadata = CalibrationMetadata(
            method="deterministic_heuristic",
            raw_score=round(raw_score, 4) if raw_score is not None else None,
            calibrated_score=(
                round(calibrated_score, 4) if calibrated_score is not None else None
            ),
        )

        return RiskAssessment(
            user_id=user_id,
            risk_level=risk_level,
            confidence=confidence,
            signals=tuple(active_signals),
            location_status=location_status,
            recommended_action=action,
            risk_vector=risk_vector,
            telemetry_summary=telemetry_summary,
            calibration_metadata=calibration_metadata,
        )
