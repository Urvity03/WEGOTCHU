"""
Unit tests for the Telemetry Adapter Service.

Covers:
1. Stable pseudonymous identity for repeated inputs.
2. Different identifiers producing different pseudonyms.
3. Empty identifiers and secrets being rejected.
4. Correct conversion of accelerometer, gyroscope, speed, and timestamps.
5. Missing gyroscope values remaining nullable.
6. Chronological ordering and duplicate timestamps.
7. Invalid timestamps and non-finite sensor values.
8. Invalid coordinates and non-finite latitude/longitude.
9. Fewer than two valid trajectory points.
10. Input records remaining unchanged.
"""

from __future__ import annotations

import copy
from datetime import datetime, timedelta, timezone
import os
from typing import Any

import pytest

# Ensure DATABASE_URL is set before importing backend models
os.environ.setdefault("DATABASE_URL", "sqlite://")

from backend.app.models.telemetry_record import TelemetryRecord  # noqa: E402
from backend.app.services.telemetry_adapter import (  # noqa: E402
    pseudonymize_identifier,
    record_to_motion_sample,
    record_to_trajectory_point,
    records_to_candidate_trajectory,
    records_to_motion_samples,
)

# ---------------------------------------------------------------------------
# Fixtures & Helpers
# ---------------------------------------------------------------------------

SECRET_KEY = "test-secret-key-for-pseudonymization"
BASE_TIME = datetime(2026, 10, 19, 12, 0, 0, tzinfo=timezone.utc)
_SENTINEL = object()


