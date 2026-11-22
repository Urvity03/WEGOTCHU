"""
Unit tests for perception router (Member 4 Audio & Computer Vision API endpoints).
"""

import io
import wave
import cv2
import numpy as np
import pytest
from fastapi.testclient import TestClient

from backend.app.auth import create_access_token
from backend.app.main import app

client = TestClient(app)
TEST_DEVICE = "dev_perception_test"


def auth_headers():
    token = create_access_token(TEST_DEVICE)
    return {"Authorization": f"Bearer {token}"}


def make_test_wav_bytes(
    duration_seconds: float = 1.0, sample_rate: int = 16000
) -> bytes:
    """Generate in-memory WAV audio bytes for testing."""
    num_samples = int(duration_seconds * sample_rate)
    t = np.linspace(0, duration_seconds, num_samples, endpoint=False)
    # Generate 440 Hz tone with some amplitude
    audio = (0.2 * np.sin(2 * np.pi * 440 * t) * 32767).astype(np.int16)

    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(audio.tobytes())
    return buf.getvalue()


def make_test_image_bytes(width: int = 100, height: int = 100) -> bytes:
    """Generate in-memory PNG image bytes for testing."""
    # Create simple checkerboard image
    img = np.zeros((height, width, 3), dtype=np.uint8)
    img[: height // 2, : width // 2] = 200
    img[height // 2 :, width // 2 :] = 200
    success, encoded = cv2.imencode(".png", img)
    assert success
    return encoded.tobytes()


def test_vision_analyze_requires_auth():
    img_bytes = make_test_image_bytes()
    resp = client.post(
        "/api/v1/perception/vision/analyze",
        files={"file": ("frame.png", img_bytes, "image/png")},
    )
    assert resp.status_code == 401


def test_vision_analyze_success():
    img_bytes = make_test_image_bytes()
    resp = client.post(
        "/api/v1/perception/vision/analyze",
        files={"file": ("frame.png", img_bytes, "image/png")},
        headers=auth_headers(),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    analysis = data["vision_analysis"]
    assert analysis["version"] == "0.1"
    assert "ambient_lux" in analysis
    assert "edge_density_score" in analysis
    assert analysis["frame_processed_ephemerally"] is True
    assert analysis["scene_type"] in ("poorly_lit", "moderately_lit", "well_lit")


def test_vision_analyze_empty_file_rejected():
    resp = client.post(
        "/api/v1/perception/vision/analyze",
        files={"file": ("frame.png", b"", "image/png")},
        headers=auth_headers(),
    )
    assert resp.status_code == 400


def test_audio_infer_requires_auth():
    wav_bytes = make_test_wav_bytes()
    resp = client.post(
        "/api/v1/perception/audio/infer",
        files={"file": ("audio.wav", wav_bytes, "audio/wav")},
    )
    assert resp.status_code == 401


def test_audio_infer_success():
    wav_bytes = make_test_wav_bytes()
    resp = client.post(
        "/api/v1/perception/audio/infer",
        files={"file": ("audio.wav", wav_bytes, "audio/wav")},
        headers=auth_headers(),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    signal = data["audio_signal"]
    assert "audio_distress_score" in signal
    assert "confidence" in signal
    assert "detected_class" in signal
    assert 0.0 <= signal["audio_distress_score"] <= 1.0


def test_audio_infer_empty_file_rejected():
    resp = client.post(
        "/api/v1/perception/audio/infer",
        files={"file": ("audio.wav", b"", "audio/wav")},
        headers=auth_headers(),
    )
    assert resp.status_code == 400
