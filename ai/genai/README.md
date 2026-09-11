# Module: GenAI Communication Layer (`ai/genai/`)

## Purpose & Scope
This module interfaces with Large Language Models (LLMs) to synthesize clear, empathetic, and context-aware crisis briefings for trusted contacts and emergency responders.

## Primary Owner
* **Lead:** Project Lead (Member 1)
* **Collaborator:** Member 3 (Mobile & Backend Lead)

## Inviolable Safety Boundaries
> [!CRITICAL]
> The LLM **NEVER** decides risk levels, overrides deterministic safety policies, or invents facts. All communications are generated from structured JSON telemetry inputs and validated via Pydantic schemas.

## Responsibilities
* Format alert SMS messages and push notification briefings.
* Synthesize timeline summaries of the event for trusted circles.
* Fall back immediately to deterministic templates if the LLM is unreachable or times out ($> 5$s).
