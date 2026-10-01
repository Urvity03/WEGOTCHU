"""Trajectory loader and segmentation layer for WEGOTCHU ML pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Union

import pandas as pd

REQUIRED_COLUMNS = {
    "user_id",
    "trajectory_id",
    "timestamp",
    "latitude",
    "longitude",
}


@dataclass(frozen=True)
class TrajectoryPoint:
    """A single discrete spatial-temporal observation in a trajectory."""

    latitude: float
    longitude: float
    timestamp: datetime

    def __post_init__(self) -> None:
        if not (-90.0 <= self.latitude <= 90.0):
            raise ValueError(
                f"Latitude must be between -90.0 and 90.0, got {self.latitude}"
            )
        if not (-180.0 <= self.longitude <= 180.0):
            raise ValueError(
                f"Longitude must be between -180.0 and 180.0, got {self.longitude}"
            )
        if not isinstance(self.timestamp, datetime):
            raise TypeError(
                f"Timestamp must be a datetime object, got {type(self.timestamp)}"
            )


@dataclass(frozen=True)
class Trajectory:
    """An ordered sequence of GPS observations belonging to a single continuous trip."""

    user_id: str
    trajectory_id: str
    points: tuple[TrajectoryPoint, ...]

    def __post_init__(self) -> None:
        if not self.user_id:
            raise ValueError("user_id cannot be empty")
        if not self.trajectory_id:
            raise ValueError("trajectory_id cannot be empty")
        if len(self.points) < 2:
            raise ValueError(
                f"Trajectory must contain at least 2 points, got {len(self.points)}"
            )
        for i in range(len(self.points) - 1):
            if self.points[i].timestamp > self.points[i + 1].timestamp:
                raise ValueError("Trajectory points must be ordered chronologically")

    def __len__(self) -> int:
        return len(self.points)

    def __getitem__(self, index: int) -> TrajectoryPoint:
        return self.points[index]

    def __iter__(self):
        return iter(self.points)


def load_trajectories(
    data: Union[pd.DataFrame, Path, str],
    gap_threshold_seconds: float | None = None,
    min_points: int = 2,
) -> list[Trajectory]:
    """
    Load preprocessed tabular GPS observations and segment them into valid trajectories.

    Args:
        data: A pandas DataFrame or a file path (CSV or Parquet) containing preprocessed data.
        gap_threshold_seconds: Optional threshold in seconds to split streams when consecutive
                               timestamps exceed this difference. If None, relies on the
                               pre-computed 'is_gap_over_threshold' column if present.
        min_points: Minimum number of valid GPS observations required to form a trajectory
                    segment (default is 2). Segments with fewer points are dropped.

    Returns:
        A list of segmented, chronologically ordered Trajectory objects.
    """
    if isinstance(data, (str, Path)):
        path = Path(data)
        if not path.is_file():
            raise FileNotFoundError(f"Trajectory data file not found: {path}")
        if path.suffix.lower() == ".parquet":
            df = pd.read_parquet(path)
        else:
            df = pd.read_csv(path)
    elif isinstance(data, pd.DataFrame):
        df = data.copy()
    else:
        raise TypeError(
            f"Expected pd.DataFrame, Path, or str, got {type(data).__name__}"
        )

    if df.empty:
        return []

    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise ValueError(
            f"Missing required columns in trajectory dataset: {sorted(missing)}"
        )

    # Convert coordinates and timestamps
    df["latitude"] = pd.to_numeric(df["latitude"], errors="coerce")
    df["longitude"] = pd.to_numeric(df["longitude"], errors="coerce")
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")

    # Filter invalid coordinates and timestamps
    valid_coords = df["latitude"].between(-90.0, 90.0) & df["longitude"].between(
        -180.0, 180.0
    )
    valid_timestamp = df["timestamp"].notna()
    valid_rows = valid_coords & valid_timestamp
    df = df.loc[valid_rows].copy()

    if df.empty:
        return []

    has_gap_flag = "is_gap_over_threshold" in df.columns

    trajectories: list[Trajectory] = []

    # Process each user and trajectory group preserving order
    for (user_id, source_id), group in df.groupby(
        ["user_id", "trajectory_id"], sort=False
    ):
        # 1. Sort observations strictly chronologically
        sorted_group = group.sort_values("timestamp", kind="stable").reset_index(
            drop=True
        )

        if len(sorted_group) < min_points:
            continue

        # 2. Identify split boundary indices
        split_indices: list[int] = [0]
        timestamps = sorted_group["timestamp"]

        for idx in range(1, len(sorted_group)):
            should_split = False

            # Check gap_seconds / time difference
            dt = (timestamps.iloc[idx] - timestamps.iloc[idx - 1]).total_seconds()

            if gap_threshold_seconds is not None and dt > gap_threshold_seconds:
                should_split = True
            elif has_gap_flag and bool(sorted_group.iloc[idx]["is_gap_over_threshold"]):
                should_split = True

            if should_split:
                split_indices.append(idx)

        split_indices.append(len(sorted_group))

        # 3. Slice into continuous segments
        segments_points: list[list[TrajectoryPoint]] = []
        for i in range(len(split_indices) - 1):
            start = split_indices[i]
            end = split_indices[i + 1]
            seg_slice = sorted_group.iloc[start:end]

            if len(seg_slice) >= min_points:
                pts = [
                    TrajectoryPoint(
                        latitude=float(row["latitude"]),
                        longitude=float(row["longitude"]),
                        timestamp=row["timestamp"].to_pydatetime(),
                    )
                    for _, row in seg_slice.iterrows()
                ]
                segments_points.append(pts)

        # 4. Construct Trajectory objects with deterministic segment IDs
        total_valid_segments = len(segments_points)
        for seg_idx, pts in enumerate(segments_points):
            if total_valid_segments == 1 and len(split_indices) == 2:
                # No split occurred in the original stream
                seg_id = str(source_id)
            else:
                # Deterministic segment identifier
                seg_id = f"{source_id}_seg{seg_idx}"

            trajectories.append(
                Trajectory(
                    user_id=str(user_id),
                    trajectory_id=seg_id,
                    points=tuple(pts),
                )
            )

    return trajectories
