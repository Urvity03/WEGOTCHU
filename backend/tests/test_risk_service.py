"""
Unit tests for the RiskService coordinating adapter, motion detector, route deviation baseline, and risk engine.

Covers all 10 required verification areas:
1. Valid motion and route results (normal, anomalous, and co-occurring).
2. Insufficient motion samples (< min_samples produces INSUFFICIENT_DATA and None score).
3. Insufficient route history (< 5 historical trajectories produces INSUFFICIENT_HISTORY and None score).
4. Missing optional gyroscope values (nullable gyroscope handled cleanly).
5. Missing or invalid timestamps (invalid/naive filtered out; total deficit yields UNUSUAL / MONITOR, never NORMAL).
6. No eligible historical trajectories (empty or None historical trajectories handled safely).
7. Detector exceptions and failure propagation/handling (raise_on_detector_error True/False).
8. Ensuring raw device identifiers are not used as user identities.
9. Preserving risk-engine output and confidence semantics (Contract 4 conformance).
10. Preventing future or other-user trajectories from being used (strict user and temporal isolation).
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import os
from typing import Any
from unittest.mock import MagicMock

import pytest

# Ensure DATABASE_URL is set before importing backend models
os.environ.setdefault("DATABASE_URL", "sqlite://")

from ai.anomaly_detection.motion import MotionAnomalyDetector  # noqa: E402
from ai.risk_engine.models import RecommendedAction, RiskLevel  # noqa: E402
from ai.route_deviation.loader import Trajectory, TrajectoryPoint  # noqa: E402
from backend.app.models.telemetry_record import TelemetryRecord  # noqa: E402
from backend.app.services.risk_service import (  # noqa: E402
    RiskService,
    RiskServiceError,
)
from backend.app.services.telemetry_adapter import pseudonymize_identifier  # noqa: E402

# ---------------------------------------------------------------------------
# Test Fixtures & Helpers
# ---------------------------------------------------------------------------

SECRET_KEY = "test-secret-key-for-pseudonymization"
BASE_TIME = datetime(2026, 10, 19, 12, 0, 0, tzinfo=timezone.utc)
TEST_DEVICE_ID = "dev_sensor_alpha"
TEST_USER_ID = pseudonymize_identifier(TEST_DEVICE_ID, SECRET_KEY)
_SENTINEL = object()


def _make_record(
    timestamp: Any = _SENTINEL,
    accel_x: float = 0.05,
    accel_y: float = 9.81,
    accel_z: float = 0.12,
    gyro_x: float | None = 0.01,
    gyro_y: float | None = -0.02,
    gyro_z: float | None = 0.03,
    speed_mps: float | None = 1.35,
    latitude: float = 28.6139,
    longitude: float = 77.2090,
    device_id: str = TEST_DEVICE_ID,
    rec_id: int | None = 1,
) -> TelemetryRecord:
    """Helper to construct a deterministic TelemetryRecord instance."""
    ts = BASE_TIME if timestamp is _SENTINEL else timestamp
    return TelemetryRecord(
        id=rec_id,
        version="0.1",
        device_id=device_id,
        timestamp=ts,
        latitude=latitude,
        longitude=longitude,
        altitude_meters=15.0,
        accuracy_meters=4.2,
        speed_mps=speed_mps,
        bearing_degrees=180.0,
        accelerometer_x=accel_x,
        accelerometer_y=accel_y,
        accelerometer_z=accel_z,
        gyroscope_x=gyro_x,
        gyroscope_y=gyro_y,
        gyroscope_z=gyro_z,
        battery_level=0.88,
        network_status="WIFI",
    )


def _make_trajectory(
    user_id: str,
    trajectory_id: str,
    start_time: datetime,
    point_count: int = 10,
    lat_offset: float = 0.0,
    lon_offset: float = 0.0,
) -> Trajectory:
    """Helper to create a deterministic Trajectory instance."""
    points: list[TrajectoryPoint] = []
    for i in range(point_count):
        pt_time = start_time + timedelta(seconds=i * 5)
        # Small linear displacement along a path
        lat = 28.6139 + lat_offset + (i * 0.0001)
        lon = 77.2090 + lon_offset + (i * 0.0001)
        points.append(TrajectoryPoint(latitude=lat, longitude=lon, timestamp=pt_time))
    return Trajectory(
        user_id=user_id, trajectory_id=trajectory_id, points=tuple(points)
    )


def _make_five_historical_trajectories(
    user_id: str,
    preceding_time: datetime,
    point_count: int = 10,
) -> list[Trajectory]:
    """Helper to create 5 eligible historical trajectories strictly preceding candidate time."""
    offsets = [-0.0005, -0.0002, 0.0, 0.0002, 0.0005]
    trajectories: list[Trajectory] = []
    for idx, off in enumerate(offsets):
        # Starts 12 to 2 hours before preceding_time
        t_start = preceding_time - timedelta(hours=12 - (idx * 2))
        traj = _make_trajectory(
            user_id=user_id,
            trajectory_id=f"hist_{idx + 1}",
            start_time=t_start,
            point_count=point_count,
            lat_offset=off,
            lon_offset=off,
        )
        trajectories.append(traj)
    return trajectories


# ---------------------------------------------------------------------------
# 1. Valid Motion and Route Results Tests
# ---------------------------------------------------------------------------


def test_valid_normal_motion_and_route_results():
    """Area 1: Valid normal motion and route deviation signals yield NORMAL risk and NONE action."""
    service = RiskService()
    t0 = BASE_TIME
    records = [
        _make_record(
            timestamp=t0 + timedelta(milliseconds=i * 20),
            accel_x=0.01,
            accel_y=9.81,
            accel_z=0.02,
            latitude=28.6139 + (i * 0.0001),
            longitude=77.2090 + (i * 0.0001),
            rec_id=i,
        )
        for i in range(10)
    ]

    hist_trajs = _make_five_historical_trajectories(
        user_id=TEST_USER_ID, preceding_time=t0
    )

    assessment = service.evaluate_telemetry(
        user_id=TEST_USER_ID,
        records=records,
        trajectory_id="candidate_trip_01",
        historical_trajectories=hist_trajs,
    )

    assert assessment.user_id == TEST_USER_ID
    assert assessment.risk_level == RiskLevel.NORMAL
    assert assessment.recommended_action == RecommendedAction.NONE
    assert assessment.confidence >= 0.85
    assert assessment.location_status == "available"
    assert assessment.risk_vector.kinematic_anomaly is not None
    assert assessment.risk_vector.route_anomaly is not None
    assert assessment.signals == ()


def test_valid_co_occurring_anomalies_yield_elevated():
    """Area 1: Co-occurring route deviation and motion anomalies yield ELEVATED risk and USER_CHECK."""
    service = RiskService()
    t0 = BASE_TIME

    # Motion with abrupt motion/jerk (high acceleration spike)
    records = [
        _make_record(
            timestamp=t0 + timedelta(milliseconds=0),
            accel_x=0.0,
            accel_y=9.81,
            accel_z=0.0,
            latitude=28.6139,
            longitude=77.2090,
            rec_id=1,
        ),
        _make_record(
            timestamp=t0 + timedelta(milliseconds=20),
            accel_x=30.0,
            accel_y=35.0,
            accel_z=20.0,  # Sudden high jerk spike
            latitude=28.8000,
            longitude=77.5000,  # Significant spatial deviation (~25km away)
            rec_id=2,
        ),
    ]

    # Historical trajectories centered near (28.6139, 77.2090)
    hist_trajs = _make_five_historical_trajectories(
        user_id=TEST_USER_ID, preceding_time=t0
    )

    assessment = service.evaluate_telemetry(
        user_id=TEST_USER_ID,
        records=records,
        trajectory_id="candidate_deviated_trip",
        historical_trajectories=hist_trajs,
    )

    assert assessment.risk_level == RiskLevel.ELEVATED
    assert assessment.recommended_action == RecommendedAction.USER_CHECK
    assert "route_deviation" in assessment.signals
    assert "unusual_motion" in assessment.signals
    assert assessment.risk_vector.kinematic_anomaly is not None
    assert assessment.risk_vector.route_anomaly is not None


# ---------------------------------------------------------------------------
# 2. Insufficient Motion Samples Tests
# ---------------------------------------------------------------------------


def test_insufficient_motion_samples():
    """Area 2: Fewer than min_samples motion samples produces INSUFFICIENT_DATA and None score."""
    service = RiskService()
    t0 = BASE_TIME
    # Only 1 record provided (min_samples is 2)
    single_rec = _make_record(timestamp=t0, rec_id=1)

    hist_trajs = _make_five_historical_trajectories(
        user_id=TEST_USER_ID, preceding_time=t0
    )

    assessment = service.evaluate_telemetry(
        user_id=TEST_USER_ID,
        records=[single_rec],
        trajectory_id="trip_short",
        historical_trajectories=hist_trajs,
    )

    # Motion is insufficient -> None in risk_vector; route is also None (only 1 point cannot form Trajectory)
    assert assessment.risk_vector.kinematic_anomaly is None
    assert assessment.risk_vector.route_anomaly is None
    # All signals missing -> UNUSUAL / MONITOR with low confidence
    assert assessment.risk_level == RiskLevel.UNUSUAL
    assert assessment.recommended_action == RecommendedAction.MONITOR
    assert assessment.confidence <= 0.30


def test_insufficient_motion_with_valid_normal_route():
    """Area 2: Insufficient motion with valid normal route produces NORMAL with reduced confidence (0.65)."""
    # Create a detector requiring 10 samples
    detector = MotionAnomalyDetector(min_samples=10)
    service = RiskService(motion_detector=detector)
    t0 = BASE_TIME

    # 3 records: enough for Trajectory (>= 2), but not enough for motion detector (3 < 10)
    records = [
        _make_record(
            timestamp=t0 + timedelta(milliseconds=i * 20),
            latitude=28.6139 + (i * 0.0001),
            longitude=77.2090 + (i * 0.0001),
            rec_id=i,
        )
        for i in range(3)
    ]
    hist_trajs = _make_five_historical_trajectories(
        user_id=TEST_USER_ID, preceding_time=t0, point_count=3
    )

    assessment = service.evaluate_telemetry(
        user_id=TEST_USER_ID,
        records=records,
        trajectory_id="trip_normal_route",
        historical_trajectories=hist_trajs,
    )

    # Motion score is None, route score is validated normal
    assert assessment.risk_vector.kinematic_anomaly is None
    assert assessment.risk_vector.route_anomaly is not None
    # Partial availability with normal route -> NORMAL with confidence 0.65
    assert assessment.risk_level == RiskLevel.NORMAL
    assert assessment.confidence == 0.65
    assert assessment.location_status == "available"


# ---------------------------------------------------------------------------
# 3. Insufficient Route History Tests
# ---------------------------------------------------------------------------


def test_insufficient_route_history_preserves_cold_start():
    """Area 3: Fewer than 5 historical trajectories preserves INSUFFICIENT_HISTORY and None score."""
    service = RiskService()
    t0 = BASE_TIME
    records = [
        _make_record(
            timestamp=t0 + timedelta(milliseconds=i * 20),
            latitude=28.6139 + (i * 0.0001),
            longitude=77.2090 + (i * 0.0001),
            rec_id=i,
        )
        for i in range(5)
    ]

    # Only 2 historical trajectories provided (< 5 required)
    hist_trajs = _make_five_historical_trajectories(
        user_id=TEST_USER_ID, preceding_time=t0
    )[:2]

    assessment = service.evaluate_telemetry(
        user_id=TEST_USER_ID,
        records=records,
        trajectory_id="candidate_cold_start",
        historical_trajectories=hist_trajs,
    )

    assert assessment.location_status == "available"
    assert assessment.risk_vector.route_anomaly is None
    assert assessment.risk_vector.kinematic_anomaly is not None
    # Normal motion with route cold start yields NORMAL with confidence 0.65
    assert assessment.risk_level == RiskLevel.NORMAL
    assert assessment.confidence == 0.65


# ---------------------------------------------------------------------------
# 4. Missing Optional Gyroscope Values Tests
# ---------------------------------------------------------------------------


def test_missing_optional_gyroscope_values():
    """Area 4: Missing optional gyroscope values do not cause errors or fabricate values."""
    service = RiskService()
    t0 = BASE_TIME
    records = [
        _make_record(
            timestamp=t0 + timedelta(milliseconds=i * 20),
            gyro_x=None,
            gyro_y=None,
            gyro_z=None,
            rec_id=i,
        )
        for i in range(5)
    ]

    assessment = service.evaluate_telemetry(
        user_id=TEST_USER_ID,
        records=records,
        trajectory_id=None,  # No route evaluation requested
    )

    # Evaluates motion successfully without gyroscope
    assert assessment.risk_vector.kinematic_anomaly is not None
    assert assessment.location_status == "unavailable"


# ---------------------------------------------------------------------------
# 5. Missing or Invalid Timestamps Tests
# ---------------------------------------------------------------------------


def test_missing_or_invalid_timestamps_excluded():
    """Area 5: Records with missing/naive/corrupted timestamps are safely filtered out."""
    service = RiskService()
    t0 = BASE_TIME
    valid_rec = _make_record(timestamp=t0, rec_id=1)
    rec_naive = _make_record(
        timestamp=datetime(2026, 10, 19, 12, 0, 0), rec_id=2
    )  # naive
    rec_none_ts = _make_record(timestamp=None, rec_id=3)
    rec_bad_ts = {
        "timestamp": "not-a-valid-date",
        "accelerometer_x": 0.0,
        "accelerometer_y": 9.8,
        "accelerometer_z": 0.0,
    }

    # Only 1 valid record survives adapter filtering -> insufficient data
    assessment = service.evaluate_telemetry(
        user_id=TEST_USER_ID,
        records=[valid_rec, rec_naive, rec_none_ts, rec_bad_ts],
        trajectory_id="trip_bad_timestamps",
    )

    # 1 valid sample < 2 min_samples -> INSUFFICIENT_DATA
    # 1 valid point < 2 min_points -> No candidate trajectory formed
    assert assessment.risk_vector.kinematic_anomaly is None
    assert assessment.risk_vector.route_anomaly is None
    assert assessment.location_status == "unavailable"
    # Never fabricates NORMAL on data deficit
    assert assessment.risk_level == RiskLevel.UNUSUAL
    assert assessment.recommended_action == RecommendedAction.MONITOR


# ---------------------------------------------------------------------------
# 6. No Eligible Historical Trajectories Tests
# ---------------------------------------------------------------------------


def test_no_eligible_historical_trajectories():
    """Area 6: Empty or None historical trajectories list produces INSUFFICIENT_HISTORY."""
    service = RiskService()
    t0 = BASE_TIME
    records = [
        _make_record(
            timestamp=t0 + timedelta(milliseconds=i * 20),
            latitude=28.6139 + (i * 0.0001),
            longitude=77.2090 + (i * 0.0001),
            rec_id=i,
        )
        for i in range(5)
    ]

    # Explicitly None historical trajectories
    assessment = service.evaluate_telemetry(
        user_id=TEST_USER_ID,
        records=records,
        trajectory_id="candidate_no_history",
        historical_trajectories=None,
    )

    assert assessment.location_status == "available"
    assert assessment.risk_vector.route_anomaly is None


# ---------------------------------------------------------------------------
# 7. Detector Exceptions and Failure Handling Tests
# ---------------------------------------------------------------------------


def test_detector_exception_handled_without_manufacturing_normal():
    """Area 7: When raise_on_detector_error=False, detector exception is caught and marked INVALID_DATA,
    never manufacturing a NORMAL assessment."""
    mock_detector = MagicMock(spec=MotionAnomalyDetector)
    mock_detector.min_samples = 2
    mock_detector.evaluate_window.side_effect = RuntimeError(
        "Simulated inference engine crash"
    )

    service = RiskService(motion_detector=mock_detector, raise_on_detector_error=False)
    t0 = BASE_TIME
    records = [
        _make_record(timestamp=t0 + timedelta(milliseconds=i * 20), rec_id=i)
        for i in range(5)
    ]

    assessment = service.evaluate_telemetry(
        user_id=TEST_USER_ID,
        records=records,
        trajectory_id=None,
    )

    # Failure was caught, score is None, evaluation is UNUSUAL/MONITOR, NEVER NORMAL
    assert assessment.risk_vector.kinematic_anomaly is None
    assert assessment.risk_level == RiskLevel.UNUSUAL
    assert assessment.recommended_action == RecommendedAction.MONITOR


def test_detector_exception_propagates_when_configured():
    """Area 7: When raise_on_detector_error=True, detector exception is raised as RiskServiceError."""
    mock_detector = MagicMock(spec=MotionAnomalyDetector)
    mock_detector.min_samples = 2
    mock_detector.evaluate_window.side_effect = RuntimeError("Inference kernel fault")

    service = RiskService(motion_detector=mock_detector, raise_on_detector_error=True)
    t0 = BASE_TIME
    records = [
        _make_record(timestamp=t0 + timedelta(milliseconds=i * 20), rec_id=i)
        for i in range(5)
    ]

    with pytest.raises(RiskServiceError, match="Motion anomaly evaluation failed"):
        service.evaluate_telemetry(
            user_id=TEST_USER_ID,
            records=records,
            trajectory_id=None,
        )


# ---------------------------------------------------------------------------
# 8. Raw Device Identifier Privacy Tests
# ---------------------------------------------------------------------------


def test_raw_device_id_rejected_as_user_identity():
    """Area 8: Supplying the raw device identifier as user_id is explicitly rejected."""
    service = RiskService(enforce_pseudonymous_id=True)
    t0 = BASE_TIME
    rec = _make_record(timestamp=t0, device_id="raw_device_xyz_123")

    # Calling with user_id matching raw device_id must be rejected
    with pytest.raises(
        ValueError, match="Raw device identifier cannot be used as user_id"
    ):
        service.evaluate_telemetry(
            user_id="raw_device_xyz_123",
            records=[rec],
        )


def test_pseudonymous_user_id_preserved_and_device_id_not_leaked():
    """Area 8: A properly pseudonymized user_id is preserved on the assessment and trajectory."""
    service = RiskService()
    t0 = BASE_TIME
    raw_device = "dev_sensor_secure_99"
    pseudo_user = pseudonymize_identifier(raw_device, SECRET_KEY)

    records = [
        _make_record(
            timestamp=t0 + timedelta(milliseconds=i * 20),
            device_id=raw_device,
            latitude=28.6139 + (i * 0.0001),
            longitude=77.2090 + (i * 0.0001),
            rec_id=i,
        )
        for i in range(5)
    ]
    hist_trajs = _make_five_historical_trajectories(
        user_id=pseudo_user, preceding_time=t0
    )

    assessment = service.evaluate_telemetry(
        user_id=pseudo_user,
        records=records,
        trajectory_id="trip_secure",
        historical_trajectories=hist_trajs,
    )

    # Assessment user_id is the pseudonym, raw device_id is never used as identity
    assert assessment.user_id == pseudo_user
    assert raw_device not in assessment.user_id


# ---------------------------------------------------------------------------
# 9. Risk-Engine Output and Confidence Semantics Tests
# ---------------------------------------------------------------------------


def test_contract4_structure_and_confidence_semantics():
    """Area 9: Verifies full Contract 4 compliance and accurate confidence bounds."""
    service = RiskService()
    t0 = BASE_TIME
    records = [
        _make_record(
            timestamp=t0 + timedelta(milliseconds=i * 20),
            speed_mps=3.25,
            rec_id=i,
        )
        for i in range(5)
    ]

    assessment = service.evaluate_telemetry(
        user_id=TEST_USER_ID,
        records=records,
        trajectory_id=None,
    )

    # Check Contract 4 required top-level attributes
    assert isinstance(assessment.user_id, str)
    assert isinstance(assessment.risk_level, RiskLevel)
    assert isinstance(assessment.confidence, float)
    assert 0.0 <= assessment.confidence <= 1.0
    assert isinstance(assessment.signals, tuple)
    assert assessment.location_status in ("available", "unavailable")
    assert isinstance(assessment.recommended_action, RecommendedAction)
    assert assessment.risk_vector is not None
    assert assessment.telemetry_summary is not None
    assert assessment.calibration_metadata is not None
    assert assessment.version == "0.1"
    assert assessment.schema == "https://json-schema.org/draft/2020-12/schema"

    # Telemetry summary populated
    assert assessment.telemetry_summary.speed_mps == 3.25
    assert assessment.telemetry_summary.motion_state in (
        "still",
        "walking",
        "running",
        "abrupt_motion",
        "unknown",
    )


# ---------------------------------------------------------------------------
# 10. Isolation of Other-User and Future Trajectories Tests
# ---------------------------------------------------------------------------


def test_cross_user_and_future_trajectories_isolated():
    """Area 10: Trajectories from other users or from the future must be excluded from reference set."""
    service = RiskService()
    candidate_start = BASE_TIME
    records = [
        _make_record(
            timestamp=candidate_start + timedelta(milliseconds=i * 20),
            latitude=28.6139 + (i * 0.0001),
            longitude=77.2090 + (i * 0.0001),
            rec_id=i,
        )
        for i in range(5)
    ]

    # Construct mixed candidate pool:
    # 2 valid historical trajectories for TEST_USER_ID (preceding)
    valid_hist_1 = _make_trajectory(
        user_id=TEST_USER_ID,
        trajectory_id="hist_valid_1",
        start_time=candidate_start - timedelta(hours=5),
    )
    valid_hist_2 = _make_trajectory(
        user_id=TEST_USER_ID,
        trajectory_id="hist_valid_2",
        start_time=candidate_start - timedelta(hours=3),
    )

    # 2 trajectories belonging to another user (MUST be ignored)
    other_user_traj_1 = _make_trajectory(
        user_id="other_intruder_user",
        trajectory_id="hist_other_1",
        start_time=candidate_start - timedelta(hours=4),
    )
    other_user_traj_2 = _make_trajectory(
        user_id="other_intruder_user",
        trajectory_id="hist_other_2",
        start_time=candidate_start - timedelta(hours=2),
    )

    # 2 trajectories starting in the future or equal time (MUST be ignored to prevent future leakage)
    future_traj = _make_trajectory(
        user_id=TEST_USER_ID,
        trajectory_id="hist_future_1",
        start_time=candidate_start + timedelta(hours=1),
    )
    equal_time_traj = _make_trajectory(
        user_id=TEST_USER_ID,
        trajectory_id="hist_equal_time",
        start_time=candidate_start,
    )

    pool = [
        valid_hist_1,
        other_user_traj_1,
        valid_hist_2,
        future_traj,
        other_user_traj_2,
        equal_time_traj,
    ]

    assessment = service.evaluate_telemetry(
        user_id=TEST_USER_ID,
        records=records,
        trajectory_id="candidate_isolated_trip",
        historical_trajectories=pool,
    )

    # Out of 6 pool trajectories, ONLY 2 qualify (valid_hist_1 and valid_hist_2).
    # Since 2 < 5 (min_history), status MUST be INSUFFICIENT_HISTORY, and route_anomaly must be None!
    assert assessment.risk_vector.route_anomaly is None
    assert assessment.location_status == "available"
