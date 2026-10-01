"""Dynamic Time Warping (DTW) trajectory alignment engine for WEGOTCHU."""

from __future__ import annotations

from typing import Sequence, Union

import numpy as np

from .distance import pairwise_haversine_matrix
from .loader import Trajectory, TrajectoryPoint


def compute_dtw_accumulated_cost_matrix(
    cost_matrix: np.ndarray,
) -> np.ndarray:
    """
    Compute the standard dynamic-programming accumulated cost matrix from a pairwise cost matrix.

    Recurrence:
        D(0, 0) = cost(0, 0)
        D(i, 0) = D(i - 1, 0) + cost(i, 0)
        D(0, j) = D(0, j - 1) + cost(0, j)
        D(i, j) = cost(i, j) + min(D(i - 1, j), D(i, j - 1), D(i - 1, j - 1))

    Args:
        cost_matrix: Pairwise local cost matrix of shape (M, N).

    Returns:
        np.ndarray of shape (M, N) containing accumulated costs.
    """
    m, n = cost_matrix.shape
    if m == 0 or n == 0:
        raise ValueError(
            "Cannot compute accumulated cost matrix for empty cost matrix."
        )

    accumulated_cost = np.empty((m, n), dtype=np.float64)

    # Base case
    accumulated_cost[0, 0] = cost_matrix[0, 0]

    # First column: only predecessor is (i - 1, 0)
    for i in range(1, m):
        accumulated_cost[i, 0] = accumulated_cost[i - 1, 0] + cost_matrix[i, 0]

    # First row: only predecessor is (0, j - 1)
    for j in range(1, n):
        accumulated_cost[0, j] = accumulated_cost[0, j - 1] + cost_matrix[0, j]

    # Core recurrence
    for i in range(1, m):
        for j in range(1, n):
            accumulated_cost[i, j] = cost_matrix[i, j] + min(
                accumulated_cost[i - 1, j],
                accumulated_cost[i, j - 1],
                accumulated_cost[i - 1, j - 1],
            )

    return accumulated_cost


def dtw_distance(
    traj_a: Union[Trajectory, Sequence[TrajectoryPoint]],
    traj_b: Union[Trajectory, Sequence[TrajectoryPoint]],
) -> float:
    """
    Compute the unnormalized Dynamic Time Warping (DTW) distance in meters between two trajectories.

    Local cost is strictly the great-circle Haversine distance in meters between observation points.
    No velocity, heading, altitude, or timestamp penalties are applied.
    No temporal interpolation or spatial resampling is performed.

    Args:
        traj_a: First Trajectory object or sequence of TrajectoryPoints.
        traj_b: Second Trajectory object or sequence of TrajectoryPoints.

    Returns:
        Non-negative float representing the cumulative spatial alignment distance in meters.

    Raises:
        ValueError: If either trajectory contains zero observation points.
    """
    points_a = traj_a.points if isinstance(traj_a, Trajectory) else traj_a
    points_b = traj_b.points if isinstance(traj_b, Trajectory) else traj_b

    m = len(points_a)
    n = len(points_b)

    if m == 0 or n == 0:
        raise ValueError("Cannot compute DTW distance for an empty trajectory.")

    # 1. Compute pairwise local cost matrix using vectorized Haversine distance
    cost_matrix = pairwise_haversine_matrix(points_a, points_b)

    # 2. Compute dynamic programming accumulated cost matrix
    accumulated_cost = compute_dtw_accumulated_cost_matrix(cost_matrix)

    # 3. Final DTW distance is accumulated cost at D(M-1, N-1)
    return float(accumulated_cost[m - 1, n - 1])
