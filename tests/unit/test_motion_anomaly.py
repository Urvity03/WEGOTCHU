"""Unit tests for motion feature extraction and kinematic anomaly detection."""

from datetime import datetime, timedelta, timezone
import pytest

from ai.anomaly_detection.motion import (
    MotionAnomalyDetector,
    MotionSample,
    STANDARD_GRAVITY_MPS2,
)


def _create_stationary_samples(
    count: int = 10,
    interval_ms: int = 20,
    base_time: datetime | None = None,
) -> list[MotionSample]:
    """Generate stationary samples with gravity predominantly along z-axis."""
    if base_time is None:
        base_time = datetime(2026, 9, 11, 12, 0, 0, tzinfo=timezone.utc)
    samples = []
    for i in range(count):
        t = base_time + timedelta(milliseconds=i * interval_ms)
        samples.append(
            MotionSample(
                timestamp=t,
                accel_x=0.02,
                accel_y=-0.01,
                accel_z=STANDARD_GRAVITY_MPS2,
                gyro_x=0.001,
                gyro_y=0.001,
                gyro_z=0.001,
                speed_mps=0.0,
            )
        )
    return samples


def _create_walking_samples(
    count: int = 20,
    interval_ms: int = 20,
) -> list[MotionSample]:
    """Generate normal walking samples with periodic dynamic acceleration."""
    import math

    base_time = datetime(2026, 9, 11, 12, 0, 0, tzinfo=timezone.utc)
    samples = []
    for i in range(count):
        t = base_time + timedelta(milliseconds=i * interval_ms)
        phase = i * 0.3
        # Mild rhythmic acceleration fluctuations around 1-2 m/s^2
        samples.append(
            MotionSample(
                timestamp=t,
                accel_x=0.5 * math.sin(phase),
                accel_y=1.2 * math.cos(phase),
                accel_z=STANDARD_GRAVITY_MPS2 + 1.0 * math.sin(phase),
                gyro_x=0.05,
                gyro_y=-0.03,
                gyro_z=0.02,
                speed_mps=1.3,
            )
        )
    return samples


def _create_abrupt_motion_samples(
    count: int = 20,
    interval_ms: int = 20,
) -> list[MotionSample]:
    """Generate high-jerk / impact anomaly samples."""
    samples = _create_stationary_samples(count=count, interval_ms=interval_ms)
    # Inject severe sudden jerk spike in the middle
    mid = count // 2
    samples[mid] = MotionSample(
        timestamp=samples[mid].timestamp,
        accel_x=18.0,
        accel_y=-22.0,
        accel_z=35.0,
        gyro_x=4.5,
        gyro_y=-3.2,
        gyro_z=5.1,
        speed_mps=4.0,
    )
    return samples


def test_motion_sample_validation():
    """Verify input validation constraints for MotionSample."""
    now = datetime.now(timezone.utc)

    # Valid construction
    sample = MotionSample(timestamp=now, accel_x=0.0, accel_y=0.0, accel_z=9.8)
    assert sample.accel_z == 9.8
    assert sample.gyro_x is None

    # Invalid timestamp type
    with pytest.raises(TypeError, match="datetime"):
        MotionSample(timestamp="2026-09-11", accel_x=0.0, accel_y=0.0, accel_z=9.8)  # type: ignore

    # Non-finite values
    with pytest.raises(ValueError, match="finite"):
        MotionSample(timestamp=now, accel_x=float("nan"), accel_y=0.0, accel_z=9.8)

    with pytest.raises(ValueError, match="finite"):
        MotionSample(timestamp=now, accel_x=0.0, accel_y=float("inf"), accel_z=9.8)

    # Negative speed
    with pytest.raises(ValueError, match="non-negative"):
        MotionSample(
            timestamp=now, accel_x=0.0, accel_y=0.0, accel_z=9.8, speed_mps=-1.0
        )


def test_stationary_motion_evaluates_low_anomaly():
    """Stationary observation window should yield low anomaly score and 'still' state."""
    detector = MotionAnomalyDetector()
    samples = _create_stationary_samples(count=15)

    result = detector.evaluate_window(samples)
    assert result.status == "SUCCESS"
    assert result.motion_anomaly_score is not None
    assert 0.0 <= result.motion_anomaly_score < 0.20
    assert result.motion_state == "still"
    assert result.confidence >= 0.8
    assert result.features is not None
    assert result.features.mean_dynamic_accel < 0.10


def test_walking_motion_evaluates_normal_locomotion():
    """Normal walking should yield moderate dynamic accel and below-threshold anomaly."""
    detector = MotionAnomalyDetector()
    samples = _create_walking_samples(count=20)

    result = detector.evaluate_window(samples)
    assert result.status == "SUCCESS"
    assert result.motion_anomaly_score is not None
    assert 0.0 <= result.motion_anomaly_score < 0.50
    assert result.motion_state == "walking"
    assert result.confidence == 1.0


def test_abrupt_motion_triggers_anomaly():
    """Violent jerk and high dynamic accel should trigger elevated anomaly score."""
    detector = MotionAnomalyDetector()
    samples = _create_abrupt_motion_samples(count=20)

    result = detector.evaluate_window(samples)
    assert result.status == "SUCCESS"
    assert result.motion_anomaly_score is not None
    assert result.motion_anomaly_score >= 0.50
    assert result.motion_state == "abrupt_motion"
    assert result.features is not None
    assert result.features.max_jerk >= 15.0


