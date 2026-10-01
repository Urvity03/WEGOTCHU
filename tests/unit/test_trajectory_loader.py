from datetime import datetime, timezone
import pandas as pd
import pytest

from ai.route_deviation.loader import (
    Trajectory,
    TrajectoryPoint,
    load_trajectories,
)


def _make_df(rows):
    """Helper to construct preprocessed-style DataFrames."""
    return pd.DataFrame(
        rows,
        columns=[
            "user_id",
            "trajectory_id",
            "timestamp",
            "latitude",
            "longitude",
            "gap_seconds",
            "is_gap_over_threshold",
        ],
    )


def test_trajectory_point_validation():
    """Test TrajectoryPoint bounds and type validation."""
    valid_ts = datetime(2026, 10, 1, 10, 0, 0, tzinfo=timezone.utc)
    pt = TrajectoryPoint(latitude=39.9, longitude=116.4, timestamp=valid_ts)
    assert pt.latitude == 39.9
    assert pt.longitude == 116.4
    assert pt.timestamp == valid_ts

    # Latitude out of bounds
    with pytest.raises(ValueError, match="Latitude"):
        TrajectoryPoint(latitude=91.0, longitude=116.4, timestamp=valid_ts)

    with pytest.raises(ValueError, match="Latitude"):
        TrajectoryPoint(latitude=-90.1, longitude=116.4, timestamp=valid_ts)

    # Longitude out of bounds
    with pytest.raises(ValueError, match="Longitude"):
        TrajectoryPoint(latitude=39.9, longitude=180.1, timestamp=valid_ts)

    with pytest.raises(ValueError, match="Longitude"):
        TrajectoryPoint(latitude=39.9, longitude=-180.1, timestamp=valid_ts)

    # Invalid timestamp type
    with pytest.raises(TypeError, match="datetime"):
        TrajectoryPoint(latitude=39.9, longitude=116.4, timestamp="2026-10-01")


def test_trajectory_validation():
    """Test Trajectory invariants (empty IDs, min 2 points, chronological ordering)."""
    t1 = datetime(2026, 10, 1, 10, 0, 0)
    t2 = datetime(2026, 10, 1, 10, 1, 0)
    p1 = TrajectoryPoint(39.0, 116.0, t1)
    p2 = TrajectoryPoint(39.1, 116.1, t2)

    # Valid trajectory
    traj = Trajectory(user_id="u1", trajectory_id="t1", points=(p1, p2))
    assert len(traj) == 2
    assert traj[0] == p1
    assert traj[1] == p2

    # Empty user_id
    with pytest.raises(ValueError, match="user_id"):
        Trajectory(user_id="", trajectory_id="t1", points=(p1, p2))

    # Empty trajectory_id
    with pytest.raises(ValueError, match="trajectory_id"):
        Trajectory(user_id="u1", trajectory_id="", points=(p1, p2))

    # Fewer than 2 points
    with pytest.raises(ValueError, match="at least 2 points"):
        Trajectory(user_id="u1", trajectory_id="t1", points=(p1,))

    # Out of chronological order
    with pytest.raises(ValueError, match="chronologically"):
        Trajectory(user_id="u1", trajectory_id="t1", points=(p2, p1))


def test_normal_trajectory_with_no_gaps():
    """Test loading a normal trajectory with contiguous observations."""
    df = _make_df(
        [
            ["geolife_000", "trip_1", "2008-10-23 02:53:04", 39.9, 116.4, 0.0, False],
            ["geolife_000", "trip_1", "2008-10-23 02:53:09", 39.91, 116.41, 5.0, False],
            ["geolife_000", "trip_1", "2008-10-23 02:53:14", 39.92, 116.42, 5.0, False],
        ]
    )

    trajectories = load_trajectories(df)
    assert len(trajectories) == 1
    traj = trajectories[0]
    assert traj.user_id == "geolife_000"
    assert traj.trajectory_id == "trip_1"
    assert len(traj) == 3
    assert traj[0].latitude == 39.9
    assert traj[2].latitude == 39.92


