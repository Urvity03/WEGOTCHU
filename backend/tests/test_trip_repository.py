"""Tests for persistent Trip model, TripRepository, and TelemetryRecord linkage."""

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.database import Base
from backend.app.models.telemetry import TelemetryPayload
from backend.app.models.telemetry_record import TelemetryRecord
from backend.app.models.trip import (
    TERMINAL_TRIP_STATUSES,
    Trip,
    TripStatus,
)
from backend.app.repositories.trip_repository import (
    TripLifecycleError,
    TripNotFoundError,
    TripOwnershipError,
    TripRepository,
)


@pytest.fixture
def db_session():
    """Create a fresh in-memory SQLite database session for each test."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
    )
    session = session_factory()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def repo(db_session):
    return TripRepository(db_session)


# -------------------------------------------------------------------
# Trip Creation & Idempotency Tests
# -------------------------------------------------------------------


def test_create_trip_valid(repo):
    started_at = datetime(2026, 10, 20, 10, 0, 0, tzinfo=timezone.utc)
    trip = repo.create_trip(
        trip_id="trip-001",
        user_id="pseudo-user-abc",
        started_at=started_at,
    )

    assert isinstance(trip, Trip)
    assert trip.id is not None
    assert trip.trip_id == "trip-001"
    assert trip.user_id == "pseudo-user-abc"
    assert trip.status == TripStatus.INITIALIZED.value
    assert trip.started_at == started_at
    assert trip.ended_at is None
    assert trip.created_at is not None
    assert trip.updated_at is not None


def test_create_trip_idempotency_same_user(repo):
    started_at = datetime(2026, 10, 20, 10, 0, 0, tzinfo=timezone.utc)
    trip_1 = repo.create_trip(
        trip_id="trip-idempotent-001",
        user_id="pseudo-user-abc",
        started_at=started_at,
    )

    # Re-invoking with identical trip_id and user_id should return existing trip
    trip_2 = repo.create_trip(
        trip_id="trip-idempotent-001",
        user_id="pseudo-user-abc",
        started_at=started_at + timedelta(minutes=5),
    )

    assert trip_1.id == trip_2.id
    assert trip_1.trip_id == trip_2.trip_id
    assert trip_2.started_at == started_at


def test_create_trip_duplicate_different_user_rejected(repo):
    started_at = datetime(2026, 10, 20, 10, 0, 0, tzinfo=timezone.utc)
    repo.create_trip(
        trip_id="trip-collision-001",
        user_id="user-original",
        started_at=started_at,
    )

    with pytest.raises(TripOwnershipError) as exc_info:
        repo.create_trip(
            trip_id="trip-collision-001",
            user_id="user-imposter",
            started_at=started_at,
        )

    assert "belongs to a different user" in str(exc_info.value)


@pytest.mark.parametrize("empty_val", ["", "   ", "\t\n"])
def test_create_trip_rejects_empty_ids(repo, empty_val):
    valid_time = datetime.now(timezone.utc)

    with pytest.raises(ValueError, match="trip_id must be a non-empty string"):
        repo.create_trip(trip_id=empty_val, user_id="user-1", started_at=valid_time)

    with pytest.raises(ValueError, match="user_id must be a non-empty string"):
        repo.create_trip(trip_id="trip-1", user_id=empty_val, started_at=valid_time)


def test_create_trip_rejects_timezone_naive_started_at(repo):
    naive_dt = datetime(2026, 10, 20, 10, 0, 0)  # tzinfo=None

    with pytest.raises(
        ValueError, match="started_at must be a timezone-aware datetime"
    ):
        repo.create_trip(
            trip_id="trip-naive",
            user_id="user-1",
            started_at=naive_dt,
        )


def test_create_trip_normalizes_non_utc_offsets(repo):
    ist = timezone(timedelta(hours=5, minutes=30))
    ist_time = datetime(2026, 10, 20, 15, 30, 0, tzinfo=ist)

    trip = repo.create_trip(
        trip_id="trip-ist",
        user_id="user-1",
        started_at=ist_time,
    )

    expected_utc = datetime(2026, 10, 20, 10, 0, 0, tzinfo=timezone.utc)
    assert trip.started_at == expected_utc
    assert trip.started_at.tzinfo == timezone.utc


# -------------------------------------------------------------------
# Trip Retrieval & Ownership Tests
# -------------------------------------------------------------------


def test_get_trip_ownership_enforcement(repo):
    started_at = datetime.now(timezone.utc)
    repo.create_trip(
        trip_id="trip-owner-test",
        user_id="owner-user",
        started_at=started_at,
    )

    # Query without user_id succeeds
    trip = repo.get_trip(trip_id="trip-owner-test")
    assert trip is not None
    assert trip.trip_id == "trip-owner-test"

    # Query with matching user_id succeeds
    trip_owned = repo.get_trip(trip_id="trip-owner-test", user_id="owner-user")
    assert trip_owned is not None

    # Query with wrong user_id raises TripOwnershipError
    with pytest.raises(TripOwnershipError) as exc_info:
        repo.get_trip(trip_id="trip-owner-test", user_id="attacker-user")
    assert "does not belong to user" in str(exc_info.value)

    # Query non-existent trip returns None
    assert repo.get_trip(trip_id="non-existent") is None


# -------------------------------------------------------------------
# Lifecycle Transitions & Terminal Immutability Tests
# -------------------------------------------------------------------


def test_valid_lifecycle_transitions(repo):
    started_at = datetime(2026, 10, 20, 8, 0, 0, tzinfo=timezone.utc)
    trip = repo.create_trip(
        trip_id="trip-lifecycle",
        user_id="user-lifecycle",
        started_at=started_at,
    )
    assert trip.status == TripStatus.INITIALIZED.value

    # INITIALIZED -> ACTIVE
    trip = repo.update_trip_status(
        trip_id="trip-lifecycle",
        user_id="user-lifecycle",
        new_status=TripStatus.ACTIVE,
    )
    assert trip.status == TripStatus.ACTIVE.value
    assert trip.ended_at is None

    # ACTIVE -> COMPLETED_NORMAL
    ended_at = datetime(2026, 10, 20, 8, 45, 0, tzinfo=timezone.utc)
    trip = repo.update_trip_status(
        trip_id="trip-lifecycle",
        user_id="user-lifecycle",
        new_status=TripStatus.COMPLETED_NORMAL,
        ended_at=ended_at,
    )
    assert trip.status == TripStatus.COMPLETED_NORMAL.value
    assert trip.ended_at == ended_at


def test_valid_lifecycle_transitions_unverified_and_anomalous(repo):
    started_at = datetime(2026, 10, 20, 8, 0, 0, tzinfo=timezone.utc)

    # 1. INITIALIZED -> ACTIVE -> COMPLETED_UNVERIFIED
    repo.create_trip(
        trip_id="trip-unverified-1",
        user_id="user-1",
        started_at=started_at,
    )
    repo.update_trip_status(
        trip_id="trip-unverified-1",
        user_id="user-1",
        new_status=TripStatus.ACTIVE,
    )
    t1 = repo.update_trip_status(
        trip_id="trip-unverified-1",
        user_id="user-1",
        new_status=TripStatus.COMPLETED_UNVERIFIED,
    )
    assert t1.status == TripStatus.COMPLETED_UNVERIFIED.value
    assert t1.ended_at is not None

    # 2. INITIALIZED -> ACTIVE -> COMPLETED_ANOMALOUS
    repo.create_trip(
        trip_id="trip-anomalous-1",
        user_id="user-1",
        started_at=started_at,
    )
    repo.update_trip_status(
        trip_id="trip-anomalous-1",
        user_id="user-1",
        new_status=TripStatus.ACTIVE,
    )
    t2 = repo.update_trip_status(
        trip_id="trip-anomalous-1",
        user_id="user-1",
        new_status=TripStatus.COMPLETED_ANOMALOUS,
    )
    assert t2.status == TripStatus.COMPLETED_ANOMALOUS.value
    assert t2.ended_at is not None

    # 3. INITIALIZED -> COMPLETED_UNVERIFIED directly (immediate cancel/completion)
    repo.create_trip(
        trip_id="trip-direct-unverified",
        user_id="user-1",
        started_at=started_at,
    )
    t3 = repo.update_trip_status(
        trip_id="trip-direct-unverified",
        user_id="user-1",
        new_status=TripStatus.COMPLETED_UNVERIFIED,
    )
    assert t3.status == TripStatus.COMPLETED_UNVERIFIED.value


@pytest.mark.parametrize("terminal_status", list(TERMINAL_TRIP_STATUSES))
def test_terminal_trips_cannot_reopen(repo, terminal_status):
    started_at = datetime(2026, 10, 20, 8, 0, 0, tzinfo=timezone.utc)
    trip_id = f"trip-terminal-{terminal_status.value.lower()}"
    user_id = "user-terminal"

    repo.create_trip(trip_id=trip_id, user_id=user_id, started_at=started_at)
    repo.update_trip_status(
        trip_id=trip_id, user_id=user_id, new_status=TripStatus.ACTIVE
    )
    repo.update_trip_status(
        trip_id=trip_id, user_id=user_id, new_status=terminal_status
    )

    # Attempting to reopen or change terminal state MUST raise TripLifecycleError
    with pytest.raises(TripLifecycleError) as exc_info:
        repo.update_trip_status(
            trip_id=trip_id,
            user_id=user_id,
            new_status=TripStatus.ACTIVE,
        )

    assert "Terminal states are immutable" in str(exc_info.value)


def test_terminal_trip_idempotent_status_update(repo):
    started_at = datetime(2026, 10, 20, 8, 0, 0, tzinfo=timezone.utc)
    trip_id = "trip-terminal-idempotent"
    user_id = "user-terminal"

    repo.create_trip(trip_id=trip_id, user_id=user_id, started_at=started_at)
    repo.update_trip_status(
        trip_id=trip_id, user_id=user_id, new_status=TripStatus.ACTIVE
    )
    trip = repo.update_trip_status(
        trip_id=trip_id, user_id=user_id, new_status=TripStatus.COMPLETED_NORMAL
    )
    assert trip.status == TripStatus.COMPLETED_NORMAL.value

    # Idempotent re-affirmation of the same terminal state should succeed
    same_trip = repo.update_trip_status(
        trip_id=trip_id, user_id=user_id, new_status=TripStatus.COMPLETED_NORMAL
    )
    assert same_trip.status == TripStatus.COMPLETED_NORMAL.value


def test_invalid_lifecycle_transition_rejected(repo):
    started_at = datetime(2026, 10, 20, 8, 0, 0, tzinfo=timezone.utc)
    repo.create_trip(
        trip_id="trip-invalid-transition",
        user_id="user-1",
        started_at=started_at,
    )

    # INITIALIZED cannot transition directly to COMPLETED_NORMAL (must be ACTIVE first)
    with pytest.raises(TripLifecycleError) as exc_info:
        repo.update_trip_status(
            trip_id="trip-invalid-transition",
            user_id="user-1",
            new_status=TripStatus.COMPLETED_NORMAL,
        )

    assert "Invalid lifecycle transition" in str(exc_info.value)


def test_cross_user_status_update_rejected(repo):
    started_at = datetime(2026, 10, 20, 8, 0, 0, tzinfo=timezone.utc)
    repo.create_trip(
        trip_id="trip-cross-user-update",
        user_id="owner-user",
        started_at=started_at,
    )

    with pytest.raises(TripOwnershipError) as exc_info:
        repo.update_trip_status(
            trip_id="trip-cross-user-update",
            user_id="unauthorized-user",
            new_status=TripStatus.ACTIVE,
        )

    assert "does not belong to user" in str(exc_info.value)


def test_update_non_existent_trip_raises_not_found(repo):
    with pytest.raises(TripNotFoundError):
        repo.update_trip_status(
            trip_id="missing-trip",
            user_id="user-1",
            new_status=TripStatus.ACTIVE,
        )


# -------------------------------------------------------------------
# TelemetryRecord Linkage & Backward Compatibility
# -------------------------------------------------------------------


def test_telemetry_record_nullable_trip_id_linkage(db_session, repo):
    started_at = datetime.now(timezone.utc)
    trip = repo.create_trip(
        trip_id="trip-linked-001",
        user_id="user-1",
        started_at=started_at,
    )

    # 1. Telemetry without trip_id (backward-compatibility for legacy streams)
    legacy_record = TelemetryRecord(
        version="0.1",
        device_id="device-001",
        trip_id=None,
        timestamp=started_at,
        latitude=28.6139,
        longitude=77.2090,
        accuracy_meters=5.0,
        accelerometer_x=0.0,
        accelerometer_y=9.81,
        accelerometer_z=0.0,
        battery_level=0.9,
        network_status="WIFI",
    )
    db_session.add(legacy_record)
    db_session.commit()
    db_session.refresh(legacy_record)

    assert legacy_record.id is not None
    assert legacy_record.trip_id is None

    # 2. Telemetry linked to an active trip
    linked_record = TelemetryRecord(
        version="0.1",
        device_id="device-001",
        trip_id=trip.trip_id,
        timestamp=started_at + timedelta(seconds=1),
        latitude=28.6140,
        longitude=77.2091,
        accuracy_meters=4.5,
        accelerometer_x=0.1,
        accelerometer_y=9.80,
        accelerometer_z=0.1,
        battery_level=0.89,
        network_status="WIFI",
    )
    db_session.add(linked_record)
    db_session.commit()
    db_session.refresh(linked_record)

    assert linked_record.id is not None
    assert linked_record.trip_id == "trip-linked-001"


def test_telemetry_payload_schema_compatibility():
    # 1. Payload without trip_id (legacy client)
    payload_dict_legacy = {
        "version": "0.1",
        "device_id": "dev-001",
        "timestamp": "2026-10-20T10:00:00Z",
        "location": {"latitude": 28.6, "longitude": 77.2, "accuracy_meters": 5.0},
        "accelerometer": {"x": 0.0, "y": 9.8, "z": 0.0},
        "battery_level": 0.8,
        "network_status": "CELLULAR",
    }
    payload_legacy = TelemetryPayload.model_validate(payload_dict_legacy)
    assert payload_legacy.trip_id is None

    # 2. Payload with trip_id (modern client)
    payload_dict_modern = {
        **payload_dict_legacy,
        "trip_id": "trip-abc-123",
    }
    payload_modern = TelemetryPayload.model_validate(payload_dict_modern)
    assert payload_modern.trip_id == "trip-abc-123"

    payload_with_whitespace = TelemetryPayload.model_validate(
        {**payload_dict_legacy, "trip_id": " trip-abc-123 "}
    )
    assert payload_with_whitespace.trip_id == "trip-abc-123"

    with pytest.raises(ValueError):
        TelemetryPayload.model_validate({**payload_dict_legacy, "trip_id": " "})
    with pytest.raises(ValueError):
        TelemetryPayload.model_validate({**payload_dict_legacy, "trip_id": "x" * 65})


# -------------------------------------------------------------------
# Historical Reference Eligibility & Pending Exclusion Tests
# -------------------------------------------------------------------


def test_get_eligible_reference_trips_excludes_pending_and_anomalous(repo):
    t0 = datetime(2026, 10, 20, 10, 0, 0, tzinfo=timezone.utc)
    user_id = "user-ref-test"

    # 1. Genuinely COMPLETED_NORMAL trip (eligible)
    repo.create_trip(
        trip_id="trip-normal-1",
        user_id=user_id,
        started_at=t0,
        status=TripStatus.INITIALIZED,
    )
    repo.update_trip_status(
        trip_id="trip-normal-1",
        user_id=user_id,
        new_status=TripStatus.ACTIVE,
    )
    repo.update_trip_status(
        trip_id="trip-normal-1",
        user_id=user_id,
        new_status=TripStatus.COMPLETED_NORMAL,
    )

    # 2. COMPLETED_UNVERIFIED trip (MUST be excluded)
    repo.create_trip(
        trip_id="trip-unverified-ref",
        user_id=user_id,
        started_at=t0 + timedelta(minutes=10),
        status=TripStatus.INITIALIZED,
    )
    repo.update_trip_status(
        trip_id="trip-unverified-ref",
        user_id=user_id,
        new_status=TripStatus.ACTIVE,
    )
    repo.update_trip_status(
        trip_id="trip-unverified-ref",
        user_id=user_id,
        new_status=TripStatus.COMPLETED_UNVERIFIED,
    )

    # 3. COMPLETION_PENDING trip (MUST be excluded)
    repo.create_trip(
        trip_id="trip-pending-ref",
        user_id=user_id,
        started_at=t0 + timedelta(minutes=20),
        status=TripStatus.INITIALIZED,
    )
    repo.update_trip_status(
        trip_id="trip-pending-ref",
        user_id=user_id,
        new_status=TripStatus.ACTIVE,
    )
    repo.update_trip_status(
        trip_id="trip-pending-ref",
        user_id=user_id,
        new_status=TripStatus.COMPLETION_PENDING,
    )

    # 4. COMPLETED_ANOMALOUS trip (MUST be excluded)
    repo.create_trip(
        trip_id="trip-anomalous-ref",
        user_id=user_id,
        started_at=t0 + timedelta(minutes=30),
        status=TripStatus.INITIALIZED,
    )
    repo.update_trip_status(
        trip_id="trip-anomalous-ref",
        user_id=user_id,
        new_status=TripStatus.ACTIVE,
    )
    repo.update_trip_status(
        trip_id="trip-anomalous-ref",
        user_id=user_id,
        new_status=TripStatus.COMPLETED_ANOMALOUS,
    )

    # 5. ACTIVE trip (in-flight; MUST be excluded)
    repo.create_trip(
        trip_id="trip-active-ref",
        user_id=user_id,
        started_at=t0 + timedelta(minutes=40),
        status=TripStatus.INITIALIZED,
    )
    repo.update_trip_status(
        trip_id="trip-active-ref",
        user_id=user_id,
        new_status=TripStatus.ACTIVE,
    )

    # 6. ABORTED_CRISIS trip (crisis; MUST be excluded)
    repo.create_trip(
        trip_id="trip-crisis-ref",
        user_id=user_id,
        started_at=t0 + timedelta(minutes=50),
        status=TripStatus.INITIALIZED,
    )
    repo.update_trip_status(
        trip_id="trip-crisis-ref",
        user_id=user_id,
        new_status=TripStatus.ABORTED_CRISIS,
    )

    # 7. Another user's COMPLETED_NORMAL trip (cross-user isolation; MUST be excluded)
    repo.create_trip(
        trip_id="trip-other-user",
        user_id="other-user-999",
        started_at=t0,
        status=TripStatus.INITIALIZED,
    )
    repo.update_trip_status(
        trip_id="trip-other-user",
        user_id="other-user-999",
        new_status=TripStatus.ACTIVE,
    )
    repo.update_trip_status(
        trip_id="trip-other-user",
        user_id="other-user-999",
        new_status=TripStatus.COMPLETED_NORMAL,
    )

    # 8. Future COMPLETED_NORMAL trip (must strictly precede candidate)
    repo.create_trip(
        trip_id="trip-future-normal",
        user_id=user_id,
        started_at=t0 + timedelta(hours=5),
        status=TripStatus.INITIALIZED,
    )
    repo.update_trip_status(
        trip_id="trip-future-normal",
        user_id=user_id,
        new_status=TripStatus.ACTIVE,
    )
    repo.update_trip_status(
        trip_id="trip-future-normal",
        user_id=user_id,
        new_status=TripStatus.COMPLETED_NORMAL,
    )

    # Candidate start time is t0 + 2 hours
    candidate_start = t0 + timedelta(hours=2)
    eligible = repo.get_eligible_reference_trips(
        user_id=user_id,
        before_timestamp=candidate_start,
    )

    assert len(eligible) == 1
    assert eligible[0].trip_id == "trip-normal-1"
    assert eligible[0].status == TripStatus.COMPLETED_NORMAL.value


def test_get_eligible_historical_trajectories_loads_points_and_excludes_pending(
    db_session, repo
):
    t0 = datetime(2026, 10, 20, 10, 0, 0, tzinfo=timezone.utc)
    user_id = "user-traj-test"

    # Trip 1: COMPLETED_NORMAL with 2 valid points
    repo.create_trip(
        trip_id="trip-traj-normal",
        user_id=user_id,
        started_at=t0,
    )
    repo.update_trip_status(
        trip_id="trip-traj-normal",
        user_id=user_id,
        new_status=TripStatus.ACTIVE,
    )
    repo.update_trip_status(
        trip_id="trip-traj-normal",
        user_id=user_id,
        new_status=TripStatus.COMPLETED_NORMAL,
    )

    rec1 = TelemetryRecord(
        version="0.1",
        device_id="dev-1",
        trip_id="trip-traj-normal",
        timestamp=t0,
        latitude=28.6139,
        longitude=77.2090,
        accuracy_meters=5.0,
        accelerometer_x=0.0,
        accelerometer_y=9.8,
        accelerometer_z=0.0,
        battery_level=0.9,
        network_status="WIFI",
    )
    rec2 = TelemetryRecord(
        version="0.1",
        device_id="dev-1",
        trip_id="trip-traj-normal",
        timestamp=t0 + timedelta(seconds=10),
        latitude=28.6145,
        longitude=77.2095,
        accuracy_meters=4.0,
        accelerometer_x=0.0,
        accelerometer_y=9.8,
        accelerometer_z=0.0,
        battery_level=0.9,
        network_status="WIFI",
    )
    db_session.add_all([rec1, rec2])

    # Trip 2: COMPLETED_UNVERIFIED with valid points (MUST be excluded)
    repo.create_trip(
        trip_id="trip-traj-unverified",
        user_id=user_id,
        started_at=t0 + timedelta(minutes=5),
    )
    repo.update_trip_status(
        trip_id="trip-traj-unverified",
        user_id=user_id,
        new_status=TripStatus.COMPLETED_UNVERIFIED,
    )
    rec3 = TelemetryRecord(
        version="0.1",
        device_id="dev-1",
        trip_id="trip-traj-unverified",
        timestamp=t0 + timedelta(minutes=5),
        latitude=28.6200,
        longitude=77.2100,
        accuracy_meters=5.0,
        accelerometer_x=0.0,
        accelerometer_y=9.8,
        accelerometer_z=0.0,
        battery_level=0.8,
        network_status="WIFI",
    )
    rec4 = TelemetryRecord(
        version="0.1",
        device_id="dev-1",
        trip_id="trip-traj-unverified",
        timestamp=t0 + timedelta(minutes=5, seconds=10),
        latitude=28.6210,
        longitude=77.2110,
        accuracy_meters=4.0,
        accelerometer_x=0.0,
        accelerometer_y=9.8,
        accelerometer_z=0.0,
        battery_level=0.8,
        network_status="WIFI",
    )
    db_session.add_all([rec3, rec4])
    db_session.commit()

    candidate_time = t0 + timedelta(hours=1)
    trajs = repo.get_eligible_historical_trajectories(
        user_id=user_id,
        before_timestamp=candidate_time,
    )

    assert len(trajs) == 1
    assert trajs[0].trajectory_id == "trip-traj-normal"
    assert trajs[0].user_id == user_id
    assert len(trajs[0].points) == 2
    assert not db_session.is_modified(rec1)
    assert not db_session.is_modified(rec2)
