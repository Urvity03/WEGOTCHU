from datetime import datetime, timezone

import pytest

from ai.route_deviation.loader import Trajectory, TrajectoryPoint
from ai.route_deviation.reference import (
    STATUS_INSUFFICIENT_HISTORY,
    STATUS_SUFFICIENT,
    ReferenceSetResult,
    build_reference_set,
    build_reference_set_from_sorted,
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
    candidate = _make_traj("user_1", "cand", start_sec=1000)

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

    history_u1 = [
        _make_traj("user_1", f"u1_hist_{i}", start_sec=100 * (i + 1)) for i in range(4)
    ]
    history_u2 = [
        _make_traj("user_2", f"u2_hist_{i}", start_sec=100 * (i + 1)) for i in range(5)
    ]

    result = build_reference_set(history_u1 + history_u2, candidate)

    assert len(result) == 4
    assert result.is_sufficient is False
    assert result.status == STATUS_INSUFFICIENT_HISTORY
    assert all(t.user_id == "user_1" for t in result)


def test_future_trajectories_are_excluded():
    """Verify that trajectories after the candidate start time are excluded."""
    candidate = _make_traj("user_1", "cand", start_sec=1000)

    past = [
        _make_traj("user_1", f"past_{i}", start_sec=700 + i * 100) for i in range(3)
    ]
    future = [
        _make_traj("user_1", f"future_{i}", start_sec=1100 + i * 100) for i in range(3)
    ]

    result = build_reference_set(past + future, candidate)

    assert len(result) == 3
    assert [t.trajectory_id for t in result] == ["past_0", "past_1", "past_2"]
    assert result.is_sufficient is False


def test_candidate_trajectory_is_excluded():
    """Verify that the candidate is never included in its own reference set."""
    candidate = _make_traj("user_1", "cand", start_sec=1000)
    history = [
        _make_traj("user_1", f"hist_{i}", start_sec=100 * (i + 1)) for i in range(5)
    ]

    result = build_reference_set(history + [candidate], candidate)

    assert len(result) == 5
    assert candidate.trajectory_id not in [t.trajectory_id for t in result]


def test_exactly_five_historical_trajectories_is_sufficient():
    """Verify the boundary where five historical trajectories are sufficient."""
    candidate = _make_traj("user_1", "cand", start_sec=1000)
    history = [
        _make_traj("user_1", f"h_{i}", start_sec=100 * (i + 1)) for i in range(5)
    ]

    result = build_reference_set(history, candidate, min_history=5)

    assert len(result) == 5
    assert result.is_sufficient is True
    assert result.status == STATUS_SUFFICIENT


def test_fewer_than_five_historical_trajectories_is_insufficient():
    """Verify that fewer than five historical trajectories are insufficient."""
    candidate = _make_traj("user_1", "cand", start_sec=1000)
    history = [
        _make_traj("user_1", f"h_{i}", start_sec=100 * (i + 1)) for i in range(4)
    ]

    result = build_reference_set(history, candidate, min_history=5)

    assert len(result) == 4
    assert result.is_sufficient is False
    assert result.status == STATUS_INSUFFICIENT_HISTORY

    empty_result = build_reference_set([], candidate, min_history=5)

    assert len(empty_result) == 0
    assert empty_result.is_sufficient is False
    assert empty_result.status == STATUS_INSUFFICIENT_HISTORY


def test_same_start_timestamp_is_excluded():
    """Verify that a trajectory starting at the candidate's time is excluded."""
    candidate = _make_traj("user_1", "cand", start_sec=1000)
    concurrent = _make_traj("user_1", "concurrent", start_sec=1000)

    earlier = [
        _make_traj("user_1", f"early_{i}", start_sec=600 + i * 100) for i in range(4)
    ]

    result = build_reference_set(earlier + [concurrent], candidate)

    assert len(result) == 4
    assert "concurrent" not in [t.trajectory_id for t in result]
    assert result.is_sufficient is False
    assert result.status == STATUS_INSUFFICIENT_HISTORY


def test_references_returned_in_chronological_order():
    """Verify chronological ordering regardless of input order."""
    candidate = _make_traj("user_1", "cand", start_sec=1000)

    t_100 = _make_traj("user_1", "t_100", start_sec=100)
    t_200 = _make_traj("user_1", "t_200", start_sec=200)
    t_300 = _make_traj("user_1", "t_300", start_sec=300)
    t_400 = _make_traj("user_1", "t_400", start_sec=400)
    t_500 = _make_traj("user_1", "t_500", start_sec=500)

    result = build_reference_set(
        [t_400, t_100, t_500, t_200, t_300],
        candidate,
    )

    assert [t.trajectory_id for t in result] == [
        "t_100",
        "t_200",
        "t_300",
        "t_400",
        "t_500",
    ]


def test_historical_selection_does_not_depend_on_id_ordering():
    """Verify that chronological selection uses timestamps, not ID ordering."""
    candidate = _make_traj("user_1", "cand", start_sec=1000)

    traj_z = _make_traj("user_1", "id_zzz", start_sec=100)
    traj_m = _make_traj("user_1", "id_mmm", start_sec=200)
    traj_a = _make_traj("user_1", "id_aaa", start_sec=300)

    result = build_reference_set(
        [traj_a, traj_z, traj_m],
        candidate,
        min_history=1,
    )

    assert [t.trajectory_id for t in result] == [
        "id_zzz",
        "id_mmm",
        "id_aaa",
    ]


def test_input_validation():
    """Verify candidate type and minimum-history validation."""
    candidate = _make_traj("user_1", "cand", start_sec=1000)

    with pytest.raises(TypeError, match="Trajectory"):
        build_reference_set([], "not-a-trajectory")  # type: ignore

    with pytest.raises(ValueError, match="min_history"):
        build_reference_set([], candidate, min_history=0)


def test_multiple_trajectories_with_same_start_time_are_excluded():
    """Exclude every trajectory tied with the candidate's start time."""
    candidate = _make_traj("user_1", "candidate", start_sec=1000)

    earlier = [
        _make_traj("user_1", f"early_{i}", start_sec=100 + i * 100) for i in range(5)
    ]
    concurrent = [
        _make_traj("user_1", "concurrent_a", start_sec=1000),
        _make_traj("user_1", "concurrent_b", start_sec=1000),
    ]
    future = _make_traj("user_1", "future", start_sec=1100)

    result = build_reference_set(
        earlier + concurrent + [future],
        candidate,
    )

    assert [t.trajectory_id for t in result] == [f"early_{i}" for i in range(5)]
    assert result.is_sufficient is True


def test_reference_selection_is_independent_of_input_order():
    """Return the same historical references regardless of pool ordering."""
    candidate = _make_traj("user_1", "candidate", start_sec=1000)

    pool = [
        _make_traj("user_1", "later", start_sec=1200),
        _make_traj("user_1", "earlier_b", start_sec=200),
        _make_traj("user_1", "same_time", start_sec=1000),
        _make_traj("user_1", "earlier_a", start_sec=100),
    ]

    forward = build_reference_set(pool, candidate, min_history=1)
    reverse = build_reference_set(list(reversed(pool)), candidate, min_history=1)

    forward_ids = [t.trajectory_id for t in forward]
    reverse_ids = [t.trajectory_id for t in reverse]

    assert forward_ids == reverse_ids == ["earlier_a", "earlier_b"]


def test_sorted_equivalence_with_build_reference_set():
    """Verify build_reference_set_from_sorted produces identical results to build_reference_set."""
    candidate = _make_traj("user_1", "cand", start_sec=1000)

    # Various trajectories: past, tied, candidate itself, and future
    raw_trajectories = [
        _make_traj("user_1", "hist_3", start_sec=300),
        _make_traj("user_1", "hist_1", start_sec=100),
        _make_traj("user_1", "hist_2", start_sec=200),
        _make_traj("user_1", "hist_5", start_sec=500),
        _make_traj("user_1", "hist_4", start_sec=400),
        _make_traj("user_1", "cand", start_sec=1000),
        _make_traj("user_1", "concurrent", start_sec=1000),
        _make_traj("user_1", "future_1", start_sec=1200),
    ]

    # Chronologically sorted as required by the precondition
    sorted_trajectories = sorted(
        raw_trajectories,
        key=lambda t: (t.points[0].timestamp, t.trajectory_id),
    )

    baseline_res = build_reference_set(sorted_trajectories, candidate, min_history=5)
    fast_res = build_reference_set_from_sorted(
        sorted_trajectories, candidate, min_history=5
    )

    assert fast_res.user_id == baseline_res.user_id == "user_1"
    assert fast_res.candidate_id == baseline_res.candidate_id == "cand"
    assert fast_res.is_sufficient == baseline_res.is_sufficient is True
    assert fast_res.status == baseline_res.status == STATUS_SUFFICIENT
    assert (
        [t.trajectory_id for t in fast_res]
        == [t.trajectory_id for t in baseline_res]
        == ["hist_1", "hist_2", "hist_3", "hist_4", "hist_5"]
    )


def test_sorted_strict_exclusion_of_equal_time_and_future():
    """Verify build_reference_set_from_sorted strictly excludes equal-time and future trajectories."""
    candidate = _make_traj("user_1", "cand", start_sec=1000)

    sorted_trajectories = [
        _make_traj("user_1", "h_100", start_sec=100),
        _make_traj("user_1", "h_200", start_sec=200),
        _make_traj("user_1", "h_300", start_sec=300),
        _make_traj("user_1", "tied_a", start_sec=1000),
        _make_traj("user_1", "tied_b", start_sec=1000),
        _make_traj("user_1", "future_1500", start_sec=1500),
    ]

    res = build_reference_set_from_sorted(sorted_trajectories, candidate, min_history=3)

    assert [t.trajectory_id for t in res] == ["h_100", "h_200", "h_300"]
    assert "tied_a" not in [t.trajectory_id for t in res]
    assert "tied_b" not in [t.trajectory_id for t in res]
    assert "future_1500" not in [t.trajectory_id for t in res]
    assert res.is_sufficient is True


def test_sorted_deterministic_ordering_for_tied_timestamps():
    """Verify deterministic tie-breaking preserves (start_timestamp, trajectory_id) order."""
    candidate = _make_traj("user_1", "cand", start_sec=1000)

    # 3 trajectories with identical start_sec=100, pre-sorted by trajectory_id
    sorted_trajectories = [
        _make_traj("user_1", "id_aaa", start_sec=100),
        _make_traj("user_1", "id_bbb", start_sec=100),
        _make_traj("user_1", "id_ccc", start_sec=100),
        _make_traj("user_1", "id_ddd", start_sec=200),
        _make_traj("user_1", "id_eee", start_sec=200),
    ]

    res = build_reference_set_from_sorted(sorted_trajectories, candidate, min_history=5)

    assert [t.trajectory_id for t in res] == [
        "id_aaa",
        "id_bbb",
        "id_ccc",
        "id_ddd",
        "id_eee",
    ]


def test_sorted_candidate_id_exclusion():
    """Verify candidate is excluded even if present in the historical prefix."""
    candidate = _make_traj("user_1", "cand", start_sec=1000)

    # Coincidentally candidate_id appears with an earlier timestamp
    sorted_trajectories = [
        _make_traj("user_1", "h_100", start_sec=100),
        _make_traj("user_1", "cand", start_sec=200),
        _make_traj("user_1", "h_300", start_sec=300),
    ]

    res = build_reference_set_from_sorted(sorted_trajectories, candidate, min_history=1)

    assert [t.trajectory_id for t in res] == ["h_100", "h_300"]
    assert "cand" not in [t.trajectory_id for t in res]


def test_sorted_empty_and_insufficient_history():
    """Verify empty input and count < min_history produce INSUFFICIENT_HISTORY."""
    candidate = _make_traj("user_1", "cand", start_sec=1000)

    # Empty
    empty_res = build_reference_set_from_sorted([], candidate, min_history=5)
    assert len(empty_res) == 0
    assert empty_res.is_sufficient is False
    assert empty_res.status == STATUS_INSUFFICIENT_HISTORY

    # 4 historical (insufficient for min_history=5)
    sorted_4 = [
        _make_traj("user_1", f"h_{i}", start_sec=100 * (i + 1)) for i in range(4)
    ]
    insufficient_res = build_reference_set_from_sorted(
        sorted_4, candidate, min_history=5
    )
    assert len(insufficient_res) == 4
    assert insufficient_res.is_sufficient is False
    assert insufficient_res.status == STATUS_INSUFFICIENT_HISTORY


def test_sorted_input_validation():
    """Verify type checking and min_history bounds."""
    candidate = _make_traj("user_1", "cand", start_sec=1000)

    with pytest.raises(TypeError, match="Trajectory"):
        build_reference_set_from_sorted([], "not-a-trajectory")  # type: ignore

    with pytest.raises(ValueError, match="min_history"):
        build_reference_set_from_sorted([], candidate, min_history=0)


def test_sorted_equivalence_across_candidate_positions():
    """Verify equivalence between build_reference_set and build_reference_set_from_sorted at different positions."""
    # Complex pool with tied timestamps, multiple trajectories, etc.
    pool = [
        _make_traj("user_1", "t_050", start_sec=50),
        _make_traj("user_1", "t_100_a", start_sec=100),
        _make_traj("user_1", "t_100_b", start_sec=100),
        _make_traj("user_1", "t_100_c", start_sec=100),
        _make_traj("user_1", "t_200", start_sec=200),
        _make_traj("user_1", "t_300_a", start_sec=300),
        _make_traj("user_1", "t_300_b", start_sec=300),
        _make_traj("user_1", "t_400", start_sec=400),
        _make_traj("user_1", "t_500", start_sec=500),
        _make_traj("user_1", "t_600", start_sec=600),
    ]

    # Test candidate at beginning (0 past)
    cand_start = _make_traj("user_1", "cand_start", start_sec=40)
    # Test candidate tied with t_100_b
    cand_tied = _make_traj("user_1", "t_100_b", start_sec=100)
    # Test candidate in the middle (after 50, 100a, 100b, 100c, 200)
    cand_mid = _make_traj("user_1", "cand_mid", start_sec=250)
    # Test candidate at end (after all 10)
    cand_end = _make_traj("user_1", "cand_end", start_sec=1000)

    for c in [cand_start, cand_tied, cand_mid, cand_end]:
        res_baseline = build_reference_set(pool, c, min_history=5)
        res_fast = build_reference_set_from_sorted(pool, c, min_history=5)

        assert res_fast.user_id == res_baseline.user_id
        assert res_fast.candidate_id == res_baseline.candidate_id
        assert res_fast.is_sufficient == res_baseline.is_sufficient
        assert res_fast.status == res_baseline.status
        assert [t.trajectory_id for t in res_fast] == [
            t.trajectory_id for t in res_baseline
        ]


def test_segmented_children_count_as_one_original_trajectory():
    """Segments from one original trajectory count only once."""
    candidate = _make_traj("user_1", "candidate", start_sec=1000)

    history = [
        _make_traj("user_1", "trip_01_seg0", start_sec=100),
        _make_traj("user_1", "trip_01_seg1", start_sec=200),
        _make_traj("user_1", "trip_02", start_sec=300),
        _make_traj("user_1", "trip_03", start_sec=400),
        _make_traj("user_1", "trip_04", start_sec=500),
    ]

    result = build_reference_set(
        history,
        candidate,
        min_history=5,
    )

    assert result.is_sufficient is False
    assert result.status == STATUS_INSUFFICIENT_HISTORY
    assert len(result) == 4


def test_sorted_reference_deduplicates_segmented_children():
    """The sorted reference path also deduplicates original trajectories."""
    candidate = _make_traj("user_1", "candidate", start_sec=1000)

    history = [
        _make_traj("user_1", "trip_01_seg0", start_sec=100),
        _make_traj("user_1", "trip_01_seg1", start_sec=200),
        _make_traj("user_1", "trip_02", start_sec=300),
        _make_traj("user_1", "trip_03", start_sec=400),
        _make_traj("user_1", "trip_04", start_sec=500),
    ]

    result = build_reference_set_from_sorted(
        history,
        candidate,
        min_history=5,
    )

    assert result.is_sufficient is False
    assert result.status == STATUS_INSUFFICIENT_HISTORY
    assert len(result) == 4
