from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest
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


client = TestClient(app)


@pytest.fixture(autouse=True)
def use_module_test_database():
    previous_override = app.dependency_overrides.get(get_db)
    app.dependency_overrides[get_db] = override_get_db
    yield
    if previous_override is None:
        app.dependency_overrides.pop(get_db, None)
    else:
        app.dependency_overrides[get_db] = previous_override


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


def test_client_anomaly_flag_does_not_verify_trip_without_backend_evidence():
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
    assert data["trip_status"] == TripStatus.COMPLETED_UNVERIFIED.value
    assert data["inference_status"] == "INSUFFICIENT_DATA"
    assert data["risk_assessment"] is None
    assert data["ended_at"] is not None


def test_normal_assessment_does_not_verify_trip_without_coverage_tracking():
    trip_id = "trip-normal-assessment-unverified"
    sample_time = datetime.now(timezone.utc) - timedelta(seconds=2)
    start_response = client.post(
        "/api/v1/telemetry/trips/start",
        json={"trip_id": trip_id, "started_at": sample_time.isoformat()},
        headers=auth_headers(),
    )
    assert start_response.status_code == 200

    db = TestingSessionLocal()
    try:
        db.add_all(
            [
                TelemetryRecord(
                    version="0.1",
                    device_id=TEST_DEVICE_ID,
                    trip_id=trip_id,
                    timestamp=sample_time + timedelta(seconds=offset),
                    latitude=28.6139 + offset * 0.0001,
                    longitude=77.2090 + offset * 0.0001,
                    accuracy_meters=5.0,
                    speed_mps=0.0,
                    accelerometer_x=0.0,
                    accelerometer_y=9.81,
                    accelerometer_z=0.0,
                    battery_level=0.9,
                    network_status="WIFI",
                )
                for offset in (0, 1)
            ]
        )
        db.commit()
    finally:
        db.close()

    response = client.post(
        "/api/v1/telemetry/trips/complete",
        json={"trip_id": trip_id},
        headers=auth_headers(),
    )

    assert response.status_code == 200
    data = response.json()
    assert data["inference_status"] == "COMPLETED"
    assert data["risk_assessment"]["risk_level"] == "NORMAL"
    assert data["trip_status"] == TripStatus.COMPLETED_UNVERIFIED.value


def test_complete_trip_assesses_persisted_window_and_reports_anomaly():
    trip_id = "trip-persisted-risk-assessment"
    started_at = datetime(2026, 9, 26, 16, 59, 0, tzinfo=timezone.utc)
    sample_time = datetime(2026, 9, 26, 17, 0, 0, tzinfo=timezone.utc)
    user_id = pseudonymize_identifier(TEST_DEVICE_ID, SECRET_KEY)

    db = TestingSessionLocal()
    try:
        repo = TripRepository(db)
        repo.create_trip(
            trip_id=trip_id,
            user_id=user_id,
            started_at=started_at,
            status=TripStatus.ACTIVE,
        )
        for index in range(5):
            history_id = f"{trip_id}-history-{index}"
            history_start = started_at - timedelta(days=5 - index)
            repo.create_trip(
                trip_id=history_id,
                user_id=user_id,
                started_at=history_start,
            )
            repo.update_trip_status(
                trip_id=history_id,
                user_id=user_id,
                new_status=TripStatus.ACTIVE,
            )
            repo.update_trip_status(
                trip_id=history_id,
                user_id=user_id,
                new_status=TripStatus.COMPLETED_NORMAL,
                ended_at=history_start + timedelta(seconds=10),
            )
            db.add_all(
                [
                    TelemetryRecord(
                        version="0.1",
                        device_id=TEST_DEVICE_ID,
                        trip_id=history_id,
                        timestamp=history_start + timedelta(seconds=offset),
                        latitude=28.6139 + index * 0.0001 + offset * 0.00001,
                        longitude=77.2090 + index * 0.0001 + offset * 0.00001,
                        accuracy_meters=5.0,
                        speed_mps=1.0,
                        accelerometer_x=0.0,
                        accelerometer_y=9.81,
                        accelerometer_z=0.0,
                        battery_level=0.9,
                        network_status="WIFI",
                    )
                    for offset in (0, 10)
                ]
            )
        db.add_all(
            [
                TelemetryRecord(
                    version="0.1",
                    device_id=TEST_DEVICE_ID,
                    trip_id=trip_id,
                    timestamp=sample_time + timedelta(seconds=offset),
                    latitude=28.6139 + offset * 0.0001,
                    longitude=77.2090 + offset * 0.0001,
                    accuracy_meters=5.0,
                    speed_mps=1.0,
                    accelerometer_x=0.0 if offset == 0 else 60.0,
                    accelerometer_y=9.81,
                    accelerometer_z=0.0,
                    battery_level=0.9,
                    network_status="WIFI",
                )
                for offset in (0, 1)
            ]
        )
        db.commit()
    finally:
        db.close()

    response = client.post(
        "/api/v1/telemetry/trips/complete",
        json={"trip_id": trip_id},
        headers=auth_headers(),
    )

    assert response.status_code == 200
    data = response.json()
    assert data["trip_status"] == TripStatus.COMPLETED_ANOMALOUS.value
    assert data["inference_status"] == "COMPLETED"
    assert data["risk_assessment"]["user_id"] == user_id
    assert data["risk_assessment"]["user_id"] != TEST_DEVICE_ID
    assert "unusual_motion" in data["risk_assessment"]["signals"]
    assert data["risk_assessment"]["telemetry_summary"]["motion_status"] == "SUCCESS"
    assert data["risk_assessment"]["telemetry_summary"]["route_status"] == "SUCCESS"
    assert data["risk_assessment"]["risk_vector"]["route_anomaly"] is not None


