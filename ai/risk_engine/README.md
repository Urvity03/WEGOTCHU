# Module: Risk Estimation Engine (`ai/risk_engine/`)

## Purpose & Scope
The Risk Engine translates fused multimodal evidence into calibrated probabilistic risk scores and standardized risk levels.

## Primary Owner
* **Lead:** Project Lead (Member 1)

## Standardized Risk Levels
1. `NORMAL`: Routine behavior, low-power background monitoring.
2. `UNUSUAL`: Minor statistical deviation; internal logging without user interruption.
3. `ELEVATED`: Sustained anomaly; triggers discreet haptic user check-in.
4. `HIGH`: Multi-signal divergence or unacknowledged check-in; activates countdown timer.
5. `EMERGENCY`: Confirmed crisis; initiates emergency dispatch to trusted contacts.

## Outputs & Interfaces
Emits the structured JSON schema specified in `docs/architecture/ai-architecture.md`.
