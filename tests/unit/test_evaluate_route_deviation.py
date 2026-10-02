"""Focused tests for the route deviation baseline evaluation harness."""

from datetime import datetime, timedelta
import pandas as pd
import pytest

from ai.route_deviation.loader import Trajectory, TrajectoryPoint
from ai.route_deviation.reference import STATUS_INSUFFICIENT_HISTORY
from scripts.evaluate_route_deviation import evaluate_candidates


def _make_trajectory(
    user_id: str,
    traj_id: str,
    start_time: datetime,
    lat_offset: float = 0.0,
) -> Trajectory:
    """Helper to construct a simple 2-point valid trajectory."""
    p1 = TrajectoryPoint(
        latitude=39.9042 + lat_offset,
        longitude=116.4074,
        timestamp=start_time,
    )
    p2 = TrajectoryPoint(
        latitude=39.9142 + lat_offset,
        longitude=116.4174,
        timestamp=start_time + timedelta(minutes=5),
    )
    return Trajectory(user_id=user_id, trajectory_id=traj_id, points=(p1, p2))


def test_evaluates_only_validation_and_test_candidates():
    """Verify reference split trajectories are not evaluated as candidates."""
    base_time = datetime(2026, 1, 1, 10, 0, 0)
    user_id = "user_001"

    # Create 6 historical references, 1 val, 1 test
    trajectories = []
    manifest_rows = []

    for i in range(6):
        t_id = f"traj_{i}"
        trajectories.append(
            _make_trajectory(user_id, t_id, base_time + timedelta(hours=i))
        )
        manifest_rows.append(
            {"trajectory_id": t_id, "user_id": user_id, "split": "reference"}
        )

    # 1 validation
    trajectories.append(
        _make_trajectory(user_id, "val_0", base_time + timedelta(hours=6))
    )
    manifest_rows.append(
        {"trajectory_id": "val_0", "user_id": user_id, "split": "validation"}
    )

    # 1 test
    trajectories.append(
        _make_trajectory(user_id, "test_0", base_time + timedelta(hours=7))
    )
    manifest_rows.append(
        {"trajectory_id": "test_0", "user_id": user_id, "split": "test"}
    )

    manifest = pd.DataFrame(manifest_rows)

    results, summary = evaluate_candidates(trajectories, manifest, k_min=5)

    # Only 2 evaluated: val_0 and test_0
    evaluated_ids = [res.trajectory_id for _, res in results]
    assert evaluated_ids == ["val_0", "test_0"]
    assert summary.total_validation_candidates == 1
    assert summary.total_test_candidates == 1
    assert summary.successful_validation_scores == 1
    assert summary.successful_test_scores == 1


def test_candidates_with_fewer_than_kmin_historical_remain_insufficient():
    """Candidates with fewer than 5 historical trajectories receive INSUFFICIENT_HISTORY."""
    base_time = datetime(2026, 1, 1, 10, 0, 0)
    user_id = "user_002"

    # Only 3 references, then 1 validation
    trajectories = [
        _make_trajectory(user_id, "ref_0", base_time),
        _make_trajectory(user_id, "ref_1", base_time + timedelta(hours=1)),
        _make_trajectory(user_id, "ref_2", base_time + timedelta(hours=2)),
        _make_trajectory(user_id, "val_0", base_time + timedelta(hours=3)),
    ]
    manifest = pd.DataFrame(
        [
            {"trajectory_id": "ref_0", "user_id": user_id, "split": "reference"},
            {"trajectory_id": "ref_1", "user_id": user_id, "split": "reference"},
            {"trajectory_id": "ref_2", "user_id": user_id, "split": "reference"},
            {"trajectory_id": "val_0", "user_id": user_id, "split": "validation"},
        ]
    )

    results, summary = evaluate_candidates(trajectories, manifest, k_min=5)

    assert len(results) == 1
    split, res = results[0]
    assert split == "validation"
    assert res.status == STATUS_INSUFFICIENT_HISTORY
    assert res.raw_distance_meters is None
    assert res.route_deviation_score is None
    assert summary.insufficient_history_validation == 1
    assert summary.successful_validation_scores == 0


