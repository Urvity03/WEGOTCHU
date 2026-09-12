# WEGOTCHU: Research Formulation

## 1. Main Research Question

> **"Can personalized and time-aware AI improve the detection of unusual situations in a person's everyday movement compared with approaches that do not consider their individual behavior?"**

The broader goal of WEGOTCHU is to explore whether AI can recognize meaningful changes in a person's usual patterns early enough to support a proactive safety check-in.

The system should not assume that an unusual action means that a person is in danger. Instead, it should identify changes that are unusual for that particular person and use them as one signal in a broader safety assessment.

---

## 2. Initial AI/ML Problem: Personalized Route-Deviation Detection

The first stage of the project focuses on **personalized route-deviation detection**.

The initial model will estimate how unusual a person's current route is compared with their previous travel patterns.

### Input Telemetry
The initial system will work primarily with:
* **Location** (Latitude, Longitude, Altitude)
* **Timestamp** (ISO-8601 UTC timestamp)
* **Speed** (Instantaneous velocity over ground, m/s)
* **Heading** (Bearing degrees $[0, 360)$)
* **GPS Accuracy** (Horizontal accuracy radius in meters)
* **Trip Information** (Trip ID, origin hint, start time, active duration)

*Additional features (e.g., perpendicular corridor distance, heading variance, velocity delta, spatial envelope boundaries) can be derived from these signals during preprocessing.*

### Output Specification
The model will produce a continuous **route-anomaly score** $[0.0, 1.0]$ representing how different the current trip is from the person's historical travel behavior.

> [!IMPORTANT]
> The anomaly score is **not a direct measure of danger**.  
> For example, taking a completely new route may be unusual while still being perfectly safe.

---

## 3. Supporting Questions

The project will gradually investigate the following scientific and engineering questions:

1. **Route Deviation:**  
   *Can a system identify when a person's current route differs substantially from their usual routes?*
2. **Personalization:**  
   *Does learning an individual's normal travel behavior reduce unnecessary alerts compared with using the same model for everyone?*
3. **Temporal Context:**  
   *Does considering how behavior changes over time improve detection compared with evaluating individual observations independently?*
4. **Multimodal Information:**  
   *Can combining location, movement, audio, and other available signals provide a more reliable picture than relying on a single signal?*
5. **Practical Deployment:**  
   *Can the resulting models operate efficiently enough for a real-time mobile safety application?*

---

## 4. Research Approach: Incremental Progression

The project will develop the system incrementally rather than starting with a complex model:

```text
Simple route-deviation baseline
            ↓
Classical anomaly detection
            ↓
Personalized behavioral model
            ↓
Temporal modeling
            ↓
Multimodal risk estimation
            ↓
Safety Intelligence Engine
```

Each stage will be evaluated against the previous stage to determine whether the additional complexity provides a meaningful improvement.

### Evaluation Metrics & Benchmarking Criteria

| Metric | Scientific Purpose | Target Optimization |
| :--- | :--- | :--- |
| **Precision** | Fraction of flagged deviations that represent genuine statistical anomalies. | High (mitigate alert fatigue) |
| **Recall (Sensitivity)** | Fraction of actual route anomalies successfully detected. | Priority ($\ge 95\%$) |
| **F1-Score / Macro-F1** | Harmonic mean of Precision and Recall across imbalanced trajectories. | Primary evaluation metric |
| **False Positive Rate (FPR)** | Rate at which routine movement is incorrectly flagged as unusual. | Target $< 2\%$ in daily usage |
| **False Negative Rate (FNR)** | Missed deviation rate on anomalous trajectories. | Target $< 1\%$ |
| **PR-AUC** | Area under Precision-Recall curve under heavy imbalance. | Target PR-AUC $> 0.85$ |
| **Expected Calibration Error (ECE)** | Reliability of continuous anomaly and risk scores. | Target ECE $< 0.05$ |
| **Inference Latency** | Execution time per route-point evaluation on mobile edge. | Target $< 50$ ms |
| **Battery Drain** | Energy consumed by background trajectory tracking. | Target $< 2.5\%$ battery / hour |

---

## 5. Important Research Principles

1. **Risk Estimation, Not Certainty:**  
   WEGOTCHU is intended to **estimate risk and identify unusual patterns, not to make absolute claims about whether someone is safe or unsafe**.
2. **Evidence, Not Decision:**  
   An AI-generated result is treated as one source of evidence within a broader safety context.
3. **Separation of Policy and Intelligence:**  
   Any real-world intervention, such as a proactive check-in, will be controlled by a separate, deterministic safety-policy layer rather than being decided directly by a generative AI model.
