"""Personalized historical reference set builder."""

from __future__ import annotations

from bisect import bisect_left
from dataclasses import dataclass
import re
from typing import Sequence

from .loader import Trajectory


MIN_HISTORICAL_TRAJECTORIES: int = 5

STATUS_SUFFICIENT: str = "SUFFICIENT"
STATUS_INSUFFICIENT_HISTORY: str = "INSUFFICIENT_HISTORY"


def parent_trajectory_id(trajectory_id: str) -> str:
    """Return the original trajectory ID without a segment suffix."""
    return re.sub(r"_seg\d+$", "", trajectory_id)


@dataclass(frozen=True)
class ReferenceSetResult:
    """Result of building a historical reference set."""

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


def _validate_inputs(
    candidate_trajectory: Trajectory,
    min_history: int,
) -> None:
    if not isinstance(candidate_trajectory, Trajectory):
        raise TypeError(
            "Expected candidate_trajectory to be a Trajectory, "
            f"got {type(candidate_trajectory).__name__}"
        )

    if min_history < 1:
        raise ValueError(f"min_history must be at least 1, got {min_history}")


def _build_result(
    candidate_trajectory: Trajectory,
    eligible: Sequence[Trajectory],
    min_history: int,
) -> ReferenceSetResult:
    is_sufficient = len(eligible) >= min_history
    status = STATUS_SUFFICIENT if is_sufficient else STATUS_INSUFFICIENT_HISTORY

    return ReferenceSetResult(
        user_id=candidate_trajectory.user_id,
        candidate_id=candidate_trajectory.trajectory_id,
        is_sufficient=is_sufficient,
        status=status,
        trajectories=tuple(eligible),
    )


def build_reference_set(
    trajectories: Sequence[Trajectory],
    candidate_trajectory: Trajectory,
    min_history: int = MIN_HISTORICAL_TRAJECTORIES,
) -> ReferenceSetResult:
    """
    Build a chronological reference set for a candidate trajectory.

    A reference trajectory must:

    - Belong to the same user.
    - Start before the candidate starts.
    - End before the candidate starts.
    - Belong to a different original trajectory.
    - Not be a future or overlapping trajectory.

    Segments from the same original trajectory count only once.
    """
    _validate_inputs(candidate_trajectory, min_history)

    user_id = candidate_trajectory.user_id
    candidate_id = candidate_trajectory.trajectory_id
    candidate_parent_id = parent_trajectory_id(candidate_id)
    candidate_start_time = candidate_trajectory.points[0].timestamp

    eligible_by_parent: dict[str, Trajectory] = {}

    for trajectory in trajectories:
        if trajectory.user_id != user_id:
            continue

        trajectory_parent_id = parent_trajectory_id(trajectory.trajectory_id)

        # Exclude the candidate and all of its child segments.
        if trajectory_parent_id == candidate_parent_id:
            continue

        reference_start_time = trajectory.points[0].timestamp
        reference_end_time = trajectory.points[-1].timestamp

        # Both the start and end must precede the candidate.
        if reference_start_time >= candidate_start_time:
            continue

        if reference_end_time >= candidate_start_time:
            continue

        # Count multiple segments from one original trajectory once.
        eligible_by_parent.setdefault(
            trajectory_parent_id,
            trajectory,
        )

    eligible = sorted(
        eligible_by_parent.values(),
        key=lambda trajectory: (
            trajectory.points[0].timestamp,
            trajectory.trajectory_id,
        ),
    )

    return _build_result(
        candidate_trajectory=candidate_trajectory,
        eligible=eligible,
        min_history=min_history,
    )


def build_reference_set_from_sorted(
    user_trajectories: Sequence[Trajectory],
    candidate_trajectory: Trajectory,
    min_history: int = MIN_HISTORICAL_TRAJECTORIES,
) -> ReferenceSetResult:
    """
    Build a reference set from chronologically sorted trajectories.

    The input must be sorted by trajectory start timestamp and trajectory ID.

    The binary-search prefix filters trajectories that start before the
    candidate. A second end-time check removes trajectories that overlap the
    candidate start time.
    """
    _validate_inputs(candidate_trajectory, min_history)

    user_id = candidate_trajectory.user_id
    candidate_id = candidate_trajectory.trajectory_id
    candidate_parent_id = parent_trajectory_id(candidate_id)
    candidate_start_time = candidate_trajectory.points[0].timestamp

    boundary_index = bisect_left(
        user_trajectories,
        candidate_start_time,
        key=lambda trajectory: trajectory.points[0].timestamp,
    )

    prefix = user_trajectories[:boundary_index]
    eligible_by_parent: dict[str, Trajectory] = {}

    for trajectory in prefix:
        if trajectory.user_id != user_id:
            continue

        trajectory_parent_id = parent_trajectory_id(trajectory.trajectory_id)

        # Exclude the candidate and all of its child segments.
        if trajectory_parent_id == candidate_parent_id:
            continue

        reference_end_time = trajectory.points[-1].timestamp

        # A trajectory that ends at or after the candidate starts overlaps it.
        if reference_end_time >= candidate_start_time:
            continue

        # Count multiple segments from one original trajectory once.
        eligible_by_parent.setdefault(
            trajectory_parent_id,
            trajectory,
        )

    eligible = list(eligible_by_parent.values())

    return _build_result(
        candidate_trajectory=candidate_trajectory,
        eligible=eligible,
        min_history=min_history,
    )
