import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.auth import create_access_token
from backend.app.database import Base, get_db
from backend.app.main import app
from backend.app.models.sos_alert import SOSAlert  # noqa: F401

TEST_ENGINE = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
Base.metadata.create_all(bind=TEST_ENGINE)

TestingSessionLocal = sessionmaker(
    bind=TEST_ENGINE,
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


def auth_headers(user_id="sos_test_user"):
    return {"Authorization": f"Bearer {create_access_token(user_id)}"}


def test_create_sos_alert():
    response = client.post(
        "/api/v1/sos",
        json={
            "latitude": 28.6139,
            "longitude": 77.2090,
            "accuracy_meters": 10,
            "note": "Need help",
        },
        headers=auth_headers(),
    )

    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "received"
    assert data["source"] == "manual"
    assert data["latitude"] == pytest.approx(28.6139)
    assert data["longitude"] == pytest.approx(77.2090)
    assert data["notification_status"] == "not_configured"


def test_create_sos_alert_without_location():
    response = client.post(
        "/api/v1/sos",
        json={},
        headers=auth_headers(),
    )

    assert response.status_code == 201
    assert response.json()["latitude"] is None
    assert response.json()["longitude"] is None


def test_create_sos_alert_requires_authentication():
    response = client.post("/api/v1/sos", json={})
    assert response.status_code == 401


@pytest.mark.parametrize(
    "payload",
    [
        {"latitude": 91, "longitude": 10},
        {"latitude": 10, "longitude": 181},
        {"latitude": 10},
        {"longitude": 10},
        {"latitude": 10, "longitude": 20, "accuracy_meters": -1},
        {"unexpected": "value"},
    ],
)
def test_create_sos_alert_rejects_invalid_payload(payload):
    response = client.post(
        "/api/v1/sos",
        json=payload,
        headers=auth_headers(),
    )
    assert response.status_code == 422


def test_user_cannot_read_another_users_sos_alert():
    created = client.post(
        "/api/v1/sos",
        json={},
        headers=auth_headers("user_a"),
    )
    assert created.status_code == 201

    alert_id = created.json()["id"]
    response = client.get(
        f"/api/v1/sos/{alert_id}",
        headers=auth_headers("user_b"),
    )

    assert response.status_code == 404


def test_user_can_read_own_sos_alert():
    created = client.post(
        "/api/v1/sos",
        json={},
        headers=auth_headers("user_c"),
    )
    assert created.status_code == 201

    alert_id = created.json()["id"]
    response = client.get(
        f"/api/v1/sos/{alert_id}",
        headers=auth_headers("user_c"),
    )

    assert response.status_code == 200
    assert response.json()["id"] == alert_id