def _make_telemetry_record(
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
    device_id: str = "dev_sensor_001",
    rec_id: int | None = 1,
) -> TelemetryRecord:
    """Helper to construct a deterministic TelemetryRecord instance."""
    ts = BASE_TIME if timestamp is _SENTINEL else timestamp
    rec = TelemetryRecord(
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
    return rec


# ---------------------------------------------------------------------------
# 1. Pseudonymous Identity Tests
# ---------------------------------------------------------------------------


def test_pseudonymize_stable_for_repeated_inputs():
    """Requirement 1: Repeated calls with identical identifier and secret yield identical pseudonym."""
    pseudo1 = pseudonymize_identifier("device_alpha_123", SECRET_KEY)
    pseudo2 = pseudonymize_identifier("device_alpha_123", SECRET_KEY)

    assert isinstance(pseudo1, str)
    assert pseudo1.startswith("usr_")
    assert pseudo1 == pseudo2, "Pseudonym must be completely deterministic and stable"


def test_pseudonymize_different_identifiers_and_secrets():
    """Requirement 2: Different identifiers produce distinct pseudonyms; raw identifier is not leaked."""
    p_a = pseudonymize_identifier("device_A", SECRET_KEY)
    p_b = pseudonymize_identifier("device_B", SECRET_KEY)
    p_a_diff_secret = pseudonymize_identifier("device_A", "different-secret-key-999")

    assert p_a != p_b, "Different identifiers must produce distinct pseudonyms"
    assert p_a != p_a_diff_secret, "Different secrets must produce distinct pseudonyms"

    # Raw identifier must not be exposed in the pseudonym
    assert "device_A" not in p_a
    assert "device_B" not in p_b


def test_pseudonymize_rejects_empty_and_invalid_inputs():
    """Requirement 3: Empty identifiers, whitespace, or empty secrets are rejected."""
    # Empty / whitespace identifier
    with pytest.raises(ValueError, match="identifier cannot be empty"):
        pseudonymize_identifier("", SECRET_KEY)

    with pytest.raises(ValueError, match="identifier cannot be empty"):
        pseudonymize_identifier("   ", SECRET_KEY)

    # Empty / whitespace secret
    with pytest.raises(ValueError, match="secret cannot be empty"):
        pseudonymize_identifier("device_123", "")

    with pytest.raises(ValueError, match="secret cannot be empty"):
        pseudonymize_identifier("device_123", "   ")

    with pytest.raises(ValueError, match="secret cannot be empty"):
        pseudonymize_identifier("device_123", b"")

    # Type validation
    with pytest.raises(TypeError, match="identifier must be a string"):
        pseudonymize_identifier(None, SECRET_KEY)  # type: ignore

    with pytest.raises(TypeError, match="identifier must be a string"):
        pseudonymize_identifier(12345, SECRET_KEY)  # type: ignore

    with pytest.raises(TypeError, match="secret must be str or bytes"):
        pseudonymize_identifier("device_123", None)  # type: ignore


# ---------------------------------------------------------------------------
# 2. Motion Sample Conversion Tests
# ---------------------------------------------------------------------------


def test_motion_sample_correct_conversion():
    """Requirement 4: Correct conversion of accelerometer, gyroscope, speed, and timestamps."""
    rec = _make_telemetry_record(
        timestamp=BASE_TIME,
        accel_x=0.15,
        accel_y=9.82,
        accel_z=-0.04,
        gyro_x=0.02,
        gyro_y=0.03,
        gyro_z=-0.01,
        speed_mps=2.45,
    )

    sample = record_to_motion_sample(rec)

    assert sample is not None
    assert sample.timestamp == BASE_TIME
    assert sample.accel_x == 0.15
    assert sample.accel_y == 9.82
    assert sample.accel_z == -0.04
    assert sample.gyro_x == 0.02
    assert sample.gyro_y == 0.03
    assert sample.gyro_z == -0.01
    assert sample.speed_mps == 2.45


def test_motion_sample_nullable_gyroscope_and_speed():
    """Requirement 5: Missing gyroscope and speed values remain None without manufacturing values."""
    rec = _make_telemetry_record(
        accel_x=0.0,
        accel_y=9.81,
        accel_z=0.0,
        gyro_x=None,
        gyro_y=None,
        gyro_z=None,
        speed_mps=None,
    )

    sample = record_to_motion_sample(rec)

    assert sample is not None
    assert sample.gyro_x is None
    assert sample.gyro_y is None
    assert sample.gyro_z is None
    assert sample.speed_mps is None


def test_motion_samples_chronological_ordering_and_duplicates():
    """Requirement 6: Chronological ordering is enforced, and duplicate timestamp behavior is deterministic."""
    t0 = BASE_TIME
    t1 = BASE_TIME + timedelta(milliseconds=20)
    t2 = BASE_TIME + timedelta(milliseconds=40)

    # Pass in shuffled order: t2, t0, t1 (with two records at t1 having distinct IDs)
    r_t2 = _make_telemetry_record(timestamp=t2, accel_x=0.2, rec_id=3)
    r_t0 = _make_telemetry_record(timestamp=t0, accel_x=0.0, rec_id=1)
    r_t1_a = _make_telemetry_record(timestamp=t1, accel_x=0.1, rec_id=2)
    r_t1_b = _make_telemetry_record(timestamp=t1, accel_x=0.15, rec_id=4)

    # 1. Default (deduplicate_timestamps=True): deduplicates safely by default
    # Retains the earliest/lowest-id record for t1 (id 2 with accel_x=0.10, discarding id 4 with accel_x=0.15)
    samples = records_to_motion_samples([r_t2, r_t0, r_t1_b, r_t1_a])

    assert len(samples) == 3
    assert [s.timestamp for s in samples] == [t0, t1, t2]
    assert samples[0].accel_x == 0.0
    assert samples[1].accel_x == 0.1  # Retained r_t1_a (rec_id=2)
    assert samples[2].accel_x == 0.2
    # Confirms no sensor averaging or synthetic value creation occurs
    assert samples[1].accel_x != (0.1 + 0.15) / 2.0

    # 2. Explicit deduplicate_timestamps=False: retains all records with deterministic tie-breaking
    raw_samples = records_to_motion_samples(
        [r_t2, r_t0, r_t1_b, r_t1_a], deduplicate_timestamps=False
    )
    assert len(raw_samples) == 4
    assert raw_samples[0].timestamp == t0
    assert raw_samples[1].timestamp == t1
    assert raw_samples[1].accel_x == 0.1  # Tie-broken to rec_id=2
    assert raw_samples[2].timestamp == t1
    assert raw_samples[2].accel_x == 0.15  # Tie-broken to rec_id=4
    assert raw_samples[3].timestamp == t2
    assert raw_samples[3].accel_x == 0.2

    # 3. Deterministic tie-breaking by sequence arrival order when record has no integer id
    rec_no_id_1 = {
        "timestamp": t1,
        "accelerometer_x": 1.1,
        "accelerometer_y": 9.8,
        "accelerometer_z": 0.0,
    }
    rec_no_id_2 = {
        "timestamp": t1,
        "accelerometer_x": 2.2,
        "accelerometer_y": 9.8,
        "accelerometer_z": 0.0,
    }
    samples_no_id = records_to_motion_samples([rec_no_id_1, rec_no_id_2])
    assert len(samples_no_id) == 1
    assert samples_no_id[0].accel_x == 1.1  # Retained the first arrived record


def test_motion_sample_rejects_invalid_timestamps_and_non_finite_values():
    """Requirement 7: Records with invalid timestamps or non-finite required sensor values are excluded."""
    valid_rec = _make_telemetry_record()

    # Invalid timestamps
    assert record_to_motion_sample(_make_telemetry_record(timestamp=None)) is None
    assert (
        record_to_motion_sample(_make_telemetry_record(timestamp="invalid-iso-date"))
        is None
    )

    # Non-finite accelerometer values (NaN, inf, -inf)
    assert record_to_motion_sample(_make_telemetry_record(accel_x=float("nan"))) is None
    assert record_to_motion_sample(_make_telemetry_record(accel_y=float("inf"))) is None
    assert (
        record_to_motion_sample(_make_telemetry_record(accel_z=float("-inf"))) is None
    )

    # Non-finite gyroscope values (if provided, must be finite)
    assert record_to_motion_sample(_make_telemetry_record(gyro_x=float("nan"))) is None
    assert record_to_motion_sample(_make_telemetry_record(gyro_y=float("inf"))) is None

    # Invalid speed (negative or non-finite)
    assert record_to_motion_sample(_make_telemetry_record(speed_mps=-1.0)) is None
    assert (
        record_to_motion_sample(_make_telemetry_record(speed_mps=float("nan"))) is None
    )

    # Boolean values must not be treated as numbers
    rec_bool = copy.copy(valid_rec)
    rec_bool.accelerometer_x = True  # type: ignore
    assert record_to_motion_sample(rec_bool) is None

    # Verify sequence filter excludes only corrupted records
    rec_bad = _make_telemetry_record(accel_x=float("nan"))
    samples = records_to_motion_samples([valid_rec, rec_bad])
    assert len(samples) == 1
    assert samples[0].accel_x == valid_rec.accelerometer_x


# ---------------------------------------------------------------------------
# 3. Candidate Trajectory Conversion Tests
# ---------------------------------------------------------------------------


def test_trajectory_point_correct_conversion():
    """Requirement 8: Valid coordinates are preserved as TrajectoryPoints."""
    rec = _make_telemetry_record(latitude=37.7749, longitude=-122.4194)
    pt = record_to_trajectory_point(rec)

    assert pt is not None
    assert pt.latitude == 37.7749
    assert pt.longitude == -122.4194
    assert pt.timestamp == BASE_TIME


def test_trajectory_point_rejects_invalid_and_non_finite_coordinates():
    """Requirement 8: Non-finite or out-of-range coordinates are excluded."""
    # Out of latitude bounds [-90, 90]
    assert record_to_trajectory_point(_make_telemetry_record(latitude=90.001)) is None
    assert record_to_trajectory_point(_make_telemetry_record(latitude=-91.0)) is None

    # Out of longitude bounds [-180, 180]
    assert record_to_trajectory_point(_make_telemetry_record(longitude=180.001)) is None
    assert record_to_trajectory_point(_make_telemetry_record(longitude=-180.5)) is None

    # Non-finite coordinates
    assert (
        record_to_trajectory_point(_make_telemetry_record(latitude=float("nan")))
        is None
    )
    assert (
        record_to_trajectory_point(_make_telemetry_record(longitude=float("inf")))
        is None
    )

    # Missing timestamp
    assert record_to_trajectory_point(_make_telemetry_record(timestamp=None)) is None


def test_candidate_trajectory_requires_at_least_two_valid_points():
    """Requirement 9: Return None when fewer than two valid trajectory points exist."""
    t0 = BASE_TIME
    t1 = BASE_TIME + timedelta(seconds=1)

    r_valid_0 = _make_telemetry_record(
        timestamp=t0, latitude=28.6139, longitude=77.2090
    )
    r_valid_1 = _make_telemetry_record(
        timestamp=t1, latitude=28.6140, longitude=77.2091
    )
    r_invalid = _make_telemetry_record(latitude=float("nan"))

    # Empty records
    assert (
        records_to_candidate_trajectory([], user_id="usr_001", trajectory_id="trip_001")
        is None
    )

    # Only 1 valid record
    assert (
        records_to_candidate_trajectory(
            [r_valid_0], user_id="usr_001", trajectory_id="trip_001"
        )
        is None
    )

    # 1 valid and 1 invalid record (only 1 valid remains)
    assert (
        records_to_candidate_trajectory(
            [r_valid_0, r_invalid], user_id="usr_001", trajectory_id="trip_001"
        )
        is None
    )

    # Exactly 2 valid records produces a valid Trajectory preserving user_id and trajectory_id
    traj = records_to_candidate_trajectory(
        [r_valid_0, r_invalid, r_valid_1],
        user_id="usr_001",
        trajectory_id="trip_active",
    )
    assert traj is not None
    assert traj.user_id == "usr_001"
    assert traj.trajectory_id == "trip_active"
    assert len(traj.points) == 2
    assert traj.points[0].latitude == 28.6139
    assert traj.points[1].latitude == 28.6140


def test_candidate_trajectory_enforces_user_id_and_trajectory_id():
    """Requirement 9: trajectory_id is required; empty, invalid, or omitted IDs are rejected."""
    t0 = BASE_TIME
    t1 = BASE_TIME + timedelta(seconds=1)
    r0 = _make_telemetry_record(timestamp=t0, latitude=10.0, longitude=20.0)
    r1 = _make_telemetry_record(timestamp=t1, latitude=10.1, longitude=20.1)

    # Missing trajectory_id entirely raises TypeError (no default "candidate" exists)
    with pytest.raises(TypeError):
        records_to_candidate_trajectory([r0, r1], user_id="usr_001")  # type: ignore

    # Empty / whitespace trajectory_id raises ValueError
    with pytest.raises(ValueError, match="trajectory_id cannot be empty"):
        records_to_candidate_trajectory([r0, r1], user_id="usr_001", trajectory_id="")

    with pytest.raises(ValueError, match="trajectory_id cannot be empty"):
        records_to_candidate_trajectory(
            [r0, r1], user_id="usr_001", trajectory_id="   "
        )

    # Non-string trajectory_id raises TypeError
    with pytest.raises(TypeError, match="trajectory_id must be a string"):
        records_to_candidate_trajectory([r0, r1], user_id="usr_001", trajectory_id=12345)  # type: ignore

    with pytest.raises(TypeError, match="trajectory_id must be a string"):
        records_to_candidate_trajectory([r0, r1], user_id="usr_001", trajectory_id=None)  # type: ignore

    # Empty / whitespace user_id raises ValueError
    with pytest.raises(ValueError, match="user_id cannot be empty"):
        records_to_candidate_trajectory([r0, r1], user_id="", trajectory_id="trip_001")

    with pytest.raises(ValueError, match="user_id cannot be empty"):
        records_to_candidate_trajectory(
            [r0, r1], user_id="   ", trajectory_id="trip_001"
        )

    # Non-string user_id raises TypeError
    with pytest.raises(TypeError, match="user_id must be a string"):
        records_to_candidate_trajectory([r0, r1], user_id=None, trajectory_id="trip_001")  # type: ignore

    # Explicitly supplied trajectory_id is preserved exactly without fabricating any identifier
    traj = records_to_candidate_trajectory(
        [r0, r1], user_id="usr_abc", trajectory_id="custom_trip_segment_42"
    )
    assert traj is not None
    assert traj.trajectory_id == "custom_trip_segment_42"
    assert traj.trajectory_id != "candidate"


# ---------------------------------------------------------------------------
# 4. Immutability Tests
# ---------------------------------------------------------------------------


def test_input_records_remain_unchanged():
    """Requirement 10: Input records are never mutated by the conversion functions."""
    rec = _make_telemetry_record(
        timestamp=BASE_TIME,
        accel_x=1.23,
        accel_y=4.56,
        accel_z=7.89,
        latitude=34.0522,
        longitude=-118.2437,
    )

    # Capture initial state
    initial_dict = {
        "timestamp": rec.timestamp,
        "accel_x": rec.accelerometer_x,
        "accel_y": rec.accelerometer_y,
        "accel_z": rec.accelerometer_z,
        "latitude": rec.latitude,
        "longitude": rec.longitude,
    }

    input_list = [rec]

    # Execute all conversion functions
    _ = record_to_motion_sample(rec)
    _ = records_to_motion_samples(input_list)
    _ = record_to_trajectory_point(rec)
    _ = records_to_candidate_trajectory(
        input_list, user_id="usr_test", trajectory_id="trip_immutability"
    )

    # Verify input record state is bit-for-bit identical
    assert rec.timestamp == initial_dict["timestamp"]
    assert rec.accelerometer_x == initial_dict["accel_x"]
    assert rec.accelerometer_y == initial_dict["accel_y"]
    assert rec.accelerometer_z == initial_dict["accel_z"]
    assert rec.latitude == initial_dict["latitude"]
    assert rec.longitude == initial_dict["longitude"]
    assert len(input_list) == 1


# ---------------------------------------------------------------------------
# 5. Timezone Consistency Tests
# ---------------------------------------------------------------------------


def test_utc_and_non_utc_offsets_representing_same_instant():
    """UTC and non-UTC offset timestamps representing the same physical instant
    must produce identical normalized UTC datetimes and be treated as duplicates."""
    # 2026-10-19T12:00:00Z == 2026-10-19T17:30:00+05:30 (same instant)
    utc_time = datetime(2026, 10, 19, 12, 0, 0, tzinfo=timezone.utc)
    ist_offset = timezone(timedelta(hours=5, minutes=30))
    ist_time = datetime(2026, 10, 19, 17, 30, 0, tzinfo=ist_offset)

    rec_utc = _make_telemetry_record(timestamp=utc_time, accel_x=1.0, rec_id=1)
    rec_ist = _make_telemetry_record(timestamp=ist_time, accel_x=2.0, rec_id=2)

    sample_utc = record_to_motion_sample(rec_utc)
    sample_ist = record_to_motion_sample(rec_ist)

    assert sample_utc is not None
    assert sample_ist is not None
    # Both must be normalized to the same UTC instant
    assert sample_utc.timestamp == sample_ist.timestamp
    assert sample_utc.timestamp.tzinfo is not None
    assert sample_utc.timestamp.utcoffset() == timedelta(0)

    # With default deduplication, these represent the same instant → only first retained
    samples = records_to_motion_samples([rec_utc, rec_ist])
    assert len(samples) == 1
    assert samples[0].accel_x == 1.0  # rec_id=1 is retained (lower id)


def test_mixed_timezone_aware_chronological_ordering():
    """Records with different timezone offsets must be sorted by absolute UTC instant,
    not by naive wall-clock comparison."""
    # t_early: 2026-10-19T10:00:00Z (10:00 UTC)
    # t_late:  2026-10-19T10:30:00+05:30 → 2026-10-19T05:00:00Z (05:00 UTC, earlier!)
    # t_mid:   2026-10-19T09:00:00-02:00 → 2026-10-19T11:00:00Z (11:00 UTC, latest!)
    t_early = datetime(2026, 10, 19, 10, 0, 0, tzinfo=timezone.utc)
    ist_offset = timezone(timedelta(hours=5, minutes=30))
    t_late_wallclock = datetime(2026, 10, 19, 10, 30, 0, tzinfo=ist_offset)
    neg_offset = timezone(timedelta(hours=-2))
    t_mid_wallclock = datetime(2026, 10, 19, 9, 0, 0, tzinfo=neg_offset)

    rec_a = _make_telemetry_record(timestamp=t_early, accel_x=1.0, rec_id=1)
    rec_b = _make_telemetry_record(timestamp=t_late_wallclock, accel_x=2.0, rec_id=2)
    rec_c = _make_telemetry_record(timestamp=t_mid_wallclock, accel_x=3.0, rec_id=3)

    # With deduplication off to see ordering
    samples = records_to_motion_samples(
        [rec_a, rec_b, rec_c], deduplicate_timestamps=False
    )

    assert len(samples) == 3
    # Correct UTC ordering: t_late_wallclock (05:00Z) < t_early (10:00Z) < t_mid_wallclock (11:00Z)
    assert samples[0].accel_x == 2.0  # IST 10:30 → UTC 05:00
    assert samples[1].accel_x == 1.0  # UTC 10:00
    assert samples[2].accel_x == 3.0  # -02:00 09:00 → UTC 11:00

    # Verify all timestamps are UTC-normalized
    for s in samples:
        assert s.timestamp.tzinfo is not None
        assert s.timestamp.utcoffset() == timedelta(0)


def test_timezone_naive_datetimes_rejected():
    """Timezone-naive datetime objects must be rejected because the contract mandates
    UTC ISO 8601 and does not define how to interpret naive timestamps."""
    naive_dt = datetime(2026, 10, 19, 12, 0, 0)  # No tzinfo

    # Motion sample conversion
    rec_naive = _make_telemetry_record(timestamp=naive_dt)
    assert record_to_motion_sample(rec_naive) is None

    # Trajectory point conversion
    assert record_to_trajectory_point(rec_naive) is None

    # Batch conversion: naive records excluded, valid records preserved
    aware_dt = datetime(2026, 10, 19, 12, 0, 0, tzinfo=timezone.utc)
    rec_aware = _make_telemetry_record(timestamp=aware_dt, accel_x=5.0, rec_id=2)
    samples = records_to_motion_samples([rec_naive, rec_aware])
    assert len(samples) == 1
    assert samples[0].accel_x == 5.0


def test_timezone_naive_iso_strings_rejected():
    """ISO 8601 strings without timezone designators must be rejected."""
    # Dict-based record with naive ISO string
    rec_naive_str = {
        "timestamp": "2026-10-19T12:00:00",  # No Z or offset
        "accelerometer_x": 0.1,
        "accelerometer_y": 9.8,
        "accelerometer_z": 0.0,
    }
    assert record_to_motion_sample(rec_naive_str) is None

    # Valid UTC ISO string is accepted
    rec_utc_str = {
        "timestamp": "2026-10-19T12:00:00Z",
        "accelerometer_x": 0.1,
        "accelerometer_y": 9.8,
        "accelerometer_z": 0.0,
    }
    sample = record_to_motion_sample(rec_utc_str)
    assert sample is not None
    assert sample.timestamp.utcoffset() == timedelta(0)

    # Non-UTC offset ISO string is accepted and normalized to UTC
    rec_offset_str = {
        "timestamp": "2026-10-19T17:30:00+05:30",
        "accelerometer_x": 0.2,
        "accelerometer_y": 9.8,
        "accelerometer_z": 0.0,
    }
    sample_offset = record_to_motion_sample(rec_offset_str)
    assert sample_offset is not None
    assert sample_offset.timestamp == datetime(
        2026, 10, 19, 12, 0, 0, tzinfo=timezone.utc
    )


def test_invalid_timestamps_still_rejected():
    """Non-parseable strings, None, and non-datetime types must still be rejected."""
    invalid_values = [
        None,
        "",
        "not-a-date",
        "2026-13-01T00:00:00Z",  # invalid month
        12345,
        True,
        3.14,
        [],
    ]
    for val in invalid_values:
        rec = {
            "timestamp": val,
            "accelerometer_x": 0.1,
            "accelerometer_y": 9.8,
            "accelerometer_z": 0.0,
        }
        assert (
            record_to_motion_sample(rec) is None
        ), f"Expected None for timestamp={val!r}"


def test_deduplication_after_timezone_normalization():
    """Records with different offsets representing the same UTC instant must be
    deduplicated to a single sample, retaining the earliest record by id."""
    utc_instant = datetime(2026, 10, 19, 14, 0, 0, tzinfo=timezone.utc)
    # Same instant in +05:30
    ist_offset = timezone(timedelta(hours=5, minutes=30))
    ist_instant = datetime(2026, 10, 19, 19, 30, 0, tzinfo=ist_offset)
    # Same instant in -03:00
    br_offset = timezone(timedelta(hours=-3))
    br_instant = datetime(2026, 10, 19, 11, 0, 0, tzinfo=br_offset)

    rec1 = _make_telemetry_record(timestamp=utc_instant, accel_x=1.0, rec_id=10)
    rec2 = _make_telemetry_record(timestamp=ist_instant, accel_x=2.0, rec_id=20)
    rec3 = _make_telemetry_record(timestamp=br_instant, accel_x=3.0, rec_id=30)

    # Default deduplication: all three map to the same UTC instant
    samples = records_to_motion_samples([rec3, rec1, rec2])
    assert len(samples) == 1
    assert samples[0].accel_x == 1.0  # rec_id=10 has the lowest id

    # Without deduplication: all three retained, all with same UTC timestamp
    raw = records_to_motion_samples([rec3, rec1, rec2], deduplicate_timestamps=False)
    assert len(raw) == 3
    assert raw[0].timestamp == raw[1].timestamp == raw[2].timestamp
    # Ordered by rec_id tie-breaking
    assert raw[0].accel_x == 1.0  # rec_id=10
    assert raw[1].accel_x == 2.0  # rec_id=20
    assert raw[2].accel_x == 3.0  # rec_id=30


def test_trajectory_mixed_timezone_ordering():
    """Trajectory points with mixed timezone offsets must be sorted by UTC instant."""
    utc_t1 = datetime(2026, 10, 19, 10, 0, 0, tzinfo=timezone.utc)
    ist_offset = timezone(timedelta(hours=5, minutes=30))
    # IST 14:30 → UTC 09:00 (earlier than utc_t1)
    ist_t0 = datetime(2026, 10, 19, 14, 30, 0, tzinfo=ist_offset)

    rec0 = _make_telemetry_record(
        timestamp=utc_t1, latitude=28.6140, longitude=77.2091, rec_id=1
    )
    rec1 = _make_telemetry_record(
        timestamp=ist_t0, latitude=28.6139, longitude=77.2090, rec_id=2
    )

    traj = records_to_candidate_trajectory(
        [rec0, rec1], user_id="usr_tz", trajectory_id="trip_tz_test"
    )
    assert traj is not None
    # IST point (UTC 09:00) must come first, then UTC point (UTC 10:00)
    assert traj.points[0].latitude == 28.6139
    assert traj.points[1].latitude == 28.6140
    # Both timestamps must be UTC
    for pt in traj.points:
        assert pt.timestamp.utcoffset() == timedelta(0)
