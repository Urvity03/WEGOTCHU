import numpy as np
import pytest


from perception.vision.src.inference import analyze_frame


def test_black_frame():
    frame = np.zeros((100, 100, 3), dtype=np.uint8)

    result = analyze_frame(frame)

    assert result["scene_type"] == "poorly_lit"
    assert result["ambient_lux"] == 0.0
    assert result["optical_flow_magnitude"] == 0.0
    assert result["estimated_crowd_density"] == "unknown"


def test_white_frame():
    frame = np.full((100, 100, 3), 255, dtype=np.uint8)

    result = analyze_frame(frame)

    assert result["scene_type"] == "well_lit"
    assert result["ambient_lux"] == 100.0


def test_mid_gray_frame():
    frame = np.full((100, 100, 3), 128, dtype=np.uint8)

    result = analyze_frame(frame)

    assert result["scene_type"] == "moderately_lit"
    assert 0.0 < result["ambient_lux"] < 100.0


def test_high_contrast_image_has_edge_density():
    frame = np.zeros((100, 100, 3), dtype=np.uint8)
    frame[:, 50:] = 255

    result = analyze_frame(frame)

    assert result["edge_density_score"] > 0.0


def test_normalized_float_frame():
    frame = np.ones((100, 100, 3), dtype=np.float32)

    result = analyze_frame(frame)

    assert result["scene_type"] == "well_lit"
    assert result["ambient_lux"] == 100.0


def test_invalid_negative_pixel_values():
    frame = np.zeros((100, 100, 3), dtype=np.float32)
    frame[0, 0, 0] = -0.1

    with pytest.raises(ValueError, match="range"):
        analyze_frame(frame)


def test_invalid_float_pixel_values_above_one():
    frame = np.zeros((100, 100, 3), dtype=np.float32)
    frame[0, 0, 0] = 1.1

    with pytest.raises(ValueError, match="range"):
        analyze_frame(frame)


def test_invalid_integer_pixel_values():
    frame = np.zeros((100, 100, 3), dtype=np.int16)
    frame[0, 0, 0] = 256

    with pytest.raises(ValueError, match="range"):
        analyze_frame(frame)


def test_contract_3_output_schema():
    frame = np.zeros((100, 100, 3), dtype=np.uint8)

    result = analyze_frame(frame)

    required_fields = {
        "version",
        "timestamp",
        "ambient_lux",
        "scene_type",
        "estimated_crowd_density",
        "optical_flow_magnitude",
        "confidence",
    }

    assert required_fields.issubset(result.keys())
    assert result["version"] == "0.1"
    assert isinstance(result["timestamp"], str)
    assert 0.0 <= result["ambient_lux"] <= 100.0
    assert isinstance(result["scene_type"], str)
    assert isinstance(result["estimated_crowd_density"], str)
    assert result["optical_flow_magnitude"] == 0.0
    assert 0.0 <= result["confidence"] <= 1.0
    assert 0.0 <= result["edge_density_score"] <= 1.0
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
