"""Geographic Haversine distance calculations for WEGOTCHU ML pipeline."""

from __future__ import annotations

import math
from typing import Sequence

import numpy as np

from .loader import TrajectoryPoint

# Authoritative Earth radius per WEGOTCHU contract
EARTH_RADIUS_METERS: float = 6_371_000.0


def haversine_distance(point_a: TrajectoryPoint, point_b: TrajectoryPoint) -> float:
    """
    Calculate the great-circle geographic distance in meters between two TrajectoryPoints.

    Uses the Haversine formula with Earth radius R = 6,371,000.0 meters.
    Calculates distance purely from spatial coordinates (latitude and longitude).
    Timestamps and any extraneous signals are ignored.

    Args:
        point_a: Starting TrajectoryPoint.
        point_b: Ending TrajectoryPoint.

    Returns:
        Non-negative float representing the distance in meters.
    """
    if point_a.latitude == point_b.latitude and point_a.longitude == point_b.longitude:
        return 0.0

    lat1_rad = math.radians(point_a.latitude)
    lat2_rad = math.radians(point_b.latitude)
    delta_lat_rad = math.radians(point_b.latitude - point_a.latitude)
    delta_lon_rad = math.radians(point_b.longitude - point_a.longitude)

    sin_half_dlat = math.sin(delta_lat_rad / 2.0)
    sin_half_dlon = math.sin(delta_lon_rad / 2.0)

    a = (
        sin_half_dlat * sin_half_dlat
        + math.cos(lat1_rad) * math.cos(lat2_rad) * sin_half_dlon * sin_half_dlon
    )

    # Clamp intermediate value to [0.0, 1.0] for numerical stability
    a = min(1.0, max(0.0, a))

    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return float(EARTH_RADIUS_METERS * c)


def pairwise_haversine_matrix(
    seq_a: Sequence[TrajectoryPoint],
    seq_b: Sequence[TrajectoryPoint],
) -> np.ndarray:
    """
    Compute pairwise Haversine distance matrix between two sequences of TrajectoryPoints.

    This matrix serves exclusively as the pairwise geographic distance calculation
    between observation points (in meters) and does not perform any DTW alignment.

    Args:
        seq_a: Sequence of M TrajectoryPoints.
        seq_b: Sequence of N TrajectoryPoints.

    Returns:
        np.ndarray of shape (M, N) containing great-circle distances in meters.
    """
    m = len(seq_a)
    n = len(seq_b)

    if m == 0 or n == 0:
        return np.zeros((m, n), dtype=np.float64)

    lats_a = np.radians([p.latitude for p in seq_a], dtype=np.float64)
    lons_a = np.radians([p.longitude for p in seq_a], dtype=np.float64)
    lats_b = np.radians([p.latitude for p in seq_b], dtype=np.float64)
    lons_b = np.radians([p.longitude for p in seq_b], dtype=np.float64)

    # Compute coordinate differences via broadcasting: (M, 1) and (1, N)
    dlat = lats_b[np.newaxis, :] - lats_a[:, np.newaxis]
    dlon = lons_b[np.newaxis, :] - lons_a[:, np.newaxis]

    sin_half_dlat = np.sin(dlat / 2.0)
    sin_half_dlon = np.sin(dlon / 2.0)

    a = sin_half_dlat**2 + np.cos(lats_a[:, np.newaxis]) * np.cos(
        lats_b[np.newaxis, :]
    ) * (sin_half_dlon**2)

    # Numerical stability clamp
    a = np.clip(a, 0.0, 1.0)

    c = 2.0 * np.arctan2(np.sqrt(a), np.sqrt(1.0 - a))
    matrix = EARTH_RADIUS_METERS * c

    return matrix.astype(np.float64)
