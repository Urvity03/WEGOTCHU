from datetime import datetime, timezone
import pytest

from ai.route_deviation.loader import Trajectory, TrajectoryPoint
from ai.route_deviation.reference import (
    STATUS_INSUFFICIENT_HISTORY,
    STATUS_SUFFICIENT,
    ReferenceSetResult,
    build_reference_set,
)


def _make_pt(lat: float, lon: float, ts_sec: int) -> TrajectoryPoint:
    """Helper to construct TrajectoryPoint from epoch seconds."""
    ts = datetime.fromtimestamp(ts_sec, tz=timezone.utc)
    return TrajectoryPoint(latitude=lat, longitude=lon, timestamp=ts)


def _make_traj(
    user_id: str, traj_id: str, start_sec: int, duration_sec: int = 10
) -> Trajectory:
    """Helper to construct a valid 2-point Trajectory with a specific start time."""
    p1 = _make_pt(39.9, 116.4, start_sec)
    p2 = _make_pt(39.91, 116.41, start_sec + duration_sec)
    return Trajectory(user_id=user_id, trajectory_id=traj_id, points=(p1, p2))


def test_same_user_historical_trajectories_selected():
    """Verify that earlier trajectories from the same user are selected."""
    # Candidate starts at t = 1000
    candidate = _make_traj("user_1", "cand", start_sec=1000)

    # 5 historical trajectories: t = 100, 200, 300, 400, 500
    history = [
        _make_traj("user_1", f"hist_{i}", start_sec=100 * (i + 1)) for i in range(5)
    ]

    result = build_reference_set(history, candidate)

    assert isinstance(result, ReferenceSetResult)
    assert result.user_id == "user_1"
    assert result.candidate_id == "cand"
    assert result.is_sufficient is True
    assert result.status == STATUS_SUFFICIENT
    assert len(result) == 5
    assert [t.trajectory_id for t in result] == [f"hist_{i}" for i in range(5)]


def test_other_users_are_excluded():
    """Verify that trajectories from other users are strictly excluded."""
    candidate = _make_traj("user_1", "cand", start_sec=1000)

    # 4 trajectories from user_1 (insufficient) + 5 trajectories from user_2
    history_u1 = [
        _make_traj("user_1", f"u1_hist_{i}", start_sec=100 * (i + 1)) for i in range(4)
    ]
    history_u2 = [
        _make_traj("user_2", f"u2_hist_{i}", start_sec=100 * (i + 1)) for i in range(5)
    ]

    pool = history_u1 + history_u2
    result = build_reference_set(pool, candidate)

    # Should only contain user_1 trajectories
    assert len(result) == 4
    assert result.is_sufficient is False
    assert result.status == STATUS_INSUFFICIENT_HISTORY
    assert all(t.user_id == "user_1" for t in result)


def test_future_trajectories_are_excluded():
    """Verify that trajectories occurring after the candidate start time are excluded."""
    candidate = _make_traj("user_1", "cand", start_sec=1000)

    # 3 past trajectories (t = 700, 800, 900)
    past = [
        _make_traj("user_1", f"past_{i}", start_sec=700 + i * 100) for i in range(3)
    ]
    # 3 future trajectories (t = 1100, 1200, 1300)
    future = [
        _make_traj("user_1", f"future_{i}", start_sec=1100 + i * 100) for i in range(3)
    ]

    result = build_reference_set(past + future, candidate)

    assert len(result) == 3
    assert [t.trajectory_id for t in result] == ["past_0", "past_1", "past_2"]
    assert result.is_sufficient is False


def test_candidate_trajectory_is_excluded():
    """Verify that the candidate trajectory is never included in its own reference set."""
    candidate = _make_traj("user_1", "cand", start_sec=1000)
    history = [
        _make_traj("user_1", f"hist_{i}", start_sec=100 * (i + 1)) for i in range(5)
    ]

    # Pool includes candidate itself
    pool = history + [candidate]
    result = build_reference_set(pool, candidate)

    assert len(result) == 5
    assert candidate.trajectory_id not in [t.trajectory_id for t in result]


