# WEGOTCHU: Engineering & Research Requirements

## 1. Functional Requirements Matrix (By Priority)

### Priority P0: Critical Path (MVP Foundation)
* **FR-01 (Manual SOS Trigger):** Inviolable hardware/screen panic trigger activating emergency escalation in $< 100$ ms.
* **FR-02 (Safety Mode Toggle):** Explicit user toggle enabling high-frequency sensor capture during transit.
* **FR-03 (Trusted Contacts Registry):** Capability to add, authenticate, and manage verified contact phone numbers and emails.
* **FR-04 (Safety Timer):** User-configurable countdown timer (e.g., "Walking home for 15 mins") requiring safe PIN deactivation.
* **FR-05 (Sensor Pipeline Ingestion):** Synchronized background capture of 3-axis accelerometer, gyroscope, and GPS.
* **FR-06 (Baseline Risk Scoring):** Rule-based and basic ML anomaly scorer classifying state into 5 risk levels.
* **FR-07 (Discreet Check-in Interface):** Non-disruptive haptic prompt and subtle UI asking "Are you okay?".
* **FR-08 (Emergency Dispatch Notification):** Automated SMS / push delivery with live location web link upon escalation.
* **FR-09 (User Authentication & Security):** Secure backend token-based authentication and encrypted contact storage.

### Priority P1: Core Intelligence & Differentiation
* **FR-10 (Personal Behavioral Baseline):** Machine learning baseline model learning personal transit corridors and movement cadence.
* **FR-11 (Temporal Sequence Modeling):** Sequence model (GRU/TCN) evaluating multi-minute sliding windows to suppress false spikes.
* **FR-12 (Acoustic Distress Perception):** On-device acoustic classifier scoring environmental distress sounds (screams, calls for help).
* **FR-13 (Multimodal Signal Fusion):** Cross-modal validation combining motion kinematics, geospatial corridor, and audio distress.
* **FR-14 (GenAI Contextual Briefing):** Structured LLM integration synthesizing natural-language incident summaries for trusted contacts.
* **FR-15 (Duress PIN Cancellation):** Silent secondary PIN that appears to cancel alarms while continuing alert beacon.

### Priority P2: Advanced Horizons (Post-MVP)
* **FR-16 (Computer Vision Scene Context):** Ambient illumination and crowd density estimation using low-power edge camera frames.
* **FR-17 (Smartwatch Wearable Integration):** WearOS companion app monitoring photoplethysmography (PPG) heart rate spikes and wrist haptics.
* **FR-18 (On-Device INT8 Quantization):** Full conversion and local execution of temporal and fusion models via LiteRT/ONNX.
* **FR-19 (Federated Baseline Adaptation):** Decentralized model training updating personal baseline weights without cloud data exfiltration.
* **FR-20 (Institutional Security Dashboard):** Web-based portal for campus security integration (with explicit user opt-in).

---

## 2. Non-Functional Requirements (NFR)

* **NFR-01 (Latency):** Edge inference execution $< 100$ ms per 2.56-second window; backend risk evaluation $< 250$ ms.
* **NFR-02 (Battery Consumption):** Active Safety Mode must consume $< 2.5\%$ smartphone battery per hour of continuous monitoring.
* **NFR-03 (Reliability & Availability):** 99.9% uptime for emergency notification backend; 100% offline edge autonomy for local SOS.
* **NFR-04 (Privacy & Compliance):** Zero persistent raw audio/video storage; zero-knowledge encryption for stored location history.
* **NFR-05 (Calibration):** Expected Calibration Error (ECE) $< 0.05$ on benchmark validation sets.
