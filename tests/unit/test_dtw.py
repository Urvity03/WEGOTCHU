from datetime import datetime, timezone
import pytest

from ai.route_deviation.distance import haversine_distance
from ai.route_deviation.dtw import compute_dtw_accumulated_cost_matrix, dtw_distance
from ai.route_deviation.loader import Trajectory, TrajectoryPoint


def _make_pt(lat: float, lon: float, ts_offset_sec: int = 0) -> TrajectoryPoint:
    """Helper to construct TrajectoryPoint with deterministic UTC timestamps."""
    base_ts = datetime(2026, 10, 1, 12, 0, 0, tzinfo=timezone.utc)
    ts = datetime.fromtimestamp(base_ts.timestamp() + ts_offset_sec, tz=timezone.utc)
    return TrajectoryPoint(latitude=lat, longitude=lon, timestamp=ts)


def _make_traj(points, traj_id="traj_test", user_id="usr_001"):
    """Helper to construct a Trajectory object."""
    return Trajectory(user_id=user_id, trajectory_id=traj_id, points=tuple(points))


def test_identical_trajectory_against_itself():
    """Verify that DTW distance of a trajectory compared with itself is 0.0."""
    pts = [
        _make_pt(39.90, 116.40, 0),
        _make_pt(39.91, 116.41, 10),
        _make_pt(39.92, 116.42, 20),
    ]
    traj = _make_traj(pts)

    dist = dtw_distance(traj, traj)
    assert dist == pytest.approx(0.0, abs=1e-6)
    assert isinstance(dist, float)


def test_identical_spatial_path_with_different_timestamps():
    """Verify that timestamp differences do not alter DTW distance."""
    pts1 = [
        _make_pt(39.90, 116.40, ts_offset_sec=0),
        _make_pt(39.91, 116.41, ts_offset_sec=10),
        _make_pt(39.92, 116.42, ts_offset_sec=20),
    ]
    # Same spatial coordinates, completely different timestamps (1 day later, different intervals)
    pts2 = [
        _make_pt(39.90, 116.40, ts_offset_sec=86400),
        _make_pt(39.91, 116.41, ts_offset_sec=86500),
        _make_pt(39.92, 116.42, ts_offset_sec=86900),
    ]

    traj1 = _make_traj(pts1, "t1")
    traj2 = _make_traj(pts2, "t2")

    dist = dtw_distance(traj1, traj2)
    assert dist == pytest.approx(0.0, abs=1e-6)


def test_small_spatial_shift():
    """Verify that a small parallel spatial shift produces a positive cumulative distance."""
    pts_base = [
        _make_pt(39.900, 116.400, 0),
        _make_pt(39.910, 116.400, 10),
        _make_pt(39.920, 116.400, 20),
    ]
    # Shift slightly east (~85 meters per point)
    pts_shifted = [
        _make_pt(39.900, 116.401, 0),
        _make_pt(39.910, 116.401, 10),
        _make_pt(39.920, 116.401, 20),
    ]

    traj_base = _make_traj(pts_base, "base")
    traj_shifted = _make_traj(pts_shifted, "shifted")

    dist = dtw_distance(traj_base, traj_shifted)
    assert dist > 0.0

    # With 3 parallel points shifted by ~85m each, cumulative DTW is approx 3 * 85m ~ 256m
    expected_shift_per_pt = haversine_distance(pts_base[0], pts_shifted[0])
    assert dist == pytest.approx(expected_shift_per_pt * 3.0, rel=0.05)


def test_clearly_different_trajectories_have_larger_distance():
    """Verify that a diverted trajectory has a strictly larger distance than a minor shift."""
    pts_base = [
        _make_pt(39.90, 116.40, 0),
        _make_pt(39.91, 116.40, 10),
        _make_pt(39.92, 116.40, 20),
    ]
    # Minor displacement
    pts_minor = [
        _make_pt(39.900, 116.401, 0),
        _make_pt(39.910, 116.401, 10),
        _make_pt(39.920, 116.401, 20),
    ]
    # Major diversion to a different corridor (~10 km away)
    pts_diverted = [
        _make_pt(39.90, 116.50, 0),
        _make_pt(39.91, 116.50, 10),
        _make_pt(39.92, 116.50, 20),
    ]

    traj_base = _make_traj(pts_base, "base")
    traj_minor = _make_traj(pts_minor, "minor")
    traj_diverted = _make_traj(pts_diverted, "diverted")

    dist_minor = dtw_distance(traj_base, traj_minor)
    dist_diverted = dtw_distance(traj_base, traj_diverted)

    assert dist_diverted > dist_minor
    assert dist_diverted > 10_000.0  # Over 10 km cumulative spatial distance


