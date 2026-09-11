# Module: Machine Learning Experiments (`experiments/`)

## Purpose & Scope
Tracks reproducible exploratory research notebooks, hyperparameter searches, and benchmark evaluation logs across the 8 planned experimental tiers.

## Rules for Experimentation
1. **Random Seed Locking:** Every notebook/script must explicitly seed all PRNGs (`numpy`, `torch`, `random`).
2. **Configuration Logging:** Hyperparameters, dataset versions, and evaluation splits must be documented.
3. **No Checked-in Datasets:** Datasets must load from local `data/` or download scripts.
4. **Naming Convention:** `exp<number>_<description>.py` or `.ipynb` (e.g., `exp01_rule_based_baseline.py`).
