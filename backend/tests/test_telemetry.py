from datetime import datetime, timezone
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.auth import SECRET_KEY, create_access_token
from backend.app.database import Base, get_db
from backend.app.main import app
from backend.app.models.telemetry_record import TelemetryRecord
from backend.app.models.trip import TripStatus
from backend.app.repositories.trip_repository import TripRepository
from backend.app.services.telemetry_adapter import pseudonymize_identifier

# -------------------------------------------------------------------
# Test database
# -------------------------------------------------------------------

TEST_DATABASE_URL = "sqlite://"

test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

Base.metadata.create_all(bind=test_engine)

TestingSessionLocal = sessionmaker(
    bind=test_engine,
    autoflush=False,
    autocommit=False,
)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)


# -------------------------------------------------------------------
# Test authentication
# -------------------------------------------------------------------

TEST_DEVICE_ID = "test_device_001"


def auth_headers(device_id: str = TEST_DEVICE_ID):
    token = create_access_token(device_id)
    return {
        "Authorization": f"Bearer {token}",
    }


# -------------------------------------------------------------------
# Test payload
# -------------------------------------------------------------------


def valid_payload():
    return {
        "version": "0.1",
        "device_id": TEST_DEVICE_ID,
        "timestamp": "2026-09-26T17:00:00Z",
        "location": {
            "latitude": 28.6139,
            "longitude": 77.2090,
            "altitude_meters": 5.0,
            "accuracy_meters": 5.0,
        },
        "speed_mps": 0.0,
        "bearing_degrees": 0.0,
        "accelerometer": {
            "x": 0.0,
            "y": 9.81,
            "z": 0.0,
        },
        "gyroscope": {
            "x": 0.0,
            "y": 0.0,
            "z": 0.0,
        },
        "battery_level": 0.85,
        "network_status": "WIFI",
    }


# -------------------------------------------------------------------
# Tests
# -------------------------------------------------------------------


def test_telemetry_endpoint_accepts_valid_payload():
    response = client.post(
        "/api/v1/telemetry",
        json=valid_payload(),
        headers=auth_headers(),
    )

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == "accepted"
    assert data["message"] == "Telemetry received successfully"
    assert data["device_id"] == TEST_DEVICE_ID


def test_telemetry_endpoint_accepts_missing_gyroscope():
    payload = valid_payload()
    payload.pop("gyroscope")

    response = client.post(
        "/api/v1/telemetry",
        json=payload,
        headers=auth_headers(),
    )

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == "accepted"
    assert data["message"] == "Telemetry received successfully"
    assert data["device_id"] == TEST_DEVICE_ID


def test_telemetry_endpoint_rejects_missing_body():
    response = client.post(
        "/api/v1/telemetry",
        headers=auth_headers(),
    )

    assert response.status_code == 422


def test_telemetry_endpoint_rejects_invalid_payload():
    payload = valid_payload()

    del payload["device_id"]

    response = client.post(
        "/api/v1/telemetry",
        json=payload,
        headers=auth_headers(),
    )

    assert response.status_code == 422


def test_telemetry_endpoint_rejects_missing_authentication():
    response = client.post(
        "/api/v1/telemetry",
        json=valid_payload(),
    )

    assert response.status_code == 401


def test_telemetry_endpoint_rejects_invalid_token():
    response = client.post(
        "/api/v1/telemetry",
        json=valid_payload(),
        headers={
            "Authorization": "Bearer invalid-token",
        },
    )

    assert response.status_code == 401


def test_telemetry_endpoint_rejects_wrong_device_identity():
    response = client.post(
        "/api/v1/telemetry",
        json=valid_payload(),
        headers=auth_headers("another_device"),
    )

    assert response.status_code == 403
    assert response.json()["detail"] == (
        "Device identity does not match authenticated identity"
    )


def test_telemetry_endpoint_persists_none_trip_id_when_omitted():
    payload = valid_payload()
    payload.pop("trip_id", None)

    response = client.post(
        "/api/v1/telemetry",
        json=payload,
        headers=auth_headers(),
    )

    assert response.status_code == 200
    assert response.json()["status"] == "accepted"

    db = TestingSessionLocal()
    try:
        records = (
            db.query(TelemetryRecord)
            .filter(TelemetryRecord.device_id == TEST_DEVICE_ID)
            .all()
        )
        assert any(r.trip_id is None for r in records)
    finally:
        db.close()


