# Module: Anomaly Detection (`ai/anomaly_detection/`)

## Purpose & Scope
This module is responsible for identifying statistical departures from normal mobility and sensor behavior. It focuses on unsupervised and semi-supervised techniques that detect point and contextual anomalies without requiring labeled crisis datasets.

## Primary Owner
* **Lead:** Project Lead (Member 1)
* **Collaborator:** Member 2 (Data Science Lead)

## Inputs & Outputs
* **Input:** Windowed kinematic feature vectors (from `data/features/`).
* **Output:** Normalized anomaly score $[0.0, 1.0]$ and reconstructed feature error vector.

## Current Implementation
* **`ai/anomaly_detection/motion.py`**:
  * `MotionSample`: Typed representation of 3-axis accelerometer observations, optional gyroscope observations, and speed.
  * `MotionFeatures`: Kinematic time-domain metrics including acceleration magnitude, dynamic acceleration ($|\|a\| - g|$), and differential jerk ($\|da/dt\|$).
  * `MotionAnomalyDetector`: Deterministic, bounded kinematic baseline scoring motion windows into `[0.0, 1.0]` with inferred qualitative motion state (`still`, `walking`, `running`, `abrupt_motion`).
  * Explicit handling of missing data, insufficient observations, and unphysical corrupted sensor spikes.

## Key Algorithms & Scaffolding
* Kinematic Jerk & Dynamic Acceleration Baseline (Active v0.1)
* Isolation Forest (`sklearn.ensemble.IsolationForest`) (Planned P1)
* One-Class Support Vector Machines (OC-SVM) (Planned P1)
* Deep Autoencoder (PyTorch) (Planned P1)

## Research & Milestones
* **Month 1 (Complete):** Deterministic kinematic motion anomaly baseline and telemetry windowing.
* **Month 2:** Benchmark Isolation Forest baseline against UCI HAR and MobiFall.
* **Month 3:** Implement online streaming anomaly scoring.
