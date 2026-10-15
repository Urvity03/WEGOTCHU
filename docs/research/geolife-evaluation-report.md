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
| Users | Pending |
| Total trajectories | Pending |
| Reference trajectories | Pending |
| Validation trajectories | Pending |
| Test trajectories | Pending |
| Cold-start users | Pending |

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