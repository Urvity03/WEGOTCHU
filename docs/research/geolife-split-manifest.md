# GeoLife Chronological Split Manifest

## Purpose

This manifest assigns each GeoLife source trajectory to a chronological
reference, validation, test, or cold-start group for the personalized
route-deviation baseline.

## Split policy

For users with at least 5 trajectories:

- 60% earliest trajectories: `reference`
- 20% following trajectories: `validation`
- remaining later trajectories: `test`

Users with fewer than 5 trajectories are assigned `cold_start` because they do
not have sufficient history for the initial personalized baseline.

The 5-trajectory minimum is provisional and may be revised after baseline
evaluation.

## Chronological ordering

Trajectories are sorted by:

1. `user_id`
2. `start_timestamp`
3. `trajectory_id`

The trajectory ID is used as a deterministic tie-breaker when two trajectories
have the same start timestamp.

## Leakage prevention

Reference, validation, and test assignments are made chronologically for each
user.

Validation and test trajectories occur later than the reference trajectories.
Future trajectories are never used to build the historical reference set.

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

## Segmentation and split inheritance

The manifest assigns splits at the original GeoLife trajectory level before
gap-based segmentation.

If the route-deviation loader divides a source trajectory into child segments
with IDs such as `_seg0`, `_seg1`, or `_seg2`, every child segment inherits the
split assigned to its parent trajectory.

For example, if:

```text
geolife_000/trajectory_01
```

is assigned to `reference`, then:

```text
geolife_000/trajectory_01_seg0
geolife_000/trajectory_01_seg1
```

also remain in the `reference` split.

Segmentation must not change:

- user trajectory counts
- the minimum-history eligibility decision
- reference, validation, or test assignment
- cold-start status

The parent trajectory ID must remain available for traceability. A source
trajectory must not produce child segments in different evaluation partitions.

## Limitations

This manifest describes dataset partitioning. It does not provide safety or
danger labels.

GeoLife transportation-mode labels are available only for some users and are
not safety labels. The manifest supports mobility and route-deviation research,
not direct danger classification.