# WEGOTCHU: Academic Literature Survey

## 1. Domain Overview

The development of a proactive personal safety intelligence system spans five distinct research disciplines:
1. Smartphone Sensor-Based Human Activity Recognition (HAR) & Kinematic Anomaly Detection.
2. Temporal Sequence Modeling for Behavioral Trajectory Analysis.
3. Multimodal Information Fusion in Resource-Constrained Environments.
4. Acoustic Distress Recognition & Environmental Noise Suppression.
5. Edge Machine Learning & Privacy-Preserving Computing.

---

## 2. Key Scholarly Findings & Methodological Foundations

### A. Sensor Anomaly Detection & Kinematics
* **Lara & Labrador (2013), "A Survey on Human Activity Recognition using Wearable Sensors":**  
  Demonstrated that time-domain features (mean, standard deviation, root mean square) combined with frequency-domain features (spectral energy, dominant frequency) from tri-axial accelerometers achieve $> 90\%$ accuracy for canonical activity categorization, but suffer from high false-alarm rates when deployed in uncontrolled environments without user calibration.
* **Chandola, Banerjee, & Kumar (2009), "Anomaly Detection: A Survey":**  
  Classified anomaly detection into point anomalies, contextual anomalies, and collective anomalies. Personal safety incidents belong predominantly to **contextual and collective anomalies**, where an isolated sensor reading is not intrinsically illegal, but its temporal sequence and context render it hazardous.

### B. Temporal Sequence Modeling
* **Bai, Kolter, & Koltun (2018), "An Empirical Evaluation of Generic Convolutional and Recurrent Networks for Sequence Modeling":**  
  Showed that Temporal Convolutional Networks (TCN) frequently outperform canonical RNNs/LSTMs in sequence modeling tasks while enabling parallelized training, deterministic receptive field sizes, and stable gradients. WEGOTCHU will benchmark TCNs against GRUs for edge temporal modeling.
* **Vaswani et al. (2017) & Mobile Transformer Variants:**  
  While multi-head self-attention captures long-range dependencies, transformer quadratic complexity poses challenges for continuous mobile execution. Lightweight alternatives (e.g., MobileViT or 1D-Linformer) are considered for cloud-assisted temporal aggregation.

### C. Multimodal Fusion Strategies
* **Baltrušaitis, Ahuja, & Morency (2018), "Multimodal Machine Learning: A Survey and Taxonomy":**  
  Synthesized multimodal paradigms into early, late, and intermediate/hybrid fusion. In mobile safety systems, **late and hybrid fusion** provide superior fault tolerance: if one sensor channel fails or encounters high ambient noise, unimodal confidence gating prevents corruption of the overall risk score.

### D. Acoustic Distress Detection
* **Ntalampiras et al. (2011), "Acoustic Detection of Hazardous Situations in Urban Environments":**  
  Evaluated hidden Markov models (HMMs) and Gaussian mixture models for identifying screams and gunshots in public soundscapes. Identified that ambient urban noise (traffic, wind) causes significant spectral masking, highlighting the necessity of SNR-aware confidence weighting.

### E. Edge AI & Privacy-Preserving Architectures
* **Howard et al. (2019), "Searching for MobileNetV3":**  
  Demonstrated the effectiveness of hardware-aware neural architecture search and quantization (INT8) for achieving low-latency edge inference with minimal degradation in top-1 accuracy.
* **McMahan et al. (2017), "Communication-Efficient Learning of Deep Networks from Decentralized Data":**  
  Established foundational principles for federated adaptation, which WEGOTCHU targets in future milestones (P2) to adapt personal baseline weights on-device without exfiltrating location or biometric traces.