def test_inference_failure_after_persistence_leaves_trip_unverified():
    trip_id = "trip-risk-assessment-failure"
    start_response = client.post(
        "/api/v1/telemetry/trips/start",
        json={"trip_id": trip_id},
        headers=auth_headers(),
    )
    assert start_response.status_code == 200

    db = TestingSessionLocal()
    try:
        db.add(
            TelemetryRecord(
                version="0.1",
                device_id=TEST_DEVICE_ID,
                trip_id=trip_id,
                timestamp=datetime(2026, 9, 26, 17, 0, 0, tzinfo=timezone.utc),
                latitude=28.6139,
                longitude=77.2090,
                accuracy_meters=5.0,
                accelerometer_x=0.0,
                accelerometer_y=9.81,
                accelerometer_z=0.0,
                battery_level=0.9,
                network_status="WIFI",
            )
        )
        db.commit()
    finally:
        db.close()

    with patch(
        "backend.app.routers.telemetry.RiskService.evaluate_telemetry",
        side_effect=RuntimeError("test inference failure"),
    ):
        response = client.post(
            "/api/v1/telemetry/trips/complete",
            json={"trip_id": trip_id},
            headers=auth_headers(),
        )

    assert response.status_code == 200
    data = response.json()
    assert data["trip_status"] == TripStatus.COMPLETED_UNVERIFIED.value
    assert data["inference_status"] == "FAILED"
    assert data["risk_assessment"] is None

    db = TestingSessionLocal()
    try:
        trip = TripRepository(db).get_trip(trip_id)
        assert trip is not None
        assert trip.status == TripStatus.COMPLETED_UNVERIFIED.value
        assert (
            db.query(TelemetryRecord).filter(TelemetryRecord.trip_id == trip_id).count()
            == 1
        )
    finally:
        db.close()


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
    assert data["inference_status"] == "SKIPPED_CRISIS"
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
    assert res2.json()["inference_status"] == "NOT_RUN"
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

    # A client-provided anomaly flag is not verification evidence.
    res_alter = client.post(
        "/api/v1/telemetry/trips/complete",
        json={"trip_id": trip_id, "anomalous": True},
        headers=auth_headers(),
    )
    assert res_alter.status_code == 200
    assert res_alter.json()["trip_status"] == TripStatus.COMPLETED_UNVERIFIED.value

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


