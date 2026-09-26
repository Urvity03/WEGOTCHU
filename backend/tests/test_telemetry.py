from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def valid_payload():
    return {
        "version": "0.1",
        "device_id": "test_device_001",
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


def test_telemetry_endpoint_accepts_valid_payload():
    response = client.post(
        "/api/v1/telemetry",
        json=valid_payload(),
    )

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == "accepted"
    assert data["message"] == "Telemetry received successfully"
    assert data["device_id"] == "test_device_001"


def test_telemetry_endpoint_rejects_missing_body():
    response = client.post(
        "/api/v1/telemetry",
    )

    assert response.status_code == 422


def test_telemetry_endpoint_rejects_invalid_payload():
    payload = valid_payload()

    del payload["device_id"]

    response = client.post(
        "/api/v1/telemetry",
        json=payload,
    )

    assert response.status_code == 422