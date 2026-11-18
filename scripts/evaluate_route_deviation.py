"""Evaluation harness for WEGOTCHU route-deviation baseline."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
import sys
from typing import Sequence

import pandas as pd

# Add repository root to sys.path if not present.
REPO_ROOT = Path(__file__).resolve().parents[1]

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ai.route_deviation.loader import (  # noqa: E402
    Trajectory,
    load_trajectories,
)
from ai.route_deviation.reference import (  # noqa: E402
    MIN_HISTORICAL_TRAJECTORIES,
    STATUS_INSUFFICIENT_HISTORY,
    build_reference_set_from_sorted,
    parent_trajectory_id,
)
from ai.route_deviation.scoring import (  # noqa: E402
    RouteDeviationResult,
    ScoreNormalizer,
    fit_normalizer_from_references,
    score_route_deviation,
)


@dataclass(frozen=True)
class EvaluationSummary:
    """Summary metrics across validation and test splits."""

    total_validation_candidates: int
    total_test_candidates: int
    successful_validation_scores: int
    successful_test_scores: int
    insufficient_history_validation: int
    insufficient_history_test: int
    score_min: float | None
    score_mean: float | None
    score_max: float | None
    raw_distance_min: float | None
    raw_distance_mean: float | None
    raw_distance_max: float | None


def evaluate_candidates(
    trajectories: Sequence[Trajectory],
    manifest: pd.DataFrame,
    k_min: int = MIN_HISTORICAL_TRAJECTORIES,
) -> tuple[list[tuple[str, RouteDeviationResult]], EvaluationSummary]:
    """
    Evaluate validation and test trajectories safely.

    Each candidate uses only same-user trajectories that both start and end
    before the candidate starts. Multiple segments from one original
    trajectory count once. Normalizers are fitted only from temporally safe
    reference-split trajectories.
    """
    split_map: dict[str, str] = {}

    for _, row in manifest.iterrows():
        split_map[str(row["trajectory_id"])] = str(row["split"])

    def get_split(trajectory_id: str) -> str | None:
        if trajectory_id in split_map:
            return split_map[trajectory_id]

        parent_id = parent_trajectory_id(trajectory_id)
        return split_map.get(parent_id)

    eval_results: list[tuple[str, RouteDeviationResult]] = []

    validation_candidates = 0
    test_candidates = 0
    validation_success = 0
    test_success = 0
    validation_insufficient = 0
    test_insufficient = 0

    successful_scores: list[float] = []
    successful_distances: list[float] = []

    sorted_trajectories = sorted(
        trajectories,
        key=lambda trajectory: (
            trajectory.points[0].timestamp,
            trajectory.trajectory_id,
        ),
    )

    trajectories_by_user: dict[str, list[Trajectory]] = {}

    for trajectory in sorted_trajectories:
        trajectories_by_user.setdefault(
            trajectory.user_id,
            [],
        ).append(trajectory)

    for candidate in sorted_trajectories:
        split = get_split(candidate.trajectory_id)

        if split not in {"validation", "test"}:
            continue

        if split == "validation":
            validation_candidates += 1
        else:
            test_candidates += 1

        reference_result = build_reference_set_from_sorted(
            user_trajectories=trajectories_by_user[candidate.user_id],
            candidate_trajectory=candidate,
            min_history=k_min,
        )

        normalizer_references = [
            trajectory
            for trajectory in reference_result.trajectories
            if get_split(trajectory.trajectory_id) == "reference"
        ]

        normalizer: ScoreNormalizer | None = None

        if len(normalizer_references) >= 2:
            normalizer = fit_normalizer_from_references(normalizer_references)

        result = score_route_deviation(
            candidate_trajectory=candidate,
            reference_set=reference_result,
            normalizer=normalizer,
        )

        eval_results.append((split, result))

        if result.status == STATUS_INSUFFICIENT_HISTORY:
            if split == "validation":
                validation_insufficient += 1
            else:
                test_insufficient += 1

        elif result.status == "SUCCESS":
            if split == "validation":
                validation_success += 1
            else:
                test_success += 1

            if result.route_deviation_score is not None:
                successful_scores.append(result.route_deviation_score)

            if result.raw_distance_meters is not None:
                successful_distances.append(result.raw_distance_meters)

    score_min = min(successful_scores) if successful_scores else None
    score_max = max(successful_scores) if successful_scores else None
    score_mean = (
        sum(successful_scores) / len(successful_scores) if successful_scores else None
    )

    distance_min = min(successful_distances) if successful_distances else None
    distance_max = max(successful_distances) if successful_distances else None
    distance_mean = (
        sum(successful_distances) / len(successful_distances)
        if successful_distances
        else None
    )

    summary = EvaluationSummary(
        total_validation_candidates=validation_candidates,
        total_test_candidates=test_candidates,
        successful_validation_scores=validation_success,
        successful_test_scores=test_success,
        insufficient_history_validation=validation_insufficient,
        insufficient_history_test=test_insufficient,
        score_min=score_min,
        score_mean=score_mean,
        score_max=score_max,
        raw_distance_min=distance_min,
        raw_distance_mean=distance_mean,
        raw_distance_max=distance_max,
    )

    return eval_results, summary


def print_summary(summary: EvaluationSummary) -> None:
    """Print formatted evaluation metrics."""
    print("=" * 60)
    print("WEGOTCHU ROUTE-DEVIATION BASELINE EVALUATION SUMMARY")
    print("=" * 60)

    print("Validation Candidates Total  : " f"{summary.total_validation_candidates}")
    print("Validation Successful Scores : " f"{summary.successful_validation_scores}")
    print(
        "Validation Insufficient Hist : " f"{summary.insufficient_history_validation}"
    )

    print("-" * 60)

    print(f"Test Candidates Total        : {summary.total_test_candidates}")
    print(f"Test Successful Scores       : {summary.successful_test_scores}")
    print("Test Insufficient Hist       : " f"{summary.insufficient_history_test}")

    print("-" * 60)

    total_candidates = (
        summary.total_validation_candidates + summary.total_test_candidates
    )

    total_successful = (
        summary.successful_validation_scores + summary.successful_test_scores
    )

    print(f"Total Candidates Evaluated   : {total_candidates}")
    print(f"Total Successful Scores      : {total_successful}")

    print("-" * 60)

    if summary.score_mean is not None:
        print(
            "Normalized Score (min/mean/max): "
            f"{summary.score_min:.4f} / "
            f"{summary.score_mean:.4f} / "
            f"{summary.score_max:.4f}"
        )
    else:
        print("Normalized Score (min/mean/max): N/A")

    if summary.raw_distance_mean is not None:
        print(
            "Raw DTW Distance (m) (min/mean/max): "
            f"{summary.raw_distance_min:.2f} / "
            f"{summary.raw_distance_mean:.2f} / "
            f"{summary.raw_distance_max:.2f}"
        )
    else:
        print("Raw DTW Distance (m) (min/mean/max): N/A")

    print("=" * 60)


def main() -> None:
    """Run the command-line evaluation."""
    project_root = Path(__file__).resolve().parents[1]

    parser = argparse.ArgumentParser(
        description=(
            "Evaluate WEGOTCHU route-deviation baseline " "on GeoLife split manifest."
        )
    )

    parser.add_argument(
        "--data",
        type=Path,
        default=(
            project_root / "data" / "processed" / "geolife" / "geolife_trajectories.csv"
        ),
        help="Path to preprocessed GeoLife trajectories CSV.",
    )

    parser.add_argument(
        "--manifest",
        type=Path,
        default=(
            project_root
            / "data"
            / "processed"
            / "geolife"
            / "geolife_split_manifest.csv"
        ),
        help="Path to chronological GeoLife split manifest CSV.",
    )

    parser.add_argument(
        "--k-min",
        type=int,
        default=MIN_HISTORICAL_TRAJECTORIES,
        help="Minimum historical trajectories required for scoring.",
    )

    args = parser.parse_args()

    if not args.data.is_file():
        raise FileNotFoundError(
            f"Processed GeoLife trajectory data not found at: {args.data}\n"
            "Please run 'python scripts/preprocess_geolife.py' first."
        )

    if not args.manifest.is_file():
        raise FileNotFoundError(
            f"GeoLife split manifest not found at: {args.manifest}\n"
            "Please run 'python scripts/create_geolife_split_manifest.py' "
            "first."
        )

    print(f"Loading trajectories from {args.data}...")
    trajectories = load_trajectories(args.data)
    print(f"Loaded {len(trajectories)} trajectory segments.")

    print(f"Loading split manifest from {args.manifest}...")
    manifest = pd.read_csv(args.manifest)
    print(f"Loaded {len(manifest)} manifest entries.")

    _, summary = evaluate_candidates(
        trajectories=trajectories,
        manifest=manifest,
        k_min=args.k_min,
    )

    print_summary(summary)


if __name__ == "__main__":
    main()
