# WEGOTCHU: Milestones & Exit Criteria

## 1. Milestone Tracking Table

| Milestone | Deliverable Goal | Target Month | Exit Criteria |
| :--- | :--- | :--- | :--- |
| **M1: Repository & Scaffolding** | Complete architecture, safety policy, contracts, and repository structure. | Month 1 | All docs approved; CI pipeline active; initial 43 issues tracked. |
| **M2: Data & Baseline Models** | Clean ingestion pipelines, dataset manifests, and classical ML baselines. | Month 2 | Reproducible ingestion scripts running; baseline F1 scored on UCI HAR. |
| **M3: Kinematic Anomaly Engine** | Feature extraction pipeline and unsupervised kinematic anomaly detector. | Month 3 | Working anomaly detector achieving $< 5\%$ FPR on daily ADL benchmarks. |
| **M4: Temporal & Baseline Model** | Temporal sequence model (GRU/TCN) and individualized baseline adaptation. | Month 4 | Statistically significant FPR reduction ($p < 0.05$) vs. static ML. |
| **M5: Android Client MVP** | Native Android app with Safety Mode, Manual SOS, and background sensor capture. | Month 5 | App streams 50Hz IMU + 1Hz GPS with $< 2.5\%$ battery drain/hr; SOS latency $< 100$ ms. |
| **M6: GenAI & Dispatch Service** | Structured LLM communication synthesis and trusted contact alerting. | Month 6 | 100% structured JSON validation; automated fallback on LLM failure. |
| **M7: Evaluation & Ablations** | Full empirical benchmarking across all 8 experimental tiers. | Month 7 | Research results documented in LaTeX/tables; PR-AUC and ECE verified. |
| **M8: Final Defense & Launch** | Dissertation submission, prototype release, and startup demo day. | Month 8 | Working prototype demonstrated; research paper submitted. |
