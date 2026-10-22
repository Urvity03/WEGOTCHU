"""
Telemetry Adapter Service for WEGOTCHU.

Provides deterministic, side-effect-free adapters for:
1. Pseudonymous user identity derivation using HMAC-SHA256.
2. Converting persisted TelemetryRecord observations to chronologically ordered MotionSamples.
3. Converting persisted TelemetryRecord observations to Trajectory objects with TrajectoryPoints.

Guiding Principles:
- Pure data transformation: no database queries, network operations, or model invocations.
- Strict input validation: non-finite (NaN, inf) values and invalid timestamps are rejected.
- Non-mutating: input records are never modified.
- Deterministic: identical inputs produce identical outputs with reproducible ordering.
"""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import hmac
import math
from typing import Any, Sequence

from ai.anomaly_detection.motion import MotionSample
from ai.route_deviation.loader import Trajectory, TrajectoryPoint


def pseudonymize_identifier(
    identifier: str,
    secret: str | bytes,
    prefix: str = "usr_",
) -> str:
    """
    Derive a deterministic pseudonymous user identifier using HMAC-SHA256.

    Args:
        identifier: The original device or user identifier to pseudonymize.
        secret: A non-empty secret key used to key the HMAC.
        prefix: Optional prefix for the resulting identifier (default: "usr_").

    Returns:
        A stable pseudonymous string representing the user_id.

    Raises:
        ValueError: If identifier or secret is empty or whitespace-only.
        TypeError: If identifier is not a string, or secret is not str or bytes.
    """
    if not isinstance(identifier, str):
        raise TypeError(f"identifier must be a string, got {type(identifier).__name__}")
    if not identifier.strip():
        raise ValueError("identifier cannot be empty or whitespace-only")

    if isinstance(secret, str):
        if not secret.strip():
            raise ValueError("secret cannot be empty or whitespace-only")
        secret_bytes = secret.encode("utf-8")
    elif isinstance(secret, (bytes, bytearray)):
        if len(secret) == 0:
            raise ValueError("secret cannot be empty")
        secret_bytes = bytes(secret)
    else:
        raise TypeError(f"secret must be str or bytes, got {type(secret).__name__}")

    digest = hmac.new(
        secret_bytes, identifier.encode("utf-8"), hashlib.sha256
    ).hexdigest()
    return f"{prefix}{digest[:16]}"


def _get_val(obj: Any, *keys: str) -> Any:
    """Helper to safely extract field values from either objects or dictionaries."""
    for k in keys:
        if isinstance(obj, dict):
            if k in obj:
                return obj[k]
        else:
            if hasattr(obj, k):
                return getattr(obj, k)
    return None


def _to_finite_float(val: Any) -> float | None:
    """Convert value to float if finite; returns None for NaN, inf, None, bool, or non-numeric."""
    if val is None or isinstance(val, bool):
        return None
    if isinstance(val, (int, float)):
        f = float(val)
        if math.isfinite(f):
            return f
    return None


def _to_datetime(val: Any) -> datetime | None:
    """
    Validate or convert value to a timezone-aware UTC datetime.

    Timezone Policy (derived from Mobile Telemetry Contract v0.1, Section 5):
      - The contract mandates "Timestamp must use UTC ISO 8601 format."
      - The database column uses DateTime(timezone=True).
      - All adapter outputs use timezone-aware UTC datetimes for safe chronological
        ordering and deduplication across records from heterogeneous sources.

    Behavior:
      - Timezone-aware datetimes (any offset) are normalized to UTC.
        For example, 2026-10-19T17:30:00+05:30 becomes 2026-10-19T12:00:00+00:00.
        This ensures chronological correctness regardless of the originating timezone.
      - ISO 8601 strings with timezone designators (Z, +HH:MM, -HH:MM) are parsed
        and normalized to UTC.
      - Timezone-naive datetimes and ISO strings without timezone designators are
        rejected (returns None). The contract does not define how to interpret naive
        timestamps, so silently assuming UTC would risk misinterpreting wall-clock
        times from non-UTC sources. Callers holding naive datetimes that are known
        to represent UTC must explicitly attach timezone.utc before passing them.
      - Non-datetime, non-string values return None.

    Args:
        val: A datetime object or ISO 8601 string.

    Returns:
        A timezone-aware UTC datetime, or None if the input is invalid or naive.
    """
    if isinstance(val, datetime):
        if val.tzinfo is None or val.tzinfo.utcoffset(val) is None:
            # Reject naive datetimes: the contract mandates UTC ISO 8601 and
            # does not specify how to interpret timestamps without timezone info.
            return None
        return val.astimezone(timezone.utc)
    if isinstance(val, str):
        try:
            parsed = datetime.fromisoformat(val.replace("Z", "+00:00"))
        except (ValueError, TypeError):
            return None
        if parsed.tzinfo is None or parsed.tzinfo.utcoffset(parsed) is None:
            return None
        return parsed.astimezone(timezone.utc)
    return None


