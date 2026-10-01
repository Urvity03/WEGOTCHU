import pandas as pd

from scripts.create_geolife_split_manifest import (
    assign_user_splits,
    summarize_trajectories,
)


def make_trajectory_rows(user_id, count):
    rows = []

    for index in range(count):
        start = pd.Timestamp("2026-01-01") + pd.Timedelta(days=index)

        rows.append(
            {
                "user_id": user_id,
                "trajectory_id": f"{user_id}/trajectory_{index}",
                "start_timestamp": start,
                "end_timestamp": start + pd.Timedelta(minutes=10),
                "observation_count": 100,
                "max_gap_seconds": 5.0,
                "flagged_gap_count": 0,
            }
        )

    return rows


def test_eligible_user_gets_chronological_60_20_20_split():
    rows = make_trajectory_rows("geolife_000", 10)
    frame = pd.DataFrame(rows)

    manifest = assign_user_splits(
        frame,
        minimum_history=5,
    )

    counts = manifest["split"].value_counts().to_dict()

    assert counts["reference"] == 6
    assert counts["validation"] == 2
    assert counts["test"] == 2
    assert manifest["personalization_eligible"].all()
    assert not manifest["is_cold_start"].any()


def test_reference_validation_test_are_chronological():
    rows = make_trajectory_rows("geolife_001", 10)
    frame = pd.DataFrame(rows)

    manifest = assign_user_splits(
        frame,
        minimum_history=5,
    )

    reference = manifest[manifest["split"] == "reference"]
    validation = manifest[manifest["split"] == "validation"]
    test = manifest[manifest["split"] == "test"]

    assert reference["end_timestamp"].max() < (validation["start_timestamp"].min())
    assert validation["end_timestamp"].max() < test["start_timestamp"].min()


def test_user_below_minimum_history_is_cold_start():
    rows = make_trajectory_rows("geolife_002", 4)
    frame = pd.DataFrame(rows)

    manifest = assign_user_splits(
        frame,
        minimum_history=5,
    )

    assert set(manifest["split"]) == {"cold_start"}
    assert not manifest["personalization_eligible"].any()
    assert manifest["is_cold_start"].all()


def test_user_with_exact_minimum_history_is_eligible():
    rows = make_trajectory_rows("geolife_003", 5)
    frame = pd.DataFrame(rows)

    manifest = assign_user_splits(
        frame,
        minimum_history=5,
    )

    counts = manifest["split"].value_counts().to_dict()

    assert counts["reference"] == 3
    assert counts["validation"] == 1
    assert counts["test"] == 1
    assert manifest["personalization_eligible"].all()


def test_summarize_trajectories_reads_input_csv(tmp_path):
    input_path = tmp_path / "trajectories.csv"

    frame = pd.DataFrame(
        [
            {
                "user_id": "geolife_004",
                "trajectory_id": "geolife_004/trip_1",
                "timestamp": "2026-01-01 10:00:00",
                "gap_seconds": 0.0,
                "is_gap_over_threshold": False,
            },
            {
                "user_id": "geolife_004",
                "trajectory_id": "geolife_004/trip_1",
                "timestamp": "2026-01-01 10:02:00",
                "gap_seconds": 120.0,
                "is_gap_over_threshold": True,
            },
        ]
    )
    frame.to_csv(input_path, index=False)

    summary = summarize_trajectories(
        input_path,
        chunksize=1,
    )

    assert len(summary) == 1
    assert summary.loc[0, "user_id"] == "geolife_004"
    assert summary.loc[0, "observation_count"] == 2
    assert summary.loc[0, "max_gap_seconds"] == 120.0
    assert summary.loc[0, "flagged_gap_count"] == 1