def test_chronological_sorting():
    """Test that input rows out of chronological order are sorted ascending."""
    df = _make_df(
        [
            [
                "geolife_001",
                "trip_unordered",
                "2008-10-23 02:53:14",
                39.92,
                116.42,
                5.0,
                False,
            ],
            [
                "geolife_001",
                "trip_unordered",
                "2008-10-23 02:53:04",
                39.90,
                116.40,
                0.0,
                False,
            ],
            [
                "geolife_001",
                "trip_unordered",
                "2008-10-23 02:53:09",
                39.91,
                116.41,
                5.0,
                False,
            ],
        ]
    )

    trajectories = load_trajectories(df)
    assert len(trajectories) == 1
    traj = trajectories[0]
    assert [p.latitude for p in traj] == [39.90, 39.91, 39.92]
    assert traj[0].timestamp < traj[1].timestamp < traj[2].timestamp


def test_segmentation_when_gap_over_threshold_flag_is_true():
    """Test physical splitting when is_gap_over_threshold is True."""
    df = _make_df(
        [
            ["geolife_002", "trip_gap", "2008-10-23 02:53:00", 39.0, 116.0, 0.0, False],
            ["geolife_002", "trip_gap", "2008-10-23 02:53:05", 39.1, 116.1, 5.0, False],
            [
                "geolife_002",
                "trip_gap",
                "2008-10-23 03:53:00",
                40.0,
                117.0,
                3595.0,
                True,
            ],
            ["geolife_002", "trip_gap", "2008-10-23 03:53:05", 40.1, 117.1, 5.0, False],
        ]
    )

    trajectories = load_trajectories(df)
    assert len(trajectories) == 2

    # Deterministic segment IDs
    assert trajectories[0].trajectory_id == "trip_gap_seg0"
    assert trajectories[1].trajectory_id == "trip_gap_seg1"

    # User ID preserved
    assert trajectories[0].user_id == "geolife_002"
    assert trajectories[1].user_id == "geolife_002"

    # Segment points
    assert len(trajectories[0]) == 2
    assert len(trajectories[1]) == 2
    assert trajectories[0][1].latitude == 39.1
    assert trajectories[1][0].latitude == 40.0


def test_segmentation_when_gap_seconds_exceeds_threshold():
    """Test splitting when gap_threshold_seconds parameter is triggered."""
    df = _make_df(
        [
            ["geolife_003", "trip_dt", "2008-10-23 02:00:00", 39.0, 116.0, 0.0, False],
            ["geolife_003", "trip_dt", "2008-10-23 02:00:10", 39.1, 116.1, 10.0, False],
            [
                "geolife_003",
                "trip_dt",
                "2008-10-23 02:05:00",
                40.0,
                117.0,
                290.0,
                False,
            ],  # 290s > 60s
            ["geolife_003", "trip_dt", "2008-10-23 02:05:10", 40.1, 117.1, 10.0, False],
        ]
    )

    trajectories = load_trajectories(df, gap_threshold_seconds=60.0)
    assert len(trajectories) == 2
    assert trajectories[0].trajectory_id == "trip_dt_seg0"
    assert trajectories[1].trajectory_id == "trip_dt_seg1"


def test_preserves_irregular_timestamps_without_interpolation():
    """Test that timestamps with non-uniform intervals are preserved as-is without interpolation."""
    irregular_times = [
        "2008-10-23 02:00:00",
        "2008-10-23 02:00:03",  # +3s
        "2008-10-23 02:00:17",  # +14s
        "2008-10-23 02:00:41",  # +24s
    ]
    df = _make_df(
        [
            [
                "geolife_004",
                "trip_irreg",
                t,
                39.0 + i * 0.01,
                116.0 + i * 0.01,
                0.0,
                False,
            ]
            for i, t in enumerate(irregular_times)
        ]
    )

    trajectories = load_trajectories(df)
    assert len(trajectories) == 1
    traj = trajectories[0]
    assert len(traj) == 4

    # Observations must match exactly, no synthetic points inserted
    expected_dts = [pd.to_datetime(t).to_pydatetime() for t in irregular_times]
    actual_dts = [p.timestamp for p in traj]
    assert actual_dts == expected_dts

    # Original coordinates must be exact
    assert traj[1].latitude == pytest.approx(39.01)
    assert traj[2].latitude == pytest.approx(39.02)