# ---------------------------------------------------------------------------
# GenAI Briefing Endpoint & Multi-Window Coverage Policy Tests
# ---------------------------------------------------------------------------


def test_trip_briefing_successful_and_guardrail_verified():
    trip_id = "trip-genai-briefing-success"

    client.post(
        "/api/v1/telemetry/trips/start",
        json={"trip_id": trip_id},
        headers=auth_headers(),
    )

    db = TestingSessionLocal()
    try:
        t0 = datetime.now(timezone.utc) - timedelta(seconds=10)
        db.add_all(
            [
                TelemetryRecord(
                    version="0.1",
                    device_id=TEST_DEVICE_ID,
                    trip_id=trip_id,
                    timestamp=t0 + timedelta(seconds=i * 2),
                    latitude=28.6139 + (i * 0.0001),
                    longitude=77.2090 + (i * 0.0001),
                    accuracy_meters=4.0,
                    speed_mps=1.2,
                    accelerometer_x=0.0,
                    accelerometer_y=9.81,
                    accelerometer_z=0.1,
                    battery_level=0.85,
                    network_status="WIFI",
                )
                for i in range(5)
            ]
        )
        db.commit()
    finally:
        db.close()

    response = client.post(
        f"/api/v1/telemetry/trips/{trip_id}/briefing",
        json={"audience": "USER", "user_display_name": "Alice"},
        headers=auth_headers(),
    )

    assert response.status_code == 200
    data = response.json()
    assert data["risk_level"] in ("NORMAL", "UNUSUAL")
    assert data["audience"] == "USER"
    assert "Alice" in data["summary"]
    assert "acoustic" in data["missing_evidence"]
    assert data["source"] == "deterministic_template"
    assert len(data["limitations_disclaimer"]) > 0


def test_trip_briefing_cross_user_rejected_403():
    trip_id = "trip-genai-cross-user"

    client.post(
        "/api/v1/telemetry/trips/start",
        json={"trip_id": trip_id},
        headers=auth_headers("device_owner_a"),
    )

    # User B requests User A's briefing -> 403 Forbidden
    response = client.post(
        f"/api/v1/telemetry/trips/{trip_id}/briefing",
        headers=auth_headers("device_intruder_b"),
    )
    assert response.status_code == 403
    assert "does not belong to authenticated user" in response.json()["detail"]


def test_trip_briefing_unknown_trip_returns_404():
    response = client.post(
        "/api/v1/telemetry/trips/trip-nonexistent-999/briefing",
        headers=auth_headers(),
    )
    assert response.status_code == 404
    assert "not found" in response.json()["detail"]


def test_trip_briefing_missing_authentication_rejected_401():
    response = client.post(
        "/api/v1/telemetry/trips/trip-any/briefing",
    )
    assert response.status_code == 401


def test_trip_briefing_trusted_contact_audience():
    trip_id = "trip-genai-trusted-contact"

    client.post(
        "/api/v1/telemetry/trips/start",
        json={"trip_id": trip_id},
        headers=auth_headers(),
    )

    response = client.post(
        f"/api/v1/telemetry/trips/{trip_id}/briefing",
        json={"audience": "TRUSTED_CONTACT", "user_display_name": "Bob"},
        headers=auth_headers(),
    )
    assert response.status_code == 200
    data = response.json()
    assert data["audience"] == "TRUSTED_CONTACT"
    assert "Bob" in data["headline"] or "Bob" in data["summary"]


