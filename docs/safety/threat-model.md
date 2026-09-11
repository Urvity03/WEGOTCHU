# WEGOTCHU: Threat Model & Security Analysis

## 1. Threat Modeling Scope

This threat model evaluates physical, digital, and adversarial threats to WEGOTCHU across its mobile client, edge inference runtime, backend APIs, and external communication channels.

Methodology: **STRIDE Classification** combined with Physical Safety Context Analysis.

---

## 2. STRIDE Threat Analysis

| Threat Category | Potential Vector | Impact | Mitigation Strategy in WEGOTCHU |
| :--- | :--- | :--- | :--- |
| **Spoofing** | Mock GPS location injection via rooted Android device or software spoofers. | Adversary falsifies safe location during an incident. | Cross-correlate GPS coordinates with cellular tower IDs, Wi-Fi BSSID signals, and IMU step dead-reckoning. |
| **Tampering** | Modification of local on-device baseline models or threshold configurations. | Malicious suppression of elevated risk alerts. | Sign on-device ONNX/LiteRT model binaries; enforce Android SafetyNet / Play Integrity verification; verify config checksums. |
| **Repudiation** | User or attacker claims an SOS alert was fabricated by the app. | Legal or evidentiary ambiguity during post-incident review. | Cryptographically sign incident state transition logs locally with device hardware keystore. |
| **Information Disclosure** | Interception of real-time location stream or audio feature vectors. | Stalker or attacker tracks victim trajectory in transit. | TLS 1.3 end-to-end transport; ephemeral in-memory processing; strict role-based access for trusted contacts via temporary signed tokens. |
| **Denial of Service** | Radio frequency jamming or battery exhaustion via continuous high-frequency sampling. | App fails to dispatch emergency alerts when battery drains. | Adaptive sensor throttling (duty cycling); fallback to carrier SMS when data network fails; offline edge autonomy. |
| **Elevation of Privilege** | Coercive partner or malicious actor installs app with covert tracking permissions. | App is misused as stalkerware or domestic surveillance tool. | Transparent persistent notification icon when Safety Mode is active; PIN/biometric authorization required to modify trusted circle; zero covert operation. |

---

## 3. Physical & Coercive Safety Threats

### A. Coercive Control & Stalkerware Abuse
* **Threat:** A controlling partner configures themselves as the sole trusted contact to track the user covertly.
* **Mitigations:**
  * Persistent, non-dismissible system tray notification whenever Safety Mode or location tracking is active.
  * Disguised / Duress PIN: Entering a secondary duress PIN appears to cancel an alert on-screen while silently continuing emergency beacon dispatch to primary authorities or secondary contacts.

### B. Attacker-Forced Cancellation
* **Threat:** An assailant forces the victim to cancel an ongoing `ELEVATED` or `HIGH` check-in.
* **Mitigations:**
  * Optional Duress Mode: Entering a decoy cancellation code quietly confirms emergency status.
  * Rapid re-verification: If cancel occurs simultaneously with high acoustic distress or sudden velocity changes, the state machine flags the cancellation as suspect.

### C. Adversarial Prompt Injection against GenAI
* **Threat:** Malicious payload injected into user profile or geocoding data attempting to alter LLM emergency output.
* **Mitigations:**
  * Strict schema parsing via Pydantic; LLM input fields are strictly delimited; output is validated against rigid JSON Schema prior to message transmission.
