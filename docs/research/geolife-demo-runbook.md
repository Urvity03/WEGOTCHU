# GeoLife Demo Runbook

## Purpose

This runbook explains how to prepare and demonstrate the GeoLife route-deviation pipeline for WEGOTCHU.

The current demo focuses on mobility unusualness and route deviation. It does not classify danger and does not provide a calibrated safety probability.

## Requirements

- Windows PowerShell
- Python 3.11
- Git
- Extracted GeoLife dataset
- WEGOTCHU repository

Use the project virtual environment:

```powershell
.\.venv311\Scripts\Activate.ps1
python --version
```

The Python version should be 3.11.x.

## Repository Locations

Raw GeoLife data:

```text
data/raw/geolife/
```

Processed trajectory data:

```text
data/processed/geolife/geolife_trajectories.csv
```

Chronological split manifest:

```text
data/processed/geolife/geolife_split_manifest.csv
```

Preprocessing script:

```text
scripts/preprocess_geolife.py
```

Split-manifest script:

```text
scripts/create_geolife_split_manifest.py
```

Evaluation script:

```text
scripts/evaluate_route_deviation.py
```

## Data-Governance Rules

- Do not modify the raw GeoLife files.
- Do not commit raw GeoLife files.
- Do not commit processed CSV files.
- Do not commit `.venv311/`.
- Do not commit secrets or credentials.
- Processed files remain under `data/processed/`, which is ignored by Git.
- Only code, documentation, tests, and reproducible instructions may be committed.

Check that a generated file is ignored:

```powershell
git check-ignore -v data\processed\geolife\geolife_trajectories.csv
```

## Step 1: Update the Repository

```powershell
git switch main
git pull origin main
git status
```

The working tree should be clean before beginning the demo preparation.

## Step 2: Verify the Raw Dataset

Check that GeoLife trajectory files exist:

```powershell
(Get-ChildItem data\raw\geolife -Recurse -Filter *.plt -File).Count
```

Inspect the first trajectory file:

```powershell
$sample = Get-ChildItem data\raw\geolife -Recurse -Filter *.plt -File |
    Select-Object -First 1

$sample.FullName
Get-Content $sample.FullName -TotalCount 15
```

The dataset should contain `.plt` files with latitude, longitude, altitude, date, and time fields.

## Step 3: Run Preprocessing

Run the preprocessing pipeline from the repository root:

```powershell
python scripts\preprocess_geolife.py `
  --input-dir data\raw\geolife `
  --output data\processed\geolife\geolife_trajectories.csv `
  --gap-threshold-seconds 60
```

The pipeline:

1. Finds GeoLife `.plt` files.
2. Skips the six-line file header.
3. Extracts user and trajectory identifiers.
4. Parses timestamps.
5. Removes invalid timestamps and coordinates.
6. Converts altitude from feet to metres.
7. Calculates timestamp gaps.
8. Flags gaps over 60 seconds.
9. Writes the processed trajectory data.

Verify the output:

```powershell
Get-Item data\processed\geolife\geolife_trajectories.csv |
    Select-Object FullName, Length

Get-Content data\processed\geolife\geolife_trajectories.csv -TotalCount 4
```

## Step 4: Create the Chronological Split Manifest

Run:

```powershell
python scripts\create_geolife_split_manifest.py `
  --input data\processed\geolife\geolife_trajectories.csv `
  --output data\processed\geolife\geolife_split_manifest.csv `
  --minimum-history 5
```

The command above creates the chronological split manifest using the
processed trajectory file and a minimum history of five trajectories. The default split policy is:

- 60% earliest trajectories: `reference`
- 20% following trajectories: `validation`
- Remaining trajectories: `test`
- Users with fewer than 5 trajectories: `cold_start`

The manifest prevents future-data leakage by assigning trajectories chronologically for each user.

Verify the manifest:

```powershell
Get-Item data\processed\geolife\geolife_split_manifest.csv |
    Select-Object FullName, Length

Get-Content data\processed\geolife\geolife_split_manifest.csv -TotalCount 5
```

## Step 5: Run the Route-Deviation Evaluation

Run:

