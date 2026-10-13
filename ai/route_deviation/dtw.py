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
    Compute the complete DTW accumulated cost matrix.

    This function is retained for compatibility and testing.

    Recurrence:
        D(0, 0) = cost(0, 0)
        D(i, 0) = D(i - 1, 0) + cost(i, 0)
        D(0, j) = D(0, j - 1) + cost(0, j)
        D(i, j) = cost(i, j) + min(
            D(i - 1, j),
            D(i, j - 1),
            D(i - 1, j - 1),
        )

    Args:
        cost_matrix: Pairwise local cost matrix of shape (M, N).

    Returns:
        Complete accumulated cost matrix of shape (M, N).
    """
    m, n = cost_matrix.shape

    if m == 0 or n == 0:
        raise ValueError(
            "Cannot compute accumulated cost matrix for empty cost matrix."
        )

    accumulated_cost = np.empty((m, n), dtype=np.float64)

    accumulated_cost[0, 0] = cost_matrix[0, 0]

    for i in range(1, m):
        accumulated_cost[i, 0] = (
            accumulated_cost[i - 1, 0] + cost_matrix[i, 0]
        )

    for j in range(1, n):
        accumulated_cost[0, j] = (
            accumulated_cost[0, j - 1] + cost_matrix[0, j]
        )

    for i in range(1, m):
        for j in range(1, n):
            accumulated_cost[i, j] = cost_matrix[i, j] + min(
                accumulated_cost[i - 1, j],
                accumulated_cost[i, j - 1],
                accumulated_cost[i - 1, j - 1],
            )

    return accumulated_cost


def _compute_dtw_final_cost(cost_matrix: np.ndarray) -> float:
    """
    Compute the final DTW cost using a single rolling row buffer.

    The recurrence is identical to the complete-matrix implementation:
        D(0, 0) = cost(0, 0)
        D(i, 0) = D(i - 1, 0) + cost(i, 0)
        D(0, j) = D(0, j - 1) + cost(0, j)
        D(i, j) = cost(i, j) + min(D(i - 1, j), D(i, j - 1), D(i - 1, j - 1))

    Memory usage is O(N) using a single 1D array of length N, with local
    scalar variables tracking diagonal, upper, and left values.
    """
    m, n = cost_matrix.shape

    if m == 0 or n == 0:
        raise ValueError(
            "Cannot compute accumulated cost for an empty cost matrix."
        )

    dp = np.empty(n, dtype=np.float64)

    # Initialize the first row: D(0, j) = D(0, j - 1) + cost(0, j)
    row0 = cost_matrix[0]
    dp[0] = row0[0]
    for j in range(1, n):
        dp[j] = dp[j - 1] + row0[j]

    # Calculate subsequent rows i = 1 .. m - 1
    for i in range(1, m):
        cost_row = cost_matrix[i]
        diag = dp[0]
        left = diag + cost_row[0]
        dp[0] = left

        for j in range(1, n):
            up = dp[j]
            # min(up, left, diag)
            min_prev = up if up < left else left
            if diag < min_prev:
                min_prev = diag

            left = cost_row[j] + min_prev
            diag = up
            dp[j] = left

    return float(dp[n - 1])


def dtw_distance(
    traj_a: Union[Trajectory, Sequence[TrajectoryPoint]],
    traj_b: Union[Trajectory, Sequence[TrajectoryPoint]],
) -> float:
    """
    Compute unnormalized DTW distance in meters between two trajectories.

    Local cost is exclusively the Haversine distance between observation
    points. Timestamps, velocity, heading, and altitude do not contribute
    to the local cost.

    No temporal interpolation or spatial resampling is performed.

    Args:
        traj_a: First Trajectory object or sequence of TrajectoryPoints.
        traj_b: Second Trajectory object or sequence of TrajectoryPoints.

    Returns:
        Non-negative cumulative spatial alignment distance in meters.

    Raises:
        ValueError: If either trajectory contains no observation points.
    """
    points_a = traj_a.points if isinstance(traj_a, Trajectory) else traj_a
    points_b = traj_b.points if isinstance(traj_b, Trajectory) else traj_b

    if len(points_a) == 0 or len(points_b) == 0:
        raise ValueError("Cannot compute DTW distance for an empty trajectory.")

    # Keep the existing Haversine calculation unchanged.
    cost_matrix = pairwise_haversine_matrix(points_a, points_b)

    # Only the final accumulated cost is needed for the distance.
    return _compute_dtw_final_cost(cost_matrix)