def record_to_motion_sample(record: Any) -> MotionSample | None:
    """
    Convert a single telemetry record into a MotionSample.

    Handles flat columns (TelemetryRecord) as well as nested structures (TelemetryPayload).

    Validation & Exclusion:
      - Requires a valid datetime timestamp.
      - Requires finite accelerometer values (x, y, z).
      - Gyroscope values must be finite if provided; otherwise remain None.
      - Speed must be non-negative and finite if provided; otherwise remains None.
      - Returns None if any required value is invalid or corrupted.

    Args:
        record: TelemetryRecord object or compatible mapping.

    Returns:
        A MotionSample instance if valid, else None.
    """
    ts = _to_datetime(_get_val(record, "timestamp"))
    if ts is None:
        return None

    # Accelerometer: check flat keys first, then nested accelerometer object/dict
    raw_ax = _get_val(record, "accelerometer_x")
    raw_ay = _get_val(record, "accelerometer_y")
    raw_az = _get_val(record, "accelerometer_z")

    if raw_ax is None and raw_ay is None and raw_az is None:
        nested_accel = _get_val(record, "accelerometer")
        if nested_accel is not None:
            raw_ax = _get_val(nested_accel, "x")
            raw_ay = _get_val(nested_accel, "y")
            raw_az = _get_val(nested_accel, "z")

    ax = _to_finite_float(raw_ax)
    ay = _to_finite_float(raw_ay)
    az = _to_finite_float(raw_az)

    if ax is None or ay is None or az is None:
        return None

    # Gyroscope: optional, but if provided must be finite
    raw_gx = _get_val(record, "gyroscope_x")
    raw_gy = _get_val(record, "gyroscope_y")
    raw_gz = _get_val(record, "gyroscope_z")

    if raw_gx is None and raw_gy is None and raw_gz is None:
        nested_gyro = _get_val(record, "gyroscope")
        if nested_gyro is not None:
            raw_gx = _get_val(nested_gyro, "x")
            raw_gy = _get_val(nested_gyro, "y")
            raw_gz = _get_val(nested_gyro, "z")

    gx: float | None = None
    gy: float | None = None
    gz: float | None = None

    if raw_gx is not None or raw_gy is not None or raw_gz is not None:
        gx = _to_finite_float(raw_gx)
        gy = _to_finite_float(raw_gy)
        gz = _to_finite_float(raw_gz)
        # If any component is provided as non-finite (e.g. NaN), reject the sample
        if (
            (raw_gx is not None and gx is None)
            or (raw_gy is not None and gy is None)
            or (raw_gz is not None and gz is None)
        ):
            return None

    # Speed: optional, non-negative finite float
    raw_sp = _get_val(record, "speed_mps")
    sp: float | None = None
    if raw_sp is not None:
        sp = _to_finite_float(raw_sp)
        if sp is None or sp < 0.0:
            return None

    try:
        return MotionSample(
            timestamp=ts,
            accel_x=ax,
            accel_y=ay,
            accel_z=az,
            gyro_x=gx,
            gyro_y=gy,
            gyro_z=gz,
            speed_mps=sp,
        )
    except (ValueError, TypeError):
        return None


def records_to_motion_samples(
    records: Sequence[Any],
    deduplicate_timestamps: bool = True,
) -> list[MotionSample]:
    """
    Convert a sequence of telemetry records into chronologically ordered MotionSamples.

    Validation & Exclusion:
      - Records with missing or invalid timestamps are excluded.
      - Records with non-finite required accelerometer values (NaN, inf) are excluded.
      - Records with non-finite optional values (NaN/inf gyro or negative speed) are excluded.
      - Input records are never mutated.

    Chronological & Duplicate Timestamp Policy:
      - Converted samples are sorted strictly chronologically by timestamp.
      - When multiple records share the exact same timestamp:
        - The earliest observation (lowest integer record.id if present, or initial arrival index
          in the sequence) is deterministically retained as the canonical reading.
        - Subsequent duplicate records sharing that timestamp are omitted during deduplication.
        - Sensor values are never averaged, interpolated, or fabricated.
      - By default (deduplicate_timestamps=True), duplicate timestamps are deduplicated to protect
        kinematic derivative extraction and feature distributions in downstream anomaly detectors.
      - Callers requiring raw sequence retention may explicitly specify deduplicate_timestamps=False.
      - Sufficiency of window size is NOT decided here (delegated to MotionAnomalyDetector).

    Args:
        records: Sequence of TelemetryRecord objects or compatible mappings.
        deduplicate_timestamps: Whether to retain only the first sample per timestamp (default: True).

    Returns:
        List of valid, chronologically ordered MotionSample objects.
    """
    valid_items: list[tuple[datetime, int, MotionSample]] = []

    for idx, rec in enumerate(records):
        sample = record_to_motion_sample(rec)
        if sample is not None:
            rec_id = _get_val(rec, "id")
            sort_id = (
                rec_id if isinstance(rec_id, int) else idx
            )  # tie-breaker for identical timestamps
            valid_items.append((sample.timestamp, sort_id, sample))

    # Sort strictly chronologically by timestamp, tie-breaking on sort_id
    valid_items.sort(key=lambda item: (item[0], item[1]))

    if not deduplicate_timestamps:
        return [item[2] for item in valid_items]

    # Deduplicate: keep first occurrence per timestamp
    deduped: list[MotionSample] = []
    seen_timestamps: set[datetime] = set()

    for item in valid_items:
        ts = item[0]
        if ts not in seen_timestamps:
            seen_timestamps.add(ts)
            deduped.append(item[2])

    return deduped


