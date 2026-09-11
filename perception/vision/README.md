# Module: Computer Vision Context (P2) (`perception/vision/`)

## Purpose & Scope
Provides optional ambient environmental context (e.g., ambient illumination level, high-level scene classification, crowd density estimation) when Safety Mode is actively engaged.

## Primary Owner
* **Lead:** Member 4 (CV, Audio & Edge AI Lead)

## Constraints & Safety Policies
* **No Facial Recognition:** Biometric facial identification or tracking is strictly prohibited.
* **Ephemeral Processing:** Raw camera frames are analyzed in volatile memory for optical flow / ambient lux and instantly discarded.
* **Explicit User Opt-in:** Vision features are classified as Priority P2 and require explicit user activation.