def test_complete_trip_with_sufficient_multi_window_coverage_becomes_completed_normal():
    """
    When an active trip has:
    1. >= 10 records
    2. Duration >= 30 seconds
    3. >= 5 historical COMPLETED_NORMAL reference trips
    4. Valid normal motion (SUCCESS) and valid normal route (SUCCESS)
    The trip satisfies multi-window coverage and transitions to COMPLETED_NORMAL.
    """
    trip_id = "trip-full-coverage-normal"
    user_id = pseudonymize_identifier(TEST_DEVICE_ID, SECRET_KEY)
    t0 = datetime(2026, 10, 20, 10, 0, 0, tzinfo=timezone.utc)

    db = TestingSessionLocal()
    try:
        repo = TripRepository(db)
        # Create 5 historical COMPLETED_NORMAL trips along the identical corridor
        for h in range(5):
            hist_id = f"{trip_id}-hist-{h}"
            hist_start = t0 - timedelta(days=5 - h)
            repo.create_trip(
                trip_id=hist_id,
                user_id=user_id,
                started_at=hist_start,
                status=TripStatus.INITIALIZED,
            )
            repo.update_trip_status(
                trip_id=hist_id,
                user_id=user_id,
                new_status=TripStatus.ACTIVE,
            )
            repo.update_trip_status(
                trip_id=hist_id,
                user_id=user_id,
                new_status=TripStatus.COMPLETED_NORMAL,
                ended_at=hist_start + timedelta(seconds=60),
            )
            # Add trajectory observations for the historical trip
            db.add_all(
                [
                    TelemetryRecord(
                        version="0.1",
                        device_id=TEST_DEVICE_ID,
                        trip_id=hist_id,
                        timestamp=hist_start + timedelta(seconds=i * 5),
                        latitude=28.6139 + (i * 0.0001),
                        longitude=77.2090 + (i * 0.0001),
                        accuracy_meters=4.0,
                        speed_mps=1.2,
                        accelerometer_x=0.0,
                        accelerometer_y=9.81,
                        accelerometer_z=0.05,
                        battery_level=0.9,
                        network_status="WIFI",
                    )
                    for i in range(12)
                ]
            )

        # Start the active candidate trip
        repo.create_trip(
            trip_id=trip_id,
            user_id=user_id,
            started_at=t0,
            status=TripStatus.ACTIVE,
        )

        # Add 12 records spanning 55 seconds (exceeding min_records=10 and min_duration=30s)
        db.add_all(
            [
                TelemetryRecord(
                    version="0.1",
                    device_id=TEST_DEVICE_ID,
                    trip_id=trip_id,
                    timestamp=t0 + timedelta(seconds=i * 5),
                    latitude=28.6139 + (i * 0.0001),
                    longitude=77.2090 + (i * 0.0001),
                    accuracy_meters=4.0,
                    speed_mps=1.2,
                    accelerometer_x=0.0,
                    accelerometer_y=9.81,
                    accelerometer_z=0.05,
                    battery_level=0.9,
                    network_status="WIFI",
                )
                for i in range(12)
            ]
        )
        db.commit()
    finally:
        db.close()

    # Complete trip
    response = client.post(
        "/api/v1/telemetry/trips/complete",
        json={"trip_id": trip_id},
        headers=auth_headers(),
    )

    assert response.status_code == 200
    data = response.json()
    assert data["inference_status"] == "COMPLETED"
    assert data["risk_assessment"]["risk_level"] == "NORMAL"
    assert len(data["risk_assessment"]["signals"]) == 0
    # Multi-window coverage satisfied -> transitions to COMPLETED_NORMAL
    assert data["trip_status"] == TripStatus.COMPLETED_NORMAL.value