def record_to_trajectory_point(record: Any) -> TrajectoryPoint | None:
    """
    Convert a single telemetry record into a TrajectoryPoint.

    Handles flat columns (TelemetryRecord) as well as nested structures (TelemetryPayload).

    Validation & Exclusion:
      - Requires a valid datetime timestamp.
      - Requires latitude in [-90.0, 90.0] and longitude in [-180.0, 180.0].
      - Non-finite coordinates (NaN, inf) or None coordinates return None.

    Args:
        record: TelemetryRecord object or compatible mapping.

    Returns:
        A TrajectoryPoint instance if valid, else None.
    """
    ts = _to_datetime(_get_val(record, "timestamp"))
    if ts is None:
        return None

    raw_lat = _get_val(record, "latitude")
    raw_lon = _get_val(record, "longitude")

    if raw_lat is None and raw_lon is None:
        nested_loc = _get_val(record, "location")
        if nested_loc is not None:
            raw_lat = _get_val(nested_loc, "latitude")
            raw_lon = _get_val(nested_loc, "longitude")

    lat = _to_finite_float(raw_lat)
    lon = _to_finite_float(raw_lon)

    if lat is None or not (-90.0 <= lat <= 90.0):
        return None
    if lon is None or not (-180.0 <= lon <= 180.0):
        return None

    try:
        return TrajectoryPoint(latitude=lat, longitude=lon, timestamp=ts)
    except (ValueError, TypeError):
        return None


def records_to_candidate_trajectory(
    records: Sequence[Any],
    user_id: str,
    trajectory_id: str,
) -> Trajectory | None:
    """
    Convert valid location records into a Trajectory representation.

    Validation & Exclusion:
      - Validates user_id and trajectory_id are non-empty strings. Callers must explicitly
        provide trajectory_id; no default or fabricated trip identifier is introduced.
      - Converts each record into a TrajectoryPoint; excludes invalid points.
      - Sorts valid points chronologically by timestamp.
      - If fewer than 2 valid points remain, returns None (Trajectory requires >= 2 points).
      - Does not fabricate trip boundaries, score trajectories, or mutate input records.

    Args:
        records: Sequence of TelemetryRecord objects or compatible mappings.
        user_id: The pseudonymous or caller-provided user identifier.
        trajectory_id: The explicit trajectory identifier for the candidate trip.

    Returns:
        A Trajectory object if at least 2 valid points exist, else None.

    Raises:
        ValueError: If user_id or trajectory_id is empty or whitespace-only.
        TypeError: If user_id or trajectory_id is not a string.
    """
    if not isinstance(user_id, str):
        raise TypeError(f"user_id must be a string, got {type(user_id).__name__}")
    if not user_id.strip():
        raise ValueError("user_id cannot be empty or whitespace-only")

    if not isinstance(trajectory_id, str):
        raise TypeError(
            f"trajectory_id must be a string, got {type(trajectory_id).__name__}"
        )
    if not trajectory_id.strip():
        raise ValueError("trajectory_id cannot be empty or whitespace-only")

    valid_points: list[TrajectoryPoint] = []
    for rec in records:
        pt = record_to_trajectory_point(rec)
        if pt is not None:
            valid_points.append(pt)

    # Sort chronologically
    valid_points.sort(key=lambda p: p.timestamp)

    if len(valid_points) < 2:
        return None

    return Trajectory(
        user_id=user_id,
        trajectory_id=trajectory_id,
        points=tuple(valid_points),
    )
