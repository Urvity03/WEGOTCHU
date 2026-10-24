"""Evaluation harness for the WEGOTCHU audio perception baseline."""

from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from perception.audio.src.inference import run_audio_inference  # noqa: E402


def evaluate_manifest(
    manifest_path: Path,
    output_path: Path,
) -> dict:
    """Evaluate manifest audio files and return a JSON-serializable report."""
    manifest_path = manifest_path.resolve()
    output_path = output_path.resolve()

    if not manifest_path.is_file():
        raise FileNotFoundError(f"Manifest not found: {manifest_path}")

    if manifest_path == output_path:
        raise ValueError("Output path must differ from the manifest path.")

    # Read and validate the manifest before processing any recordings.
    with manifest_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)

        if not reader.fieldnames or "audio_path" not in reader.fieldnames:
            raise ValueError("CSV manifest must contain an 'audio_path' column.")

        rows = list(reader)

    # Prevent the JSON report from overwriting any listed input recording.
    for row in rows:
        raw_path = (row.get("audio_path") or "").strip()
        if not raw_path:
            continue

        audio_path = Path(raw_path)
        if not audio_path.is_absolute():
            audio_path = manifest_path.parent / audio_path

        if audio_path.resolve() == output_path:
            raise ValueError(
                "Output path must not match an audio file listed in the manifest."
            )

    results = []
    scores = []
    confidences = []
    classes = Counter()
    failures = 0

    for row_number, row in enumerate(rows, start=2):
        raw_path = (row.get("audio_path") or "").strip()
        sample_id = (row.get("sample_id") or "").strip() or f"row-{row_number}"

        if not raw_path:
            failures += 1
            results.append(
                {
                    "sample_id": sample_id,
                    "status": "error",
                    "error": "Missing audio_path.",
                }
            )
            continue

        audio_path = Path(raw_path)
        if not audio_path.is_absolute():
            audio_path = manifest_path.parent / audio_path

        try:
            prediction = run_audio_inference(audio_path)

            score = float(prediction["audio_distress_score"])
            confidence = float(prediction["confidence"])

            if not math.isfinite(score) or not 0.0 <= score <= 1.0:
                raise ValueError("Inference returned an invalid score.")
            if not math.isfinite(confidence) or not 0.0 <= confidence <= 1.0:
                raise ValueError("Inference returned invalid confidence.")

            scores.append(score)
            confidences.append(confidence)
            classes[prediction["detected_class"]] += 1

            results.append(
                {
                    "sample_id": sample_id,
                    "status": "success",
                    "audio_distress_score": score,
                    "confidence": confidence,
                    "detected_class": prediction["detected_class"],
                    "window_duration_seconds": prediction["window_duration_seconds"],
                    "timestamp": prediction["timestamp"],
                    "model_version": prediction["model_version"],
                }
            )
        except Exception as exc:
            failures += 1
            results.append(
                {
                    "sample_id": sample_id,
                    "status": "error",
                    "error": f"{type(exc).__name__}: {exc}",
                }
            )

    if not results:
        raise ValueError("Manifest contains no audio samples to evaluate.")

    successful = len(scores)

    # Use the first successful result's model version, if available.
    model_version = next(
        (
            result["model_version"]
            for result in results
            if result.get("status") == "success" and result.get("model_version")
        ),
        "unknown",
    )

    report = {
        "evaluation_type": "audio_acoustic_activity_baseline",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "model_version": model_version,
        "interpretation": (
            "The reported score is a baseline heuristic, not a validated "
            "probability of distress. The existing preprocessing peak-normalizes "
            "each clip before RMS calculation, so scores must not be interpreted "
            "as absolute acoustic intensity or compared as such across recordings. "
            "This evaluation does not establish distress-detection accuracy."
        ),
        "privacy": (
            "Raw audio is not included in this report. Only inference "
            "metadata, scores, and errors are recorded."
        ),
        "summary": {
            "total_samples": len(results),
            "successful_samples": successful,
            "failed_samples": failures,
            "mean_acoustic_activity_score": mean(scores) if scores else None,
            "min_acoustic_activity_score": min(scores) if scores else None,
            "max_acoustic_activity_score": max(scores) if scores else None,
            "mean_confidence_heuristic": mean(confidences) if confidences else None,
            "detected_class_counts": dict(classes),
        },
        "results": results,
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(report, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    return report


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Evaluate WEGOTCHU audio inference on files listed in a CSV "
            "manifest. Scores are baseline heuristics, not validated distress "
            "probabilities or absolute acoustic intensity measurements."
        )
    )
    parser.add_argument(
        "--manifest",
        required=True,
        type=Path,
        help="CSV file containing an audio_path column and optional sample_id.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("reports/audio_evaluation.json"),
        help="JSON report destination (default: reports/audio_evaluation.json).",
    )
    args = parser.parse_args()

    try:
        report = evaluate_manifest(args.manifest, args.output)
    except (OSError, ValueError, csv.Error) as exc:
        print(f"Audio evaluation failed: {exc}", file=sys.stderr)
        return 1

    summary = report["summary"]
    print(f"Report written to: {args.output.resolve()}")
    print(f"Samples: {summary['total_samples']}")
    print(f"Successful: {summary['successful_samples']}")
    print(f"Failed: {summary['failed_samples']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
