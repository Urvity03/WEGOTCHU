"""Preprocess GeoLife .plt trajectories into a reproducible tabular dataset."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

import pandas as pd

SOURCE_COLUMNS = [
    "latitude",
    "longitude",
    "unused",
    "altitude_feet",
    "days",
    "date",
    "time",
]

OUTPUT_COLUMNS = [
    "user_id",
    "trajectory_id",
    "timestamp",
    "latitude",
    "longitude",
    "altitude_meters",
    "accuracy_meters",
    "gap_seconds",
    "is_gap_over_threshold",
]


def find_project_root() -> Path:
    """Return the repository root based on this script's location."""
    return Path(__file__).resolve().parents[1]


def parse_trajectory(
    trajectory_path: Path,
    dataset_root: Path,
    gap_threshold_seconds: float,
) -> tuple[pd.DataFrame, dict[str, int]]:
    """Read, validate, and prepare one GeoLife trajectory."""
    frame = pd.read_csv(
        trajectory_path,
        skiprows=6,
        header=None,
        names=SOURCE_COLUMNS,
    )

    if frame.empty:
        raise ValueError(
            f"Trajectory contains no observation rows: {trajectory_path.name}"
        )

    original_rows = len(frame)

    frame["latitude"] = pd.to_numeric(frame["latitude"], errors="coerce")
    frame["longitude"] = pd.to_numeric(frame["longitude"], errors="coerce")
    frame["altitude_feet"] = pd.to_numeric(
        frame["altitude_feet"], errors="coerce"
    )

    frame["timestamp"] = pd.to_datetime(
        frame["date"].astype(str) + " " + frame["time"].astype(str),
        format="%Y-%m-%d %H:%M:%S",
        errors="coerce",
    )

    # GeoLife uses -777 as its missing-altitude sentinel.
    frame["altitude_feet"] = frame["altitude_feet"].replace(-777, pd.NA)
    frame["altitude_meters"] = frame["altitude_feet"] * 0.3048

    invalid_timestamp = frame["timestamp"].isna()
    invalid_coordinates = ~frame["latitude"].between(-90, 90) | ~frame[
        "longitude"
    ].between(-180, 180)

    valid_rows = ~(invalid_timestamp | invalid_coordinates)
    frame = frame.loc[valid_rows].copy()
    frame = frame.sort_values("timestamp").reset_index(drop=True)

    source_user_id = trajectory_path.parent.parent.name
    user_id = f"geolife_{source_user_id}"
    trajectory_id = f"{user_id}/{trajectory_path.stem}"
    frame["user_id"] = user_id
    frame["trajectory_id"] = trajectory_id

    # Gaps are measured within each source trajectory. No interpolation or
    # segmentation is performed. The threshold is a provisional flag only.
    frame["gap_seconds"] = (
        frame["timestamp"].diff().dt.total_seconds().fillna(0)
    )
    frame["is_gap_over_threshold"] = (
        frame["gap_seconds"] > gap_threshold_seconds
    )

    # GeoLife does not provide GPS accuracy. Leave it unavailable.
    frame["accuracy_meters"] = pd.NA

    result = frame[OUTPUT_COLUMNS].copy()

    summary = {
        "input_rows": original_rows,
        "kept_rows": len(result),
        "invalid_timestamp_rows": int(invalid_timestamp.sum()),
        "invalid_coordinate_rows": int(
            (invalid_coordinates & ~invalid_timestamp).sum()
        ),
        "flagged_gaps": int(result["is_gap_over_threshold"].sum()),
    }

    return result, summary


def preprocess_dataset(
    dataset_root: Path,
    output_path: Path,
    gap_threshold_seconds: float,
) -> None:
    """Process all .plt files and stream rows to the ignored output CSV."""
    trajectory_paths = sorted(dataset_root.rglob("*.plt"))

    if not trajectory_paths:
        raise FileNotFoundError(
            f"No .plt files found under dataset directory: {dataset_root}"
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)

    totals = {
        "input_rows": 0,
        "kept_rows": 0,
        "invalid_timestamp_rows": 0,
        "invalid_coordinate_rows": 0,
        "flagged_gaps": 0,
    }

    with output_path.open("w", newline="", encoding="utf-8") as output_file:
        writer = csv.DictWriter(output_file, fieldnames=OUTPUT_COLUMNS)
        writer.writeheader()

        for index, trajectory_path in enumerate(trajectory_paths, start=1):
            try:
                trajectory, summary = parse_trajectory(
                    trajectory_path=trajectory_path,
                    dataset_root=dataset_root,
                    gap_threshold_seconds=gap_threshold_seconds,
                )
            except Exception as error:
                relative_path = trajectory_path.relative_to(dataset_root)
                raise RuntimeError(
                    f"Could not process trajectory {relative_path}"
                ) from error

            # Convert missing values to blank CSV fields.
            records = trajectory.astype(object).where(
                pd.notna(trajectory), None
            )
            writer.writerows(records.to_dict(orient="records"))

            for key, value in summary.items():
                totals[key] += value

            if index % 1000 == 0:
                print(
                    f"Processed {index}/{len(trajectory_paths)} trajectories"
                )

    print("Preprocessing complete.")
    print("Trajectory files:", len(trajectory_paths))
    print("Input observations:", totals["input_rows"])
    print("Retained observations:", totals["kept_rows"])
    print("Rows with invalid timestamps:", totals["invalid_timestamp_rows"])
    print("Rows with invalid coordinates:", totals["invalid_coordinate_rows"])
    print("Gaps over provisional threshold:", totals["flagged_gaps"])
    print("Output:", output_path)


def main() -> None:
    project_root = find_project_root()

    parser = argparse.ArgumentParser(
        description="Preprocess GeoLife GPS trajectory files."
    )
    parser.add_argument(
        "--input-dir",
        type=Path,
        default=project_root / "data" / "raw" / "geolife",
        help="Directory containing the extracted GeoLife dataset.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=(
            project_root
            / "data"
            / "processed"
            / "geolife"
            / "geolife_trajectories.csv"
        ),
        help="Destination CSV path. Keep generated data out of Git.",
    )
    parser.add_argument(
        "--gap-threshold-seconds",
        type=float,
        default=60.0,
        help=(
            "Provisional threshold used only to flag gaps. "
            "It does not split trajectories or interpolate points."
        ),
    )

    args = parser.parse_args()

    if args.gap_threshold_seconds <= 0:
        parser.error("--gap-threshold-seconds must be greater than zero")

    if not args.input_dir.is_dir():
        raise FileNotFoundError(
            f"Dataset directory does not exist: {args.input_dir}"
        )

    preprocess_dataset(
        dataset_root=args.input_dir,
        output_path=args.output,
        gap_threshold_seconds=args.gap_threshold_seconds,
    )


if __name__ == "__main__":
    main()
