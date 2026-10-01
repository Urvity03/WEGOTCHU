"""Route-deviation baseline module for WEGOTCHU."""

from .distance import (
    EARTH_RADIUS_METERS,
    haversine_distance,
    pairwise_haversine_matrix,
)
from .dtw import (
    compute_dtw_accumulated_cost_matrix,
    dtw_distance,
)
from .loader import Trajectory, TrajectoryPoint, load_trajectories
from .reference import (
    MIN_HISTORICAL_TRAJECTORIES,
    STATUS_INSUFFICIENT_HISTORY,
    STATUS_SUFFICIENT,
    ReferenceSetResult,
    build_reference_set,
)
from .scoring import (
    RouteDeviationResult,
    ScoreNormalizer,
    fit_normalizer_from_references,
    score_route_deviation,
)

__all__ = [
    "EARTH_RADIUS_METERS",
    "MIN_HISTORICAL_TRAJECTORIES",
    "ReferenceSetResult",
    "RouteDeviationResult",
    "STATUS_INSUFFICIENT_HISTORY",
    "STATUS_SUFFICIENT",
    "ScoreNormalizer",
    "Trajectory",
    "TrajectoryPoint",
    "build_reference_set",
    "compute_dtw_accumulated_cost_matrix",
    "dtw_distance",
    "fit_normalizer_from_references",
    "haversine_distance",
    "load_trajectories",
    "pairwise_haversine_matrix",
    "score_route_deviation",
]
