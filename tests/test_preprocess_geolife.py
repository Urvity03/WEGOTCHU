import pandas as pd
import pytest

from scripts.preprocess_geolife import parse_trajectory


def write_plt(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    header = ["header"] * 6
    path.write_text(
        "\n".join(header + rows) + "\n",
        encoding="utf-8",
    )


def make_row(latitude, longitude, altitude, date, time):
    return f"{latitude},{longitude},0,{altitude},0,{date},{time}"


def test_parses_fields_and_extracts_user_id(tmp_path):
    dataset_root = tmp_path / "Data"
    trajectory_path = dataset_root / "000" / "Trajectory" / "trip001.plt"
    write_plt(
        trajectory_path,
        [
            make_row(39.0, 116.0, 100, "2008-10-23", "02:53:04"),
            make_row(39.1, 116.1, -777, "2008-10-23", "02:53:09"),
        ],
    )

    result, summary = parse_trajectory(
        trajectory_path,
        dataset_root,
        gap_threshold_seconds=60,
    )

    assert result["user_id"].unique().tolist() == ["geolife_000"]
    assert result["trajectory_id"].unique().tolist() == ["geolife_000/trip001"]
    assert result.loc[0, "altitude_meters"] == pytest.approx(30.48)
    assert pd.isna(result.loc[1, "altitude_meters"])
    assert summary["kept_rows"] == 2


def test_drops_invalid_coordinates(tmp_path):
    dataset_root = tmp_path / "Data"
    trajectory_path = dataset_root / "001" / "Trajectory" / "trip002.plt"
    write_plt(
        trajectory_path,
        [
            make_row(91, 116.0, 10, "2008-10-23", "02:53:04"),
            make_row(39.0, 116.0, 10, "2008-10-23", "02:53:09"),
        ],
    )

    result, summary = parse_trajectory(
        trajectory_path,
        dataset_root,
        gap_threshold_seconds=60,
    )

    assert len(result) == 1
    assert summary["invalid_coordinate_rows"] == 1


def test_calculates_and_flags_large_gap(tmp_path):
    dataset_root = tmp_path / "Data"
    trajectory_path = dataset_root / "002" / "Trajectory" / "trip003.plt"
    write_plt(
        trajectory_path,
        [
            make_row(39.0, 116.0, 10, "2008-10-23", "02:53:04"),
            make_row(39.0, 116.1, 10, "2008-10-23", "02:55:04"),
        ],
    )

    result, summary = parse_trajectory(
        trajectory_path,
        dataset_root,
        gap_threshold_seconds=60,
    )

    assert result["gap_seconds"].tolist() == [0.0, 120.0]
    assert result["is_gap_over_threshold"].tolist() == [False, True]
    assert summary["flagged_gaps"] == 1


def test_drops_observation_with_invalid_timestamp(tmp_path):
    dataset_root = tmp_path / "Data"
    trajectory_path = dataset_root / "003" / "Trajectory" / "trip004.plt"
    write_plt(
        trajectory_path,
        [
            make_row(39.0, 116.0, 10, "not-a-date", "not-a-time"),
            make_row(39.1, 116.1, 10, "2008-10-23", "02:53:09"),
        ],
    )

    result, summary = parse_trajectory(
        trajectory_path,
        dataset_root,
        gap_threshold_seconds=60,
    )

    assert len(result) == 1
    assert summary["invalid_timestamp_rows"] == 1


def test_reports_empty_trajectory_file(tmp_path):
    dataset_root = tmp_path / "Data"
    trajectory_path = dataset_root / "004" / "Trajectory" / "empty.plt"
    write_plt(trajectory_path, [])

    with pytest.raises(ValueError, match="no observation rows"):
        parse_trajectory(
            trajectory_path,
            dataset_root,
            gap_threshold_seconds=60,
        )
