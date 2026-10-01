from datetime import datetime, timezone
import pytest

from ai.route_deviation.loader import Trajectory, TrajectoryPoint
from ai.route_deviation.reference import (
    ReferenceSetResult,
    STATUS_INSUFFICIENT_HISTORY,
    STATUS_SUFFICIENT,
)
from ai.route_deviation.scoring import (
    RouteDeviationResult,
    ScoreNormalizer,
    fit_normalizer_from_references,
    score_route_deviation,
)


def _make_pt(lat: float, lon: float, ts_sec: int) -> TrajectoryPoint:
    ts = datetime.fromtimestamp(ts_sec, tz=timezone.utc)
    return TrajectoryPoint(latitude=lat, longitude=lon, timestamp=ts)


def _make_traj(
    user_id: str,
    traj_id: str,
    lats: list[float],
    lons: list[float],
    start_sec: int = 100,
) -> Trajectory:
    pts = [
        _make_pt(lat, lon, start_sec + i * 10)
        for i, (lat, lon) in enumerate(zip(lats, lons))
    ]
    return Trajectory(user_id=user_id, trajectory_id=traj_id, points=tuple(pts))


def test_score_normalizer_bounds_and_clamping():
    """Verify normalizer maps distances strictly to [0.0, 1.0] with clipping."""
    normalizer = ScoreNormalizer(min_distance=100.0, max_distance=500.0)

    # Below min -> clamped to 0.0
    assert normalizer.normalize(50.0) == 0.0
    assert normalizer.normalize(100.0) == 0.0

    # Intermediate value (e.g. 300m -> 0.5)
    assert normalizer.normalize(300.0) == pytest.approx(0.5)

    # Above max -> clamped to 1.0
    assert normalizer.normalize(500.0) == 1.0
    assert normalizer.normalize(1000.0) == 1.0

    # Monotonicity: larger raw distance produces larger or equal normalized score
    scores = [normalizer.normalize(d) for d in [50, 100, 200, 300, 400, 500, 600]]
    for i in range(len(scores) - 1):
        assert scores[i] <= scores[i + 1]


def test_score_normalizer_validation():
    """Verify normalizer rejects negative min_distance or max < min."""
    with pytest.raises(ValueError, match="negative"):
        ScoreNormalizer(min_distance=-1.0, max_distance=100.0)

    with pytest.raises(ValueError, match="smaller"):
        ScoreNormalizer(min_distance=200.0, max_distance=100.0)


def test_minimum_dtw_distance_selected():
    """Verify that score_route_deviation selects the minimum DTW distance and closest reference ID."""
    # Candidate along path 1
    candidate = _make_traj(
        "user_1", "cand", [39.0, 39.1], [116.0, 116.1], start_sec=1000
    )

    # 5 references: ref_0 is identical to candidate; others are shifted further away
    ref_0 = _make_traj(
        "user_1", "ref_identical", [39.0, 39.1], [116.0, 116.1], start_sec=100
    )
    ref_1 = _make_traj(
        "user_1", "ref_near", [39.01, 39.11], [116.0, 116.1], start_sec=200
    )
    ref_2 = _make_traj("user_1", "ref_far", [39.5, 39.6], [116.0, 116.1], start_sec=300)
    ref_3 = _make_traj(
        "user_1", "ref_farther", [40.0, 40.1], [116.0, 116.1], start_sec=400
    )
    ref_4 = _make_traj(
        "user_1", "ref_farthest", [41.0, 41.1], [116.0, 116.1], start_sec=500
    )

    refs = [ref_4, ref_3, ref_2, ref_1, ref_0]
    ref_result = ReferenceSetResult(
        user_id="user_1",
        candidate_id="cand",
        is_sufficient=True,
        status=STATUS_SUFFICIENT,
        trajectories=tuple(refs),
    )

    result = score_route_deviation(candidate, ref_result)

    assert isinstance(result, RouteDeviationResult)
    assert result.status == "SUCCESS"
    assert result.closest_reference_id == "ref_identical"
    assert result.raw_distance_meters == pytest.approx(0.0, abs=1e-6)
    assert result.route_deviation_score == pytest.approx(0.0, abs=1e-6)
    assert result.reference_trajectory_count == 5