def test_complete_trip_with_insufficient_duration_remains_completed_unverified():
    """
    Trip has 12 records matching historical corridor perfectly, but duration
    is only 22 seconds (< 30.0s).
    Coverage is not satisfied -> remains COMPLETED_UNVERIFIED.
    """
    trip_id = "trip-short-duration-unverified"
    user_id = pseudonymize_identifier(TEST_DEVICE_ID, SECRET_KEY)
    t0 = datetime(2026, 10, 20, 11, 0, 0, tzinfo=timezone.utc)

    db = TestingSessionLocal()
    try:
        repo = TripRepository(db)
        repo.create_trip(
            trip_id=trip_id,
            user_id=user_id,
            started_at=t0,
            status=TripStatus.ACTIVE,
        )
        # 12 records spaced by 2 seconds -> duration = 22 seconds (< 30s)
        db.add_all(
            [
                TelemetryRecord(
                    version="0.1",
                    device_id=TEST_DEVICE_ID,
                    trip_id=trip_id,
                    timestamp=t0 + timedelta(seconds=i * 2),
                    latitude=28.6139 + (i * 0.0001),
                    longitude=77.2090 + (i * 0.0001),
                    accuracy_meters=4.0,
                    speed_mps=1.2,
                    accelerometer_x=0.0,
                    accelerometer_y=9.81,
                    accelerometer_z=0.05,
                    battery_level=0.9,
                    network_status="WIFI",
                )
                for i in range(12)
            ]
        )
        db.commit()
    finally:
        db.close()

    response = client.post(
        "/api/v1/telemetry/trips/complete",
        json={"trip_id": trip_id},
        headers=auth_headers(),
    )

    assert response.status_code == 200
    data = response.json()
    assert data["inference_status"] == "COMPLETED"
    assert data["risk_assessment"]["risk_level"] == "NORMAL"
    assert len(data["risk_assessment"]["signals"]) == 0
    # Unverified coverage -> remains COMPLETED_UNVERIFIED
    assert data["trip_status"] == TripStatus.COMPLETED_UNVERIFIED.value


def test_coverage_rejected_when_observation_gap_exceeds_threshold():
    """
    Trip has 12 valid records and spans 50 seconds (> 30s), but contains
    a 20-second gap between observations (> MAX_PERMITTED_OBSERVATION_GAP_SECONDS=15s).
    Coverage is not satisfied -> remains COMPLETED_UNVERIFIED.
    """
    trip_id = "trip-gap-exceeded-unverified"
    user_id = pseudonymize_identifier(TEST_DEVICE_ID, SECRET_KEY)
    t0 = datetime(2026, 10, 20, 12, 0, 0, tzinfo=timezone.utc)

    # Offsets in seconds with a 20s gap between 12s and 32s
    offsets = [0, 3, 6, 9, 12, 32, 35, 38, 41, 44, 47, 50]

    db = TestingSessionLocal()
    try:
        repo = TripRepository(db)
        repo.create_trip(
            trip_id=trip_id,
            user_id=user_id,
            started_at=t0,
            status=TripStatus.ACTIVE,
        )
        db.add_all(
            [
                TelemetryRecord(
                    version="0.1",
                    device_id=TEST_DEVICE_ID,
                    trip_id=trip_id,
                    timestamp=t0 + timedelta(seconds=offsets[i]),
                    latitude=28.6139 + (i * 0.0001),
                    longitude=77.2090 + (i * 0.0001),
                    accuracy_meters=4.0,
                    speed_mps=1.2,
                    accelerometer_x=0.0,
                    accelerometer_y=9.81,
                    accelerometer_z=0.05,
                    battery_level=0.9,
                    network_status="WIFI",
                )
                for i in range(12)
            ]
        )
        db.commit()
    finally:
        db.close()

    response = client.post(
        "/api/v1/telemetry/trips/complete",
        json={"trip_id": trip_id},
        headers=auth_headers(),
    )

    assert response.status_code == 200
    data = response.json()
    assert data["inference_status"] == "COMPLETED"
    # Gap exceeded -> remains COMPLETED_UNVERIFIED
    assert data["trip_status"] == TripStatus.COMPLETED_UNVERIFIED.value


