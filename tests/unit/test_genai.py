"""Unit tests for GenAI communication layer, guardrails, and deterministic fallbacks."""

import pytest

from ai.genai import (
    BriefingAudience,
    GenAIBriefingRequest,
    GenAIBriefingResponse,
    GenAIBriefingService,
    GenAIGuardrailViolation,
    STANDARD_SAFETY_DISCLAIMER,
    enforce_briefing_guardrails,
)


def test_deterministic_template_fallback_user_normal():
    service = GenAIBriefingService(llm_provider=None)
    req = GenAIBriefingRequest(
        risk_level="NORMAL",
        confidence=0.88,
        signals=(),
        available_modalities=("motion", "route"),
        missing_modalities=(),
        audience=BriefingAudience.USER,
        user_display_name="Alice",
    )

    resp = service.synthesize_briefing(req)
    assert isinstance(resp, GenAIBriefingResponse)
    assert resp.risk_level == "NORMAL"
    assert resp.source == "deterministic_template"
    assert "Alice" in resp.summary
    assert resp.limitations_disclaimer == STANDARD_SAFETY_DISCLAIMER


def test_deterministic_template_elevated_checkin():
    service = GenAIBriefingService()
    req = GenAIBriefingRequest(
        risk_level="ELEVATED",
        confidence=0.91,
        signals=("route_deviation", "unusual_motion"),
        available_modalities=("motion", "route"),
        missing_modalities=("acoustic",),
        recommended_action="USER_CHECK",
        audience=BriefingAudience.USER,
        user_display_name="Bob",
    )

    resp = service.synthesize_briefing(req)
    assert resp.risk_level == "ELEVATED"
    assert resp.recommended_action == "USER_CHECK"
    assert "Bob" in resp.summary
    assert "check-in" in resp.headline.lower() or "check" in resp.summary.lower()
    assert "acoustic" in resp.missing_evidence


def test_guardrails_prevent_llm_from_overriding_risk_level():
    # Simulate an adversarial or hallucinating LLM that attempts to downgrade ELEVATED to NORMAL
    def malicious_llm(_):
        return {
            "headline": "Everything is Great!",
            "summary": "We downgraded your risk. You are totally safe.",
            "risk_level": "NORMAL",  # Hallucinated downgrade!
            "recommended_action": "NONE",
            "active_signals": [],
            "missing_evidence": [],
        }

    service = GenAIBriefingService(llm_provider=malicious_llm)
    req = GenAIBriefingRequest(
        risk_level="ELEVATED",
        confidence=0.90,
        signals=("unusual_motion",),
        recommended_action="USER_CHECK",
        audience=BriefingAudience.USER,
        user_display_name="Charlie",
    )

    resp = service.synthesize_briefing(req)
    # INVIOLABLE: risk_level MUST remain ELEVATED
    assert resp.risk_level == "ELEVATED"
    assert resp.recommended_action == "USER_CHECK"
    assert resp.active_signals == ["unusual_motion"]


def test_guardrails_sanitize_prohibited_guarantee_claims():
    # Simulate LLM producing prohibited medical guarantee
    def hallucinating_llm(_):
        return {
            "headline": "Safe Status",
            "summary": "We guarantee safety and medical emergency confirmed false.",
            "risk_level": "NORMAL",
            "recommended_action": "NONE",
        }

    service = GenAIBriefingService(llm_provider=hallucinating_llm)
    req = GenAIBriefingRequest(
        risk_level="NORMAL",
        confidence=0.85,
        audience=BriefingAudience.USER,
    )

    resp = service.synthesize_briefing(req)
    assert "[claim omitted by safety policy]" in resp.summary
    assert "guarantee safety" not in resp.summary.lower()


def test_guardrail_violation_raises_when_configured():
    req = GenAIBriefingRequest(
        risk_level="NORMAL",
        confidence=0.85,
    )
    raw = {
        "headline": "Diagnosis",
        "summary": "We diagnose no fracture and guarantee safety.",
        "risk_level": "NORMAL",
        "recommended_action": "NONE",
    }
    with pytest.raises(GenAIGuardrailViolation):
        enforce_briefing_guardrails(req, raw, fallback_on_violation=False)


def test_llm_provider_exception_falls_back_cleanly():
    def broken_llm(_):
        raise TimeoutError("Provider connection timed out after 5.0s")

    service = GenAIBriefingService(llm_provider=broken_llm)
    req = GenAIBriefingRequest(
        risk_level="UNUSUAL",
        confidence=0.75,
        signals=("route_deviation",),
        audience=BriefingAudience.TRUSTED_CONTACT,
        user_display_name="Dana",
    )

    # Should not raise; falls back immediately to deterministic template
    resp = service.synthesize_briefing(req)
    assert resp.source == "deterministic_template"
    assert resp.risk_level == "UNUSUAL"
    assert "Dana" in resp.summary
