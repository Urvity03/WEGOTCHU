from fastapi import APIRouter

from ..models.telemetry import TelemetryPayload

router = APIRouter(prefix="/api/v1", tags=["telemetry"])


@router.post("/telemetry")
async def receive_telemetry(payload: TelemetryPayload):
    return {
        "status": "accepted",
        "message": "Telemetry received successfully",
        "device_id": payload.device_id,
    }
