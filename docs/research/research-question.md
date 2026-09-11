# WEGOTCHU: Research Formulation & Experimental Design

## 1. Primary Research Question

> **"Can personalized temporal multimodal AI improve proactive personal safety-risk estimation compared with isolated or non-personalized models?"**

---

## 2. Supporting Research Questions

To systematically decompose the primary inquiry, the research addresses six supporting scientific questions:

1. **SRQ 1 (Temporal Context):**  
   *Does incorporating temporal sequence context (e.g., GRU/TCN over multi-minute windows) significantly reduce transient false positives compared to instantaneous static ML evaluations?*
2. **SRQ 2 (Personalization):**  
   *Does conditioning anomaly detection on learned individual behavioral baselines (e.g., commute routes, baseline walking pace) achieve a statistically significant decrease in false-positive rates (FPR) without compromising recall?*
3. **SRQ 3 (Multimodal Robustness):**  
   *Does cross-modal fusion (motion kinematics + geospatial corridor adherence + acoustic distress) provide resilience against single-modality sensor noise or spoofing?*
4. **SRQ 4 (Fusion Architecture):**  
   *Which multimodal fusion paradigm (Early Feature Fusion, Late Decision Fusion, or Hybrid Cross-Attention Fusion) achieves the optimal trade-off between calibrated risk classification and computational complexity?*
5. **SRQ 5 (Edge Feasibility & Latency):**  
   *Can the proposed temporal anomaly models be quantized (INT8 via ONNX / LiteRT) to execute on mobile edge hardware with $< 100$ ms inference latency and $< 2\%$ battery consumption per hour of active Safety Mode?*
6. **SRQ 6 (Privacy vs. Utility Trade-offs):**  
   *What is the quantitative degradation in risk estimation accuracy when raw acoustic and visual data are strictly restricted to ephemeral on-device ring buffers versus centralized cloud embeddings?*

---

## 3. Planned Experimental Hierarchy

The project establishes an eight-tier experimental ladder to isolate performance gains:

```
[Experiment 1: Rule-Based Heuristic Baseline]
                      ↓
[Experiment 2: Traditional ML Baseline (Random Forest / SVM)]
                      ↓
[Experiment 3: Static ML (MLP on Independent Windows)]
                      ↓
[Experiment 4: Temporal ML (GRU / TCN Sequence Modeling)]
                      ↓
[Experiment 5: Generic Population Model]
                      ↓
[Experiment 6: Personalized Baseline Model (GMM / Online Adaptation)]
                      ↓
[Experiment 7: Single-Modal Baselines (IMU-only, Audio-only, GPS-only)]
                      ↓
[Experiment 8: Multimodal Cross-Modal Fusion Model]
```

### Experiment Descriptions
1. **Exp 1 — Rule-Based Baseline:** Static thresholding (e.g., acceleration magnitude $> 3.5g$ or speed $> 15$ km/h on foot). Acts as the traditional safety app benchmark.
2. **Exp 2 — Traditional ML Baseline:** Scikit-learn Random Forest and One-Class SVM applied to engineered statistical features over individual time windows.
3. **Exp 3 — Static Deep Learning:** Multi-Layer Perceptron (MLP) or Feed-Forward Neural Network evaluating isolated windows without temporal awareness.
4. **Exp 4 — Temporal Sequence ML:** Gated Recurrent Units (GRU) and Temporal Convolutional Networks (TCN) processing contiguous sequences of 30 to 120 seconds.
5. **Exp 5 — Generic Population Model:** Model trained uniformly across all participants without individual calibration.
6. **Exp 6 — Personalized Model:** Model augmented with individual baseline statistics (Mahalanobis distance to personal mean velocity, route corridor bounds).
7. **Exp 7 — Single-Modal Isolation:** Evaluating performance when only IMU, only Audio, or only GPS telemetry is provided to quantify modality impact.
8. **Exp 8 — Multimodal Fusion:** Full system integrating kinematic, acoustic, and geospatial streams with confidence weighting.

---

## 4. Evaluation Metrics & Benchmarking Criteria

| Metric | Scientific Purpose | Target Optimization |
| :--- | :--- | :--- |
| **Precision** | Fraction of triggered interventions that represented genuine anomalies. | High (mitigate alert fatigue) |
| **Recall (Sensitivity)** | Fraction of actual risk scenarios detected by the system. | Maximum Priority ($\ge 95\%$) |
| **F1-Score / Macro-F1** | Harmonic mean of Precision and Recall across imbalanced classes. | Primary optimization metric |
| **False Positive Rate (FPR)** | Rate at which normal behavior is incorrectly flagged as elevated risk. | Target $< 2\%$ in daily usage |
| **False Negative Rate (FNR)** | Critical safety failure rate (missed elevated/emergency events). | Target $< 1\%$ |
| **ROC-AUC & PR-AUC** | Area under ROC and Precision-Recall curves; PR-AUC is primary due to extreme class imbalance in safety anomalies. | Target PR-AUC $> 0.85$ |
| **Expected Calibration Error (ECE)** | Measures how closely predicted probability reflects real-world empirical frequency. | Target ECE $< 0.05$ |
| **Inference Latency** | Time required to process a 2.56-second window on an Android edge device. | Target $< 100$ ms |
| **Memory Footprint** | RAM consumed by the running inference runtime. | Target $< 80$ MB |
| **Battery Drain** | Energy consumption under continuous Safety Mode background monitoring. | Target $< 2.5\%$ battery / hour |
