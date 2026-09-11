# Module: Data Governance & Pipelines (`data/`)

## Purpose & Scope
This directory contains ingestion, preprocessing, and feature engineering pipelines.

## Directory Structure
* `raw/`: Unprocessed public benchmark data and controlled test recordings. **(Ignored by Git)**
* `processed/`: Cleaned, resampled, and synchronized sensor streams. **(Ignored by Git)**
* `features/`: Extracted feature matrices ready for model training. **(Ignored by Git)**

## Primary Owner
* **Lead:** Member 2 (Data Science & Data Engineering Lead)

## Core Standards
* Raw datasets must never be committed to Git.
* Ingestion pipelines must be deterministic, reproducible, and documented in `docs/research/datasets.md`.
* Feature extraction code must adhere to schemas defined in `docs/architecture/data-flow.md`.
