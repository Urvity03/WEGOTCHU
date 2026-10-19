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
  * **Confidence Assessment Policy:**
    * **Distinction between Concepts:**
      * *Anomaly Scores:* Bounded numerical values in `[0.0, 1.0]` indicating statistical divergence from an individual or kinematic baseline.
      * *Detector Confidence:* Reliability indicator reflecting observation density, sampling frequency, or sensor validity (e.g., `MotionAnomalyResult.confidence`).
      * *Risk-Assessment Confidence:* Overall certainty of the synthesized `RiskAssessment`.
      * *Safety-Risk Probability:* A calibrated likelihood of genuine physical danger. **The risk engine outputs deterministic heuristic confidence scores, NOT calibrated probabilities of danger or crisis.**
    * **Single Anomaly Confidence:**
      * When kinematic motion is the sole anomalous signal, risk confidence scales directly with motion detector confidence: `confidence = min(0.90, max(0.0, motion_conf))`. Lower detector confidence directly lowers assessment certainty rather than being held artificially high or clamped by an artificial floor.
      * When route deviation is the sole anomalous signal, route scoring does not currently provide a detector-level confidence metric (such as reference corridor density). The engine assigns a nominal baseline confidence of `0.75`.
    * **Co-Occurring Anomaly Confidence:**
      * When both route deviation and kinematic anomalies co-occur, confidence is synthesized as `(0.85 + motion_conf) / 2.0` (bounded in `[0.0, 0.95]`).
      * There is no artificial minimum confidence floor (such as `0.70`). If motion detector confidence is low (e.g. `0.20`), risk confidence drops proportionally (`0.525`), preventing overstated certainty during multimodal escalation.
    * **Handling of Detector Confidence Bounds and Missing Values:**
      * Detector confidence values are clamped to `[0.0, 1.0]`.
      * Non-finite confidence values (`NaN`, `+inf`, `-inf`) fall back safely to `0.0`.
      * Unavailable confidence (`None`) preserves conservative nominal baseline values (`0.75` for single motion anomaly; `0.80` weight for co-occurring anomalies).
  * **Missing-Data & Cold-Start Policy:**
    * Validated-normal signal with a missing/cold-start counterpart evaluates to `NORMAL` with reduced confidence (`0.65`).
    * All signals missing evaluates conservatively to `UNUSUAL` / `MONITOR` with low confidence (`0.20`), ensuring absence of telemetry is never treated as confirmed safety.
    * Unavailable scores are preserved as `None` in `RiskVector` and never coerced to `0.0`.
  * **Co-occurrence Escalation:** When both route deviation and kinematic anomalies co-occur, risk escalates to `ELEVATED` / `USER_CHECK`. Statistical anomaly scores alone never trigger `HIGH` or `EMERGENCY`.

## Testing & Validation
* Unit test suite: `tests/unit/test_risk_engine.py`
* Covers normal mobility, single-modality deviations, multimodal co-occurrence, high vs. low motion detector confidence scaling, cold-start handling, partial and all-missing telemetry policies, score bound invariants, and strict Contract 4 serialization.