def test_empty_and_insufficient_samples():
    """Test handling of None, empty list, and sample counts below minimum threshold."""
    detector = MotionAnomalyDetector(min_samples=3)

    # None input
    res_none = detector.evaluate_window(None)
    assert res_none.status == "INSUFFICIENT_DATA"
    assert res_none.motion_anomaly_score is None
    assert res_none.confidence == 0.0

    # Empty list
    res_empty = detector.evaluate_window([])
    assert res_empty.status == "INSUFFICIENT_DATA"
    assert res_empty.motion_anomaly_score is None

    # Below minimum threshold (2 samples provided when min_samples=3)
    samples = _create_stationary_samples(count=2)
    res_few = detector.evaluate_window(samples)
    assert res_few.status == "INSUFFICIENT_DATA"
    assert res_few.motion_anomaly_score is None
    assert res_few.metadata["provided_count"] == 2


def test_invalid_unphysical_accelerometer_reading():
    """Sensor readings beyond operating range (e.g. >100 m/s^2) are rejected as INVALID_DATA."""
    detector = MotionAnomalyDetector()
    samples = _create_stationary_samples(count=5)
    now = samples[-1].timestamp + timedelta(milliseconds=20)
    samples.append(MotionSample(timestamp=now, accel_x=150.0, accel_y=0.0, accel_z=0.0))

    result = detector.evaluate_window(samples)
    assert result.status == "INVALID_DATA"
    assert result.motion_anomaly_score is None
    assert "sensor_saturation_or_quality_limit_exceeded" in str(
        result.metadata["reason"]
    )


def test_duplicate_timestamps_prevents_derivative_explosion():
    """Consecutive samples with zero dt must not cause artificial jerk explosion."""
    detector = MotionAnomalyDetector()
    base_time = datetime(2026, 9, 11, 12, 0, 0, tzinfo=timezone.utc)

    # 3 samples: s1 and s2 have identical timestamps, s3 is 20ms later
    s1 = MotionSample(timestamp=base_time, accel_x=0.0, accel_y=0.0, accel_z=9.8)
    s2 = MotionSample(timestamp=base_time, accel_x=1.0, accel_y=0.0, accel_z=9.8)
    s3 = MotionSample(
        timestamp=base_time + timedelta(milliseconds=20),
        accel_x=1.0,
        accel_y=0.0,
        accel_z=9.8,
    )

    feats = detector.extract_features([s1, s2, s3])
    # The duplicate dt between s1 and s2 was skipped; s2 to s3 had zero delta-a -> jerk is 0.0
    assert feats.max_jerk == 0.0


def test_zero_duration_window_rejected():
    """A window where all samples share the exact same timestamp must yield INVALID_DATA."""
    detector = MotionAnomalyDetector()
    base_time = datetime(2026, 9, 11, 12, 0, 0, tzinfo=timezone.utc)

    s1 = MotionSample(timestamp=base_time, accel_x=0.0, accel_y=0.0, accel_z=9.8)
    s2 = MotionSample(timestamp=base_time, accel_x=0.1, accel_y=0.0, accel_z=9.8)

    result = detector.evaluate_window([s1, s2])
    assert result.status == "INVALID_DATA"
    assert result.metadata["reason"] == "zero_window_duration"


def test_irregular_timestamps_preserves_derivative_correctness():
    """Jerk calculation must use actual delta-time intervals, not assume uniform 50 Hz."""
    detector = MotionAnomalyDetector()
    base_time = datetime(2026, 9, 11, 12, 0, 0, tzinfo=timezone.utc)

    # Sample 0 at t=0s, Sample 1 at t=1.0s (large delta t)
    s1 = MotionSample(timestamp=base_time, accel_x=0.0, accel_y=0.0, accel_z=9.8)
    s2 = MotionSample(
        timestamp=base_time + timedelta(seconds=1.0),
        accel_x=1.0,
        accel_y=0.0,
        accel_z=9.8,
    )
    feats_slow = detector.extract_features([s1, s2])
    # jerk = delta_a / delta_t = 1.0 / 1.0 = 1.0 m/s^3
    assert pytest.approx(feats_slow.max_jerk, rel=1e-2) == 1.0

    # Fast transition: same delta_a over 0.01s -> jerk = 1.0 / 0.01 = 100 m/s^3
    s3 = MotionSample(
        timestamp=base_time + timedelta(seconds=0.01),
        accel_x=1.0,
        accel_y=0.0,
        accel_z=9.8,
    )
    feats_fast = detector.extract_features([s1, s3])
    assert pytest.approx(feats_fast.max_jerk, rel=1e-2) == 100.0


def test_deterministic_output():
    """Identical input samples must produce bit-level identical anomaly evaluation."""
    detector = MotionAnomalyDetector()
    samples = _create_abrupt_motion_samples(count=15)

    res1 = detector.evaluate_window(samples)
    res2 = detector.evaluate_window(samples)

    assert res1.motion_anomaly_score == res2.motion_anomaly_score
    assert res1.confidence == res2.confidence
    assert res1.motion_state == res2.motion_state
    assert res1.status == res2.status