def test_telemetry_endpoint_unknown_trip_id_returns_404():
    payload = valid_payload()
    payload["trip_id"] = "nonexistent_trip_id_999"

    response = client.post(
        "/api/v1/telemetry",
        json=payload,
        headers=auth_headers(),
    )

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_telemetry_endpoint_cross_user_trip_returns_403():
    db = TestingSessionLocal()
    try:
        repo = TripRepository(db)
        other_user_id = pseudonymize_identifier("other_device_002", SECRET_KEY)
        repo.create_trip(
            trip_id="trip_owned_by_other",
            user_id=other_user_id,
            started_at=datetime.now(timezone.utc),
            status=TripStatus.ACTIVE,
        )
    finally:
        db.close()

    payload = valid_payload()
    payload["trip_id"] = "trip_owned_by_other"

    response = client.post(
        "/api/v1/telemetry",
        json=payload,
        headers=auth_headers(TEST_DEVICE_ID),
    )

    assert response.status_code == 403
    assert "not belong to authenticated user" in response.json()["detail"]


def test_telemetry_endpoint_finalized_trip_returns_409():
    db = TestingSessionLocal()
    try:
        repo = TripRepository(db)
        user_id = pseudonymize_identifier(TEST_DEVICE_ID, SECRET_KEY)
        repo.create_trip(
            trip_id="trip_finalized_test",
            user_id=user_id,
            started_at=datetime.now(timezone.utc),
            status=TripStatus.ACTIVE,
        )
        repo.update_trip_status(
            trip_id="trip_finalized_test",
            user_id=user_id,
            new_status=TripStatus.COMPLETED_NORMAL,
        )
    finally:
        db.close()

    payload = valid_payload()
    payload["trip_id"] = "trip_finalized_test"

    response = client.post(
        "/api/v1/telemetry",
        json=payload,
        headers=auth_headers(),
    )

    assert response.status_code == 409
    assert "finalized" in response.json()["detail"].lower()


def test_telemetry_endpoint_valid_active_trip_accepted():
    db = TestingSessionLocal()
    try:
        repo = TripRepository(db)
        user_id = pseudonymize_identifier(TEST_DEVICE_ID, SECRET_KEY)
        repo.create_trip(
            trip_id="trip_active_valid",
            user_id=user_id,
            started_at=datetime.now(timezone.utc),
            status=TripStatus.ACTIVE,
        )
    finally:
        db.close()

    payload = valid_payload()
    payload["trip_id"] = "trip_active_valid"

    response = client.post(
        "/api/v1/telemetry",
        json=payload,
        headers=auth_headers(),
    )

    assert response.status_code == 200
    assert response.json()["status"] == "accepted"

    db = TestingSessionLocal()
    try:
        record = (
            db.query(TelemetryRecord)
            .filter(TelemetryRecord.trip_id == "trip_active_valid")
            .first()
        )
        assert record is not None
        assert record.trip_id == "trip_active_valid"
        assert record.device_id == TEST_DEVICE_ID
    finally:
        db.close()


def test_telemetry_endpoint_initialized_trip_promoted_and_accepted():
    db = TestingSessionLocal()
    try:
        repo = TripRepository(db)
        user_id = pseudonymize_identifier(TEST_DEVICE_ID, SECRET_KEY)
        repo.create_trip(
            trip_id="trip_init_valid",
            user_id=user_id,
            started_at=datetime.now(timezone.utc),
            status=TripStatus.INITIALIZED,
        )
    finally:
        db.close()

    payload = valid_payload()
    payload["trip_id"] = "trip_init_valid"

    response = client.post(
        "/api/v1/telemetry",
        json=payload,
        headers=auth_headers(),
    )

    assert response.status_code == 200
    assert response.json()["status"] == "accepted"

    db = TestingSessionLocal()
    try:
        repo = TripRepository(db)
        trip = repo.get_trip("trip_init_valid")
        assert trip is not None
        assert trip.status == TripStatus.ACTIVE.value
    finally:
        db.close()


