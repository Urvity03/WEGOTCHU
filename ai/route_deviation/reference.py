"""Personalized historical reference set builder for WEGOTCHU route-deviation pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from .loader import Trajectory

# Authoritative minimum historical trajectories per WEGOTCHU contract
MIN_HISTORICAL_TRAJECTORIES: int = 5

STATUS_SUFFICIENT: str = "SUFFICIENT"
STATUS_INSUFFICIENT_HISTORY: str = "INSUFFICIENT_HISTORY"


@dataclass(frozen=True)
class ReferenceSetResult:
    """
    Result of building a personalized historical reference set for a candidate trajectory.

    Attributes:
        user_id: The identifier of the user to whom the candidate belongs.
        candidate_id: The identifier of the candidate trajectory.
        is_sufficient: True if the number of eligible historical trajectories >= min_history.
        status: "SUFFICIENT" if is_sufficient else "INSUFFICIENT_HISTORY".
        trajectories: Tuple of eligible historical trajectories sorted chronologically (oldest to newest).
    """

    user_id: str
    candidate_id: str
    is_sufficient: bool
    status: str
    trajectories: tuple[Trajectory, ...]

    def __len__(self) -> int:
        return len(self.trajectories)

    def __iter__(self):
        return iter(self.trajectories)

    def __getitem__(self, index: int) -> Trajectory:
        return self.trajectories[index]


def build_reference_set(
    trajectories: Sequence[Trajectory],
    candidate_trajectory: Trajectory,
    min_history: int = MIN_HISTORICAL_TRAJECTORIES,
) -> ReferenceSetResult:
    """
    Identify and return the valid historical reference set for a candidate trajectory.

    Rules:
        1. User Identity: Only trajectories matching candidate_trajectory.user_id qualify.
        2. Strict Temporal Precedence: Only trajectories whose start timestamp strictly
           precedes candidate_trajectory's start timestamp (start_time < candidate_start_time) qualify.
        3. Candidate Exclusion: The candidate trajectory is never included in its own reference set.
        4. Deterministic Ordering: References are returned sorted chronologically from oldest to newest.
        5. Cold-Start Enforcement: If eligible historical count < min_history, reports
           status = "INSUFFICIENT_HISTORY" and is_sufficient = False.

    Args:
        trajectories: Pool of candidate and historical Trajectory objects.
        candidate_trajectory: The candidate Trajectory being evaluated.
        min_history: Minimum required historical trajectories (default is 5).

    Returns:
        ReferenceSetResult indicating sufficiency status and containing the reference trajectories.

    Raises:
        TypeError: If candidate_trajectory is not a Trajectory instance.
        ValueError: If min_history < 1.
    """
    if not isinstance(candidate_trajectory, Trajectory):
        raise TypeError(
            f"Expected candidate_trajectory to be a Trajectory, got {type(candidate_trajectory).__name__}"
        )

    if min_history < 1:
        raise ValueError(f"min_history must be at least 1, got {min_history}")

    user_id = candidate_trajectory.user_id
    candidate_id = candidate_trajectory.trajectory_id
    candidate_start_time = candidate_trajectory.points[0].timestamp

    eligible: list[Trajectory] = []

    for traj in trajectories:
        # Rule 1: Same user only (no cross-user pooling or global reference sets)
        if traj.user_id != user_id:
            continue

        # Rule 3: Candidate itself must never appear in its own reference set
        if traj.trajectory_id == candidate_id:
            continue

        ref_start_time = traj.points[0].timestamp

        # Rule 2: Strictly historical (must strictly precede candidate start time)
        # Trajectories occurring at the exact same start timestamp or in the future are excluded.
        if ref_start_time < candidate_start_time:
            eligible.append(traj)

    # Rule 4: Deterministic chronological ordering from oldest to newest
    # Tie-break on trajectory_id for absolute determinism if start timestamps match
    eligible.sort(key=lambda t: (t.points[0].timestamp, t.trajectory_id))

    is_sufficient = len(eligible) >= min_history
    status = STATUS_SUFFICIENT if is_sufficient else STATUS_INSUFFICIENT_HISTORY

    return ReferenceSetResult(
        user_id=user_id,
        candidate_id=candidate_id,
        is_sufficient=is_sufficient,
        status=status,
        trajectories=tuple(eligible),
    )
