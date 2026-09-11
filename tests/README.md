# Module: Automated Test Suite (`tests/`)

## Purpose & Scope
Houses unit tests, integration harnesses, and AI evaluation verification suites.

## Directory Layout
* `unit/`: Tests for individual feature extractors, schema validators, and algorithms.
* `integration/`: End-to-end tests connecting simulated mobile telemetry to risk evaluation and policy triggers.
* `ai_eval/`: Statistical evaluation tests verifying false-positive rates, recall bounds, and calibration error.

## Running Tests
```bash
pytest tests/ -v
```