def test_telemetry_failure_does_not_activate_trip_without_first_record():
    trip_id = "trip-atomic-first-telemetry"
    db = TestingSessionLocal()
    try:
        user_id = pseudonymize_identifier(TEST_DEVICE_ID, SECRET_KEY)
        TripRepository(db).create_trip(
            trip_id=trip_id,
            user_id=user_id,
            started_at=datetime.now(timezone.utc),
            status=TripStatus.INITIALIZED,
        )
    finally:
        db.close()

    original_commit = Session.commit

    def fail_when_telemetry_is_pending(session):
        if any(isinstance(item, TelemetryRecord) for item in session.new):
            raise SQLAlchemyError("Telemetry write failed")
        original_commit(session)

    payload = valid_payload()
    payload["trip_id"] = trip_id

    with patch("sqlalchemy.orm.Session.commit", new=fail_when_telemetry_is_pending):
        response = client.post(
            "/api/v1/telemetry",
            json=payload,
            headers=auth_headers(),
        )

    assert response.status_code == 500

    db = TestingSessionLocal()
    try:
        trip = TripRepository(db).get_trip(trip_id)
        assert trip is not None
        assert trip.status == TripStatus.INITIALIZED.value
        assert (
            db.query(TelemetryRecord).filter(TelemetryRecord.trip_id == trip_id).count()
            == 0
        )
    finally:
        db.close()


def test_telemetry_endpoint_database_failure_triggers_rollback():
    payload = valid_payload()

    with patch(
        "sqlalchemy.orm.Session.commit",
        side_effect=SQLAlchemyError("DB write failed"),
    ), patch("sqlalchemy.orm.Session.rollback") as mock_rollback:
        response = client.post(
            "/api/v1/telemetry",
            json=payload,
            headers=auth_headers(),
        )

        assert response.status_code == 500
        assert "Failed to persist telemetry record" in response.json()["detail"]
        assert mock_rollback.called


# -------------------------------------------------------------------
# Trip Lifecycle API Tests (/api/v1/telemetry/trips/start & complete)
# -------------------------------------------------------------------


