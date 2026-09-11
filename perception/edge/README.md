# Module: Edge AI & Quantization (`perception/edge/`)

## Purpose & Scope
Optimizes and quantizes machine learning models for low-latency, battery-efficient on-device execution on mobile hardware (ARM64 Android).

## Primary Owner
* **Lead:** Member 4 (CV, Audio & Edge AI Lead)
* **Collaborator:** Project Lead (Member 1)

## Target Runtimes & Frameworks
* ONNX Runtime Mobile
* Google LiteRT / TensorFlow Lite
* INT8 Post-Training Quantization (PTQ)

## Target Benchmarks
* **Inference Latency:** $< 100$ ms per analysis window.
* **Memory Footprint:** $< 80$ MB RAM.
* **Energy Impact:** $< 2.5\%$ battery drain per hour of active Safety Mode.