def test_coverage_rejected_for_clustered_observations():
    """
    Trip has 12 records along the valid historical corridor, but contains a 30-second
    observation gap between observation 10 (at 30s) and observation 11 (at 60s).
    Total duration is 60 seconds, but the gap exceeds MAX_PERMITTED_OBSERVATION_GAP_SECONDS (15s).
    Coverage is not satisfied -> remains COMPLETED_UNVERIFIED.
    """
    trip_id = "trip-clustered-unverified"
    user_id = pseudonymize_identifier(TEST_DEVICE_ID, SECRET_KEY)
    t0 = datetime(2026, 10, 20, 13, 0, 0, tzinfo=timezone.utc)

    # 11 records spaced by 3s (0s to 30s), then 12th record at 60s (30s gap)
    offsets = [i * 3 for i in range(11)] + [60]

    db = TestingSessionLocal()
    try:
        repo = TripRepository(db)
        repo.create_trip(
            trip_id=trip_id,
            user_id=user_id,
            started_at=t0,
            status=TripStatus.ACTIVE,
        )
        db.add_all(
            [
                TelemetryRecord(
                    version="0.1",
                    device_id=TEST_DEVICE_ID,
                    trip_id=trip_id,
                    timestamp=t0 + timedelta(seconds=offsets[i]),
                    latitude=28.6139 + (i * 0.0001),
                    longitude=77.2090 + (i * 0.0001),
                    accuracy_meters=4.0,
                    speed_mps=1.0,
                    accelerometer_x=0.0,
                    accelerometer_y=9.81,
                    accelerometer_z=0.05,
                    battery_level=0.9,
                    network_status="WIFI",
                )
                for i in range(12)
            ]
        )
        db.commit()
    finally:
        db.close()

    response = client.post(
        "/api/v1/telemetry/trips/complete",
        json={"trip_id": trip_id},
        headers=auth_headers(),
    )

    assert response.status_code == 200
    data = response.json()
    assert data["inference_status"] == "COMPLETED"
    assert data["risk_assessment"]["risk_level"] == "NORMAL"
    assert len(data["risk_assessment"]["signals"]) == 0
    assert data["trip_status"] == TripStatus.COMPLETED_UNVERIFIED.value