def test_start_trip_successful():
    trip_id = "trip-start-success-001"
    response = client.post(
        "/api/v1/telemetry/trips/start",
        json={"trip_id": trip_id},
        headers=auth_headers(),
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "accepted"
    assert data["trip_id"] == trip_id
    assert data["trip_status"] == TripStatus.INITIALIZED.value
    assert data["started_at"] is not None
    assert data["ended_at"] is None

    # Verify DB persistence
    db = TestingSessionLocal()
    try:
        repo = TripRepository(db)
        trip = repo.get_trip(trip_id)
        assert trip is not None
        assert trip.status == TripStatus.INITIALIZED.value
        expected_user = pseudonymize_identifier(TEST_DEVICE_ID, SECRET_KEY)
        assert trip.user_id == expected_user
        assert trip.user_id != TEST_DEVICE_ID
    finally:
        db.close()


def test_start_trip_missing_authentication():
    response = client.post(
        "/api/v1/telemetry/trips/start",
        json={"trip_id": "trip-no-auth"},
    )
    assert response.status_code == 401


def test_start_trip_duplicate_idempotency_same_user():
    trip_id = "trip-idempotent-start"
    res1 = client.post(
        "/api/v1/telemetry/trips/start",
        json={"trip_id": trip_id},
        headers=auth_headers(),
    )
    assert res1.status_code == 200

    res2 = client.post(
        "/api/v1/telemetry/trips/start",
        json={"trip_id": trip_id},
        headers=auth_headers(),
    )
    assert res2.status_code == 200
    assert res1.json()["trip_id"] == res2.json()["trip_id"]
    assert res1.json()["started_at"] == res2.json()["started_at"]


def test_start_trip_duplicate_cross_user_rejected():
    trip_id = "trip-collision-start"
    # User A starts trip
    res1 = client.post(
        "/api/v1/telemetry/trips/start",
        json={"trip_id": trip_id},
        headers=auth_headers("user_A"),
    )
    assert res1.status_code == 200

    # User B attempts to start trip with same trip_id
    res2 = client.post(
        "/api/v1/telemetry/trips/start",
        json={"trip_id": trip_id},
        headers=auth_headers("user_B"),
    )
    assert res2.status_code == 403
    assert "belongs to a different user" in res2.json()["detail"]


def test_complete_trip_unknown_trip_returns_404():
    response = client.post(
        "/api/v1/telemetry/trips/complete",
        json={"trip_id": "nonexistent-trip-999"},
        headers=auth_headers(),
    )
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_complete_trip_missing_authentication():
    response = client.post(
        "/api/v1/telemetry/trips/complete",
        json={"trip_id": "trip-no-auth"},
    )
    assert response.status_code == 401


def test_complete_trip_cross_user_rejected_403():
    trip_id = "trip-cross-user-complete"
    # User A starts trip
    res1 = client.post(
        "/api/v1/telemetry/trips/start",
        json={"trip_id": trip_id},
        headers=auth_headers("user_owner"),
    )
    assert res1.status_code == 200

    # User B attempts to complete User A's trip
    res2 = client.post(
        "/api/v1/telemetry/trips/complete",
        json={"trip_id": trip_id},
        headers=auth_headers("user_attacker"),
    )
    assert res2.status_code == 403
    assert "not belong to authenticated user" in res2.json()["detail"]


def test_complete_trip_valid_lifecycle_transitions():
    trip_id = "trip-lifecycle-complete"

    # 1. Start trip -> INITIALIZED
    start_res = client.post(
        "/api/v1/telemetry/trips/start",
        json={"trip_id": trip_id},
        headers=auth_headers(),
    )
    assert start_res.status_code == 200
    assert start_res.json()["trip_status"] == TripStatus.INITIALIZED.value

    # 2. Ingest telemetry -> INITIALIZED promoted to ACTIVE
    telem_payload = valid_payload()
    telem_payload["trip_id"] = trip_id
    telem_res = client.post(
        "/api/v1/telemetry",
        json=telem_payload,
        headers=auth_headers(),
    )
    assert telem_res.status_code == 200

    # Verify active status
    db = TestingSessionLocal()
    try:
        repo = TripRepository(db)
        trip = repo.get_trip(trip_id)
        assert trip.status == TripStatus.ACTIVE.value
    finally:
        db.close()

    # 3. Complete trip -> COMPLETED_UNVERIFIED (unverified completion without fabricated normal/anomaly)
    comp_res = client.post(
        "/api/v1/telemetry/trips/complete",
        json={"trip_id": trip_id},
        headers=auth_headers(),
    )
    assert comp_res.status_code == 200
    comp_data = comp_res.json()
    assert comp_data["status"] == "accepted"
    assert comp_data["trip_id"] == trip_id
    assert comp_data["trip_status"] == TripStatus.COMPLETED_UNVERIFIED.value
    # Semantic verification: never falsely marked normal or anomalous
    assert comp_data["trip_status"] != TripStatus.COMPLETED_NORMAL.value
    assert comp_data["trip_status"] != TripStatus.COMPLETED_ANOMALOUS.value
    assert comp_data["ended_at"] is not None


def test_complete_trip_evidenced_anomaly_transitions_to_completed_anomalous():
    trip_id = "trip-anomalous-complete"

    client.post(
        "/api/v1/telemetry/trips/start",
        json={"trip_id": trip_id},
        headers=auth_headers(),
    )

    response = client.post(
        "/api/v1/telemetry/trips/complete",
        json={"trip_id": trip_id, "anomalous": True},
        headers=auth_headers(),
    )

    assert response.status_code == 200
    data = response.json()
    assert data["trip_status"] == TripStatus.COMPLETED_ANOMALOUS.value
    assert data["ended_at"] is not None


def test_complete_trip_crisis_transitions_to_aborted_crisis():
    trip_id = "trip-crisis-complete"

    client.post(
        "/api/v1/telemetry/trips/start",
        json={"trip_id": trip_id},
        headers=auth_headers(),
    )

    response = client.post(
        "/api/v1/telemetry/trips/complete",
        json={"trip_id": trip_id, "crisis": True},
        headers=auth_headers(),
    )

    assert response.status_code == 200
    data = response.json()
    assert data["trip_status"] == TripStatus.ABORTED_CRISIS.value
    assert data["ended_at"] is not None


def test_complete_trip_repeated_requests_idempotent():
    trip_id = "trip-repeat-complete"

    client.post(
        "/api/v1/telemetry/trips/start",
        json={"trip_id": trip_id},
        headers=auth_headers(),
    )

    res1 = client.post(
        "/api/v1/telemetry/trips/complete",
        json={"trip_id": trip_id},
        headers=auth_headers(),
    )
    assert res1.status_code == 200
    assert res1.json()["trip_status"] == TripStatus.COMPLETED_UNVERIFIED.value

    # Repeat complete request with identical parameters
    res2 = client.post(
        "/api/v1/telemetry/trips/complete",
        json={"trip_id": trip_id},
        headers=auth_headers(),
    )
    assert res2.status_code == 200
    assert res2.json()["trip_status"] == TripStatus.COMPLETED_UNVERIFIED.value
    assert res1.json()["ended_at"] == res2.json()["ended_at"]


def test_complete_trip_cannot_reopen_or_alter_terminal_state():
    trip_id = "trip-terminal-guard"

    client.post(
        "/api/v1/telemetry/trips/start",
        json={"trip_id": trip_id},
        headers=auth_headers(),
    )

    # Complete as COMPLETED_UNVERIFIED
    res1 = client.post(
        "/api/v1/telemetry/trips/complete",
        json={"trip_id": trip_id, "crisis": False},
        headers=auth_headers(),
    )
    assert res1.status_code == 200
    assert res1.json()["trip_status"] == TripStatus.COMPLETED_UNVERIFIED.value

    # Attempt to alter to ABORTED_CRISIS -> 409 Conflict
    res2 = client.post(
        "/api/v1/telemetry/trips/complete",
        json={"trip_id": trip_id, "crisis": True},
        headers=auth_headers(),
    )
    assert res2.status_code == 409
    assert "already finalized" in res2.json()["detail"].lower()

    # Attempt to alter to COMPLETED_ANOMALOUS -> 409 Conflict
    res_alter = client.post(
        "/api/v1/telemetry/trips/complete",
        json={"trip_id": trip_id, "anomalous": True},
        headers=auth_headers(),
    )
    assert res_alter.status_code == 409
    assert "already finalized" in res_alter.json()["detail"].lower()

    # Attempt to stream telemetry to finalized trip -> 409 Conflict
    telem_payload = valid_payload()
    telem_payload["trip_id"] = trip_id
    res3 = client.post(
        "/api/v1/telemetry",
        json=telem_payload,
        headers=auth_headers(),
    )
    assert res3.status_code == 409
    assert "finalized" in res3.json()["detail"].lower()


def test_start_trip_database_failure_triggers_rollback():
    with patch(
        "sqlalchemy.orm.Session.commit",
        side_effect=SQLAlchemyError("DB write failed"),
    ), patch("sqlalchemy.orm.Session.rollback") as mock_rollback:
        response = client.post(
            "/api/v1/telemetry/trips/start",
            json={"trip_id": "trip-rollback-start"},
            headers=auth_headers(),
        )

        assert response.status_code == 500
        assert "Failed to create trip" in response.json()["detail"]
        assert mock_rollback.called


def test_complete_trip_database_failure_triggers_rollback():
    trip_id = "trip-rollback-complete"
    client.post(
        "/api/v1/telemetry/trips/start",
        json={"trip_id": trip_id},
        headers=auth_headers(),
    )

    with patch(
        "sqlalchemy.orm.Session.commit",
        side_effect=SQLAlchemyError("DB complete failed"),
    ), patch("sqlalchemy.orm.Session.rollback") as mock_rollback:
        response = client.post(
            "/api/v1/telemetry/trips/complete",
            json={"trip_id": trip_id},
            headers=auth_headers(),
        )

        assert response.status_code == 500
        assert "Failed to complete trip" in response.json()["detail"]
        assert mock_rollback.called


def test_confirmation_raw_device_id_never_used_as_ml_user_identity():
    trip_id = "trip-privacy-verification"
    raw_device = "mobile-android-pixel8-device-xyz"

    response = client.post(
        "/api/v1/telemetry/trips/start",
        json={"trip_id": trip_id},
        headers=auth_headers(raw_device),
    )
    assert response.status_code == 200

    db = TestingSessionLocal()
    try:
        repo = TripRepository(db)
        trip = repo.get_trip(trip_id)
        assert trip is not None
        # Must NEVER be raw device ID
        assert trip.user_id != raw_device
        # Must be deterministic HMAC-SHA256 pseudonym
        expected_pseudo = pseudonymize_identifier(raw_device, SECRET_KEY)
        assert trip.user_id == expected_pseudo
        assert trip.user_id.startswith("usr_")
    finally:
        db.close()
