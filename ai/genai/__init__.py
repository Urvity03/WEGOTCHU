"""GenAI Communication Layer with guardrails and deterministic fallback."""

from ai.genai.guardrails import (
    STANDARD_SAFETY_DISCLAIMER,
    GenAIGuardrailViolation,
    enforce_briefing_guardrails,
)
from ai.genai.schemas import (
    BriefingAudience,
    GenAIBriefingRequest,
    GenAIBriefingResponse,
)
from ai.genai.service import GenAIBriefingService

__all__ = [
    "BriefingAudience",
    "GenAIBriefingRequest",
    "GenAIBriefingResponse",
    "GenAIBriefingService",
    "GenAIGuardrailViolation",
    "STANDARD_SAFETY_DISCLAIMER",
    "enforce_briefing_guardrails",
]
