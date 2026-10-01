from datetime import datetime, timezone
import math
import numpy as np
import pytest

from ai.route_deviation.distance import (
    EARTH_RADIUS_METERS,
    haversine_distance,
    pairwise_haversine_matrix,
)
from ai.route_deviation.loader import TrajectoryPoint


def _make_pt(lat: float, lon: float, ts_offset_sec: int = 0) -> TrajectoryPoint:
    """Helper to create TrajectoryPoint with default UTC timestamp."""
    base_ts = datetime(2026, 10, 1, 12, 0, 0, tzinfo=timezone.utc)
    ts = datetime.fromtimestamp(base_ts.timestamp() + ts_offset_sec, tz=timezone.utc)
    return TrajectoryPoint(latitude=lat, longitude=lon, timestamp=ts)


def test_earth_radius_constant():
    """Verify that Earth radius constant matches WEGOTCHU specification exactly."""
    assert EARTH_RADIUS_METERS == 6_371_000.0


def test_same_point_returns_zero():
    """Verify that distance between identical coordinates is exactly 0.0."""
    pt = _make_pt(39.9042, 116.4074)
    dist = haversine_distance(pt, pt)
    assert dist == 0.0
    assert isinstance(dist, float)


def test_timestamp_does_not_affect_distance():
    """Verify that points with identical coordinates but different timestamps return 0.0."""
    pt1 = _make_pt(28.6139, 77.2090, ts_offset_sec=0)
    pt2 = _make_pt(28.6139, 77.2090, ts_offset_sec=3600)  # 1 hour later
    assert haversine_distance(pt1, pt2) == 0.0


def test_symmetry():
    """Verify that haversine_distance(A, B) == haversine_distance(B, A)."""
    pt_a = _make_pt(37.7749, -122.4194)  # San Francisco
    pt_b = _make_pt(34.0522, -118.2437)  # Los Angeles
    dist_ab = haversine_distance(pt_a, pt_b)
    dist_ba = haversine_distance(pt_b, pt_a)
    assert dist_ab == pytest.approx(dist_ba, rel=1e-12)


def test_known_geographic_distance():
    """
    Verify distance against a known geographic pair: London to Paris.
    London: 51.5074, -0.1278
    Paris: 48.8566, 2.3522
    Expected great-circle distance with R=6371km is approx 343.556 km (343,556 meters).
    """
    london = _make_pt(51.5074, -0.1278)
    paris = _make_pt(48.8566, 2.3522)
    dist = haversine_distance(london, paris)

    expected_meters = 343_556.0
    assert dist == pytest.approx(
        expected_meters, abs=100.0
    )  # within 100 meters tolerance


def test_equatorial_degree_distance():
    """
    Verify 1 degree of longitude at the equator.
    Expected = 2 * pi * 6,371,000 / 360 approx 111,194.9 meters.
    """
    p1 = _make_pt(0.0, 0.0)
    p2 = _make_pt(0.0, 1.0)
    expected = (2.0 * math.pi * EARTH_RADIUS_METERS) / 360.0
    assert haversine_distance(p1, p2) == pytest.approx(expected, rel=1e-6)


def test_small_geographic_displacement():
    """Verify distance for a very small displacement (~1.1 meter)."""
    p1 = _make_pt(39.900000, 116.400000)
    p2 = _make_pt(39.900010, 116.400000)  # 0.00001 degrees lat approx 1.11 meters
    dist = haversine_distance(p1, p2)
    assert 1.0 < dist < 1.2
    assert dist > 0.0


def test_large_geographic_displacement_antipodes():
    """
    Verify distance between near-antipodal points.
    Expected = pi * R approx 20,015,086.8 meters.
    """
    p1 = _make_pt(0.0, 0.0)
    p2 = _make_pt(0.0, 180.0)
    expected = math.pi * EARTH_RADIUS_METERS
    dist = haversine_distance(p1, p2)
    assert dist == pytest.approx(expected, rel=1e-6)


def test_boundary_coordinates():
    """Verify distance across boundary coordinates (North Pole to South Pole, +/-180 lon)."""
    north_pole = _make_pt(90.0, 0.0)
    south_pole = _make_pt(-90.0, 0.0)
    dist_poles = haversine_distance(north_pole, south_pole)
    assert dist_poles == pytest.approx(math.pi * EARTH_RADIUS_METERS, rel=1e-6)

    # Across anti-meridian
    p_anti_west = _make_pt(0.0, -179.9)
    p_anti_east = _make_pt(0.0, 179.9)
    # The shorter arc across 180 is 0.2 degrees
    expected_short_arc = (0.2 / 360.0) * (2.0 * math.pi * EARTH_RADIUS_METERS)
    dist_anti = haversine_distance(p_anti_west, p_anti_east)
    assert dist_anti == pytest.approx(expected_short_arc, rel=1e-6)


def test_return_type_and_non_negativity():
    """Verify return type is strictly float and non-negative."""
    p1 = _make_pt(10.0, 20.0)
    p2 = _make_pt(15.0, 25.0)
    dist = haversine_distance(p1, p2)
    assert isinstance(dist, float)
    assert dist >= 0.0


def test_pairwise_haversine_matrix():
    """Verify pairwise Haversine distance matrix properties."""
    points = [
        _make_pt(39.9, 116.4),
        _make_pt(39.91, 116.41),
        _make_pt(39.95, 116.45),
    ]

    matrix = pairwise_haversine_matrix(points, points)

    # Correct shape
    assert matrix.shape == (3, 3)

    # Diagonal is zero
    assert np.allclose(np.diag(matrix), 0.0)

    # Matrix symmetry
    assert np.allclose(matrix, matrix.T)

    # Pairwise values match scalar function
    for i in range(3):
        for j in range(3):
            expected = haversine_distance(points[i], points[j])
            assert matrix[i, j] == pytest.approx(expected, rel=1e-7)


def test_pairwise_haversine_matrix_rectangular():
    """Verify pairwise Haversine distance matrix between two unequal sequences."""
    seq_a = [_make_pt(39.0, 116.0), _make_pt(39.1, 116.1)]
    seq_b = [
        _make_pt(40.0, 117.0),
        _make_pt(40.1, 117.1),
        _make_pt(40.2, 117.2),
    ]

    matrix = pairwise_haversine_matrix(seq_a, seq_b)
    assert matrix.shape == (2, 3)

    for i in range(2):
        for j in range(3):
            expected = haversine_distance(seq_a[i], seq_b[j])
            assert matrix[i, j] == pytest.approx(expected, rel=1e-7)


def test_pairwise_haversine_matrix_empty():
    """Verify empty input handling for pairwise matrix."""
    empty_seq = []
    non_empty = [_make_pt(39.0, 116.0)]

    mat1 = pairwise_haversine_matrix(empty_seq, non_empty)
    assert mat1.shape == (0, 1)

    mat2 = pairwise_haversine_matrix(non_empty, empty_seq)
    assert mat2.shape == (1, 0)
