from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.auth import create_access_token


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

    assert response.status_code == 403


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