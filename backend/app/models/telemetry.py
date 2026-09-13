from datetime import datetime

from pydantic import BaseModel, Field


class Location(BaseModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    altitude_meters: float | None = None
    accuracy_meters: float = Field(ge=0)


class Accelerometer(BaseModel):
    x: float
    y: float
    z: float


class Gyroscope(BaseModel):
    x: float
    y: float
    z: float


class TelemetryPayload(BaseModel):
    version: str
    device_id: str
    timestamp: datetime
    location: Location
    speed_mps: float | None = Field(default=None, ge=0)
    bearing_degrees: float | None = Field(default=None, ge=0, lt=360)
    accelerometer: Accelerometer
    gyroscope: Gyroscope
    battery_level: float = Field(ge=0.0, le=1.0)
    network_status: str
