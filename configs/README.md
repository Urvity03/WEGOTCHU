# Module: System Configurations (`configs/`)

## Purpose & Scope
Stores configuration files for model hyperparameters, feature extraction windows, safety policy thresholds, and environment settings.

## Format
* Use YAML or JSON configuration files.
* Production secrets must never be placed in config files; reference environment variables from `.env` instead.