def test_single_point_sequences():
    """Verify that DTW distance between two 1-point sequences equals exactly the Haversine distance."""
    p_a = _make_pt(39.90, 116.40)
    p_b = _make_pt(39.95, 116.45)

    dist = dtw_distance([p_a], [p_b])
    expected = haversine_distance(p_a, p_b)

    assert dist == pytest.approx(expected, rel=1e-9)


def test_different_trajectory_lengths():
    """Verify that DTW naturally aligns variable-length trajectories along the same path."""
    # Coarse path with 3 points
    pts_coarse = [
        _make_pt(39.0, 116.0, 0),
        _make_pt(39.5, 116.0, 30),
        _make_pt(40.0, 116.0, 60),
    ]
    # Denser path along the same line with 5 points
    pts_dense = [
        _make_pt(39.0, 116.0, 0),
        _make_pt(39.25, 116.0, 15),
        _make_pt(39.5, 116.0, 30),
        _make_pt(39.75, 116.0, 45),
        _make_pt(40.0, 116.0, 60),
    ]

    traj_coarse = _make_traj(pts_coarse, "coarse")
    traj_dense = _make_traj(pts_dense, "dense")

    # DTW should execute cleanly on unequal lengths (3 vs 5)
    dist = dtw_distance(traj_coarse, traj_dense)
    assert isinstance(dist, float)
    assert dist >= 0.0

    # Because intermediate points (39.25 and 39.75) warp to the nearest collinear points,
    # the distance should be relatively small
    assert dist < 100_000.0


def test_symmetry():
    """Verify that dtw(A, B) == dtw(B, A)."""
    pts_a = [
        _make_pt(39.0, 116.0, 0),
        _make_pt(39.1, 116.1, 10),
        _make_pt(39.2, 116.2, 20),
    ]
    pts_b = [
        _make_pt(39.05, 116.05, 0),
        _make_pt(39.15, 116.15, 15),
    ]

    traj_a = _make_traj(pts_a, "a")
    traj_b = _make_traj(pts_b, "b")

    dist_ab = dtw_distance(traj_a, traj_b)
    dist_ba = dtw_distance(traj_b, traj_a)

    assert dist_ab == pytest.approx(dist_ba, rel=1e-12)


def test_accumulated_cost_matrix_recurrence():
    """Verify the step-by-step recurrence values in the accumulated cost matrix."""
    pts_a = [_make_pt(0.0, 0.0), _make_pt(0.0, 1.0)]
    pts_b = [_make_pt(0.0, 0.0), _make_pt(0.0, 1.0)]

    c00 = haversine_distance(pts_a[0], pts_b[0])  # 0.0
    c01 = haversine_distance(pts_a[0], pts_b[1])  # ~111,195m
    c10 = haversine_distance(pts_a[1], pts_b[0])  # ~111,195m
    c11 = haversine_distance(pts_a[1], pts_b[1])  # 0.0

    cost_matrix = compute_dtw_accumulated_cost_matrix(
        pytest.importorskip("numpy").array([[c00, c01], [c10, c11]])
    )

    # D(0,0) = 0.0
    assert cost_matrix[0, 0] == 0.0
    # D(0,1) = D(0,0) + c01 = c01
    assert cost_matrix[0, 1] == pytest.approx(c01)
    # D(1,0) = D(0,0) + c10 = c10
    assert cost_matrix[1, 0] == pytest.approx(c10)
    # D(1,1) = c11 + min(D(0,1), D(1,0), D(0,0)) = 0.0 + min(c01, c10, 0.0) = 0.0
    assert cost_matrix[1, 1] == pytest.approx(0.0, abs=1e-6)


def test_empty_trajectory_raises_value_error():
    """Verify that passing an empty sequence raises ValueError."""
    pts = [_make_pt(39.0, 116.0), _make_pt(39.1, 116.1)]

    with pytest.raises(ValueError, match="empty"):
        dtw_distance([], pts)

    with pytest.raises(ValueError, match="empty"):
        dtw_distance(pts, [])
