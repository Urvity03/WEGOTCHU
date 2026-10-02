from pathlib import Path
import time
import psutil

from perception.audio.src.inference import run_audio_inference

TARGET_LATENCY_MS = 100.0
TARGET_MEMORY_MB = 80.0


def benchmark_audio_inference(
    file_path: str | Path,
    sample_rate: int = 16000,
    warmup_runs: int = 1,
    measured_runs: int = 5,
) -> dict:
    """
    Benchmark the existing audio perception pipeline.

    The measurements are host-machine measurements and should not be
    interpreted as Android ARM64 performance.
    """
    if warmup_runs < 0:
        raise ValueError("warmup_runs must be non-negative.")

    if measured_runs <= 0:
        raise ValueError("measured_runs must be greater than zero.")

    process = psutil.Process()

    for _ in range(warmup_runs):
        run_audio_inference(
            file_path=file_path,
            sample_rate=sample_rate,
        )

    latencies_ms = []
    memory_usages_mb = []

    for _ in range(measured_runs):
        memory_before_mb = process.memory_info().rss / (1024 * 1024)

        start = time.perf_counter()

        result = run_audio_inference(
            file_path=file_path,
            sample_rate=sample_rate,
        )

        elapsed_ms = (time.perf_counter() - start) * 1000.0
        memory_after_mb = process.memory_info().rss / (1024 * 1024)

        latencies_ms.append(elapsed_ms)
        memory_usages_mb.append(max(memory_before_mb, memory_after_mb))

    average_latency_ms = sum(latencies_ms) / len(latencies_ms)
    peak_latency_ms = max(latencies_ms)
    memory_usage_mb = max(memory_usages_mb)

    return {
        "average_latency_ms": float(average_latency_ms),
        "peak_latency_ms": float(peak_latency_ms),
        "memory_usage_mb": float(memory_usage_mb),
        "latency_target_ms": TARGET_LATENCY_MS,
        "memory_target_mb": TARGET_MEMORY_MB,
        "latency_target_met": average_latency_ms < TARGET_LATENCY_MS,
        "memory_target_met": memory_usage_mb < TARGET_MEMORY_MB,
        "measured_runs": measured_runs,
        "model_version": result["model_version"],
    }
