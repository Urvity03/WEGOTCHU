"""Safety guardrails and post-generation validators for GenAI outputs."""

from __future__ import annotations

import re
from typing import Any

from ai.genai.schemas import GenAIBriefingRequest, GenAIBriefingResponse

STANDARD_SAFETY_DISCLAIMER: str = (
    "WEGOTCHU Safety Notice: Automated assessment based on available mobile telemetry. "
    "This indicator is not an infallible guarantee of safety or emergency diagnosis."
)

PROHIBITED_CLAIM_PATTERNS = [
    re.compile(r"\b(guarantee(s|d)?\s+safe(ty)?)\b", re.IGNORECASE),
    re.compile(r"\b(diagnos(e|is|ed))\b", re.IGNORECASE),
    re.compile(r"\b(medical\s+emergency\s+confirmed)\b", re.IGNORECASE),
    re.compile(r"\b(police\s+dispatched)\b", re.IGNORECASE),
]


class GenAIGuardrailViolation(Exception):
    """Raised when an LLM generation violates non-negotiable safety guardrails."""


def enforce_briefing_guardrails(
    request: GenAIBriefingRequest,
    raw_response: dict[str, Any] | GenAIBriefingResponse,
    fallback_on_violation: bool = True,
) -> GenAIBriefingResponse:
    """
    Enforce deterministic supremacy, evidence disclosure, and claim restrictions.

    Invariants:
      1. Deterministic Supremacy: The output risk_level and recommended_action
         CANNOT be modified by the LLM. If the generated text deviates, it is
         forced back to the authoritative deterministic state.
      2. Missing Evidence Transparency: Any missing modalities must remain
         explicitly disclosed in missing_evidence.
      3. Prohibited Claim Sanitization: False guarantees or medical diagnoses
         are strictly rejected or stripped.
    """
    if isinstance(raw_response, GenAIBriefingResponse):
        resp_data = raw_response.model_dump()
    else:
        resp_data = dict(raw_response)

    # Invariant 1: Force authoritative risk_level and recommended_action
    resp_data["risk_level"] = request.risk_level
    resp_data["recommended_action"] = request.recommended_action
    resp_data["audience"] = request.audience
    resp_data["active_signals"] = list(request.signals)
    resp_data["missing_evidence"] = list(request.missing_modalities)
    resp_data["limitations_disclaimer"] = STANDARD_SAFETY_DISCLAIMER

    summary_text = str(resp_data.get("summary", ""))
    headline_text = str(resp_data.get("headline", ""))

    # Invariant 2: Prohibited claims check
    has_prohibited = any(
        pattern.search(summary_text) or pattern.search(headline_text)
        for pattern in PROHIBITED_CLAIM_PATTERNS
    )

    if has_prohibited:
        if not fallback_on_violation:
            raise GenAIGuardrailViolation(
                "LLM generation contained prohibited medical, dispatch, or safety guarantee claims."
            )
        # Sanitize summary by neutralizing prohibited guarantees
        for pattern in PROHIBITED_CLAIM_PATTERNS:
            summary_text = pattern.sub("[claim omitted by safety policy]", summary_text)
        resp_data["summary"] = summary_text

    return GenAIBriefingResponse.model_validate(resp_data)
