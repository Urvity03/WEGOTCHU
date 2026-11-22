"""
Perception Router for WEGOTCHU (Member 4 Audio & Computer Vision Integration).

Provides secure, authenticated endpoints for edge perception:
  - Ephemeral Audio Distress Inference: Analyzes short microphone buffers for acoustic anomalies.
  - Ephemeral Camera Frame Scene Analysis: Computes ambient illumination and edge density.

Privacy Invariants:
  - Raw audio waveforms and camera frames are processed in-memory ephemerally.
  - No continuous audio/video streaming or long-term disk persistence.
"""

from __future__ import annotations

import logging
import os
import tempfile

import cv2
import numpy as np
from fastapi import APIRouter, Depends, HTTPException, UploadFile, status

from backend.app.auth import get_current_user_id
from perception.audio.src.inference import run_audio_inference
from perception.vision.src.inference import analyze_frame

router = APIRouter(prefix="/api/v1/perception", tags=["perception"])
logger = logging.getLogger(__name__)


@router.post("/audio/infer")
async def infer_audio_distress(
    file: UploadFile,
    current_user_id: str = Depends(get_current_user_id),
):
    """
    Run ephemeral acoustic distress perception on an uploaded audio sample.

    Strictly ephemeral: temporary file is immediately deleted after feature extraction.
    """
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Audio file must have a valid filename.",
        )

    # Read bytes into memory
    content = await file.read()
    if not content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded audio file is empty.",
        )

    # Use an ephemeral temp file for audio loader
    suffix = os.path.splitext(file.filename)[1] or ".wav"
    temp_fd, temp_path = tempfile.mkstemp(suffix=suffix)
    try:
        with os.fdopen(temp_fd, "wb") as f:
            f.write(content)

        result = run_audio_inference(file_path=temp_path)
        return {
            "status": "success",
            "audio_signal": result,
        }
    except Exception as exc:
        logger.exception("Audio inference failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Audio inference failed: {exc}",
        ) from exc
    finally:
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except OSError:
                pass


@router.post("/vision/analyze")
async def analyze_camera_frame(
    file: UploadFile,
    current_user_id: str = Depends(get_current_user_id),
):
    """
    Run ephemeral camera frame scene analysis (Contract 3).

    Strictly in-memory: bytes decoded directly to numpy BGR array.
    Zero disk storage — complies with docs/safety/privacy.md.
    """
    content = await file.read()
    if not content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded image frame is empty.",
        )

    # Decode in-memory BGR array
    np_arr = np.frombuffer(content, np.uint8)
    frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

    if frame is None or frame.size == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unable to decode image frame from provided bytes.",
        )

    try:
        analysis = analyze_frame(frame)
        return {
            "status": "success",
            "vision_analysis": analysis,
        }
    except Exception as exc:
        logger.exception("Vision frame analysis failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Frame analysis failed: {exc}",
        ) from exc