def test_drops_segments_with_fewer_than_two_points():
    """Test that split fragments with < 2 valid observations are safely dropped."""
    df = _make_df(
        [
            # Segment 0: 2 points -> kept
            [
                "geolife_005",
                "trip_singleton",
                "2008-10-23 02:00:00",
                39.0,
                116.0,
                0.0,
                False,
            ],
            [
                "geolife_005",
                "trip_singleton",
                "2008-10-23 02:00:10",
                39.1,
                116.1,
                10.0,
                False,
            ],
            # Segment 1: 1 point only -> dropped!
            [
                "geolife_005",
                "trip_singleton",
                "2008-10-23 03:00:00",
                39.5,
                116.5,
                3590.0,
                True,
            ],
            # Segment 2: 2 points -> kept
            [
                "geolife_005",
                "trip_singleton",
                "2008-10-23 04:00:00",
                40.0,
                117.0,
                3600.0,
                True,
            ],
            [
                "geolife_005",
                "trip_singleton",
                "2008-10-23 04:00:10",
                40.1,
                117.1,
                10.0,
                False,
            ],
        ]
    )

    trajectories = load_trajectories(df)
    assert len(trajectories) == 2
    assert trajectories[0].trajectory_id == "trip_singleton_seg0"
    assert trajectories[1].trajectory_id == "trip_singleton_seg1"
    assert len(trajectories[0]) == 2
    assert len(trajectories[1]) == 2


def test_entire_trajectory_with_only_one_point_returns_empty():
    """Test that an input trajectory with only 1 observation yields no valid trajectory."""
    df = _make_df(
        [
            [
                "geolife_006",
                "trip_single",
                "2008-10-23 02:00:00",
                39.0,
                116.0,
                0.0,
                False,
            ],
        ]
    )

    trajectories = load_trajectories(df)
    assert len(trajectories) == 0


def test_filters_invalid_coordinates_and_timestamps():
    """Test filtering of NaN/out-of-range coordinates and invalid timestamps."""
    df = _make_df(
        [
            [
                "geolife_007",
                "trip_invalid",
                "2008-10-23 02:00:00",
                39.0,
                116.0,
                0.0,
                False,
            ],
            [
                "geolife_007",
                "trip_invalid",
                "2008-10-23 02:00:05",
                95.0,
                116.0,
                5.0,
                False,
            ],  # lat > 90
            [
                "geolife_007",
                "trip_invalid",
                "not-a-timestamp",
                39.1,
                116.1,
                5.0,
                False,
            ],  # invalid time
            [
                "geolife_007",
                "trip_invalid",
                "2008-10-23 02:00:15",
                39.2,
                -190.0,
                5.0,
                False,
            ],  # lon < -180
            [
                "geolife_007",
                "trip_invalid",
                "2008-10-23 02:00:20",
                39.3,
                116.3,
                5.0,
                False,
            ],
        ]
    )

    trajectories = load_trajectories(df)
    assert len(trajectories) == 1
    traj = trajectories[0]
    assert len(traj) == 2
    assert [p.latitude for p in traj] == [39.0, 39.3]


def test_load_from_csv_file(tmp_path):
    """Test loading directly from a CSV file on disk."""
    csv_file = tmp_path / "preprocessed.csv"
    df = _make_df(
        [
            ["geolife_008", "csv_trip", "2008-10-23 02:00:00", 39.0, 116.0, 0.0, False],
            [
                "geolife_008",
                "csv_trip",
                "2008-10-23 02:00:10",
                39.1,
                116.1,
                10.0,
                False,
            ],
        ]
    )
    df.to_csv(csv_file, index=False)

    trajectories = load_trajectories(csv_file)
    assert len(trajectories) == 1
    assert trajectories[0].user_id == "geolife_008"
    assert trajectories[0].trajectory_id == "csv_trip"


def test_multiple_users_and_trajectories():
    """Test that multiple users and trajectories in the same dataset remain cleanly separated."""
    df = _make_df(
        [
            ["geolife_001", "u1_t1", "2008-10-23 02:00:00", 39.0, 116.0, 0.0, False],
            ["geolife_001", "u1_t1", "2008-10-23 02:00:10", 39.1, 116.1, 10.0, False],
            ["geolife_002", "u2_t1", "2008-10-23 03:00:00", 40.0, 117.0, 0.0, False],
            ["geolife_002", "u2_t1", "2008-10-23 03:00:10", 40.1, 117.1, 10.0, False],
        ]
    )

    trajectories = load_trajectories(df)
    assert len(trajectories) == 2
    assert trajectories[0].user_id == "geolife_001"
    assert trajectories[0].trajectory_id == "u1_t1"
    assert trajectories[1].user_id == "geolife_002"
    assert trajectories[1].trajectory_id == "u2_t1"