def test_exactly_five_historical_trajectories_is_sufficient():
    """Verify the exact boundary where count == 5 produces is_sufficient == True."""
    candidate = _make_traj("user_1", "cand", start_sec=1000)
    history_5 = [
        _make_traj("user_1", f"h_{i}", start_sec=100 * (i + 1)) for i in range(5)
    ]

    result = build_reference_set(history_5, candidate, min_history=5)

    assert len(result) == 5
    assert result.is_sufficient is True
    assert result.status == STATUS_SUFFICIENT


def test_fewer_than_five_historical_trajectories_is_insufficient():
    """Verify that count < 5 produces an explicit INSUFFICIENT_HISTORY status."""
    candidate = _make_traj("user_1", "cand", start_sec=1000)

    # 4 historical trajectories
    history_4 = [
        _make_traj("user_1", f"h_{i}", start_sec=100 * (i + 1)) for i in range(4)
    ]

    result = build_reference_set(history_4, candidate, min_history=5)

    assert len(result) == 4
    assert result.is_sufficient is False
    assert result.status == STATUS_INSUFFICIENT_HISTORY

    # 0 historical trajectories
    empty_result = build_reference_set([], candidate, min_history=5)
    assert len(empty_result) == 0
    assert empty_result.is_sufficient is False
    assert empty_result.status == STATUS_INSUFFICIENT_HISTORY


def test_same_start_timestamp_is_excluded():
    """Verify that a trajectory with the exact same start timestamp as the candidate is excluded."""
    candidate = _make_traj("user_1", "cand", start_sec=1000)

    # Starts at the exact same second: t = 1000
    concurrent_traj = _make_traj("user_1", "concurrent", start_sec=1000)

    # 4 strictly earlier trajectories (t = 600, 700, 800, 900)
    earlier = [
        _make_traj("user_1", f"early_{i}", start_sec=600 + i * 100) for i in range(4)
    ]

    pool = earlier + [concurrent_traj]
    result = build_reference_set(pool, candidate)

    # concurrent_traj must be excluded, leaving only 4 -> INSUFFICIENT_HISTORY
    assert len(result) == 4
    assert "concurrent" not in [t.trajectory_id for t in result]
    assert result.is_sufficient is False
    assert result.status == STATUS_INSUFFICIENT_HISTORY


def test_references_returned_in_chronological_order():
    """Verify that references are returned sorted from oldest to newest regardless of input order."""
    candidate = _make_traj("user_1", "cand", start_sec=1000)

    t_100 = _make_traj("user_1", "t_100", start_sec=100)
    t_200 = _make_traj("user_1", "t_200", start_sec=200)
    t_300 = _make_traj("user_1", "t_300", start_sec=300)
    t_400 = _make_traj("user_1", "t_400", start_sec=400)
    t_500 = _make_traj("user_1", "t_500", start_sec=500)

    # Pass in scrambled order
    scrambled = [t_400, t_100, t_500, t_200, t_300]
    result = build_reference_set(scrambled, candidate)

    assert [t.trajectory_id for t in result] == [
        "t_100",
        "t_200",
        "t_300",
        "t_400",
        "t_500",
    ]


def test_historical_selection_does_not_depend_on_id_ordering():
    """Verify that chronological selection uses timestamp rather than alphanumeric ID order."""
    candidate = _make_traj("user_1", "cand", start_sec=1000)

    # IDs reverse alphabetical to timestamps
    traj_z = _make_traj("user_1", "id_zzz", start_sec=100)  # Oldest time, "largest" ID
    traj_m = _make_traj("user_1", "id_mmm", start_sec=200)
    traj_a = _make_traj("user_1", "id_aaa", start_sec=300)  # Newest time, "smallest" ID

    result = build_reference_set([traj_a, traj_z, traj_m], candidate, min_history=1)

    assert [t.trajectory_id for t in result] == ["id_zzz", "id_mmm", "id_aaa"]


def test_input_validation():
    """Verify validation of candidate_trajectory type and min_history bounds."""
    candidate = _make_traj("user_1", "cand", start_sec=1000)

    with pytest.raises(TypeError, match="Trajectory"):
        build_reference_set([], "not-a-trajectory")  # type: ignore

    with pytest.raises(ValueError, match="min_history"):
        build_reference_set([], candidate, min_history=0)
