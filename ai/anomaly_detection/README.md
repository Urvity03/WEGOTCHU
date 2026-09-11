# Module: Anomaly Detection (`ai/anomaly_detection/`)

## Purpose & Scope
This module is responsible for identifying statistical departures from normal mobility and sensor behavior. It focuses on unsupervised and semi-supervised techniques that detect point and contextual anomalies without requiring labeled crisis datasets.

## Primary Owner
* **Lead:** Project Lead (Member 1)
* **Collaborator:** Member 2 (Data Science Lead)

## Inputs & Outputs
* **Input:** Windowed kinematic feature vectors (from `data/features/`).
* **Output:** Normalized anomaly score $[0.0, 1.0]$ and reconstructed feature error vector.

## Key Algorithms & Scaffolding
* Isolation Forest (`sklearn.ensemble.IsolationForest`)
* One-Class Support Vector Machines (OC-SVM)
* Deep Autoencoder (PyTorch)

## Research & Milestones
* **Month 2:** Benchmark Isolation Forest baseline against UCI HAR and MobiFall.
* **Month 3:** Implement online streaming anomaly scoring.
