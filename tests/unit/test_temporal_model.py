"""Unit tests for temporal sequence window and persistence modeling."""

from datetime import datetime, timedelta, timezone

from ai.temporal_model import (
    TemporalObservation,
    TemporalPersistenceEstimator,
)


def test_temporal_window_transient_spike():
    t0 = datetime(2026, 10, 28, 10, 0, 0, tzinfo=timezone.utc)
    estimator = TemporalPersistenceEstimator(
        min_duration_seconds=30.0, min_sustained_seconds=15.0
    )

    # 45-second window with a single 5-second anomaly spike
    obs = [
        TemporalObservation(timestamp=t0, score=0.1, is_anomalous=False),
        TemporalObservation(
            timestamp=t0 + timedelta(seconds=10), score=0.1, is_anomalous=False
        ),
        TemporalObservation(
            timestamp=t0 + timedelta(seconds=20), score=0.9, is_anomalous=True
        ),
        TemporalObservation(
            timestamp=t0 + timedelta(seconds=25), score=0.1, is_anomalous=False
        ),
        TemporalObservation(
            timestamp=t0 + timedelta(seconds=45), score=0.1, is_anomalous=False
        ),
    ]

    res = estimator.evaluate_persistence(obs)
    assert res.window_duration_seconds == 45.0
    assert res.is_transient is True
    assert res.is_sustained is False
    assert res.persistence_ratio < 0.25


def test_temporal_window_sustained_trend():
    t0 = datetime(2026, 10, 28, 10, 0, 0, tzinfo=timezone.utc)
    estimator = TemporalPersistenceEstimator(
        min_duration_seconds=30.0,
        min_sustained_seconds=20.0,
        min_persistence_ratio=0.60,
    )

    # 60-second window where anomalies persist from t=15 to t=55 (40 seconds continuous)
    obs = [
        TemporalObservation(timestamp=t0, score=0.1, is_anomalous=False),
        TemporalObservation(
            timestamp=t0 + timedelta(seconds=15), score=0.8, is_anomalous=True
        ),
        TemporalObservation(
            timestamp=t0 + timedelta(seconds=30), score=0.85, is_anomalous=True
        ),
        TemporalObservation(
            timestamp=t0 + timedelta(seconds=45), score=0.82, is_anomalous=True
        ),
        TemporalObservation(
            timestamp=t0 + timedelta(seconds=55), score=0.1, is_anomalous=False
        ),
        TemporalObservation(
            timestamp=t0 + timedelta(seconds=60), score=0.1, is_anomalous=False
        ),
    ]

    res = estimator.evaluate_persistence(obs)
    assert res.window_duration_seconds == 60.0
    assert res.is_sustained is True
    assert res.is_transient is False
    assert res.persistence_ratio >= 0.60


def test_temporal_window_short_duration_not_sustained():
    t0 = datetime(2026, 10, 28, 10, 0, 0, tzinfo=timezone.utc)
    estimator = TemporalPersistenceEstimator(min_duration_seconds=30.0)

    # 10-second window (below min_duration_seconds)
    obs = [
        TemporalObservation(timestamp=t0, score=0.9, is_anomalous=True),
        TemporalObservation(
            timestamp=t0 + timedelta(seconds=10), score=0.9, is_anomalous=True
        ),
    ]

    res = estimator.evaluate_persistence(obs)
    assert res.is_sustained is False
    assert res.is_transient is True
    assert res.persistence_ratio == 0.0