def test_raw_distance_in_meters():
    """Verify that raw distance is in meters matching physical displacement."""
    # Candidate shifted ~111 meters north of references
    candidate = _make_traj(
        "user_1", "cand", [39.001, 39.101], [116.0, 116.1], start_sec=1000
    )

    # 5 baseline references along 39.0 -> 39.1
    refs = [
        _make_traj(
            "user_1", f"ref_{i}", [39.0, 39.1], [116.0, 116.1], start_sec=100 * (i + 1)
        )
        for i in range(5)
    ]
    ref_result = ReferenceSetResult(
        user_id="user_1",
        candidate_id="cand",
        is_sufficient=True,
        status=STATUS_SUFFICIENT,
        trajectories=tuple(refs),
    )

    result = score_route_deviation(candidate, ref_result)
    assert result.raw_distance_meters is not None
    # 2 points shifted by ~111m each -> cumulative DTW ~ 222m
    assert 200.0 < result.raw_distance_meters < 250.0


def test_insufficient_history_returns_none_values():
    """Verify that when reference set is insufficient, raw distance and score are None."""
    candidate = _make_traj(
        "user_1", "cand", [39.0, 39.1], [116.0, 116.1], start_sec=1000
    )

    # Only 3 references -> insufficient
    refs = [
        _make_traj(
            "user_1", f"ref_{i}", [39.0, 39.1], [116.0, 116.1], start_sec=100 * (i + 1)
        )
        for i in range(3)
    ]
    insufficient_ref_result = ReferenceSetResult(
        user_id="user_1",
        candidate_id="cand",
        is_sufficient=False,
        status=STATUS_INSUFFICIENT_HISTORY,
        trajectories=tuple(refs),
    )

    result = score_route_deviation(candidate, insufficient_ref_result)

    assert result.status == STATUS_INSUFFICIENT_HISTORY
    assert result.raw_distance_meters is None
    assert result.route_deviation_score is None
    assert result.closest_reference_id is None
    assert result.reference_trajectory_count == 3


def test_normalization_stays_within_zero_one():
    """Verify that route_deviation_score is strictly bounded in [0.0, 1.0]."""
    candidate_extreme = _make_traj(
        "user_1", "cand_far", [80.0, 80.1], [0.0, 0.1], start_sec=1000
    )
    refs = [
        _make_traj(
            "user_1", f"ref_{i}", [39.0, 39.1], [116.0, 116.1], start_sec=100 * (i + 1)
        )
        for i in range(5)
    ]
    ref_result = ReferenceSetResult(
        user_id="user_1",
        candidate_id="cand_far",
        is_sufficient=True,
        status=STATUS_SUFFICIENT,
        trajectories=tuple(refs),
    )

    result = score_route_deviation(candidate_extreme, ref_result)
    assert result.route_deviation_score is not None
    assert 0.0 <= result.route_deviation_score <= 1.0
    assert result.route_deviation_score == 1.0  # Far away route saturated at 1.0


def test_candidate_distance_does_not_affect_fitted_parameters():
    """Verify that normalization parameters are fitted exclusively from references."""
    refs = [
        _make_traj("user_1", "ref_0", [39.00, 39.10], [116.0, 116.0], start_sec=100),
        _make_traj("user_1", "ref_1", [39.01, 39.11], [116.0, 116.0], start_sec=200),
        _make_traj("user_1", "ref_2", [39.02, 39.12], [116.0, 116.0], start_sec=300),
        _make_traj("user_1", "ref_3", [39.03, 39.13], [116.0, 116.0], start_sec=400),
        _make_traj("user_1", "ref_4", [39.04, 39.14], [116.0, 116.0], start_sec=500),
    ]

    normalizer1 = fit_normalizer_from_references(refs)

    # Evaluate candidate A (nearby)
    cand_a = _make_traj(
        "user_1", "cand_a", [39.00, 39.10], [116.0, 116.0], start_sec=1000
    )
    res_a = score_route_deviation(cand_a, refs, normalizer=normalizer1)
    assert res_a.route_deviation_score is not None

    # Evaluate candidate B (thousands of km away)
    cand_b = _make_traj(
        "user_1", "cand_b", [10.00, 10.10], [116.0, 116.0], start_sec=1000
    )
    res_b = score_route_deviation(cand_b, refs, normalizer=normalizer1)
    assert res_b.route_deviation_score is not None

    normalizer2 = fit_normalizer_from_references(refs)

    # Normalizer parameters must be identical and unaffected by candidate evaluation
    assert normalizer1.min_distance == normalizer2.min_distance
    assert normalizer1.max_distance == normalizer2.max_distance
