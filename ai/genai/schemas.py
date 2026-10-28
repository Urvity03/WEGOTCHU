"""Pydantic schemas and data contracts for GenAI Communication Layer."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field, field_validator


class BriefingAudience(str, Enum):
    """Target audience for safety briefings."""

    USER = "USER"
    TRUSTED_CONTACT = "TRUSTED_CONTACT"
    DISPATCHER = "DISPATCHER"


class GenAIBriefingRequest(BaseModel):
    """
    Structured input for GenAI explanation synthesis.

    Guarantees:
      - Raw coordinates (latitude/longitude) are strictly excluded from LLM context.
      - Device secrets and raw hardware IDs are disallowed.
      - Authoritative risk_level and signals originate from deterministic RiskAssessment.
    """

    risk_level: str = Field(description="Authoritative risk state from RiskAssessment")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence score [0.0, 1.0]")
    signals: tuple[str, ...] = Field(
        default_factory=tuple,
        description="Active anomaly signal identifiers",
    )
    location_status: str = Field(default="available")
    available_modalities: tuple[str, ...] = Field(default_factory=tuple)
    missing_modalities: tuple[str, ...] = Field(default_factory=tuple)
    motion_state: str = Field(default="unknown")
    corridor_deviation_meters: float | None = Field(default=None, ge=0.0)
    speed_mps: float | None = Field(default=None, ge=0.0)
    recommended_action: str = Field(default="NONE")
    audience: BriefingAudience = Field(default=BriefingAudience.USER)
    user_display_name: str = Field(default="User", max_length=64)

    @field_validator("user_display_name")
    @classmethod
    def sanitize_name(cls, value: str) -> str:
        clean = value.strip()
        if not clean:
            return "User"
        # Prevent prompt injection delimiters in display names
        for char in ("\n", "\r", "<", ">", "{", "}"):
            clean = clean.replace(char, "")
        return clean or "User"


class GenAIBriefingResponse(BaseModel):
    """
    Validated safety briefing output.

    Safety Invariant:
      - risk_level MUST match the authoritative input risk level.
      - Missing evidence and system limitations must be explicitly disclosed.
    """

    headline: str = Field(description="Concise summary header")
    summary: str = Field(description="Empathetic, clear, and factual briefing text")
    audience: BriefingAudience = Field(description="Target audience")
    risk_level: str = Field(description="Immutable authoritative risk level")
    recommended_action: str = Field(description="Deterministic action directive")
    active_signals: list[str] = Field(default_factory=list)
    missing_evidence: list[str] = Field(default_factory=list)
    limitations_disclaimer: str = Field(description="Standardized safety disclaimer")
    source: str = Field(
        default="deterministic_template",
        description="Generation source: deterministic_template or llm_verified",
    )
