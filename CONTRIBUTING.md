# WEGOTCHU Contribution Guide

Welcome to the **WEGOTCHU** engineering and research team. This document defines the development standards, Git workflow, security rules, and code quality expectations for all 4 team members.

---

## 1. Core Engineering Rules

1. **No Direct Pushes to `main`:** The `main` branch is protected. All changes must arrive via Pull Requests.
2. **Issue First:** Before beginning significant work, ensure a tracking issue exists on the GitHub Project Board.
3. **Dedicated Branches:** Create a focused branch for every task or experiment.
4. **Follow Naming Conventions:** Adhere to branch and commit conventions strictly.
5. **Local Verification:** Run test suites and linting checks locally before opening a PR.
6. **Thorough Documentation:** Update relevant documentation in `docs/` whenever interfaces, architectures, or schemas change.
7. **Peer Review Required:** Every Pull Request must be reviewed and approved by at least one other team member before merging.
8. **Atomic Commits:** Keep commits logical, focused, and well-described.
9. **Zero Secrets Policy:** NEVER commit API keys, tokens, passwords, or connection strings.
10. **Zero Private Data Policy:** NEVER commit raw personal telemetry, identifiable audio recordings, or location logs.
11. **No Large Datasets:** Datasets must reside outside version control (use `data/raw/` with `.gitignore` and link via storage manifests).
12. **Reproducible Research:** All machine learning experiments must document random seeds, environment dependencies, and configurations.
13. **Deterministic Safety Isolation:** Code that determines safety escalation must remain deterministic. Never allow an LLM to override safety states.
14. **No Premature Overengineering:** Build according to current milestone specifications. Do not add speculative dependencies.
15. **Respect Modality Ownership:** Consult module leads before altering cross-module interfaces.

---

## 2. Branch Naming Conventions

Branches must use lowercase alphanumeric characters and hyphens, structured as follows:

| Prefix | Usage | Example |
| :--- | :--- | :--- |
| `feature/` | Implementation of new functional code or pipelines | `feature/risk-engine` |
| `fix/` | Bug fixes or interface corrections | `fix/sensor-timestamp-parsing` |
| `research/` | ML exploratory code, baseline notebooks, or evaluations | `research/temporal-model-experiment` |
| `docs/` | Updates to architecture, documentation, or specifications | `docs/system-architecture` |
| `refactor/` | Code structure refactoring without changing functionality | `refactor/audio-feature-extractor` |
| `test/` | Adding or updating unit and integration test suites | `test/fusion-calibration` |

---

## 3. Commit Message Standards

WEGOTCHU enforces the **Conventional Commits** specification:

`<type>(<optional scope>): <description>`

### Types
* `feat`: A new feature or pipeline capability.
* `fix`: A bug fix.
* `research`: A research notebook, experiment script, or evaluation.
* `docs`: Documentation updates only.
* `test`: Adding or correcting tests.
* `refactor`: Code refactoring without behavioral alterations.
* `chore`: Tooling, dependency, or configuration updates.

### Examples
* `feat(risk_engine): add rule-based risk baseline scoring`
* `feat(audio): implement spectral flux and Mel-spectrogram extractor`
* `fix(mobile): correct timestamp synchronization between GPS and IMU`
* `docs(architecture): update data contract schemas to v0.1`
* `research(temporal): add LSTM baseline benchmark on UCI HAR dataset`
* `chore(ci): configure automated flake8 and pytest workflow`

---

## 4. Pull Request (PR) Workflow

1. **Pull Latest Main:** Ensure your local branch is rebased on the latest `main`.
2. **Verify Tests & Linting:**
   ```bash
   flake8 .
   black --check .
   pytest tests/
   ```
3. **Submit PR:** Use the provided Pull Request Template (`.github/pull_request_template.md`).
4. **Assign Reviewers:**
   * AI/ML/GenAI tasks: Assign Project Lead.
   * Data tasks: Assign Member 2.
   * Mobile/Backend tasks: Assign Member 3.
   * Perception/Audio/Vision/Edge tasks: Assign Member 4.
5. **Address Feedback:** Resolve comments and re-request review.
6. **Squash & Merge:** Once approved and CI passes, squash and merge into `main`.

---

## 5. Data & Model Weight Storage Guidelines

* **Raw Data:** Store exclusively in local `data/raw/` (ignored by Git).
* **Processed Data:** Store in `data/processed/` (ignored by Git).
* **Feature Matrices:** Store in `data/features/` (ignored by Git).
* **Dataset Manifests:** Document dataset sources, licenses, and preprocessing parameters in `docs/research/datasets.md`.
* **Model Checkpoints:** Do NOT commit `.pt`, `.onnx`, or `.tflite` files to Git. Store weights in cloud artifact storage (e.g., Google Drive / AWS S3 / HuggingFace Hub) and document download links in `models/README.md`.

---

## 6. Security & Vulnerability Reporting

If you identify a security vulnerability or sensitive information accidentally committed:
1. Immediately notify the Project Lead.
2. Invalidate compromised credentials immediately.
3. Remove the sensitive commit from history using `git-filter-repo` or BFG Repo-Cleaner before any public sync.
