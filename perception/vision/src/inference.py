from datetime import datetime, timezone

import cv2
import numpy as np

CONTRACT_VERSION = "0.1"


def _prepare_frame(frame: np.ndarray) -> np.ndarray:
    """Validate and convert a supported frame to uint8 BGR."""
    frame = np.asarray(frame)

    if frame.size == 0:
        raise ValueError("Frame is empty.")

    if frame.ndim != 3 or frame.shape[2] != 3:
        raise ValueError("Frame must have shape (height, width, 3).")

    if not np.all(np.isfinite(frame)):
        raise ValueError("Frame contains NaN or Inf values.")

    if np.issubdtype(frame.dtype, np.integer):
        if np.any(frame < 0) or np.any(frame > 255):
            raise ValueError("Integer frame values must be in the range [0, 255].")

        return frame.astype(np.uint8)

    if np.issubdtype(frame.dtype, np.floating):
        if np.any(frame < 0.0) or np.any(frame > 1.0):
            raise ValueError(
                "Floating-point frame values must be normalized to the range [0, 1]."
            )

        return np.rint(frame * 255.0).astype(np.uint8)

    raise ValueError("Unsupported frame dtype. Use uint8 or floating-point [0, 1].")


def analyze_frame(frame: np.ndarray) -> dict:
    """
    Analyze one camera frame in memory.

    The output follows Contract 3 from docs/architecture/data-flow.md.

    This baseline estimates illumination and static edge density from a
    single frame. It does not perform facial recognition, identity
    tracking, frame storage, crowd detection, or true optical-flow
    measurement.
    """
    frame = _prepare_frame(frame)

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    illumination_score = float(np.mean(gray) / 255.0)

    if illumination_score < 0.20:
        scene_type = "poorly_lit"
    elif illumination_score < 0.70:
        scene_type = "moderately_lit"
    else:
        scene_type = "well_lit"

    edges = cv2.Canny(gray, 100, 200)
    edge_density_score = float(np.count_nonzero(edges) / edges.size)

    confidence = float(np.clip(abs(illumination_score - 0.5) * 2.0, 0.0, 1.0))

    return {
        "version": CONTRACT_VERSION,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "ambient_lux": float(illumination_score * 100.0),
        "scene_type": scene_type,
        "estimated_crowd_density": "unknown",
        "optical_flow_magnitude": 0.0,
        "confidence": confidence,
        "edge_density_score": float(np.clip(edge_density_score, 0.0, 1.0)),
        "frame_processed_ephemerally": True,
    }
