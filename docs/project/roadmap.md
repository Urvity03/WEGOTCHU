# WEGOTCHU: 8-Month Comprehensive Project Roadmap

## 1. High-Level 8-Month Schedule

```
Month 1: Foundation, Architecture, Threat Modeling & Privacy (CURRENT)
Month 2: Datasets, Preprocessing Pipeline, Controlled Scenarios & Classical Baselines
Month 3: Motion/Context Feature Pipeline, Kinematic Anomaly Detection, Initial Risk Scorer
Month 4: Personal Baseline Adaptation, Temporal Sequence Modeling & AI Evaluation Suite
Month 5: Android Mobile MVP, Sensor Streaming Integration, Safety Policy Engine
Month 6: GenAI Communication Layer, System Integration, Security & Duress Auditing
Month 7: Controlled Experimental Evaluation, Ablation Studies, Error Analysis & User Testing
Month 8: Final Prototype Polish, Academic Research Paper / Dissertation, Startup Pitch & Demo
```

---

## 2. Monthly Milestone Breakdown

### Month 1: Foundation & Architecture (Current Phase)
* Finalize end-to-end 13-tier system architecture and AI stack specifications.
* Establish Git repository standards, branching, and Conventional Commits.
* Formalize AI Safety Policy, STRIDE Threat Model, and Data Retention rules.
* Define Data Contracts v0.1 for mobile, backend, and AI interfaces.
* Formulate primary and supporting research questions.

### Month 2: Data Foundations & Classical Baselines
* Member 2 curates public benchmark datasets (UCI HAR, MobiFall, AudioSet distress subset, GeoLife).
* Build automated ingestion, normalization, and windowing pipelines (`data/pipelines/`).
* Establish baseline feature extraction (time-domain, frequency-domain, MFCCs).
* Train classical ML baselines (Random Forest, Isolation Forest, OC-SVM).

### Month 3: Kinematic Anomaly Detection & Risk Scorer
* Member 1 & 2 build kinematic anomaly detection engine.
* Member 4 initiates audio preprocessing and acoustic feature extraction benchmark.
* Member 3 initializes Android project skeleton and background sensor foreground service.
* Implement initial rule-based + ML risk engine outputting 5 standard risk states.

### Month 4: Temporal Modeling & Personalization
* Member 1 trains temporal sequence models (GRU vs. TCN) on multi-window motion series.
* Member 1 & 2 design personal baseline model (GMM / online distance metric).
* Member 4 benchmarks lightweight acoustic distress classifier on AudioSet subset.
* Validate reduction of false-positive rate (FPR) via temporal sequence persistence.

### Month 5: Mobile MVP & Policy Engine
* Member 3 completes Android MVP: Onboarding, Safety Mode UI, Manual SOS, Safety Timer.
* Implement local deterministic Safety Policy Engine on Android and Backend.
* Integrate background GPS and IMU collection with edge feature extractor.
* Connect Android client to FastAPI backend via authenticated WebSockets / REST.

### Month 6: GenAI Gateway & System Integration
* Member 1 & 3 implement GenAI Communication Service using structured outputs and strict JSON schema.
* Enforce prompt guardrails: zero danger classification, zero coordinate modification.
* Connect automated SMS / push notification dispatcher for trusted contacts.
* Implement Duress PIN and offline SMS fallback mechanisms.

### Month 7: Empirical Evaluation & Ablation Studies
* Conduct systematic experiments across all 8 planned tiers (Exp 1 through Exp 8).
* Compute statistical evaluation metrics: Precision, Recall, F1, FPR, FNR, PR-AUC, ECE.
* Conduct latency, memory footprint, and battery drain benchmarks on physical devices.
* Perform ablation studies: impact of personalization vs. temporal vs. multimodal fusion.

### Month 8: Final Defense, Publication & Startup Launch
* Finalize academic dissertation / research publication draft.
* Package end-to-end reproducible codebase with Docker deployment.
* Prepare interactive demonstration, investor pitch deck, and startup MVP landing page.
