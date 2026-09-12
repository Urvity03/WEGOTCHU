from fastapi.testclient import TestClient

from backend.app.main import app

client = TestClient(app)


def test_status():
    response = client.get("/api/v1/status")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_valid_telemetry():
    payload = {
        "version": "0.1",
        "device_id": "usr_dev_test",
        "timestamp": "2026-09-11T23:14:00Z",
        "location": {
            "latitude": 37.774929,
            "longitude": -122.419416,
            "altitude_meters": 16.4,
            "accuracy_meters": 4.2,
        },
        "speed_mps": 1.45,
        "bearing_degrees": 182.5,
        "accelerometer": {
            "x": 0.12,
            "y": 9.78,
            "z": 1.05,
        },
        "gyroscope": {
            "x": 0.01,
            "y": -0.04,
            "z": 0.02,
        },
        "battery_level": 0.68,
        "network_status": "CELLULAR_4G",
    }

    response = client.post("/api/v1/telemetry", json=payload)

    assert response.status_code == 200
    assert response.json()["status"] == "accepted"
    assert response.json()["device_id"] == "usr_dev_test"


def test_invalid_latitude():
    payload = {
        "version": "0.1",
        "device_id": "usr_dev_test",
        "timestamp": "2026-09-11T23:14:00Z",
        "location": {
            "latitude": 200,
            "longitude": -74.0,
            "altitude_meters": 10,
            "accuracy_meters": 5,
        },
        "speed_mps": 1.0,
        "bearing_degrees": 180,
        "accelerometer": {
            "x": 0.1,
            "y": 9.8,
            "z": 1.0,
        },
        "gyroscope": {
            "x": 0.01,
            "y": 0.02,
            "z": 0.03,
        },
        "battery_level": 0.5,
        "network_status": "CELLULAR_4G",
    }

    response = client.post("/api/v1/telemetry", json=payload)

    assert response.status_code == 422
