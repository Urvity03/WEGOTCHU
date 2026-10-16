# Module: Risk Estimation Engine (`ai/risk_engine/`)

## Purpose & Scope
The Risk Engine translates fused multimodal evidence (spatial route deviation and kinematic motion anomalies) into calibrated probabilistic risk scores, standardized risk levels, and actionable interventions.

## Primary Owner
* **Lead:** Project Lead (Member 1)

## Standardized Risk Levels & Recommended Actions
Conforming to Contract 4 (Version 0.1) and `docs/architecture/ai-architecture.md`:

| Risk Level | Recommended Action | Description |
| :--- | :--- | :--- |
| `NORMAL` | `NONE` | Routine behavior, low-power background monitoring. |
| `UNUSUAL` | `MONITOR` | Minor statistical deviation or missing signal; internal telemetry logging and observation. |
| `ELEVATED` | `USER_CHECK` | Sustained anomaly or co-occurring anomalies; triggers discreet haptic user check-in. |
| `HIGH` | `PRE_ALERT` | Multi-signal distress (e.g., acoustic) or unacknowledged check-in; activates countdown timer. (Policy Engine) |
| `EMERGENCY` | `DISPATCH_EMERGENCY` | Confirmed crisis, manual SOS, or expired countdown; emergency dispatch. (Policy Engine) |

## Contract 4 Compliance (`docs/architecture/data-flow.md`)
The engine produces structured `RiskAssessment` payloads strictly complying with Contract 4:
* `$schema`: `"https://json-schema.org/draft/2020-12/schema"`
* `version`: `"0.1"`
* `risk_vector`: Explicit decomposition across `kinematic_anomaly`, `route_anomaly`, `acoustic_anomaly`, and `temporal_persistence`.
* `signals`: Flat list of validated signal identifier strings (e.g., `["route_deviation", "unusual_motion"]`). Authoritative motion signal identifier is `"unusual_motion"` per `docs/architecture/ai-architecture.md` §3 (line 126).
* `location_status`: `"available"` (when location observed) or `"unavailable"`.

## Current Implementation
* **`ai/risk_engine/models.py`**:
  * `RiskLevel` and `RecommendedAction`: Standardized enums matching Contract 4.
  * `RiskVector`, `TelemetrySummary`, `CalibrationMetadata`: Structured signal payload components.
  * `RiskAssessment`: Central immutable dataclass with `.to_dict()` for strict Contract 4 (10 mandatory fields) and `.to_dict(include_extended_metadata=True)` / `.to_architecture_dict()` for extended architecture representations.
* **`ai/risk_engine/engine.py`**:
  * `RiskEngine`: Deterministic, rule-anchored risk engine integrating `RouteDeviationResult` and `MotionAnomalyResult`.
  * **Missing-Data & Cold-Start Policy:**
    * Validated-normal signal with a missing/cold-start counterpart evaluates to `NORMAL` with reduced confidence (`0.65`).
    * All signals missing evaluates conservatively to `UNUSUAL` / `MONITOR` with low confidence (`0.20`), ensuring absence of telemetry is never treated as confirmed safety.
    * Unavailable scores are preserved as `None` in `RiskVector` and never coerced to `0.0`.
  * **Co-occurrence Escalation:** When both route deviation and kinematic anomalies co-occur, risk escalates to `ELEVATED` / `USER_CHECK`. Statistical anomaly scores alone never trigger `HIGH` or `EMERGENCY`.

## Testing & Validation
* Unit test suite: `tests/unit/test_risk_engine.py`
* Covers normal mobility, single-modality deviations, multimodal co-occurrence, cold-start handling, partial and all-missing telemetry policies, score bound invariants, and strict Contract 4 serialization.
