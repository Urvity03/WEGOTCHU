# Module: Audio Perception (`perception/audio/`)

## Purpose & Scope
Processes environmental soundscapes to detect acoustic indicators of distress (e.g., screams, calls for help, violent impacts) while strictly respecting user privacy.

## Primary Owner
* **Lead:** Member 4 (CV, Audio & Edge AI Lead)

## Key Responsibilities
* In-memory ephemeral audio buffering (16 kHz, max 3 seconds in volatile RAM).
* Acoustic feature extraction: Short-Time Fourier Transform (STFT), log-Mel spectrograms, MFCCs.
* Environmental noise suppression and Signal-to-Noise Ratio (SNR) estimation.
* Acoustic distress scoring via lightweight 1D-CNN or MobileNet-v3.

## Privacy Guarantee
Raw audio waveforms are processed in-memory and immediately discarded. Raw audio is never written to persistent disk storage or uploaded to the cloud.
