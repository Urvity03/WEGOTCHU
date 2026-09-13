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

#### GeoLife GPS Trajectories — Microsoft Research Asia

- **Modality:** GPS / geospatial trajectory
- **Source:** Microsoft Research GeoLife GPS Trajectories
- **Official URL:** https://www.microsoft.com/en-ie/download/details.aspx?id=52367
- **Data Category:** Public benchmark dataset
- **Number of Users:** 182, according to the official download page
- **Number of Trajectories:** Approximately 17,621
- **Available Fields:** Latitude, longitude, altitude, date, time, and trajectory file identity
- **Timestamp Resolution:** Irregular; sampling intervals vary
- **Trip Segmentation:** Trajectories are provided as separate files and can be treated as separate trips or sessions
- **Geographic Coverage:** Outdoor movement recorded through the GeoLife project
- **Annotations:** Some transportation-mode labels may be available, but the dataset does not contain safety or danger labels
- **Target Use Case:** Personalized route-deviation and mobility-baseline research
- **Derived Fields:** Speed, bearing, distance, stop duration, and deviation score
- **Missing / Noisy GPS Points:** Possible GPS gaps, noise, and irregular sampling
- **Accelerometer Availability:** Not available
- **Audio Availability:** Not available
- **Safety Labels:** Not available
- **Privacy Concerns:** GPS traces represent human mobility and must remain outside Git
- **Commercial-Use Restrictions:** Verify the source’s current access and usage terms before startup or commercial use
- **Known Limitations:** The dataset does not label routes as safe, dangerous, or unsafe
- **Phase 1 Recommendation:** Suitable for route-anomaly research, not direct danger classification

#### Compatibility with the WEGOTCHU GPS Contract

GeoLife provides:

- `timestamp`
- `location.latitude`
- `location.longitude`
- `location.altitude_meters`

The following fields must be derived or left unavailable:

- `speed_mps`: derive from consecutive GPS points
- `bearing_degrees`: derive from consecutive GPS points
- `accuracy_meters`: keep null if unavailable
- `device_id`: map to an anonymized source-user identifier
- `trajectory_id`: create from the source trajectory file

The dataset does not provide accelerometer, audio, or vision data. These modalities are outside the scope of the Phase 1 GPS experiment.

GeoLife does not contain real safety or danger labels. Phase 1 will evaluate route anomaly using historical trajectories and clearly documented controlled or synthetic evaluation cases.

#### Phase 1 Candidate Assessment

GeoLife is currently the **primary candidate** for the Phase 1 route-deviation experiment. It is not yet considered the final dataset until the team validates its structure, access terms, sampling behavior, and suitability.

The dataset contains multiple users and multiple trajectories associated with users. This allows the team to:

1. Build a route baseline for an individual user.
2. Hold out some trajectories from that user for testing.
3. Compare a personalized baseline with a general population baseline.

The dataset should not be treated as globally representative because its geographic coverage and mobility patterns come from the original GeoLife collection. Results should be reported as a proof of concept on historical mobility data.

The raw dataset will remain outside GitHub. Only metadata, documentation, and reproducible processing instructions may be committed.

#### Phase 1 Candidate Assessment

GeoLife is currently the **primary candidate** for the Phase 1 route-deviation experiment. It is not yet the final dataset until the team validates its structure, access terms, sampling behavior, and suitability.

##### Repeated Trajectories and Personalization

The dataset contains multiple users and multiple trajectory files associated with users. This allows the team to:

1. Build a route baseline for an individual user.
2. Hold out some trajectories from that user for testing.
3. Compare a personalized baseline with a general population baseline.

The exact number of usable trajectories per user must be verified during dataset inspection because the data volume may not be equal for every user.

##### Sampling Variability

GeoLife trajectories have irregular sampling intervals. Some tracks are densely sampled, while others may contain larger time or distance gaps.

The preprocessing stage must:

- Preserve the original timestamps.
- Measure time differences between consecutive points.
- Detect unusually large gaps.
- Avoid assuming a fixed sampling rate.
- Resample only if required by a later experiment.

##### Geographic Limitations

The dataset represents the geographic and mobility context of the original GeoLife collection. It should not be treated as globally representative of all cities, countries, users, or travel behaviors.

Results may be affected by:

- Limited geographic coverage.
- Local road and transport patterns.
- Differences in travel modes.
- Historical collection conditions.
- Unequal data volume between users.

Therefore, Phase 1 results should be reported as a proof of concept on historical mobility data, not as universal safety performance.

##### Access and License Considerations

The dataset source and current access terms must be recorded before use. The team must not assume that academic access automatically permits commercial or startup use.

The raw dataset will remain outside GitHub. Only documentation, metadata, and reproducible processing instructions may be committed.

##### Suitability Decision

GeoLife is suitable as the primary Phase 1 candidate because it provides:

- Multiple users
- Repeated trajectories
- Latitude and longitude
- Timestamps
- Historical trajectory sequences

The team will make the final dataset decision after validating the extracted file structure, usable trajectory counts, sampling behavior, and access terms.

---

## 4. Controlled Data Collection Protocol (Drafting Guidelines)

When collecting team-generated synthetic or staged telemetry in Month 2:
1. **Informed Written Consent:** All participants must sign a consent release stating the exact scope of data recorded.
2. **Zero Involuntary Capture:** Never record bystanders or non-consenting individuals.
3. **No Weapon or Real Threat Simulation in Public Spaces:** Controlled physical tests (e.g., running, fast walking, sudden stops) must be conducted in safe, private, or designated university test spaces.
4. **Immediate De-identification:** GPS traces must be offset/normalized, and audio samples stripped of vocal biometric identifiers.
