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
    """A single discrete spatial-temporal observation."""

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
                "Longitude must be between -180.0 and 180.0, " f"got {self.longitude}"
            )

        if not isinstance(self.timestamp, datetime):
            raise TypeError(
                "Timestamp must be a datetime object, " f"got {type(self.timestamp)}"
            )


@dataclass(frozen=True)
class Trajectory:
    """An ordered sequence of GPS observations."""

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
                "Trajectory must contain at least 2 points, " f"got {len(self.points)}"
            )

        for index in range(len(self.points) - 1):
            if self.points[index].timestamp > self.points[index + 1].timestamp:
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
    Load observations and segment them into valid trajectories.

    Args:
        data: DataFrame or CSV/Parquet path containing trajectory data.
        gap_threshold_seconds: Optional gap threshold for segmentation.
        min_points: Minimum observations required for a segment.

    Returns:
        Chronologically ordered trajectory objects.
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
            "Missing required columns in trajectory dataset: " f"{sorted(missing)}"
        )

    df["latitude"] = pd.to_numeric(df["latitude"], errors="coerce")
    df["longitude"] = pd.to_numeric(df["longitude"], errors="coerce")
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")

    valid_coordinates = df["latitude"].between(
        -90.0,
        90.0,
    ) & df[
        "longitude"
    ].between(-180.0, 180.0)

    valid_timestamps = df["timestamp"].notna()
    df = df.loc[valid_coordinates & valid_timestamps].copy()

    if df.empty:
        return []

    has_gap_flag = "is_gap_over_threshold" in df.columns
    trajectories: list[Trajectory] = []

    for (user_id, source_id), group in df.groupby(
        ["user_id", "trajectory_id"],
        sort=False,
    ):
        sorted_group = group.sort_values(
            "timestamp",
            kind="stable",
        ).reset_index(drop=True)

        if len(sorted_group) < min_points:
            continue

        latitudes = sorted_group["latitude"].to_numpy(dtype=float)
        longitudes = sorted_group["longitude"].to_numpy(dtype=float)
        timestamps = sorted_group["timestamp"].tolist()

        if has_gap_flag:
            gap_flags = (
                sorted_group["is_gap_over_threshold"]
                .fillna(False)
                .astype(bool)
                .to_numpy()
            )
        else:
            gap_flags = None

        split_indices: list[int] = [0]

        for index in range(1, len(timestamps)):
            time_gap = (timestamps[index] - timestamps[index - 1]).total_seconds()

            should_split = (
                gap_threshold_seconds is not None and time_gap > gap_threshold_seconds
            )

            if not should_split and gap_flags is not None:
                should_split = bool(gap_flags[index])

            if should_split:
                split_indices.append(index)

        split_indices.append(len(timestamps))

        segments_points: list[list[TrajectoryPoint]] = []

        for segment_index in range(len(split_indices) - 1):
            start = split_indices[segment_index]
            end = split_indices[segment_index + 1]

            if end - start < min_points:
                continue

            points = [
                TrajectoryPoint(
                    latitude=latitudes[index],
                    longitude=longitudes[index],
                    timestamp=timestamps[index].to_pydatetime(),
                )
                for index in range(start, end)
            ]

            segments_points.append(points)

        total_segments = len(segments_points)

        for segment_index, points in enumerate(segments_points):
            if total_segments == 1 and len(split_indices) == 2:
                segment_id = str(source_id)
            else:
                segment_id = f"{source_id}_seg{segment_index}"

            trajectories.append(
                Trajectory(
                    user_id=str(user_id),
                    trajectory_id=segment_id,
                    points=tuple(points),
                )
            )

    return trajectories
