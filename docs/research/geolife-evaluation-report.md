# GeoLife Route-Deviation Evaluation Report Template

## Purpose

This document is a template for recording the results of the personalized
route-deviation evaluation on the GeoLife dataset.

The methodology and evaluation configuration are defined now. The numerical
results will be added after the large-dataset evaluation completes.

## Configuration

- Minimum history: 5 trajectories
- Reference split: 60%
- Validation split: 20%
- Test split: 20%
- Evaluation order: chronological
- Historical references: same user only
- Future-data leakage: prevented
- Score normalization: fitted only on reference data

## Dataset Summary

| Metric | Value |
|---|---:|
| Users | 182 |
| Total trajectories | 18,670 |
| Reference trajectories | 11,105 |
| Validation trajectories | 3,664 |
| Test trajectories | 3,850 |
| Cold-start users | 22 |

Counts are derived from the checked-in split manifest. It marks 51 trajectories
as cold-start and 160 users as personalization-eligible; 135 users have at
least five reference trajectories and at least one validation or test
trajectory.

## Evaluation Results

| Metric | Validation | Test |
|---|---:|---:|
| Candidates | Pending | Pending |
| Successfully scored | Pending | Pending |
| Skipped candidates | Pending | Pending |
| Mean deviation score | Pending | Pending |
| Median deviation score | Pending | Pending |
| Minimum score | Pending | Pending |
| Maximum score | Pending | Pending |

## Bounded Exploratory Sample

The full-dataset evaluation remains pending. A bounded descriptive run selected
three low-volume users with at least five reference trajectories and both
validation and test data. The run streamed through 11,650,000 CSV rows and
retained 3,926 observations across 41 manifest trajectories (24 reference,
7 validation, 10 test). Gap segmentation produced 361 trajectory segments.

| Metric | Validation | Test |
|---|---:|---:|
| Candidate segments | 53 | 55 |
| Successfully scored | 53 | 55 |
| Insufficient history | 0 | 0 |
| Median raw DTW distance (m) | 1,080.50 | 790.73 |
| 90th-percentile raw DTW distance (m) | 9,936.52 | 2,597.26 |
| Median normalized deviation score | 0.00964 | 0.00623 |

Across the 108 scored segments, raw DTW distance was 32.90 / 4,467.55 /
212,091.37 m (min/mean/max), and normalized deviation score was 0.00000 /
0.02772 / 1.00000 (min/mean/max). This low-volume, lexically early sample is
descriptive only and is not representative evidence of generalization or
accuracy. Segment counts exceed manifest counts because long observation gaps
split source trajectories into multiple segments. GeoLife has no safety labels,
so these values do not measure danger-detection performance.

## Interpretation

The deviation score represents unusual movement relative to a user's historical
trajectories. It is not a probability of danger or manipulation.

## Limitations

- GeoLife has no safety or danger labels.
- GPS sampling intervals are irregular.
- Users have unequal trajectory counts.
- Cold-start users have insufficient personal history.
- Results represent a proof of concept on historical mobility data.
- Full evaluation is currently pending because the large processed dataset
  requires loader-performance optimization.


## Raw Evaluation Metrics

The following values will be populated after the evaluator completes:

| Metric | Validation | Test |
|---|---:|---:|
| Candidate trajectories | Pending | Pending |
| Successfully scored | Pending | Pending |
| Skipped candidates | Pending | Pending |
| Mean raw DTW distance | Pending | Pending |
| Median raw DTW distance | Pending | Pending |
| Minimum raw DTW distance | Pending | Pending |
| Maximum raw DTW distance | Pending | Pending |
