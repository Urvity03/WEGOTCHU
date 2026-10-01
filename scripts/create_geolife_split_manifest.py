"""Create a chronological GeoLife trajectory split manifest."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

REQUIRED_COLUMNS = [
    "user_id",
    "trajectory_id",
    "timestamp",
    "gap_seconds",
    "is_gap_over_threshold",
]


def summarize_trajectories(
    input_path: Path,
    chunksize: int = 250_000,
) -> pd.DataFrame:
    """Create one summary row for each trajectory."""
    summaries = []

    for chunk in pd.read_csv(
        input_path,
        usecols=REQUIRED_COLUMNS,
        parse_dates=["timestamp"],
        chunksize=chunksize,
    ):
        chunk_summary = chunk.groupby(["user_id", "trajectory_id"], as_index=False).agg(
            start_timestamp=("timestamp", "min"),
            end_timestamp=("timestamp", "max"),
            observation_count=("timestamp", "size"),
            max_gap_seconds=("gap_seconds", "max"),
            flagged_gap_count=(
                "is_gap_over_threshold",
                "sum",
            ),
        )
        summaries.append(chunk_summary)

    if not summaries:
        raise ValueError("The processed trajectory file is empty.")

    result = pd.concat(summaries, ignore_index=True)

    # A trajectory should normally occur in one or more chunks, so combine
    # partial summaries if the input is chunked across boundaries.
    result = result.groupby(["user_id", "trajectory_id"], as_index=False).agg(
        start_timestamp=("start_timestamp", "min"),
        end_timestamp=("end_timestamp", "max"),
        observation_count=("observation_count", "sum"),
        max_gap_seconds=("max_gap_seconds", "max"),
        flagged_gap_count=("flagged_gap_count", "sum"),
    )

    return result


def assign_user_splits(
    user_trajectories: pd.DataFrame,
    minimum_history: int,
) -> pd.DataFrame:
    """Assign chronological reference, validation, and test splits."""
    result = user_trajectories.sort_values(
        ["user_id", "start_timestamp", "trajectory_id"]
    ).copy()

    result["trajectory_count_for_user"] = result.groupby("user_id")[
        "trajectory_id"
    ].transform("size")

    result["personalization_eligible"] = (
        result["trajectory_count_for_user"] >= minimum_history
    )
    result["is_cold_start"] = ~result["personalization_eligible"]
    result["split"] = "cold_start"

    for user_id, indices in result.groupby("user_id", sort=False).groups.items():
        ordered_indices = list(indices)
        trajectory_count = len(ordered_indices)

        if trajectory_count < minimum_history:
            continue

        reference_count = max(1, int(trajectory_count * 0.60))
        validation_count = max(1, int(trajectory_count * 0.20))

        # Ensure every eligible user has at least one test trajectory.
        if reference_count + validation_count >= trajectory_count:
            validation_count = max(1, validation_count - 1)

        reference_end = reference_count
        validation_end = reference_end + validation_count

        result.loc[ordered_indices[:reference_end], "split"] = "reference"
        result.loc[
            ordered_indices[reference_end:validation_end],
            "split",
        ] = "validation"
        result.loc[ordered_indices[validation_end:], "split"] = "test"

    return result


def create_manifest(
    input_path: Path,
    output_path: Path,
    minimum_history: int,
) -> pd.DataFrame:
    """Create and save the chronological split manifest."""
    trajectory_summary = summarize_trajectories(input_path)
    manifest = assign_user_splits(
        trajectory_summary,
        minimum_history=minimum_history,
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    manifest.to_csv(output_path, index=False)

    return manifest


def main() -> None:
    project_root = Path(__file__).resolve().parents[1]

    parser = argparse.ArgumentParser(
        description="Create a chronological GeoLife split manifest."
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=(
            project_root / "data" / "processed" / "geolife" / "geolife_trajectories.csv"
        ),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=(
            project_root
            / "data"
            / "processed"
            / "geolife"
            / "geolife_split_manifest.csv"
        ),
    )
    parser.add_argument(
        "--minimum-history",
        type=int,
        default=5,
        help="Minimum trajectories required for personalization.",
    )

    args = parser.parse_args()

    if args.minimum_history < 2:
        parser.error("--minimum-history must be at least 2.")

    if not args.input.is_file():
        raise FileNotFoundError(f"Input file not found: {args.input}")

    manifest = create_manifest(
        input_path=args.input,
        output_path=args.output,
        minimum_history=args.minimum_history,
    )

    print("Manifest created:", args.output)
    print("Trajectories:", len(manifest))
    print("Users:", manifest["user_id"].nunique())
    print("\nSplit counts:")
    print(manifest["split"].value_counts())
    print("\nUser eligibility:")
    print(
        manifest.groupby("user_id")["personalization_eligible"].first().value_counts()
    )


if __name__ == "__main__":
    main()