def test_coverage_rejected_when_timestamps_are_duplicate():
    """
    Trip has 12 records spanning 35 seconds, but duplicate timestamps leave
    only 6 distinct observation moments (< MIN_VERIFIED_TELEMETRY_RECORDS=10).
    Coverage is not satisfied -> remains COMPLETED_UNVERIFIED.
    """
    trip_id = "trip-duplicate-ts-unverified"
    device_id = "device_dup_ts_test"
    user_id = pseudonymize_identifier(device_id, SECRET_KEY)
    t0 = datetime(2026, 10, 20, 14, 0, 0, tzinfo=timezone.utc)

    db = TestingSessionLocal()
    try:
        repo = TripRepository(db)
        repo.create_trip(
            trip_id=trip_id,
            user_id=user_id,
            started_at=t0,
            status=TripStatus.ACTIVE,
        )
        # 12 records but only 6 unique timestamps (2 records per timestamp)
        db.add_all(
            [
                TelemetryRecord(
                    version="0.1",
                    device_id=device_id,
                    trip_id=trip_id,
                    timestamp=t0 + timedelta(seconds=(i // 2) * 6),
                    latitude=28.6139 + (i * 0.00005),
                    longitude=77.2090 + (i * 0.00005),
                    accuracy_meters=4.0,
                    speed_mps=1.0,
                    accelerometer_x=0.0,
                    accelerometer_y=9.81,
                    accelerometer_z=0.05,
                    battery_level=0.9,
                    network_status="WIFI",
                )
                for i in range(12)
            ]
        )
        db.commit()
    finally:
        db.close()

    response = client.post(
        "/api/v1/telemetry/trips/complete",
        json={"trip_id": trip_id},
        headers=auth_headers(device_id),
    )

    assert response.status_code == 200
    data = response.json()
    assert data["inference_status"] == "COMPLETED"
    assert data["risk_assessment"]["risk_level"] == "NORMAL"
    assert len(data["risk_assessment"]["signals"]) == 0
    assert data["trip_status"] == TripStatus.COMPLETED_UNVERIFIED.value


def test_direct_coverage_eligibility_policy_semantics():
    """
    Unit test verify check_trip_coverage_eligibility directly across edge cases:
    - Non-active trip
    - Detector failure
    - Low confidence
    - Corrupted coordinate values
    - Non-numeric IMU values
    """
    from backend.app.models.trip import Trip
    from backend.app.routers.telemetry import check_trip_coverage_eligibility
    from ai.risk_engine.models import (
        RiskAssessment,
        RiskLevel,
        RecommendedAction,
        RiskVector,
        TelemetrySummary,
        CalibrationMetadata,
    )

    t0 = datetime(2026, 10, 20, 15, 0, 0, tzinfo=timezone.utc)

    mock_trip = Trip(
        trip_id="mock-trip",
        user_id="usr_123",
        status=TripStatus.ACTIVE.value,
        started_at=t0,
    )

    nominal_summary = TelemetrySummary(
        speed_mps=1.0,
        corridor_deviation_meters=0.0,
        motion_state="still",
        motion_status="SUCCESS",
        route_status="SUCCESS",
    )

    nominal_assessment = RiskAssessment(
        user_id="usr_123",
        risk_level=RiskLevel.NORMAL,
        confidence=0.88,
        signals=(),
        location_status="available",
        recommended_action=RecommendedAction.NONE,
        risk_vector=RiskVector(kinematic_anomaly=0.0, route_anomaly=0.0),
        telemetry_summary=nominal_summary,
        calibration_metadata=CalibrationMetadata(method="deterministic_heuristic"),
    )

    valid_records = [
        {
            "timestamp": t0 + timedelta(seconds=i * 4),
            "latitude": 28.6139,
            "longitude": 77.2090,
            "accelerometer_x": 0.0,
            "accelerometer_y": 9.81,
            "accelerometer_z": 0.0,
        }
        for i in range(11)  # 11 records spanning 40s with 4s gaps
    ]

    # Nominal: should pass
    assert check_trip_coverage_eligibility(mock_trip, valid_records, nominal_assessment) is True

    # 1. Non-active trip rejects
    inactive_trip = Trip(trip_id="mock-trip", user_id="usr_123", status=TripStatus.INITIALIZED.value, started_at=t0)
    assert check_trip_coverage_eligibility(inactive_trip, valid_records, nominal_assessment) is False

    # 2. Detector failure in route status rejects
    failed_route_summary = TelemetrySummary(
        speed_mps=1.0,
        corridor_deviation_meters=None,
        motion_state="still",
        motion_status="SUCCESS",
        route_status="COMPUTATION_ERROR",
    )
    failed_route_assessment = RiskAssessment(
        user_id="usr_123",
        risk_level=RiskLevel.UNUSUAL,
        confidence=0.35,
        signals=(),
        location_status="unavailable",
        recommended_action=RecommendedAction.MONITOR,
        risk_vector=RiskVector(),
        telemetry_summary=failed_route_summary,
        calibration_metadata=CalibrationMetadata(method="deterministic_heuristic"),
    )
    assert check_trip_coverage_eligibility(mock_trip, valid_records, failed_route_assessment) is False

    # 3. Confidence < 0.70 rejects
    low_conf_assessment = RiskAssessment(
        user_id="usr_123",
        risk_level=RiskLevel.NORMAL,
        confidence=0.65,  # e.g. clean partial availability
        signals=(),
        location_status="available",
        recommended_action=RecommendedAction.NONE,
        risk_vector=RiskVector(kinematic_anomaly=0.0),
        telemetry_summary=nominal_summary,
        calibration_metadata=CalibrationMetadata(method="deterministic_heuristic"),
    )
    assert check_trip_coverage_eligibility(mock_trip, valid_records, low_conf_assessment) is False

    # 4. Records with invalid latitude (> 90) leaves < 10 valid records
    corrupted_records = list(valid_records)
    for j in range(5):
        corrupted_records[j] = dict(valid_records[j])
        corrupted_records[j]["latitude"] = 999.0
    assert check_trip_coverage_eligibility(mock_trip, corrupted_records, nominal_assessment) is False

    # 5. Records with non-numeric IMU leaves < 10 valid records
    corrupted_imu_records = list(valid_records)
    for j in range(5):
        corrupted_imu_records[j] = dict(valid_records[j])
        corrupted_imu_records[j]["accelerometer_y"] = "corrupted"
    assert check_trip_coverage_eligibility(mock_trip, corrupted_imu_records, nominal_assessment) is False
