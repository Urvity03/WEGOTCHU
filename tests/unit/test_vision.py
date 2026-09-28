import numpy as np
import pytest

from perception.vision.src.inference import analyze_frame


def test_analyze_frame():
    frame = np.zeros((100, 100, 3), dtype=np.uint8)

    result = analyze_frame(frame)

    assert 0.0 <= result["illumination_score"] <= 1.0
    assert 0.0 <= result["scene_activity_score"] <= 1.0
    assert result["frame_processed_ephemerally"] is True


def test_analyze_frame_rejects_empty_frame():
    frame = np.array([])

    with pytest.raises(ValueError, match="Frame is empty"):
        analyze_frame(frame)


def test_analyze_frame_rejects_invalid_shape():
    frame = np.zeros((100, 100), dtype=np.uint8)

    with pytest.raises(ValueError, match="shape"):
        analyze_frame(frame)


def test_analyze_frame_rejects_non_finite_values():
    frame = np.zeros((100, 100, 3), dtype=np.float32)
    frame[0, 0, 0] = np.nan

    with pytest.raises(ValueError, match="NaN or Inf"):
        analyze_frame(frame)
