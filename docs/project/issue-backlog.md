# WEGOTCHU: Initial GitHub Issues Backlog (#1 to #43)

This document specifies the initial backlog of 43 tracked engineering and research issues across 13 functional categories.

---

## 1. FOUNDATION ISSUES (#1 – #7)

* **#1 Define system architecture**  
  *Category:* FOUNDATION | *Labels:* `Documentation`, `Priority-High` | *Assignee:* Member 1  
  *Description:* Document the complete 13-tier conceptual flow, layer responsibilities, and non-negotiables. Deliver in `docs/architecture/system-architecture.md`.
* **#2 Define AI architecture**  
  *Category:* FOUNDATION | *Labels:* `AI/ML`, `Documentation`, `Priority-High` | *Assignee:* Member 1  
  *Description:* Specify layers A through J, define the 5 standardized risk levels, and establish the structured JSON output specification in `docs/architecture/ai-architecture.md`.
* **#3 Define data contracts**  
  *Category:* FOUNDATION | *Labels:* `Data`, `Documentation`, `Priority-High` | *Assignee:* Member 1 & Member 3  
  *Description:* Define initial v0.1 JSON schemas for mobile sensors, audio signals, vision context, and AI risk outputs in `docs/architecture/data-flow.md`.
* **#4 Define safety policy**  
  *Category:* FOUNDATION | *Labels:* `Security`, `Documentation`, `Priority-High` | *Assignee:* Member 1 & Entire Team  
  *Description:* Formalize principles: no guaranteed safety, probabilistic risk, inviolable manual SOS, false alarm suppression, and LLM guardrails in `docs/safety/ai-safety-policy.md`.
* **#5 Define privacy requirements**  
  *Category:* FOUNDATION | *Labels:* `Security`, `Documentation`, `Priority-High` | *Assignee:* Member 1 & Member 2  
  *Description:* Document on-device vs. cloud boundaries, ephemeral RAM buffers, and cryptographic purge schedules in `docs/safety/privacy.md` and `docs/safety/data-retention.md`.
* **#6 Configure repository contribution workflow**  
  *Category:* FOUNDATION | *Labels:* `Documentation`, `Priority-Medium` | *Assignee:* Member 1  
  *Description:* Create `CONTRIBUTING.md`, issue templates, PR template, CI workflow, and branching rules.
* **#7 Create project roadmap**  
  *Category:* FOUNDATION | *Labels:* `Documentation`, `Priority-Medium` | *Assignee:* Member 1  
  *Description:* Document 8-month timeline, milestone exit criteria, and P0/P1/P2 priorities in `docs/project/roadmap.md` and `docs/project/milestones.md`.

---

## 2. AI/ML ISSUES (#8 – #15)

* **#8 Define ML problem formulation**  
  *Category:* AI/ML | *Labels:* `AI/ML`, `Research`, `Priority-High` | *Assignee:* Member 1  
  *Description:* Formulate proactive risk estimation as a sequential anomaly and classification problem under extreme class imbalance.
* **#9 Implement rule-based risk baseline**  
  *Category:* AI/ML | *Labels:* `AI/ML`, `Priority-High` | *Assignee:* Member 1  
  *Description:* Create a deterministic rule-based benchmark (speed, sudden stop, basic geofence threshold) as Exp 1 baseline.
* **#10 Implement anomaly detection baseline**  
  *Category:* AI/ML | *Labels:* `AI/ML`, `Priority-High` | *Assignee:* Member 1  
  *Description:* Prototype Isolation Forest and One-Class SVM on windowed kinematic features in `ai/anomaly_detection/`.
* **#11 Design personal baseline**  
  *Category:* AI/ML | *Labels:* `AI/ML`, `Research`, `Priority-Medium` | *Assignee:* Member 1  
  *Description:* Design mathematical formulation for online personal baseline modeling (GMM / Mahalanobis distance) in `ai/personalization/`.
* **#12 Design temporal modeling experiment**  
  *Category:* AI/ML | *Labels:* `AI/ML`, `Research`, `Priority-Medium` | *Assignee:* Member 1  
  *Description:* Design GRU vs. TCN experimental protocol over 30-120 second sequential windows in `ai/temporal_model/`.
* **#13 Design multimodal fusion experiment**  
  *Category:* AI/ML | *Labels:* `AI/ML`, `Research`, `Priority-Medium` | *Assignee:* Member 1  
  *Description:* Specify early vs. late vs. hybrid cross-modal fusion architectures in `ai/multimodal_fusion/`.
* **#14 Define risk engine**  
  *Category:* AI/ML | *Labels:* `AI/ML`, `Priority-High` | *Assignee:* Member 1  
  *Description:* Implement probability calibration (temperature scaling) and risk score aggregation into 5 standard risk states in `ai/risk_engine/`.
* **#15 Define AI evaluation framework**  
  *Category:* AI/ML | *Labels:* `AI/ML`, `Testing`, `Priority-High` | *Assignee:* Member 1  
  *Description:* Build automated evaluation scripts computing Precision, Recall, Macro-F1, PR-AUC, and ECE in `tests/`.

---

## 3. GENAI ISSUES (#16 – #19)

* **#16 Define GenAI responsibilities**  
  *Category:* GENAI | *Labels:* `GenAI`, `Documentation`, `Priority-High` | *Assignee:* Member 1  
  *Description:* Specify exact operational boundaries: text synthesis only, strict JSON output schema, zero risk decision authority.
* **#17 Design structured LLM interface**  
  *Category:* GENAI | *Labels:* `GenAI`, `Priority-Medium` | *Assignee:* Member 1  
  *Description:* Build Pydantic schema validation for LLM inputs and outputs in `ai/genai/`.
* **#18 Design GenAI safety guardrails**  
  *Category:* GENAI | *Labels:* `GenAI`, `Security`, `Priority-High` | *Assignee:* Member 1  
  *Description:* Implement pre-prompt validation and deterministic fallback if LLM response is delayed ($> 5$s) or schema is violated.
* **#19 Design emergency communication generation**  
  *Category:* GENAI | *Labels:* `GenAI`, `Priority-Medium` | *Assignee:* Member 1 & Member 3  
  *Description:* Prototype empathetic, concise SMS and push alert templates with dynamic token insertion.

---

## 4. DATA ISSUES (#20 – #24)

* **#20 Research available datasets**  
  *Category:* DATA | *Labels:* `Data`, `Research`, `Priority-High` | *Assignee:* Member 2  
  *Description:* Survey public benchmark datasets (UCI HAR, MobiFall, AudioSet, GeoLife) and verify licensing terms in `docs/research/datasets.md`.
* **#21 Create dataset documentation**  
  *Category:* DATA | *Labels:* `Data`, `Documentation`, `Priority-Medium` | *Assignee:* Member 2  
  *Description:* Populate dataset intake metadata templates for all ingested datasets.
* **#22 Design data preprocessing pipeline**  
  *Category:* DATA | *Labels:* `Data`, `Priority-High` | *Assignee:* Member 2  
  *Description:* Implement data loading, bandpass filtering, and 2.56-second window segmentation in `data/`.
* **#23 Define feature schema**  
  *Category:* DATA | *Labels:* `Data`, `Priority-High` | *Assignee:* Member 2  
  *Description:* Standardize feature names, units, and scaling for kinematic, geospatial, and acoustic features.
* **#24 Design controlled data collection protocol**  
  *Category:* DATA | *Labels:* `Data`, `Research`, `Priority-Medium` | *Assignee:* Member 2  
  *Description:* Formulate ethical participant consent form and scripted non-hazardous motion scenarios (walking, running, bus transit).

---

## 5. MOBILE ISSUES (#25 – #31)

* **#25 Create Android project**  
  *Category:* MOBILE | *Labels:* `Mobile`, `Priority-High` | *Assignee:* Member 3  
  *Description:* Initialize Android Kotlin project with Jetpack Compose, Clean Architecture, and Gradle build config in `mobile/`.
* **#26 Implement onboarding**  
  *Category:* MOBILE | *Labels:* `Mobile`, `Priority-Medium` | *Assignee:* Member 3  
  *Description:* Build onboarding flow explaining proactive safety, privacy principles, and sensor permission requests.
* **#27 Implement Safety Mode**  
  *Category:* MOBILE | *Labels:* `Mobile`, `Priority-High` | *Assignee:* Member 3  
  *Description:* Build foreground service with persistent notification enabling continuous transit monitoring.
* **#28 Implement SOS**  
  *Category:* MOBILE | *Labels:* `Mobile`, `Priority-High` | *Assignee:* Member 3  
  *Description:* Build instant manual SOS button with immediate hardware vibration and $< 100$ ms dispatch trigger.
