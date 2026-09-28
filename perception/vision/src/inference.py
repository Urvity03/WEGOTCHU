import cv2
import numpy as np


def analyze_frame(frame: np.ndarray) -> dict:
    """
    Analyze a single camera frame in memory.

    The frame is used only for ephemeral perception.
    No facial recognition, identity tracking, or frame storage
    is performed.
    """
    frame = np.asarray(frame)

    if frame.size == 0:
        raise ValueError("Frame is empty.")

    if not np.all(np.isfinite(frame)):
        raise ValueError("Frame contains NaN or Inf values.")

    if frame.ndim != 3 or frame.shape[2] != 3:
        raise ValueError("Frame must have shape (height, width, 3).")

    gray = cv2.cvtColor(frame.astype(np.uint8), cv2.COLOR_BGR2GRAY)

    illumination = float(np.mean(gray)) / 255.0

    # Basic visual activity/context signal based on edge density.
    edges = cv2.Canny(gray, 100, 200)
    activity = float(np.count_nonzero(edges)) / float(edges.size)

    return {
        "illumination_score": float(np.clip(illumination, 0.0, 1.0)),
        "scene_activity_score": float(np.clip(activity, 0.0, 1.0)),
        "frame_processed_ephemerally": True,
    }
