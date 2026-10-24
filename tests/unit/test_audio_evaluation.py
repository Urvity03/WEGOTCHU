import csv
import json
from pathlib import Path

import pytest

from scripts import evaluate_audio


def write_manifest(path: Path, rows: list[dict]) -> None:
    """Create a temporary CSV manifest for testing."""
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["sample_id", "audio_path"])
        writer.writeheader()
        writer.writerows(rows)


def fake_prediction(audio_path):
    """Return a deterministic prediction without loading real audio."""
    return {
        "audio_distress_score": 0.4,
        "confidence": 0.2,
        "detected_class": "acoustic_activity",
        "window_duration_seconds": 1.0,
        "timestamp": "2026-01-01T00:00:00+00:00",
        "model_version": "audio-baseline-v2",
    }


def test_evaluate_manifest_success(tmp_path, monkeypatch):
    manifest = tmp_path / "manifest.csv"
    output = tmp_path / "report.json"

    write_manifest(
        manifest,
        [{"sample_id": "sample-001", "audio_path": "sample.wav"}],
    )
    monkeypatch.setattr(evaluate_audio, "run_audio_inference", fake_prediction)

    report = evaluate_audio.evaluate_manifest(manifest, output)

    assert report["summary"]["total_samples"] == 1
    assert report["summary"]["successful_samples"] == 1
    assert report["summary"]["failed_samples"] == 0
    assert report["summary"]["mean_acoustic_activity_score"] == 0.4
    assert report["model_version"] == "audio-baseline-v2"
    assert output.is_file()

    saved_report = json.loads(output.read_text(encoding="utf-8"))
    assert saved_report["results"][0]["status"] == "success"


def test_missing_manifest_raises_error(tmp_path):
    with pytest.raises(FileNotFoundError, match="Manifest not found"):
        evaluate_audio.evaluate_manifest(
            tmp_path / "missing.csv",
            tmp_path / "report.json",
        )


def test_manifest_requires_audio_path_column(tmp_path):
    manifest = tmp_path / "manifest.csv"
    manifest.write_text("sample_id\nsample-001\n", encoding="utf-8")

    with pytest.raises(ValueError, match="audio_path"):
        evaluate_audio.evaluate_manifest(
            manifest,
            tmp_path / "report.json",
        )


def test_empty_manifest_raises_error(tmp_path):
    manifest = tmp_path / "manifest.csv"
    write_manifest(manifest, [])

    with pytest.raises(ValueError, match="no audio samples"):
        evaluate_audio.evaluate_manifest(
            manifest,
            tmp_path / "report.json",
        )


def test_inference_failure_is_recorded(tmp_path, monkeypatch):
    manifest = tmp_path / "manifest.csv"
    output = tmp_path / "report.json"

    write_manifest(
        manifest,
        [{"sample_id": "sample-001", "audio_path": "missing.wav"}],
    )

    def failing_prediction(audio_path):
        raise FileNotFoundError("Audio file not found")

    monkeypatch.setattr(evaluate_audio, "run_audio_inference", failing_prediction)

    report = evaluate_audio.evaluate_manifest(manifest, output)

    assert report["summary"]["successful_samples"] == 0
    assert report["summary"]["failed_samples"] == 1
    assert report["results"][0]["status"] == "error"
    assert "FileNotFoundError" in report["results"][0]["error"]


def test_missing_audio_path_is_recorded_as_failure(tmp_path):
    manifest = tmp_path / "manifest.csv"
    output = tmp_path / "report.json"
    write_manifest(manifest, [{"sample_id": "sample-001", "audio_path": ""}])

    report = evaluate_audio.evaluate_manifest(manifest, output)

    assert report["summary"]["total_samples"] == 1
    assert report["summary"]["failed_samples"] == 1
    assert report["results"][0]["error"] == "Missing audio_path."


def test_output_cannot_overwrite_manifest(tmp_path):
    manifest = tmp_path / "manifest.csv"
    write_manifest(manifest, [])

    with pytest.raises(ValueError, match="differ"):
        evaluate_audio.evaluate_manifest(manifest, manifest)


def test_output_cannot_overwrite_listed_audio_file(tmp_path, monkeypatch):
    manifest = tmp_path / "manifest.csv"
    audio_file = tmp_path / "sample.wav"
    original_audio = b"original audio bytes"
    audio_file.write_bytes(original_audio)

    write_manifest(
        manifest,
        [{"sample_id": "sample-001", "audio_path": "sample.wav"}],
    )
    monkeypatch.setattr(evaluate_audio, "run_audio_inference", fake_prediction)

    with pytest.raises(ValueError, match="audio file listed in the manifest"):
        evaluate_audio.evaluate_manifest(manifest, audio_file)

    assert audio_file.read_bytes() == original_audio


def test_model_version_uses_first_successful_result(tmp_path, monkeypatch):
    manifest = tmp_path / "manifest.csv"
    output = tmp_path / "report.json"

    write_manifest(
        manifest,
        [
            {"sample_id": "sample-001", "audio_path": "missing.wav"},
            {"sample_id": "sample-002", "audio_path": "valid.wav"},
        ],
    )

    def fail_first_then_succeed(audio_path):
        if Path(audio_path).name == "missing.wav":
            raise FileNotFoundError("Audio file not found")
        return fake_prediction(audio_path)

    monkeypatch.setattr(
        evaluate_audio,
        "run_audio_inference",
        fail_first_then_succeed,
    )

    report = evaluate_audio.evaluate_manifest(manifest, output)

    assert report["results"][0]["status"] == "error"
    assert report["results"][1]["status"] == "success"
    assert report["model_version"] == "audio-baseline-v2"
