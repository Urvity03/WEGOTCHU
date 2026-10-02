"""Evaluation harness for WEGOTCHU personalized route-deviation baseline."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
import sys
from typing import Sequence

import pandas as pd

# Add repository root to sys.path if not present
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ai.route_deviation.loader import Trajectory, load_trajectories  # noqa: E402
from ai.route_deviation.reference import (  # noqa: E402
    MIN_HISTORICAL_TRAJECTORIES,
    STATUS_INSUFFICIENT_HISTORY,
    build_reference_set,
)
from ai.route_deviation.scoring import (  # noqa: E402
    RouteDeviationResult,
    ScoreNormalizer,
    fit_normalizer_from_references,
    score_route_deviation,
)


@dataclass(frozen=True)
class EvaluationSummary:
    """Summary metrics for baseline evaluation across validation and test splits."""

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
    Evaluate validation and test trajectories using expanding historical reference sets.

    Anti-leakage rules:
    - Normalizers are fit exclusively per user from their static 'reference' trajectories.
    - Each candidate uses an expanding historical set: all same-user trajectories strictly
      preceding the candidate start time.
    - If < k_min historical trajectories exist, returns INSUFFICIENT_HISTORY.
    - Candidate trajectories are never used to fit normalizers.
    """
    # Map trajectory_id to split in manifest.
    # Note: if loader split trajectories into segments (_seg0, _seg1),
    # map using the parent trajectory_id prefix if exact id is not in manifest.
    split_map: dict[str, str] = {}
    for _, row in manifest.iterrows():
        split_map[str(row["trajectory_id"])] = str(row["split"])

    def get_split(t_id: str) -> str | None:
        if t_id in split_map:
            return split_map[t_id]
        parent_id = t_id.split("_seg")[0]
        return split_map.get(parent_id)

    # 1. Identify users and organize their static reference trajectories for normalizer fitting
    user_reference_trajs: dict[str, list[Trajectory]] = {}
    for traj in trajectories:
        split = get_split(traj.trajectory_id)
        if split == "reference":
            user_reference_trajs.setdefault(traj.user_id, []).append(traj)

    # Fit a static, leakage-safe normalizer per user using only their reference trajectories
    user_normalizers: dict[str, ScoreNormalizer] = {}
    for u_id, ref_list in user_reference_trajs.items():
        if len(ref_list) >= 2:
            user_normalizers[u_id] = fit_normalizer_from_references(ref_list)

    # 2. Evaluate only validation and test candidates
    eval_results: list[tuple[str, RouteDeviationResult]] = []

    val_candidates = 0
    test_candidates = 0
    val_success = 0
    test_success = 0
    val_insufficient = 0
    test_insufficient = 0

    successful_scores: list[float] = []
    successful_distances: list[float] = []

    # Sort all trajectories chronologically to ensure deterministic expanding evaluation
    sorted_trajectories = sorted(
        trajectories,
        key=lambda t: (t.points[0].timestamp, t.trajectory_id),
    )

    for candidate in sorted_trajectories:
        split = get_split(candidate.trajectory_id)
        if split not in ("validation", "test"):
            continue

        if split == "validation":
            val_candidates += 1
        elif split == "test":
            test_candidates += 1

        # Build expanding reference set (same user, strictly preceding candidate)
        ref_result = build_reference_set(
            trajectories=sorted_trajectories,
            candidate_trajectory=candidate,
            min_history=k_min,
        )

        normalizer = user_normalizers.get(candidate.user_id)

        result = score_route_deviation(
            candidate_trajectory=candidate,
            reference_set=ref_result,
            normalizer=normalizer,
        )

        eval_results.append((split, result))

        if result.status == STATUS_INSUFFICIENT_HISTORY:
            if split == "validation":
                val_insufficient += 1
            else:
                test_insufficient += 1
        elif result.status == "SUCCESS":
            if split == "validation":
                val_success += 1
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

    dist_min = min(successful_distances) if successful_distances else None
    dist_max = max(successful_distances) if successful_distances else None
    dist_mean = (
        sum(successful_distances) / len(successful_distances)
        if successful_distances
        else None
    )

    summary = EvaluationSummary(
        total_validation_candidates=val_candidates,
        total_test_candidates=test_candidates,
        successful_validation_scores=val_success,
        successful_test_scores=test_success,
        insufficient_history_validation=val_insufficient,
        insufficient_history_test=test_insufficient,
        score_min=score_min,
        score_mean=score_mean,
        score_max=score_max,
        raw_distance_min=dist_min,
        raw_distance_mean=dist_mean,
        raw_distance_max=dist_max,
    )

    return eval_results, summary


def print_summary(summary: EvaluationSummary) -> None:
    """Print formatted evaluation metrics."""
    print("=" * 60)
    print("WEGOTCHU ROUTE-DEVIATION BASELINE EVALUATION SUMMARY")
    print("=" * 60)
    print(f"Validation Candidates Total  : {summary.total_validation_candidates}")
    print(f"Validation Successful Scores : {summary.successful_validation_scores}")
    print(f"Validation Insufficient Hist : {summary.insufficient_history_validation}")
    print("-" * 60)
    print(f"Test Candidates Total        : {summary.total_test_candidates}")
    print(f"Test Successful Scores       : {summary.successful_test_scores}")
    print(f"Test Insufficient Hist       : {summary.insufficient_history_test}")
    print("-" * 60)

    total_evaluated = (
        summary.total_validation_candidates + summary.total_test_candidates
    )
    total_successful = (
        summary.successful_validation_scores + summary.successful_test_scores
    )
    print(f"Total Candidates Evaluated   : {total_evaluated}")
    print(f"Total Successful Scores      : {total_successful}")
    print("-" * 60)

    if summary.score_mean is not None:
        print(
            f"Normalized Score (min/mean/max): "
            f"{summary.score_min:.4f} / {summary.score_mean:.4f} / {summary.score_max:.4f}"
        )
    else:
        print("Normalized Score (min/mean/max): N/A (no successful scores)")

    if summary.raw_distance_mean is not None:
        print(
            f"Raw DTW Distance (m) (min/mean/max): "
            f"{summary.raw_distance_min:.2f} / {summary.raw_distance_mean:.2f} / {summary.raw_distance_max:.2f}"
        )
    else:
        print("Raw DTW Distance (m) (min/mean/max): N/A (no successful scores)")
    print("=" * 60)


def main() -> None:
    project_root = Path(__file__).resolve().parents[1]

    parser = argparse.ArgumentParser(
        description="Evaluate WEGOTCHU route-deviation baseline on GeoLife split manifest."
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
            f"Please run 'python scripts/preprocess_geolife.py' first."
        )

    if not args.manifest.is_file():
        raise FileNotFoundError(
            f"GeoLife split manifest not found at: {args.manifest}\n"
            f"Please run 'python scripts/create_geolife_split_manifest.py' first."
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
