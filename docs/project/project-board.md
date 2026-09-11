# WEGOTCHU: GitHub Project Board Configuration Guide

## 1. Project Board Workflow Columns

The team utilizes a Kanban project board structured into seven lifecycle states:

```
[1. BACKLOG] ──> [2. TODO] ──> [3. IN PROGRESS] ──> [4. CODE REVIEW] ──> [5. TESTING] ──> [6. DONE]
                                       │
                                       └──> [BLOCKED]
```

### Column Definitions
1. **BACKLOG:** All triaged and planned issues awaiting assignment to a future sprint.
2. **TODO:** Issues committed to the active 2-week sprint; ready for implementation.
3. **IN PROGRESS:** Actively being worked on by an assigned contributor (max 2 active issues per member).
4. **CODE REVIEW:** Pull Request opened; awaiting peer code review and approval.
5. **TESTING / BENCHMARKING:** PR merged to `develop`; verifying automated tests, latency, or ML evaluation metrics.
6. **BLOCKED:** Work halted due to an unresolved upstream dependency or architectural clarification.
7. **DONE:** Successfully tested, merged to `main`, documented, and verified.

---

## 2. Taxonomy & Label Specifications

### Functional Domain Labels
* `AI/ML`: Core modeling, anomaly detection, temporal models, risk engine.
* `GenAI`: LLM prompt design, structured outputs, communication guardrails.
* `Data`: Ingestion pipelines, feature extraction, dataset curation, EDA.
* `Mobile`: Android native client, Jetpack Compose, sensor services, UI/UX.
* `Backend`: FastAPI services, database schemas, WebSocket telemetry endpoints.
* `Audio`: Acoustic feature processing, distress classifier, noise filtering.
* `Computer-Vision`: Ambient illumination, scene classification, optical flow.
* `Edge-AI`: Quantization (INT8), ONNX Runtime, LiteRT, battery/latency optimization.
* `Research`: Scientific hypotheses, literature analysis, ablation studies.
* `Documentation`: Architecture updates, API contracts, research reports.
* `Testing`: Unit tests, integration harnesses, calibration verification.
* `Security`: Threat model mitigations, encryption, privacy, duress features.

### Priority Labels
* `Priority-High`: Critical path for current milestone; blocks other contributors.
* `Priority-Medium`: Standard milestone objective; required for feature completion.
* `Priority-Low`: Exploratory research, optimization, or nice-to-have capability.

---

## 3. Automation Rules

* When a PR is opened referencing `Closes #XX`, move issue to **CODE REVIEW**.
* When a PR is merged into `develop` or `main`, move issue to **TESTING** or **DONE**.
* When a review is requested, notify assigned reviewer on team communications.
