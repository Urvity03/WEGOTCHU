"""GenAI Communication Service with deterministic fallback and safety guardrails."""

from __future__ import annotations

import logging
from typing import Any, Callable

from ai.genai.guardrails import (
    STANDARD_SAFETY_DISCLAIMER,
    enforce_briefing_guardrails,
)
from ai.genai.schemas import (
    BriefingAudience,
    GenAIBriefingRequest,
    GenAIBriefingResponse,
)

logger = logging.getLogger(__name__)


class GenAIBriefingService:
    """
    Synthesizes clear, empathetic, and factual briefings from structured RiskAssessments.

    Safety Principles:
      - Deterministic Fallback: Never blocks core safety logic. Immediately falls
        back to validated deterministic templates if LLM is unavailable or fails.
      - Zero Authority: The LLM NEVER alters risk levels, creates emergency actions,
        or overrides deterministic engine outputs.
    """

    def __init__(
        self,
        llm_provider: Callable[[dict[str, Any]], dict[str, Any]] | None = None,
        timeout_seconds: float = 5.0,
    ) -> None:
        self.llm_provider = llm_provider
        self.timeout_seconds = timeout_seconds

    def synthesize_briefing(
        self,
        request: GenAIBriefingRequest,
    ) -> GenAIBriefingResponse:
        """
        Generate a validated briefing for the specified audience.

        Falls back immediately to deterministic templates if the LLM provider
        is unconfigured or raises an exception.
        """
        if self.llm_provider is not None:
            try:
                raw_result = self.llm_provider(request.model_dump())
                raw_result["source"] = "llm_verified"
                return enforce_briefing_guardrails(request, raw_result)
            except Exception as exc:
                logger.warning(
                    "GenAI LLM provider failed or timed out (%s); engaging deterministic fallback.",
                    type(exc).__name__,
                )

        return self._generate_deterministic_template(request)

    def _generate_deterministic_template(
        self,
        request: GenAIBriefingRequest,
    ) -> GenAIBriefingResponse:
        """Generate a deterministic, rule-based briefing guaranteed to comply with safety contracts."""
        user = request.user_display_name
        risk = request.risk_level.upper()

        if request.audience == BriefingAudience.USER:
            headline, summary = self._template_user(user, risk, request)
        elif request.audience == BriefingAudience.TRUSTED_CONTACT:
            headline, summary = self._template_contact(user, risk, request)
        else:
            headline, summary = self._template_dispatcher(user, risk, request)

        return GenAIBriefingResponse(
            headline=headline,
            summary=summary,
            audience=request.audience,
            risk_level=request.risk_level,
            recommended_action=request.recommended_action,
            active_signals=list(request.signals),
            missing_evidence=list(request.missing_modalities),
            limitations_disclaimer=STANDARD_SAFETY_DISCLAIMER,
            source="deterministic_template",
        )

    def _template_user(
        self,
        user: str,
        risk: str,
        req: GenAIBriefingRequest,
    ) -> tuple[str, str]:
        if risk == "NORMAL":
            return (
                "Transit Normal",
                f"Hello {user}, your active transit matches your normal baseline pattern. Have a safe journey.",
            )
        if risk == "UNUSUAL":
            signals_desc = (
                ", ".join(req.signals) if req.signals else "telemetry pattern"
            )
            return (
                "Monitoring Transit Variation",
                (
                    f"Hello {user}, we noticed a departure in your {signals_desc}. "
                    "WEGOTCHU is continuing silent background monitoring."
                ),
            )
        if risk == "ELEVATED":
            return (
                "Check-in Requested",
                f"{user}, unusual motion and route variation were observed. "
                "Please tap to confirm you are safe.",
            )
        return (
            "Safety Alert Active",
            f"Safety alert state {risk} active. Recommended action: {req.recommended_action}.",
        )

    def _template_contact(
        self,
        user: str,
        risk: str,
        req: GenAIBriefingRequest,
    ) -> tuple[str, str]:
        if risk in ("NORMAL", "UNUSUAL"):
            return (
                f"{user}'s Transit Update",
                f"WEGOTCHU Update: {user}'s Safety Mode is currently active in state {risk}.",
            )
        return (
            f"[Alert] {user} Safety Notice",
            f"WEGOTCHU Alert: {user} has entered {risk} state. Action recommended: {req.recommended_action}.",
        )

    def _template_dispatcher(
        self,
        user: str,
        risk: str,
        req: GenAIBriefingRequest,
    ) -> tuple[str, str]:
        signals = ", ".join(req.signals) if req.signals else "None"
        missing = (
            ", ".join(req.missing_modalities) if req.missing_modalities else "None"
        )
        return (
            f"DISPATCH INCIDENT LOG: {user} ({risk})",
            f"Incident telemetry report for user '{user}'. Risk Level: {risk}. "
            f"Active Signals: [{signals}]. Missing Modalities: [{missing}]. "
            f"Confidence: {req.confidence:.2f}. Directive: {req.recommended_action}.",
        )