```powershell
python scripts\evaluate_route_deviation.py `
  --data data\processed\geolife\geolife_trajectories.csv `
  --manifest data\processed\geolife\geolife_split_manifest.csv `
  --k-min 5
```

The evaluation:

1. Loads processed trajectories.
2. Selects validation and test candidates.
3. Uses only earlier trajectories from the same user.
4. Requires at least five historical trajectories.
5. Computes route similarity using the route-deviation baseline.
6. Produces deviation scores.
7. Prevents future-data and cross-user leakage.

## Current Evaluation Limitation

The full processed GeoLife CSV is very large. The current loader may be slow because it processes rows using pandas indexing operations.

If the evaluation takes too long, stop it with `Ctrl+C` and report the issue. Do not modify the raw or processed dataset to hide the problem.

The evaluation should be rerun only after the loader is optimized or a smaller deterministic demo dataset is provided.

## Expected Data Fields

The processed trajectory output contains:

```text
user_id
trajectory_id
timestamp
latitude
longitude
altitude_meters
accuracy_meters
gap_seconds
is_gap_over_threshold
```

The split manifest contains trajectory-level assignment fields such as:

```text
user_id
trajectory_id
start_timestamp
end_timestamp
observation_count
max_gap_seconds
flagged_gap_count
trajectory_count_for_user
personalization_eligible
is_cold_start
split
```

## Demo Flow

The college demonstration should show:

```text
GeoLife trajectory input
        ↓
Preprocessing
        ↓
Chronological split assignment
        ↓
Historical reference selection
        ↓
DTW route comparison
        ↓
Route-deviation score
        ↓
Basic risk-engine input
```

The route-deviation score represents unusual movement compared with the user's historical trajectories.

It is not:

- A danger probability
- A safety label
- A manipulation probability
- A replacement for manual SOS or safety policy decisions

## Demo Explanation

A simple explanation for the college demonstration is:

> WEGOTCHU builds a historical mobility baseline for a user. When a new trajectory is received, the system compares it with earlier trajectories from the same user. A larger distance means that the movement is less similar to the user's previous behavior. This produces a route-deviation indicator that can later be combined with sensor, audio, vision, and policy signals.

## Important Limitations

- GeoLife contains no ground-truth danger labels.
- GPS sampling intervals are irregular.
- Users have unequal numbers of trajectories.
- Some users have insufficient history and are marked `cold_start`.
- Geographic coverage is limited to the original collection.
- GPS accuracy is unavailable.
- Speed and bearing are not part of the initial preprocessing output.
- Results represent a proof of concept on historical mobility data.

## Final Safety Check

Before presenting the project:

```powershell
git status
git diff --check
```

Confirm that:

- No raw dataset is staged.
- No processed CSV is staged.
- No credentials are staged.
- The project environment is Python 3.11.
- The demo commands are documented.
- The route-deviation score is described as an unusualness indicator, not a danger probability.

## Mobile Telemetry Integration

The mobile telemetry contract uses nested fields and identifies the source
device with `device_id`.

The backend or session layer must map `device_id` to a stable pseudonymous
`user_id` before personalization or route-deviation evaluation.

The raw `device_id` must not be used directly as the user's identity.

### Mobile-to-Internal Field Mapping

| Mobile contract field | Internal pipeline field |
|---|---|
| `device_id` | Map to pseudonymous `user_id` |
| `timestamp` | `timestamp` |
| `location.latitude` | `latitude` |
| `location.longitude` | `longitude` |
| `speed_mps` | `speed_mps` |
| `location.accuracy_meters` | `accuracy_meters` |
| `accelerometer.x` | `accelerometer_x` |
| `accelerometer.y` | `accelerometer_y` |
| `accelerometer.z` | `accelerometer_z` |
| `gyroscope.x` | `gyroscope_x` |
| `gyroscope.y` | `gyroscope_y` |
| `gyroscope.z` | `gyroscope_z` |

### Missing Gyroscope Data

Gyroscope fields may be unavailable on some mobile devices or during some
collection periods.

Missing gyroscope values must be represented as `null` or unavailable. They
must not cause an otherwise valid telemetry event to be rejected.

The route-deviation pipeline must continue processing location data when
gyroscope readings are missing.