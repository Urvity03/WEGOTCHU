"""Route-deviation scoring and score normalization for WEGOTCHU ML pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence, Union

from .dtw import dtw_distance
from .loader import Trajectory
from .reference import ReferenceSetResult, STATUS_INSUFFICIENT_HISTORY


@dataclass(frozen=True)
class ScoreNormalizer:
    """
    Min-max normalizer fitted exclusively on historical reference distributions.

    Maps raw geographic deviation distance in meters to [0.0, 1.0].
    """

    min_distance: float
    max_distance: float

    def __post_init__(self) -> None:
        if self.min_distance < 0.0:
            raise ValueError(
                f"min_distance cannot be negative, got {self.min_distance}"
            )

        if self.max_distance < self.min_distance:
            raise ValueError(
                f"max_distance ({self.max_distance}) cannot be smaller "
                f"than min_distance ({self.min_distance})"
            )

    def normalize(self, distance: float) -> float:
        """Map raw distance in meters to [0.0, 1.0] with clipping."""
        if distance <= self.min_distance:
            return 0.0

        if self.max_distance <= self.min_distance:
            return 0.0

        scaled = (distance - self.min_distance) / (
            self.max_distance - self.min_distance
        )

        return float(max(0.0, min(1.0, scaled)))


@dataclass(frozen=True)
class RouteDeviationResult:
    """
    Result of evaluating a candidate trajectory against its
    personalized historical reference set.
    """

    user_id: str
    trajectory_id: str
    status: str
    raw_distance_meters: float | None
    route_deviation_score: float | None
    reference_trajectory_count: int
    closest_reference_id: str | None


def fit_normalizer_from_references(
    reference_trajectories: Sequence[Trajectory],
) -> ScoreNormalizer:
    """
    Fit normalization parameters using only historical references.

    For each reference trajectory, calculate its minimum DTW distance
    to the other reference trajectories. These distances form the
    historical baseline distribution.
    """
    k = len(reference_trajectories)

    if k < 2:
        return ScoreNormalizer(
            min_distance=0.0,
            max_distance=100.0,
        )

    loo_distances: list[float] = []

    for i in range(k):
        target = reference_trajectories[i]

        distances = [
            dtw_distance(target, reference_trajectories[j]) for j in range(k) if i != j
        ]

        loo_distances.append(min(distances))

    min_dist = float(min(loo_distances))
    max_dist = float(max(loo_distances))

    # Avoid division by zero when all historical routes are identical.
    if max_dist <= min_dist:
        max_dist = min_dist + 100.0

    return ScoreNormalizer(
        min_distance=min_dist,
        max_distance=max_dist,
    )


def score_route_deviation(
    candidate_trajectory: Trajectory,
    reference_set: Union[ReferenceSetResult, Sequence[Trajectory]],
    normalizer: ScoreNormalizer | None = None,
) -> RouteDeviationResult:
    """
    Score a candidate trajectory against its personalized reference set.

    If historical data is insufficient, no distance or score is produced.
    Otherwise, the minimum DTW distance to the historical references is
    calculated and normalized to [0.0, 1.0].
    """
    user_id = candidate_trajectory.user_id
    candidate_id = candidate_trajectory.trajectory_id

    if isinstance(reference_set, ReferenceSetResult):
        if not reference_set.is_sufficient:
            return RouteDeviationResult(
                user_id=user_id,
                trajectory_id=candidate_id,
                status=STATUS_INSUFFICIENT_HISTORY,
                raw_distance_meters=None,
                route_deviation_score=None,
                reference_trajectory_count=len(reference_set.trajectories),
                closest_reference_id=None,
            )

        refs = list(reference_set.trajectories)

    else:
        refs = list(reference_set)

        if len(refs) < 5:
            return RouteDeviationResult(
                user_id=user_id,
                trajectory_id=candidate_id,
                status=STATUS_INSUFFICIENT_HISTORY,
                raw_distance_meters=None,
                route_deviation_score=None,
                reference_trajectory_count=len(refs),
                closest_reference_id=None,
            )

    min_dist: float | None = None
    closest_id: str | None = None

    for ref in refs:
        dist = dtw_distance(candidate_trajectory, ref)

        if min_dist is None or dist < min_dist:
            min_dist = dist
            closest_id = ref.trajectory_id

    if normalizer is None:
        normalizer = fit_normalizer_from_references(refs)

    norm_score = normalizer.normalize(min_dist)

    return RouteDeviationResult(
        user_id=user_id,
        trajectory_id=candidate_id,
        status="SUCCESS",
        raw_distance_meters=min_dist,
        route_deviation_score=norm_score,
        reference_trajectory_count=len(refs),
        closest_reference_id=closest_id,
    )
