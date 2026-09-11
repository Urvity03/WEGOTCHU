# WEGOTCHU: Privacy Architecture & Principles

## 1. Privacy by Design Framework

WEGOTCHU treats privacy as an architectural requirement rather than a compliance afterthought. Personal safety tools must never become personal surveillance systems.

---

## 2. On-Device vs. Cloud Boundary Architecture

```
┌─────────────────────────────────────────────────────────────┐
│ ON-DEVICE (EDGE) TRUST BOUNDARY                             │
│ • Raw Microphone Audio (Continuous Ring Buffer in RAM)       │
│ • Raw 50Hz Accelerometer & Gyroscope Streams                │
│ • Raw Camera Frames (P2)                                    │
│ • Personal Baseline Statistical Profiles (GMM/KDE)          │
│ • Acoustic Feature Extraction (MFCC / Mel-Spectrogram)      │
│ • Immediate Signal Transformation & Discard                 │
└──────────────────────────────┬──────────────────────────────┘
                               │ Extracted Features Only
                               │ (TLS 1.3 Encrypted)
                               ▼
┌─────────────────────────────────────────────────────────────┐
│ BACKEND CLOUD BOUNDARY                                      │
│ • Aggregated Temporal Sequence Models                       │
│ • Calibrated Multimodal Risk Engine                         │
│ • Encrypted Trusted Contacts Registry                       │
│ • GenAI Alert Synthesis Gateway                             │
│ • Ephemeral Incident Dispatch Tokens                        │
└─────────────────────────────────────────────────────────────┘
```

---

## 3. Ephemeral In-Memory Ring Buffers

To guarantee that ambient audio and visual recordings are never stored:
1. **Audio Ring Buffer:** Audio is captured into a volatile circular RAM buffer of maximum duration 3 seconds.
2. **Immediate Feature Transformation:** The perception module computes spectral flux, MFCCs, and distress classification scores in-memory.
3. **Deterministic Overwrite:** As each new audio chunk arrives, old samples are immediately overwritten in memory. Raw audio is **never written to persistent disk storage** (NAND/eMMC).

---

## 4. Location Privacy & Obfuscation

* **Geographic Fuzzing in Passive Mode:** While in `NORMAL` state, coarse location resolution is used to establish corridor familiarity.
* **Precision Activation Only in Safety Mode:** High-precision GPS is activated strictly when the user turns on "Safety Mode" or when the system detects sustained situational anomalies.
* **Time-Bounded Access Links:** Live tracking links sent to trusted contacts expire automatically 2 hours after resolution of the event.