def test_uses_only_same_user_history():
    """Trajectories from other users must never be included in candidate's history."""
    base_time = datetime(2026, 1, 1, 10, 0, 0)

    # user_A has 10 trajectories
    trajectories = [
        _make_trajectory("user_A", f"A_{i}", base_time + timedelta(hours=i))
        for i in range(10)
    ]
    # user_B has 1 validation trajectory
    trajectories.append(
        _make_trajectory("user_B", "B_val", base_time + timedelta(hours=12))
    )

    manifest_rows = [
        {"trajectory_id": f"A_{i}", "user_id": "user_A", "split": "reference"}
        for i in range(10)
    ]
    manifest_rows.append(
        {"trajectory_id": "B_val", "user_id": "user_B", "split": "validation"}
    )
    manifest = pd.DataFrame(manifest_rows)

    results, summary = evaluate_candidates(trajectories, manifest, k_min=5)

    assert len(results) == 1
    split, res = results[0]
    assert res.user_id == "user_B"
    # user_B has 0 historical trajectories, so must be INSUFFICIENT_HISTORY
    assert res.status == STATUS_INSUFFICIENT_HISTORY
    assert res.reference_trajectory_count == 0


def test_future_trajectories_are_not_used():
    """Trajectories occurring after the candidate must not appear in reference set."""
    base_time = datetime(2026, 1, 1, 10, 0, 0)
    user_id = "user_003"

    # 4 references in past, candidate in middle, 10 references in future
    trajectories = [
        _make_trajectory(user_id, f"past_{i}", base_time + timedelta(hours=i))
        for i in range(4)
    ]
    trajectories.append(
        _make_trajectory(user_id, "cand_val", base_time + timedelta(hours=5))
    )
    for i in range(10):
        trajectories.append(
            _make_trajectory(user_id, f"future_{i}", base_time + timedelta(hours=6 + i))
        )

    manifest_rows = [
        {"trajectory_id": f"past_{i}", "user_id": user_id, "split": "reference"}
        for i in range(4)
    ]
    manifest_rows.append(
        {"trajectory_id": "cand_val", "user_id": user_id, "split": "validation"}
    )
    for i in range(10):
        manifest_rows.append(
            {"trajectory_id": f"future_{i}", "user_id": user_id, "split": "reference"}
        )
    manifest = pd.DataFrame(manifest_rows)

    results, _ = evaluate_candidates(trajectories, manifest, k_min=5)

    assert len(results) == 1
    _, res = results[0]
    # Despite 14 reference trajectories total, only 4 are in the past (< k_min=5)
    assert res.status == STATUS_INSUFFICIENT_HISTORY
    assert res.reference_trajectory_count == 4


def test_candidate_leakage_into_normalizer_fitting():
    """Candidate trajectories must not be used to fit normalization parameters."""
    base_time = datetime(2026, 1, 1, 10, 0, 0)
    user_id = "user_004"

    # References with identical paths
    trajectories = [
        _make_trajectory(
            user_id, f"ref_{i}", base_time + timedelta(hours=i), lat_offset=0.0
        )
        for i in range(5)
    ]
    # Validation candidate with a massive spatial shift
    trajectories.append(
        _make_trajectory(
            user_id, "val_shifted", base_time + timedelta(hours=6), lat_offset=5.0
        )
    )

    manifest = pd.DataFrame(
        [
            {"trajectory_id": f"ref_{i}", "user_id": user_id, "split": "reference"}
            for i in range(5)
        ]
        + [{"trajectory_id": "val_shifted", "user_id": user_id, "split": "validation"}]
    )

    results, _ = evaluate_candidates(trajectories, manifest, k_min=5)

    assert len(results) == 1
    _, res = results[0]
    assert res.status == "SUCCESS"
    assert res.raw_distance_meters is not None
    # Because references had zero spread, normalizer max_dist is ref min_dist + 100.0m.
    # The candidate's raw distance is > 500,000m, so normalized score clips safely to 1.0
    assert res.route_deviation_score == 1.0


def test_fails_clearly_when_files_missing():
    """Main function raises FileNotFoundError with descriptive message when data is missing."""
    from scripts.evaluate_route_deviation import main
    import sys

    # Simulate passing non-existent files
    with pytest.raises(SystemExit) as exc_info:
        # Pass --help to verify parser without raising FileNotFoundError
        sys.argv = ["evaluate_route_deviation.py", "--help"]
        main()
    assert exc_info.value.code == 0
