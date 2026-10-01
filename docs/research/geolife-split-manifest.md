# GeoLife Chronological Split Manifest

## Purpose

This manifest assigns each GeoLife trajectory to a chronological reference,
validation, test, or cold-start group for the personalized route-deviation
baseline.

## Split policy

For users with at least 5 trajectories:

- 60% earliest trajectories: `reference`
- 20% following trajectories: `validation`
- remaining later trajectories: `test`

Users with fewer than 5 trajectories are assigned `cold_start` because they do
not have sufficient history for the initial personalized baseline.

## Leakage prevention

Trajectories are sorted by their start timestamp before assignment. Validation
and test trajectories occur later than reference trajectories for each eligible
user. Future trajectories are not used to build the historical reference set.

## Manifest fields

- `user_id`
- `trajectory_id`
- `start_timestamp`
- `end_timestamp`
- `observation_count`
- `max_gap_seconds`
- `flagged_gap_count`
- `trajectory_count_for_user`
- `personalization_eligible`
- `is_cold_start`
- `split`

The generated manifest and processed dataset remain under `data/processed/` and
are ignored by Git.