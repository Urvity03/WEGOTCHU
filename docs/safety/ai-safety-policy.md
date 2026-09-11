# WEGOTCHU: AI Safety & Governance Policy

## 1. Core Safety Principles

WEGOTCHU is built upon strict ethical, technical, and operational guardrails to prevent harm, safeguard user privacy, and deliver responsible risk estimation.

### Principle 1: No Absolute Safety Guarantees
WEGOTCHU provides probabilistic risk estimation, situational anomaly detection, and decision support. The system **never** claims or guarantees absolute personal safety, nor does it guarantee the prevention or prediction of crime.

### Principle 2: Probabilistic Calibration over Binary Certainty
Safety is not a binary toggle. System outputs represent calibrated likelihood states (`NORMAL`, `UNUSUAL`, `ELEVATED`, `HIGH`, `EMERGENCY`). The system must communicate uncertainty explicitly and avoid unjustified certainty.

### Principle 3: Inviolable Manual SOS Primacy
Automated AI evaluation is secondary to human agency. The manual SOS trigger is inviolable, permanently accessible, and executes an instantaneous bypass ($< 100$ ms) around all machine learning layers.

### Principle 4: Active Mitigation of False Alarms
False alarms induce alert fatigue, leading users to mute or uninstall safety tools. The architecture suppresses transient spikes through temporal sequence modeling and personal baseline calibration.

### Principle 5: Asymmetric Optimization of False Negatives vs. False Positives
In personal safety, a False Negative (failing to recognize a true crisis) carries severe physical danger, whereas a False Positive (an unnecessary discreet check-in) carries inconvenience. We optimize for high recall ($\ge 95\%$) while deploying non-disruptive graduated check-ins to handle false positives gently.

### Principle 6: Granular User Consent for Sensitive Sensors
Access to microphone buffers, fine location, camera (P2), and motion sensors requires explicit, granular, and opt-in user consent. Users can revoke individual sensor permissions at any time.

### Principle 7: Data Minimization & Privacy by Design
The system collects only telemetry strictly necessary for risk estimation. Telemetry is processed locally whenever technically feasible and discarded immediately after feature computation.

### Principle 8: On-Device Processing Where Feasible
Acoustic feature extraction and baseline kinematic anomaly detection are executed on-device. Raw audio waveforms and video frames are never continuously streamed or stored in the cloud.

### Principle 9: Prohibition of Covert Surveillance & Unauthorized Facial Recognition
WEGOTCHU is an assistive personal protection tool, not surveillance spyware. It is strictly prohibited from:
* Operating in a covert or hidden mode designed to record bystanders without indication.
* Implementing facial recognition, biometric face-indexing, or identity matching.
* Recording long-term ambient audio without an active elevated safety trigger.

---

## 2. Generative AI Safety Guardrails & Boundaries

The Large Language Model (LLM) component is strictly restricted to text synthesis and contextual formatting.

```
┌─────────────────────────────────────────────────────────────┐
│ FORBIDDEN LLM ACTIONS                                       │
│ ❌ The LLM CANNOT classify risk level.                      │
│ ❌ The LLM CANNOT override deterministic safety policies.    │
│ ❌ The LLM CANNOT invent or extrapolate incident details.    │
│ ❌ The LLM CANNOT fabricate or alter GPS coordinates.       │
│ ❌ The LLM CANNOT claim certainty that an emergency exists. │
└─────────────────────────────────────────────────────────────┘
```

### Deterministic Policy Supremacy
* High-risk actions (initiating emergency sirens, broadcasting SMS to trusted circles, notifying campus security) are governed exclusively by the **Deterministic Safety Policy Engine**.
* If the LLM service encounters downtime, produces malformed JSON, or fails prompt validation, the system falls back immediately to hardcoded deterministic templates. Emergency response is never blocked by LLM availability.

---

## 3. Cryptography & Data Hygiene Standards

1. **Encryption Standards:**
   * Data in Transit: TLS 1.3 with strict cipher suites.
   * Data at Rest: AES-256-GCM encryption for stored user profiles and contact registries.
2. **Zero Secrets in Source Control:**
   * No API tokens, private keys, database credentials, or staging URLs may ever be committed to Git.
3. **Auditability:**
   * All state transitions from `NORMAL` through `EMERGENCY` generate immutable local audit logs for post-incident verification.
