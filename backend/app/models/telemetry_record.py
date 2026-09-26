from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base


class TelemetryRecord(Base):
    __tablename__ = "telemetry_records"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    version: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    device_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )

    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )

    latitude: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    longitude: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    altitude_meters: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    accuracy_meters: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    speed_mps: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    bearing_degrees: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    accelerometer_x: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    accelerometer_y: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    accelerometer_z: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    gyroscope_x: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    gyroscope_y: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    gyroscope_z: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    battery_level: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    network_status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )
