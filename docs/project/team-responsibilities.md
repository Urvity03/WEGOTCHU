# WEGOTCHU: Team Structure & Engineering Ownership

## 1. Governance Principles

WEGOTCHU is a multidisciplinary collaboration among four specialized engineers. To maintain architectural integrity while enabling parallel velocity:
1. **Architectural Authority:** The Project Lead owns overall AI architecture, system interfaces, and final integration approval.
2. **Modular Ownership:** The Project Lead does **NOT** implement every task. Each member is the designated technical owner of their respective domain.
3. **Contract Adherence:** No member may alter cross-module data contracts (`docs/architecture/data-flow.md`) without consensus.

---

## 2. Team Member Ownership Breakdown

```
┌─────────────────────────────────────────────────────────────┐
│ MEMBER 1: Project Lead — AI/ML + GenAI Lead                 │
├─────────────────────────────────────────────────────────────┤
│ • Overall AI Architecture & Design Decisions                │
│ • Machine Learning Models & Kinematic Anomaly Detection    │
│ • Personal Behavioral Baseline Modeling                     │
│ • Temporal Sequence Modeling (GRU / TCN)                    │
│ • Multimodal Signal Fusion Strategy                         │
│ • Calibrated Risk Estimation Engine                         │
│ • GenAI Communication Layer & Safety Guardrails             │
│ • AI Evaluation Framework & Statistical Benchmarking        │
│ • Scientific Research Direction & Paper Authorship          │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ MEMBER 2: Data Science + Data Engineering Lead              │
├─────────────────────────────────────────────────────────────┤
│ • Dataset Research, Acquisition & Licensing Verification    │
│ • Controlled Data Collection Protocols & Ethical Compliance │
│ • Data Ingestion, Cleaning & Normalization Pipelines        │
│ • Feature Engineering (Time, Frequency, Geospatial)         │
│ • Exploratory Data Analysis (EDA) & Data Visualization      │
│ • Data Quality Auditing, Missing Value & Drift Handling     │
│ • Dataset Documentation & Intake Manifests                  │
│ • Feature Store Schemas & Parquet Export Pipelines          │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ MEMBER 3: Mobile + Backend Engineer                         │
├─────────────────────────────────────────────────────────────┤
│ • Android Native Client (Kotlin, Jetpack Compose)           │
│ • User Onboarding, Authentication & Profile Management      │
│ • Safety Mode Foreground Service & Lifecycle Management     │
│ • Inviolable Manual SOS & Discreet Check-in UI              │
│ • Trusted Contacts Management & Safety Countdown Timer      │
│ • Background Sensor Collection (Accelerometer, Gyro, GPS)   │
│ • Backend Architecture (FastAPI, PostgreSQL, Pydantic)      │
│ • Secure REST & WebSocket Telemetry APIs                    │
│ • Dispatch Integration (SMS via Twilio, Push via FCM)       │
│ • End-to-End Encryption & Keystore Security                │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ MEMBER 4: Computer Vision + Audio + Edge AI Lead            │
├─────────────────────────────────────────────────────────────┤
│ • Audio Signal Preprocessing (STFT, Mel-filterbanks)        │
│ • Audio Machine Learning (Distress / Scream Classifier)     │
│ • Environmental Noise Suppression & SNR Calculation         │
│ • Computer Vision Telemetry (OpenCV / MediaPipe / YOLO)     │
│ • Scene Context & Ambient Illumination Analysis (P2)        │
│ • Edge Model Quantization (INT8 via ONNX / LiteRT / TFLite) │
│ • On-Device Inference Runtime Integration                   │
│ • Latency, Memory Footprint & Battery Optimization          │
└─────────────────────────────────────────────────────────────┘
```

---

## 3. Review & Approval Responsibility Matrix (RACI)

| Capability / Module | Responsible (R) | Accountable (A) | Consulted (C) | Informed (I) |
| :--- | :--- | :--- | :--- | :--- |
| **System Architecture** | Member 1 | Member 1 | Members 2, 3, 4 | Entire Team |
| **AI Models & Fusion** | Member 1 | Member 1 | Members 2, 4 | Member 3 |
| **Data Pipelines & Datasets** | Member 2 | Member 2 | Member 1 | Members 3, 4 |
| **Android Application** | Member 3 | Member 3 | Members 1, 4 | Member 2 |
| **Backend APIs & DB** | Member 3 | Member 3 | Member 1 | Members 2, 4 |
| **Audio & CV Models** | Member 4 | Member 4 | Member 1 | Members 2, 3 |
| **Edge Quantization & Perf**| Member 4 | Member 4 | Members 1, 3 | Member 2 |
| **GenAI Guardrails** | Member 1 | Member 1 | Member 3 | Members 2, 4 |
| **Safety & Threat Model** | Entire Team | Member 1 | Entire Team | Entire Team |
