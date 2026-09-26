# GeoLife Preprocessing Pipeline

## Purpose

`scripts/preprocess_geolife.py` converts extracted GeoLife `.plt` files into a
reproducible tabular dataset for the Phase 1 route-deviation experiment.

Raw data is read from `data/raw/geolife/`. Generated output is written under
`data/processed/`, which is ignored by Git. Raw and processed dataset files
must not be committed.

## Input and output paths

Default input:

```text
data/raw/geolife/
```

Default output:

```text
data/processed/geolife/geolife_trajectories.csv
```

## Running the pipeline

Run from the repository root:

```powershell
python scripts\preprocess_geolife.py
```

Optional arguments:

```powershell
python scripts\preprocess_geolife.py `
  --input-dir data\raw\geolife `
  --output data\processed\geolife\geolife_trajectories.csv `
  --gap-threshold-seconds 60
```

CLI arguments:

- `--input-dir`: directory containing extracted GeoLife files.
- `--output`: destination CSV path.
- `--gap-threshold-seconds`: threshold used to flag a timestamp gap. The default
  is 60 seconds and is provisional.

## Processing steps

1. Recursively find all `.plt` files under the input directory.
2. Skip the six-line GeoLife file header.
3. Parse latitude, longitude, altitude, date, and time.
4. Extract the user ID from the GeoLife user directory.
5. Create a trajectory ID from the user ID and source filename.
6. Combine date and time into a timestamp.
7. Remove invalid timestamps.
8. Remove coordinates outside valid latitude and longitude ranges.
9. Treat GeoLife altitude `-777` as missing.
10. Convert altitude from feet to metres.
11. Sort observations chronologically within each trajectory.
12. Calculate the time gap from the previous observation.
13. Flag gaps above the configured threshold.
14. Write the output incrementally to avoid loading the entire dataset into memory.

The pipeline does not interpolate missing points, split trajectories, or derive
speed and bearing. Duplicate timestamps are preserved. GeoLife does not provide
GPS accuracy, so `accuracy_meters` is left blank.

## Output schema

| Field | Description |
|---|---|
| `user_id` | Stable pseudonymous ID derived from the GeoLife user folder |
| `trajectory_id` | User ID and source trajectory filename |
| `timestamp` | Parsed observation date and time |
| `latitude` | Latitude in decimal degrees |
| `longitude` | Longitude in decimal degrees |
| `altitude_meters` | Altitude converted from feet; blank when source value is `-777` |
| `accuracy_meters` | Blank because GeoLife does not provide GPS accuracy |
| `gap_seconds` | Seconds since the previous point in the same trajectory |
| `is_gap_over_threshold` | Whether the gap exceeds the configured threshold |

The initial DTW baseline uses `user_id`, `trajectory_id`, `timestamp`,
`latitude`, and `longitude`. Altitude is retained as supplemental data but is
not an input to the initial baseline.

## Gap handling

The configured gap threshold is used to flag large time gaps. The pipeline
does not interpolate across gaps or claim that a flagged gap represents danger
or an anomaly. The threshold may be revised after further dataset analysis.

## Limitations

GeoLife does not contain safety or danger labels. Transportation-mode labels
are available only for some users and are not safety labels. The processed
dataset supports mobility and route-deviation research, not direct danger
classification.