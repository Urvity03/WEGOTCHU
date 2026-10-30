"""Domain models and schemas for the WEGOTCHU Risk Estimation Engine."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

SCHEMA_URI: str = "https://json-schema.org/draft/2020-12/schema"
CONTRACT_VERSION: str = "0.1"


class RiskLevel(str, Enum):
    """
    Standardized 5-tier risk levels from docs/architecture/ai-architecture.md.

    Operational Semantics:
      - NORMAL: Behavior aligns with personal baseline. Passive background monitoring.
      - UNUSUAL: Minor statistical deviation. Background logging; silent monitoring.
      - ELEVATED: Moderate sustained deviation / co-occurring anomalies. Discreet user check-in.
      - HIGH: Multi-signal divergence or unacknowledged ELEVATED check-in. Cancellation countdown.
      - EMERGENCY: Confirmed crisis, manual SOS, or expired countdown. Automated dispatch.
    """

    NORMAL = "NORMAL"
    UNUSUAL = "UNUSUAL"
    ELEVATED = "ELEVATED"
    HIGH = "HIGH"
    EMERGENCY = "EMERGENCY"


class RecommendedAction(str, Enum):
    """Standardized intervention actions from docs/architecture/ai-architecture.md."""

    NONE = "NONE"
    MONITOR = "MONITOR"
    USER_CHECK = "USER_CHECK"
    PRE_ALERT = "PRE_ALERT"
    DISPATCH_EMERGENCY = "DISPATCH_EMERGENCY"


@dataclass(frozen=True)
class RiskVector:
    """
    Component risk scores contributing to the overall evaluation.

    Each metric is bounded in [0.0, 1.0], or None when telemetry for that
    modality is missing or insufficient (e.g. cold start).
    """

    kinematic_anomaly: float | None = None
    route_anomaly: float | None = None
    acoustic_anomaly: float | None = None
    temporal_persistence: float | None = None

    def __post_init__(self) -> None:
        for name, val in [
            ("kinematic_anomaly", self.kinematic_anomaly),
            ("route_anomaly", self.route_anomaly),
            ("acoustic_anomaly", self.acoustic_anomaly),
            ("temporal_persistence", self.temporal_persistence),
        ]:
            if val is not None and not (0.0 <= val <= 1.0):
                raise ValueError(f"{name} must be bounded in [0.0, 1.0], got {val}")


@dataclass(frozen=True)
class TelemetrySummary:
    """Summary of raw or intermediate telemetry supporting the risk assessment."""

    speed_mps: float | None = None
    corridor_deviation_meters: float | None = None
    motion_state: str = "unknown"
    acoustic_anomaly_score: float | None = None
    motion_status: str = "UNAVAILABLE"
    route_status: str = "UNAVAILABLE"


@dataclass(frozen=True)
class CalibrationMetadata:
    """Confidence calibration metadata."""

    method: str = "deterministic_heuristic"
    raw_score: float | None = None
    calibrated_score: float | None = None


@dataclass(frozen=True)
class RiskAssessment:
    """
    Authoritative structured output from the Risk Estimation Engine.

    Conforms to Contract 4 (Version 0.1) from docs/architecture/data-flow.md
    and docs/architecture/ai-architecture.md §3.
    """

    user_id: str
    risk_level: RiskLevel
    confidence: float
    signals: tuple[str, ...]
    location_status: str
    recommended_action: RecommendedAction
    risk_vector: RiskVector
    telemetry_summary: TelemetrySummary = field(default_factory=TelemetrySummary)
    calibration_metadata: CalibrationMetadata = field(
        default_factory=CalibrationMetadata
    )
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    version: str = CONTRACT_VERSION
    schema: str = SCHEMA_URI

    def __post_init__(self) -> None:
        if not (0.0 <= self.confidence <= 1.0):
            raise ValueError(f"confidence must be in [0.0, 1.0], got {self.confidence}")
        if not isinstance(self.risk_level, RiskLevel):
            raise TypeError(
                f"risk_level must be a RiskLevel Enum, got {type(self.risk_level).__name__}"
            )
        if not isinstance(self.recommended_action, RecommendedAction):
            raise TypeError(
                f"recommended_action must be a RecommendedAction Enum, got {type(self.recommended_action).__name__}"
            )

    def to_dict(self, include_extended_metadata: bool = False) -> dict[str, Any]:
        """
        Convert assessment into Contract 4 JSON-serializable dictionary.

        By default (include_extended_metadata=False), this serializes precisely the
        10 fields mandated by Contract 4 in docs/architecture/data-flow.md without
        inventing root-level keys.

        When include_extended_metadata=True, adds telemetry_summary and calibration_metadata
        specified in docs/architecture/ai-architecture.md §3.
        """
        payload: dict[str, Any] = {
            "$schema": self.schema,
            "version": self.version,
            "user_id": self.user_id,
            "timestamp": self.timestamp,
            "risk_level": self.risk_level.value,
            "confidence": round(self.confidence, 4),
            "signals": list(self.signals),
            "location_status": self.location_status,
            "recommended_action": self.recommended_action.value,
            "risk_vector": asdict(self.risk_vector),
        }
        if include_extended_metadata:
            payload["telemetry_summary"] = asdict(self.telemetry_summary)
            payload["calibration_metadata"] = asdict(self.calibration_metadata)
        return payload

    def to_contract4_dict(self) -> dict[str, Any]:
        """Convert assessment into strict Contract 4 JSON dictionary (exact 10 fields)."""
        return self.to_dict(include_extended_metadata=False)

    def to_architecture_dict(self) -> dict[str, Any]:
        """Convert assessment into ai-architecture.md §3 structured output dictionary."""
        return {
            "risk_level": self.risk_level.value,
            "confidence": round(self.confidence, 4),
            "signals": list(self.signals),
            "timestamp": self.timestamp,
            "location_status": self.location_status,
            "recommended_action": self.recommended_action.value,
            "telemetry_summary": asdict(self.telemetry_summary),
            "calibration_metadata": asdict(self.calibration_metadata),
        }
