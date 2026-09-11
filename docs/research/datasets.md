# WEGOTCHU: Dataset Research, Curation & Governance

## 1. Ethical Governance & Data Categories

WEGOTCHU strictly upholds privacy by design and research ethics. Contributors must never harvest, scrape, or commit unconsented personal data.

Data sources are categorized into three distinct regimes:

```
┌─────────────────────────────────────────────────────────────┐
│ 1. PUBLIC BENCHMARK DATA                                   │
│ Open-source, peer-reviewed academic datasets for baseline  │
│ motion, fall detection, and environmental audio.           │
├─────────────────────────────────────────────────────────────┤
│ 2. CONTROLLED EXPERIMENT DATA                              │
│ Synthetic or staged sensor recordings conducted by the     │
│ research team under controlled, documented protocols.       │
├─────────────────────────────────────────────────────────────┤
│ 3. CONSENTED REAL-WORLD DATA                               │
│ Telemetry collected exclusively from fully informed,       │
│ consenting participants with explicit opt-in and right     │
│ to deletion.                                                │
└─────────────────────────────────────────────────────────────┘
```

> [!CAUTION]
> **Strict Repository Rule:**  
> Raw data files must **NEVER** be committed to Git. All dataset files belong in `data/raw/`, `data/processed/`, or `data/features/`, which are enforced in `.gitignore`. Only metadata documentation and reproducible download/preprocessing scripts are permitted in the repository.

---

## 2. Dataset Intake Specification Template

Member 2 (Data Science Lead) must document all candidate datasets using the following standardized intake template before integrating them into pipelines:

```markdown
### [Dataset Name]
- **Modality:** [IMU / GPS / Audio / Vision / Multimodal]
- **Source / Reference:** [URL or Paper Citation]
- **License:** [e.g., CC BY 4.0, MIT, Research Only, Non-Commercial]
- **Size on Disk:** [e.g., 2.4 GB]
- **Target Labels / Classes:** [e.g., Walking, Running, Fall, Distress Scream]
- **Sampling Frequency:** [e.g., 50 Hz accelerometer, 16 kHz audio]
- **Relevant Features:** [e.g., 3-axis accel, 3-axis gyro, timestamp, lat/lon]
- **Target Use Case:** [e.g., Kinematic baseline training for Exp 2 and Exp 4]
- **Known Limitations:** [e.g., Phone kept exclusively in front pocket; lacks handheld variance]
- **Privacy Concerns:** [e.g., Contains GPS traces of specific university campus; requires spatial obfuscation]
- **Commercial-Use Restrictions:** [e.g., Permitted for academic research only; must replace before commercialization]
- **Data Category:** [Public Benchmark / Controlled Experiment / Consented Real-World]
```

---

## 3. Preliminary Benchmark Dataset Candidates (For Evaluation)

The following peer-reviewed academic datasets are currently under evaluation for baseline training:

### A. Kinematics & Motion (IMU)
1. **UCI Human Activity Recognition (HAR) Using Smartphones:**
   * *Modality:* 3-axis accelerometer and gyroscope at 50 Hz.
   * *Labels:* Walking, walking upstairs, walking downstairs, sitting, standing, laying.
   * *License:* Non-commercial academic research.
   * *Role in WEGOTCHU:* Pre-training kinematic feature extractor and activity baseline classifier.
2. **MobiFall & SisFall Datasets:**
   * *Modality:* Smartphone and wearable accelerometer/gyroscope.
   * *Labels:* Falls, slips, sudden trips vs. activities of daily living (ADL).
   * *Role in WEGOTCHU:* Benchmarking sudden kinetic anomaly detection algorithms.

### B. Acoustic & Environmental Audio
1. **AudioSet (Google Research - Distress & Emergency Subsets):**
   * *Modality:* 16 kHz acoustic clips.
   * *Labels:* Screaming, shouting, sirens, breaking glass, crying.
   * *License:* CC BY 4.0 (AudioSet ontology).
   * *Role in WEGOTCHU:* Benchmarking acoustic distress anomaly detection.
2. **ESC-50 (Dataset for Environmental Sound Classification):**
   * *Modality:* 5-second acoustic recordings (44.1 kHz).
   * *Labels:* 50 environmental sound classes (footsteps, sirens, dog barking, exterior noise).
   * *Role in WEGOTCHU:* Negative-class noise suppression to reduce audio false positives.

### C. Geospatial & Trajectory
1. **GeoLife GPS Trajectories (Microsoft Research Asia):**
   * *Modality:* GPS coordinates, altitude, timestamp.
   * *Labels:* Routine commute corridors, walking trajectories, transit modes.
   * *Role in WEGOTCHU:* Evaluating route deviation algorithms and personal spatial baselines.

---

## 4. Controlled Data Collection Protocol (Drafting Guidelines)

When collecting team-generated synthetic or staged telemetry in Month 2:
1. **Informed Written Consent:** All participants must sign a consent release stating the exact scope of data recorded.
2. **Zero Involuntary Capture:** Never record bystanders or non-consenting individuals.
3. **No Weapon or Real Threat Simulation in Public Spaces:** Controlled physical tests (e.g., running, fast walking, sudden stops) must be conducted in safe, private, or designated university test spaces.
4. **Immediate De-identification:** GPS traces must be offset/normalized, and audio samples stripped of vocal biometric identifiers.
