"""Unit tests for multimodal late-fusion engine."""

from ai.multimodal_fusion import (
    ModalitySignal,
    ModalityStatus,
    MultimodalFusionEngine,
)


def test_fusion_all_modalities_available_normal():
    engine = MultimodalFusionEngine()
    signals = [
        ModalitySignal(
            "route_deviation",
            score=0.15,
            status=ModalityStatus.AVAILABLE,
            confidence=0.85,
        ),
        ModalitySignal(
            "kinematic_motion",
            score=0.10,
            status=ModalityStatus.AVAILABLE,
            confidence=0.80,
        ),
        ModalitySignal(
            "acoustic_distress",
            score=0.05,
            status=ModalityStatus.AVAILABLE,
            confidence=0.75,
        ),
    ]

    fused = engine.fuse(signals)
    assert fused.fused_score is not None
    assert fused.fused_score < 0.20
    assert fused.overall_confidence > 0.70
    assert not fused.co_occurring_anomaly
    assert len(fused.active_signals) == 0
    assert len(fused.missing_modalities) == 0


def test_fusion_missing_modalities_preserved():
    engine = MultimodalFusionEngine()
    signals = [
        ModalitySignal(
            "route_deviation",
            score=0.70,
            status=ModalityStatus.AVAILABLE,
            confidence=0.85,
        ),
        ModalitySignal(
            "kinematic_motion",
            score=None,
            status=ModalityStatus.INSUFFICIENT_DATA,
            confidence=0.0,
        ),
        ModalitySignal(
            "acoustic_distress",
            score=None,
            status=ModalityStatus.MISSING,
            confidence=0.0,
        ),
    ]

    fused = engine.fuse(signals)
    assert (
        fused.fused_score == 0.70
    )  # Only route available, takes 100% of available weight
    assert "route_deviation" in fused.active_signals
    assert "kinematic_motion" in fused.missing_modalities
    assert "acoustic_distress" in fused.missing_modalities
    # Confidence is appropriately penalized for missing modalities
    assert fused.overall_confidence < 0.85
    assert not fused.co_occurring_anomaly


def test_fusion_co_occurring_anomalies_flagged():
    engine = MultimodalFusionEngine()
    signals = [
        ModalitySignal(
            "route_deviation",
            score=0.85,
            status=ModalityStatus.AVAILABLE,
            confidence=0.90,
        ),
        ModalitySignal(
            "kinematic_motion",
            score=0.75,
            status=ModalityStatus.AVAILABLE,
            confidence=0.85,
        ),
    ]

    fused = engine.fuse(signals)
    assert fused.co_occurring_anomaly is True
    assert set(fused.active_signals) == {"route_deviation", "kinematic_motion"}


def test_fusion_all_modalities_missing():
    engine = MultimodalFusionEngine()
    signals = [
        ModalitySignal("route_deviation", score=None, status=ModalityStatus.MISSING),
        ModalitySignal("kinematic_motion", score=None, status=ModalityStatus.FAILED),
    ]

    fused = engine.fuse(signals)
    assert fused.fused_score is None
    assert fused.overall_confidence == 0.20
    assert len(fused.active_signals) == 0
    assert set(fused.missing_modalities) == {"route_deviation", "kinematic_motion"}