* **#29 Implement trusted contacts**  
  *Category:* MOBILE | *Labels:* `Mobile`, `Priority-High` | *Assignee:* Member 3  
  *Description:* Build contact selection, phone number validation, and local encrypted contact storage.
* **#30 Implement GPS collection**  
  *Category:* MOBILE | *Labels:* `Mobile`, `Priority-High` | *Assignee:* Member 3  
  *Description:* Implement FusedLocationProviderClient with dynamic duty cycling based on risk state.
* **#31 Implement accelerometer/gyroscope collection**  
  *Category:* MOBILE | *Labels:* `Mobile`, `Priority-High` | *Assignee:* Member 3  
  *Description:* Implement SensorEventListener capturing 50 Hz tri-axial accelerometer and gyroscope into ring buffers.

---

## 6. AUDIO ISSUES (#32 – #34)

* **#32 Research audio datasets**  
  *Category:* AUDIO | *Labels:* `Audio`, `Research`, `Priority-Medium` | *Assignee:* Member 4  
  *Description:* Evaluate AudioSet distress subset and ESC-50 for acoustic anomaly baseline training.
* **#33 Build audio preprocessing pipeline**  
  *Category:* AUDIO | *Labels:* `Audio`, `Priority-High` | *Assignee:* Member 4  
  *Description:* Implement 1-second framing, 16 kHz resampler, STFT, and Mel-spectrogram feature extractor in `perception/audio/`.
* **#34 Establish audio classification baseline**  
  *Category:* AUDIO | *Labels:* `Audio`, `AI/ML`, `Priority-Medium` | *Assignee:* Member 4  
  *Description:* Train baseline 1D-CNN / MobileNet-v3 classifier predicting `audio_distress_score`.

---

## 7. VISION ISSUES (#35 – #37)

* **#35 Research computer vision requirements**  
  *Category:* VISION | *Labels:* `Computer-Vision`, `Research`, `Priority-Low` | *Assignee:* Member 4  
  *Description:* Investigate feasibility, privacy implications, and power budget for ambient scene classification.
* **#36 Define CV signals**  
  *Category:* VISION | *Labels:* `Computer-Vision`, `Priority-Low` | *Assignee:* Member 4  
  *Description:* Define schema for optical flow magnitude and ambient lux estimation in `perception/vision/`.
* **#37 Prototype CV pipeline**  
  *Category:* VISION | *Labels:* `Computer-Vision`, `Priority-Low` | *Assignee:* Member 4  
  *Description:* Create lightweight OpenCV test harness analyzing lighting and motion variance.

---

## 8. EDGE AI ISSUES (#38 – #40)

* **#38 Research lightweight inference**  
  *Category:* EDGE AI | *Labels:* `Edge-AI`, `Research`, `Priority-Medium` | *Assignee:* Member 4  
  *Description:* Benchmark ONNX Runtime Mobile vs. LiteRT / TFLite runtime on Android ARM64 architecture in `perception/edge/`.
* **#39 Benchmark model latency**  
  *Category:* EDGE AI | *Labels:* `Edge-AI`, `Priority-Medium` | *Assignee:* Member 4  
  *Description:* Measure inference latency (ms) and RAM usage (MB) for baseline kinematic models.
* **#40 Evaluate ONNX/TFLite/LiteRT options**  
  *Category:* EDGE AI | *Labels:* `Edge-AI`, `Priority-Medium` | *Assignee:* Member 4  
  *Description:* Document export and INT8 post-training quantization pipeline from PyTorch.

---

## 9. TESTING ISSUES (#41 – #43)

* **#41 Define AI test strategy**  
  *Category:* TESTING | *Labels:* `Testing`, `AI/ML`, `Priority-High` | *Assignee:* Member 1  
  *Description:* Implement unit tests verifying tensor shapes, deterministic reproducibility, and seed locking in `tests/`.
* **#42 Define integration test strategy**  
  *Category:* TESTING | *Labels:* `Testing`, `Priority-High` | *Assignee:* Member 3 & Member 1  
  *Description:* Create simulated client-server test verifying telemetry ingestion through risk scoring and alert generation.
* **#43 Define false-positive/false-negative evaluation**  
  *Category:* TESTING | *Labels:* `Testing`, `Research`, `Priority-High` | *Assignee:* Member 1 & Member 2  
  *Description:* Build automated test harness computing FPR and FNR across edge-case sensor scenarios.
