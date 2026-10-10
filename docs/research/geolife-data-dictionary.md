# GeoLife Data Dictionary

## Purpose

This document defines the fields used by the GeoLife preprocessing pipeline and route-deviation experiments.

Raw GeoLife files are stored locally under:

```text
data/raw/geolife/
```

Generated processed files are written under:

```text
data/processed/geolife/
```

Raw and processed datasets are ignored by Git and must not be committed.

## Output Schema

| Field | Type | Description |
|---|---|---|
| `user_id` | string | Stable pseudonymous user identifier derived from the GeoLife user folder, for example `geolife_000`. |
| `trajectory_id` | string | Unique trajectory identifier composed of the user ID and original trajectory filename. |
| `timestamp` | datetime | Date and time of the GPS observation. Observations are ordered chronologically within each trajectory. |
| `latitude` | float | Latitude in decimal degrees. Valid range is `-90` to `90`. |
| `longitude` | float | Longitude in decimal degrees. Valid range is `-180` to `180`. |
| `altitude_meters` | float or null | Altitude converted from feet to metres. Missing GeoLife altitude values are represented by `-777` and converted to null. |
| `accuracy_meters` | float or null | GPS accuracy in metres. GeoLife does not provide this field, so it remains null. |
| `gap_seconds` | float | Number of seconds since the previous observation in the same trajectory. The first observation has a value of `0`. |
| `is_gap_over_threshold` | boolean | Indicates whether the time gap exceeds the configured threshold. The provisional default threshold is 60 seconds. |
| `split` | string | Chronological evaluation assignment: `reference`, `validation`, `test`, or `cold_start`. This field is present in the split manifest. |

## Source Fields

GeoLife `.plt` files contain:

```text
latitude
longitude
unused
altitude_feet
days
date
time
```

The preprocessing pipeline creates the following additional fields:

```text
user_id
trajectory_id
timestamp
altitude_meters
accuracy_meters
gap_seconds
is_gap_over_threshold
```

The original `altitude_feet` field is converted to `altitude_meters` in the processed output.

## Data Cleaning Rules

The preprocessing pipeline applies these rules:

1. The six-line GeoLife header is skipped.
2. Date and time are combined into `timestamp`.
3. Rows with invalid timestamps are removed.
4. Rows with invalid latitude or longitude values are removed.
5. Altitude value `-777` is treated as missing.
6. Valid altitude values are converted using:

```text
altitude_meters = altitude_feet × 0.3048
```

7. Observations are sorted chronologically within each trajectory.
8. Time gaps are calculated between consecutive observations.
9. Gaps over the configured threshold are flagged.
10. Missing points are not interpolated.
11. Trajectories are not split by the preprocessing pipeline; gap-based segmentation is handled separately when required.

## Gap Handling

The current provisional threshold is:

```text
60 seconds
```

A gap greater than 60 seconds is recorded as:

```text
is_gap_over_threshold = true
```

The original trajectory remains the source of truth for chronological split assignment. If later processing creates child segments such as:

```text
trajectory_01_seg0
trajectory_01_seg1
```

each child segment inherits the split of its parent trajectory.

Segmentation must not change:

- User trajectory counts
- Minimum-history eligibility
- Reference/validation/test assignment
- Cold-start classification

## Split Assignments

The chronological split manifest uses the following policy for users with at least five trajectories:

- Earliest 60%: `reference`
- Next 20%: `validation`
- Remaining 20%: `test`

Users with fewer than five trajectories are assigned to:

```text
cold_start
```

Trajectories are sorted by their start timestamp before assignment. Validation and test trajectories must occur later than the reference trajectories for the same user.

## Route-Deviation Baseline Fields

The initial route-deviation baseline uses:

```text
user_id
trajectory_id
timestamp
latitude
longitude
```

Altitude is retained as supplemental information but is not used by the initial DTW baseline.

The baseline may later derive:

- Speed
- Bearing
- Distance travelled
- Stop duration
- Gap statistics

These derived features are not currently required for the initial DTW comparison.

## Missing and Unsupported Fields

GeoLife does not provide:

- GPS accuracy
- Accelerometer data
- Gyroscope data
- Audio data
- Camera or vision data
- Safety labels
- Danger labels
- Ground-truth route-anomaly labels

Therefore, the current dataset supports mobility and route-deviation research, but it does not directly support danger classification.

## Privacy and Governance

GPS trajectories represent human mobility patterns and may reveal sensitive locations or routines.

The following rules apply:

- Raw GeoLife files must remain outside Git.
- Processed datasets must remain outside Git.
- Only code, documentation, schemas, and reproducible instructions may be committed.
- Dataset access and licensing terms must be checked before commercial or startup use.
- User IDs are pseudonymous and must not be treated as real identities.

## Limitations

- Sampling intervals are irregular.
- Some trajectories contain large timestamp gaps.
- Data volume is unequal across users.
- Geographic coverage reflects the original GeoLife collection.
- Transportation labels exist only for some users.
- Transportation labels are not safety labels.
- The dataset is not globally representative.
- Evaluation results should be reported as a proof of concept on historical mobility data.

## Ownership

Primary owner:

```text
Member 2 — Data Science and Data Engineering Lead
```

Coordination partners:

- Member 1: route-deviation model, evaluation, risk integration
- Member 3: mobile telemetry and backend data contract
- Member 4: audio, vision, and edge data requirements