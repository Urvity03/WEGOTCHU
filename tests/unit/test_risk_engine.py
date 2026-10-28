"""
Unit tests for the WEGOTCHU Risk Estimation Engine.

Policy sources:
  - docs/safety/ai-safety-policy.md
  - docs/architecture/ai-architecture.md §2 (risk levels) and §3 (output schema, signal identifiers)

Contract 4 schema: docs/architecture/data-flow.md lines 126-151.

Signal identifier authority:
  - AUTHORITATIVE: ai-architecture.md §3 Validation Constraints (line 126):
      "unusual_motion" is the documented identifier for motion anomalies.
  - NOTE: data-flow.md line 139 illustrative JSON uses "abnormal_motion", but that example
    also contains a mutually inconsistent risk_level/recommended_action pair (HIGH + USER_CHECK),
    confirming it is a draft illustration rather than a normative definition.

Agreed initial escalation rules (v0.1 baseline):
  - Both signals validated normal:                  NORMAL / NONE
  - One validated signal anomalous:                 UNUSUAL / MONITOR
  - Both validated signals anomalous:               ELEVATED / USER_CHECK
  - Statistical anomaly scores alone:               NEVER trigger HIGH or EMERGENCY
  - HIGH / PRE_ALERT:                               unacknowledged ELEVATED or acoustic distress
                                                    (Policy Engine responsibility, not RiskEngine)
  - EMERGENCY / DISPATCH_EMERGENCY:                 countdown expired, manual SOS, confirmed crisis
                                                    (Policy Engine responsibility, not RiskEngine)

Partial-availability policy (one signal available, other missing/cold-start):
  - Available signal validated normal:              NORMAL with reduced confidence (0.65)
  - Available signal anomalous:                     UNUSUAL / MONITOR (single-anomaly rule)
  - This is DISTINCT from all-signals-missing.

All-signals-missing policy:
  - Both signals unavailable:                       UNUSUAL / MONITOR, confidence = 0.20
  - Rationale: absence of evidence is not evidence of safety (Safety Principle 5 recall bias),
    but silent UNUSUAL (no user interruption) also respects Principle 4 (false alarm mitigation).

Invariants:
  - Unavailable score never converted to 0.0:       None must remain None in risk_vector
  - calibration scores are None when no valid score exists
"""

from ai.anomaly_detection.motion import MotionAnomalyResult, MotionFeatures
from ai.risk_engine.engine import (
    SIGNAL_ROUTE_DEVIATION,
    SIGNAL_UNUSUAL_MOTION,
    RiskEngine,
)
from ai.risk_engine.models import (
    CONTRACT_VERSION,
    RecommendedAction,
    RiskLevel,
    SCHEMA_URI,
)
from ai.route_deviation.scoring import RouteDeviationResult

# Contract 4 mandatory top-level keys from docs/architecture/data-flow.md
CONTRACT4_REQUIRED_KEYS = {
    "$schema",
    "version",
    "user_id",
    "timestamp",
    "risk_level",
    "confidence",
    "signals",
    "location_status",
    "recommended_action",
    "risk_vector",
}

# Documented risk_vector field names from Contract 4
RISK_VECTOR_KEYS = {
    "kinematic_anomaly",
    "route_anomaly",
    "acoustic_anomaly",
    "temporal_persistence",
}

# Authoritative signal identifiers from docs/architecture/ai-architecture.md §3 (line 126).
# "abnormal_motion" from the data-flow.md illustrative JSON is NOT included here because
# that JSON example is a draft illustration (it contains internally inconsistent fields).
VALID_SIGNAL_IDENTIFIERS = {
    "route_deviation",
    "unusual_motion",
    "acoustic_distress",
    "prolonged_immobility",
    "manual_sos",
}

# Documented risk levels from ai-architecture.md
VALID_RISK_LEVELS = {"NORMAL", "UNUSUAL", "ELEVATED", "HIGH", "EMERGENCY"}

# Documented recommended actions from ai-architecture.md
VALID_RECOMMENDED_ACTIONS = {
    "NONE",
    "MONITOR",
    "USER_CHECK",
    "PRE_ALERT",
    "DISPATCH_EMERGENCY",
}


def _make_route_result(
    score: float | None = 0.15,
    distance_meters: float | None = 45.0,
    status: str = "SUCCESS",
) -> RouteDeviationResult:
    """Helper: mock a RouteDeviationResult with SUCCESS status."""
    return RouteDeviationResult(
        user_id="usr_test_001",
        trajectory_id="usr_test_001/trip_1",
        status=status,
        raw_distance_meters=distance_meters,
        route_deviation_score=score,
        reference_trajectory_count=10,
        closest_reference_id="usr_test_001/ref_0",
    )


def _make_motion_result(
    score: float | None = 0.10,
    confidence: float = 0.90,
    motion_state: str = "still",
    status: str = "SUCCESS",
) -> MotionAnomalyResult:
    """Helper: mock a MotionAnomalyResult with SUCCESS status."""
    feats = MotionFeatures(
        sample_count=15,
        duration_seconds=0.3,
        mean_accel_magnitude=9.8,
        std_accel_magnitude=0.1,
        max_accel_magnitude=9.9,
        mean_dynamic_accel=0.05,
        max_dynamic_accel=0.1,
        mean_jerk=1.0,
        max_jerk=2.0,
        mean_gyro_magnitude=0.01,
        max_gyro_magnitude=0.02,
    )
    return MotionAnomalyResult(
        status=status,
        motion_anomaly_score=score,
        confidence=confidence,
        motion_state=motion_state,
        features=feats,
        metadata={},
    )


# ---------------------------------------------------------------------------
# Section 1 — Escalation policy verification
# ---------------------------------------------------------------------------


def test_normal_signals_yield_normal_risk():
    """Both route and motion within baseline bounds -> NORMAL (NONE)."""
    engine = RiskEngine()
    route_res = _make_route_result(score=0.12, distance_meters=30.0)
    motion_res = _make_motion_result(score=0.08, motion_state="walking")

    a = engine.evaluate(
        user_id="usr_test_001",
        route_result=route_res,
        motion_result=motion_res,
        speed_mps=1.3,
    )

    assert a.risk_level == RiskLevel.NORMAL
    assert a.recommended_action == RecommendedAction.NONE
    assert len(a.signals) == 0
    assert a.risk_vector.route_anomaly == 0.12
    assert a.risk_vector.kinematic_anomaly == 0.08
    assert a.confidence >= 0.80


def test_single_route_anomaly_yields_unusual_not_elevated():
    """
    Single route anomaly (motion normal) -> UNUSUAL / MONITOR.
    Must NOT escalate to ELEVATED or higher under the initial agreed policy.
    """
    engine = RiskEngine()
    route_res = _make_route_result(score=0.78, distance_meters=250.0)
    motion_res = _make_motion_result(score=0.15, motion_state="walking")

    a = engine.evaluate(
        user_id="usr_test_001",
        route_result=route_res,
        motion_result=motion_res,
    )

    assert a.risk_level == RiskLevel.UNUSUAL
    assert a.recommended_action == RecommendedAction.MONITOR
    assert a.signals == (SIGNAL_ROUTE_DEVIATION,)
    assert a.risk_vector.route_anomaly == 0.78
    assert a.risk_vector.kinematic_anomaly == 0.15


def test_single_motion_anomaly_yields_unusual_not_elevated():
    """
    Single motion anomaly (route normal) -> UNUSUAL / MONITOR.
    Must NOT escalate to ELEVATED or higher under the initial agreed policy.
    High motion score alone is NOT sufficient evidence for USER_CHECK.
    """
    engine = RiskEngine()
    route_res = _make_route_result(score=0.20, distance_meters=40.0)
    motion_res = _make_motion_result(score=0.82, motion_state="abrupt_motion")

    a = engine.evaluate(
        user_id="usr_test_001",
        route_result=route_res,
        motion_result=motion_res,
    )

    assert a.risk_level == RiskLevel.UNUSUAL
    assert a.recommended_action == RecommendedAction.MONITOR
    assert a.signals == (SIGNAL_UNUSUAL_MOTION,)
    assert a.risk_vector.kinematic_anomaly == 0.82


def test_co_occurring_anomalies_yield_elevated_user_check():
    """
    Co-occurring route + motion anomalies -> ELEVATED / USER_CHECK.
    This is the maximum level reachable from statistical anomaly scores alone.
    """
    engine = RiskEngine()
    route_res = _make_route_result(score=0.85, distance_meters=350.0)
    motion_res = _make_motion_result(score=0.79, motion_state="abrupt_motion")

    a = engine.evaluate(
        user_id="usr_test_001",
        route_result=route_res,
        motion_result=motion_res,
    )

    assert a.risk_level == RiskLevel.ELEVATED
    assert a.recommended_action == RecommendedAction.USER_CHECK
    assert set(a.signals) == {SIGNAL_ROUTE_DEVIATION, SIGNAL_UNUSUAL_MOTION}
    assert a.risk_vector.route_anomaly == 0.85
    assert a.risk_vector.kinematic_anomaly == 0.79
    assert 0.70 <= a.confidence <= 1.0


def test_statistical_anomalies_never_trigger_high_or_emergency():
    """
    Regardless of how high the anomaly scores are, statistical anomaly signals
    alone must NEVER produce HIGH or EMERGENCY under the initial agreed policy.
    HIGH requires multi-signal distress (acoustic) or unacknowledged ELEVATED.
    EMERGENCY requires countdown expiry, manual SOS, or critical confirmed event.
    """
    engine = RiskEngine()
    # Use maximum possible statistical anomaly scores in both modalities
    route_res = _make_route_result(score=0.99, distance_meters=999.0)
    motion_res = _make_motion_result(score=0.99, motion_state="abrupt_motion")

    a = engine.evaluate(
        user_id="usr_test_001",
        route_result=route_res,
        motion_result=motion_res,
    )

    assert a.risk_level not in (RiskLevel.HIGH, RiskLevel.EMERGENCY), (
        f"Statistical anomalies alone must not trigger {a.risk_level.value}. "
        "Verify engine escalation rules."
    )
    assert a.recommended_action not in (
        RecommendedAction.PRE_ALERT,
        RecommendedAction.DISPATCH_EMERGENCY,
    )


# ---------------------------------------------------------------------------
# Section 2 — Cold start and missing / invalid data
# ---------------------------------------------------------------------------


def test_cold_start_route_preserves_none_score():
    """
    Cold start (INSUFFICIENT_HISTORY) preserves route_anomaly=None.
    Normal motion -> NORMAL (NONE). None must NOT be converted to 0.0.
    """
    engine = RiskEngine()
    route_res = RouteDeviationResult(
        user_id="usr_new_002",
        trajectory_id="usr_new_002/trip_0",
        status="INSUFFICIENT_HISTORY",
        raw_distance_meters=None,
        route_deviation_score=None,
        reference_trajectory_count=2,
        closest_reference_id=None,
    )
    motion_res = _make_motion_result(score=0.10, motion_state="still")

    a = engine.evaluate(
        user_id="usr_new_002",
        route_result=route_res,
        motion_result=motion_res,
    )

    assert a.risk_level == RiskLevel.NORMAL
    assert a.recommended_action == RecommendedAction.NONE
    # None must remain None, not be converted to 0.0
    assert a.risk_vector.route_anomaly is None
    assert a.risk_vector.kinematic_anomaly == 0.10
    assert a.telemetry_summary.corridor_deviation_meters is None


def test_cold_start_route_with_motion_anomaly_yields_unusual():
    """
    Cold start route + motion anomaly -> UNUSUAL / MONITOR.
    Motion anomaly is the only available signal; escalation based on it alone.
    """
    engine = RiskEngine()
    route_res = RouteDeviationResult(
        user_id="usr_new_002",
        trajectory_id="usr_new_002/trip_0",
        status="INSUFFICIENT_HISTORY",
        raw_distance_meters=None,
        route_deviation_score=None,
        reference_trajectory_count=2,
        closest_reference_id=None,
    )
    motion_res = _make_motion_result(score=0.75, motion_state="abrupt_motion")

    a = engine.evaluate(
        user_id="usr_new_002",
        route_result=route_res,
        motion_result=motion_res,
    )

    assert a.risk_level == RiskLevel.UNUSUAL
    assert a.recommended_action == RecommendedAction.MONITOR
    assert a.risk_vector.route_anomaly is None
    assert a.risk_vector.kinematic_anomaly == 0.75


def test_route_none_no_result_yields_unavailable_location():
    """
    route_result=None -> location_status must be 'unavailable'.
    Should not raise; must handle gracefully.
    """
    engine = RiskEngine()
    motion_res = _make_motion_result(score=0.10, motion_state="still")

    a = engine.evaluate(
        user_id="usr_test_001",
        route_result=None,
        motion_result=motion_res,
    )

    assert a.location_status == "unavailable"
    assert a.risk_vector.route_anomaly is None


def test_invalid_route_result_score_preserved_as_none():
    """
    A RouteDeviationResult with non-SUCCESS status and None score must have
    route_anomaly=None in risk_vector (never substituted with 0.0), and must
    escalate to UNUSUAL / MONITOR rather than manufacturing a NORMAL assessment.
    """
    engine = RiskEngine()
    route_res = _make_route_result(
        score=None,
        distance_meters=None,
        status="COMPUTATION_ERROR",
    )
    motion_res = _make_motion_result(score=0.10)

    a = engine.evaluate(
        user_id="usr_test_001",
        route_result=route_res,
        motion_result=motion_res,
    )

    assert (
        a.risk_vector.route_anomaly is None
    ), "Non-SUCCESS route result must preserve None score, not convert to 0.0"
    assert a.risk_level == RiskLevel.UNUSUAL, "Failing detector must not produce NORMAL"
    assert a.recommended_action == RecommendedAction.MONITOR
    assert a.confidence <= 0.40


def test_invalid_motion_result_score_preserved_as_none():
    """
    MotionAnomalyResult with non-SUCCESS status and None score must have
    kinematic_anomaly=None in risk_vector (never substituted with 0.0), and must
    escalate to UNUSUAL / MONITOR rather than manufacturing a NORMAL assessment.
    """
    engine = RiskEngine()
    route_res = _make_route_result(score=0.10)
    motion_res = _make_motion_result(
        score=None,
        status="INVALID_DATA",
    )

    a = engine.evaluate(
        user_id="usr_test_001",
        route_result=route_res,
        motion_result=motion_res,
    )

    assert (
        a.risk_vector.kinematic_anomaly is None
    ), "Non-SUCCESS motion result must preserve None score, not convert to 0.0"
    assert a.risk_level == RiskLevel.UNUSUAL, "Failing detector must not produce NORMAL"
    assert a.recommended_action == RecommendedAction.MONITOR
    assert a.confidence <= 0.40


def test_route_normal_with_failing_motion_escalates_to_unusual_monitor():
    """
    Item 2: One detector normal and the other failing.
    Route is validated normal (0.15), but motion failed (INVALID_DATA).
    Must escalate to UNUSUAL / MONITOR with degraded confidence, never NORMAL.
    """
    engine = RiskEngine()
    route_res = _make_route_result(score=0.15)
    motion_res = _make_motion_result(score=None, status="INVALID_DATA")

    a = engine.evaluate(
        user_id="usr_test_001",
        route_result=route_res,
        motion_result=motion_res,
    )

    assert a.risk_level == RiskLevel.UNUSUAL
    assert a.recommended_action == RecommendedAction.MONITOR
    assert a.confidence <= 0.40
    assert a.risk_vector.route_anomaly == 0.15
    assert a.risk_vector.kinematic_anomaly is None
    assert a.telemetry_summary.motion_status == "INVALID_DATA"


def test_motion_normal_with_failing_route_escalates_to_unusual_monitor():
    """
    Item 2: One detector normal and the other failing.
    Motion is validated normal (0.12), but route failed (COMPUTATION_ERROR).
    Must escalate to UNUSUAL / MONITOR with degraded confidence, never NORMAL.
    """
    engine = RiskEngine()
    route_res = _make_route_result(score=None, status="COMPUTATION_ERROR")
    motion_res = _make_motion_result(score=0.12)

    a = engine.evaluate(
        user_id="usr_test_001",
        route_result=route_res,
        motion_result=motion_res,
    )

    assert a.risk_level == RiskLevel.UNUSUAL
    assert a.recommended_action == RecommendedAction.MONITOR
    assert a.confidence <= 0.40
    assert a.risk_vector.kinematic_anomaly == 0.12
    assert a.risk_vector.route_anomaly is None
    assert a.telemetry_summary.route_status == "COMPUTATION_ERROR"


def test_motion_insufficient_samples_with_normal_route_is_normal():
    """
    Item 5: Motion data does not meet minimum requirements (INSUFFICIENT_DATA).
    With a validated normal route, this is partial availability (clean missing sensor data),
    yielding NORMAL with reduced confidence (0.65).
    """
    engine = RiskEngine()
    route_res = _make_route_result(score=0.18)
    motion_res = _make_motion_result(score=None, status="INSUFFICIENT_DATA")

    a = engine.evaluate(
        user_id="usr_test_001",
        route_result=route_res,
        motion_result=motion_res,
    )

    assert a.risk_level == RiskLevel.NORMAL
    assert a.recommended_action == RecommendedAction.NONE
    assert a.confidence == 0.65
    assert a.risk_vector.route_anomaly == 0.18
    assert a.risk_vector.kinematic_anomaly is None


def test_motion_insufficient_samples_with_insufficient_route_is_unusual():
    """
    Item 3 & 5: Motion INSUFFICIENT_DATA + Route INSUFFICIENT_HISTORY.
    Both modalities lack sufficient data -> all-signals-missing policy applies.
    Yields UNUSUAL / MONITOR with confidence 0.20.
    """
    engine = RiskEngine()
    route_res = RouteDeviationResult(
        user_id="usr_test_001",
        trajectory_id="usr_test_001/trip_1",
        status="INSUFFICIENT_HISTORY",
        raw_distance_meters=None,
        route_deviation_score=None,
        reference_trajectory_count=2,
        closest_reference_id=None,
    )
    motion_res = _make_motion_result(score=None, status="INSUFFICIENT_DATA")

    a = engine.evaluate(
        user_id="usr_test_001",
        route_result=route_res,
        motion_result=motion_res,
    )

    assert a.risk_level == RiskLevel.UNUSUAL
    assert a.recommended_action == RecommendedAction.MONITOR
    assert a.confidence == 0.20
    assert a.risk_vector.route_anomaly is None
    assert a.risk_vector.kinematic_anomaly is None


def test_missing_all_signals_yields_unusual_not_normal():
    """
    Both route and motion unavailable -> UNUSUAL / MONITOR.
    Must NEVER yield NORMAL when all telemetry is absent.
    Confidence must reflect the data deficit (low).
    """
    engine = RiskEngine()

    a = engine.evaluate(
        user_id="usr_disconnected_003",
        route_result=None,
        motion_result=None,
    )

    assert (
        a.risk_level == RiskLevel.UNUSUAL
    ), "Missing all signals must NOT default to NORMAL; use UNUSUAL (conservative monitor)"
    assert a.recommended_action == RecommendedAction.MONITOR
    assert a.confidence <= 0.30, "Missing-signal confidence must be low"
    assert a.risk_vector.route_anomaly is None
    assert a.risk_vector.kinematic_anomaly is None
    assert a.location_status == "unavailable"
    # calibration scores must also be None, not 0.0
    assert a.calibration_metadata.raw_score is None
    assert a.calibration_metadata.calibrated_score is None


def test_partial_cold_start_route_with_normal_motion_is_normal():
    """
    Cold-start route (INSUFFICIENT_HISTORY) + validated-normal motion signal -> NORMAL (NONE).

    Documented policy (engine.py §4 Partial Availability):
      If the available validated signal is normal, the assessment is NORMAL with
      reduced confidence, reflecting genuine uncertainty from the missing modality.
    This case is DISTINCT from all-signals-missing (which yields UNUSUAL).
    The cold-start condition means the user exists and has location data; we simply
    lack sufficient history to score the route.
    """
    engine = RiskEngine()
    route_res = RouteDeviationResult(
        user_id="usr_new_007",
        trajectory_id="usr_new_007/trip_0",
        status="INSUFFICIENT_HISTORY",
        raw_distance_meters=None,
        route_deviation_score=None,
        reference_trajectory_count=3,
        closest_reference_id=None,
    )
    motion_res = _make_motion_result(score=0.12, motion_state="walking")

    a = engine.evaluate(
        user_id="usr_new_007",
        route_result=route_res,
        motion_result=motion_res,
    )

    assert a.risk_level == RiskLevel.NORMAL, (
        "Cold-start route + validated-normal motion must yield NORMAL, not UNUSUAL. "
        "UNUSUAL is reserved for all-signals-missing or an actually anomalous signal."
    )
    assert a.recommended_action == RecommendedAction.NONE
    # Confidence must be reduced (below full-dual-signal confidence of 0.88)
    assert (
        a.confidence < 0.88
    ), "Partial availability must reduce confidence below dual-signal level"
    assert (
        a.confidence >= 0.50
    ), "Confidence must not drop to all-missing-signal level for a valid observation"
    assert a.risk_vector.route_anomaly is None  # cold-start: no score
    assert a.risk_vector.kinematic_anomaly == 0.12  # validated signal preserved


def test_partial_route_normal_with_unavailable_motion_is_normal():
    """
    Validated-normal route + unavailable motion (None result) -> NORMAL with reduced confidence.

    Documented policy (engine.py §4 Partial Availability):
      If the available validated signal is normal, the assessment is NORMAL with
      reduced confidence, reflecting genuine uncertainty from the missing modality.
    """
    engine = RiskEngine()
    route_res = _make_route_result(score=0.18, distance_meters=50.0)

    a = engine.evaluate(
        user_id="usr_test_001",
        route_result=route_res,
        motion_result=None,  # motion sensor unavailable
    )

    assert (
        a.risk_level == RiskLevel.NORMAL
    ), "Normal route + unavailable motion must yield NORMAL with reduced confidence."
    assert a.recommended_action == RecommendedAction.NONE
    assert (
        a.confidence < 0.88
    ), "Partial availability must reduce confidence below dual-signal level"
    assert a.risk_vector.route_anomaly == 0.18
    assert a.risk_vector.kinematic_anomaly is None  # unavailable: no score


def test_partial_unavailable_route_with_anomalous_motion_is_unusual():
    """
    Unavailable route (None) + validated-anomalous motion -> UNUSUAL / MONITOR.

    When one signal is unavailable but the other is anomalous, the anomaly takes
    precedence under the single-anomaly escalation rule.
    """
    engine = RiskEngine()
    motion_res = _make_motion_result(score=0.72, motion_state="abrupt_motion")

    a = engine.evaluate(
        user_id="usr_test_001",
        route_result=None,
        motion_result=motion_res,
    )

    assert a.risk_level == RiskLevel.UNUSUAL
    assert a.recommended_action == RecommendedAction.MONITOR
    assert a.risk_vector.route_anomaly is None
    assert a.risk_vector.kinematic_anomaly == 0.72
    assert a.location_status == "unavailable"


def test_partial_anomalous_route_with_unavailable_motion_is_unusual():
    """
    Validated-anomalous route + unavailable motion (None) -> UNUSUAL / MONITOR.

    When one signal is anomalous and the other unavailable, a single-anomaly
    escalation applies. This is not ELEVATED (which requires both signals anomalous).
    """
    engine = RiskEngine()
    route_res = _make_route_result(score=0.75, distance_meters=200.0)

    a = engine.evaluate(
        user_id="usr_test_001",
        route_result=route_res,
        motion_result=None,
    )

    assert a.risk_level == RiskLevel.UNUSUAL
    assert a.recommended_action == RecommendedAction.MONITOR
    assert a.risk_vector.route_anomaly == 0.75
    assert a.risk_vector.kinematic_anomaly is None


# ---------------------------------------------------------------------------
# Section 3 — Contract 4 schema conformance
# ---------------------------------------------------------------------------


def test_contract4_exact_keys_present():
    """
    to_dict() default output must contain exactly the 10 Contract 4 fields
    from docs/architecture/data-flow.md lines 129-151.
    No invented fields; no missing mandatory fields.
    """
    engine = RiskEngine()
    route_res = _make_route_result(score=0.91, distance_meters=142.5)
    motion_res = _make_motion_result(score=0.84, motion_state="rapid_walking")

    a = engine.evaluate(
        user_id="usr_9941a80c",
        route_result=route_res,
        motion_result=motion_res,
        speed_mps=2.4,
    )

    d = a.to_dict()

    # All 10 mandatory Contract 4 keys must be present
    missing = CONTRACT4_REQUIRED_KEYS - d.keys()
    assert not missing, f"Contract 4 mandatory keys missing: {missing}"

    # No keys beyond Contract 4 mandatory set should be present by default
    extra = d.keys() - CONTRACT4_REQUIRED_KEYS
    assert not extra, (
        f"to_dict() contains non-Contract-4 keys: {extra}. "
        "Use include_extended_metadata=True for extended output."
    )


def test_contract4_field_types_and_values():
    """
    Each Contract 4 field must have the documented type and value constraints.
    """
    engine = RiskEngine()
    route_res = _make_route_result(score=0.91, distance_meters=142.5)
    motion_res = _make_motion_result(score=0.84, motion_state="rapid_walking")

    a = engine.evaluate(
        user_id="usr_9941a80c",
        route_result=route_res,
        motion_result=motion_res,
        speed_mps=2.4,
    )

    d = a.to_dict()

    # Schema and version
    assert d["$schema"] == SCHEMA_URI
    assert d["version"] == CONTRACT_VERSION == "0.1"

    # risk_level must be one of the documented values
    assert d["risk_level"] in VALID_RISK_LEVELS

    # confidence must be a float in [0.0, 1.0]
    assert isinstance(d["confidence"], float)
    assert 0.0 <= d["confidence"] <= 1.0

    # signals must be a list of valid identifiers (possibly empty)
    assert isinstance(d["signals"], list)
    for sig in d["signals"]:
        assert sig in VALID_SIGNAL_IDENTIFIERS, f"Unknown signal: {sig!r}"

    # location_status must be a string
    assert isinstance(d["location_status"], str)

    # recommended_action must be one of the documented values
    assert d["recommended_action"] in VALID_RECOMMENDED_ACTIONS

    # risk_vector must have exactly the 4 documented fields
    rv = d["risk_vector"]
    assert set(rv.keys()) == RISK_VECTOR_KEYS

    # Each risk_vector component is float in [0.0, 1.0] or null/None
    for field_name, val in rv.items():
        if val is not None:
            assert isinstance(
                val, float
            ), f"risk_vector.{field_name} should be float or None, got {type(val)}"
            assert 0.0 <= val <= 1.0, f"risk_vector.{field_name} out of bounds: {val}"


def test_contract4_elevated_co_occurring_output():
    """Concrete verification of ELEVATED co-occurrence output against Contract 4 schema."""
    engine = RiskEngine()
    route_res = _make_route_result(score=0.91, distance_meters=142.5)
    motion_res = _make_motion_result(score=0.84, motion_state="rapid_walking")

    a = engine.evaluate(
        user_id="usr_9941a80c",
        route_result=route_res,
        motion_result=motion_res,
        speed_mps=2.4,
    )

    d = a.to_dict()

    assert d["risk_level"] == "ELEVATED"
    assert d["recommended_action"] == "USER_CHECK"
    assert set(d["signals"]) == {"route_deviation", "unusual_motion"}
    assert d["risk_vector"]["route_anomaly"] == 0.91
    assert d["risk_vector"]["kinematic_anomaly"] == 0.84
    assert d["risk_vector"]["acoustic_anomaly"] is None
    assert d["risk_vector"]["temporal_persistence"] is None


def test_contract4_extended_metadata_flag():
    """
    to_dict(include_extended_metadata=True) must include telemetry_summary and
    calibration_metadata; to_dict() default must NOT include them.
    """
    engine = RiskEngine()
    route_res = _make_route_result(score=0.60, distance_meters=80.0)
    motion_res = _make_motion_result(score=0.65, motion_state="walking")

    a = engine.evaluate(
        user_id="usr_test_001",
        route_result=route_res,
        motion_result=motion_res,
    )

    d_base = a.to_dict()
    d_ext = a.to_dict(include_extended_metadata=True)

    # Default must NOT include extended keys
    assert "telemetry_summary" not in d_base
    assert "calibration_metadata" not in d_base

    # Extended must include them
    assert "telemetry_summary" in d_ext
    assert "calibration_metadata" in d_ext

    ts = d_ext["telemetry_summary"]
    assert "corridor_deviation_meters" in ts
    assert "motion_state" in ts
    assert ts["corridor_deviation_meters"] == 80.0


def test_missing_signals_contract4_null_risk_vector():
    """
    All-signals-missing output must have None in all risk_vector components
    in the serialized Contract 4 dictionary.
    """
    engine = RiskEngine()

    a = engine.evaluate(
        user_id="usr_disconnected_003",
        route_result=None,
        motion_result=None,
    )

    d = a.to_dict()
    assert d["risk_level"] == "UNUSUAL"
    rv = d["risk_vector"]
    for field_name, val in rv.items():
        assert (
            val is None
        ), f"Expected risk_vector.{field_name}=None when all signals missing, got {val}"


# ---------------------------------------------------------------------------
# Section 4 — Confidence and score bounds
# ---------------------------------------------------------------------------


def test_confidence_always_within_bounds():
    """Confidence must be in [0.0, 1.0] across all input combinations."""
    engine = RiskEngine()

    scenarios = [
        # (route_result, motion_result)
        (None, None),
        (_make_route_result(score=0.90), None),
        (None, _make_motion_result(score=0.90)),
        (_make_route_result(score=0.10), _make_motion_result(score=0.10)),
        (_make_route_result(score=0.90), _make_motion_result(score=0.90)),
        (_make_route_result(score=0.99), _make_motion_result(score=0.99)),
        (
            RouteDeviationResult(
                user_id="u",
                trajectory_id="t",
                status="INSUFFICIENT_HISTORY",
                raw_distance_meters=None,
                route_deviation_score=None,
                reference_trajectory_count=1,
                closest_reference_id=None,
            ),
            _make_motion_result(score=0.10),
        ),
    ]

    for route_res, motion_res in scenarios:
        a = engine.evaluate(
            user_id="usr_bounds_check",
            route_result=route_res,
            motion_result=motion_res,
        )
        assert 0.0 <= a.confidence <= 1.0, (
            f"confidence={a.confidence} out of bounds for "
            f"route={route_res}, motion={motion_res}"
        )


def test_risk_vector_scores_never_coerced_from_none():
    """
    When a signal is unavailable (status != SUCCESS), the corresponding
    risk_vector component must be None, not 0.0. Coercion to 0.0 would
    mislead downstream consumers into treating absence as evidence of safety.
    """
    engine = RiskEngine()

    # Route failure
    route_fail = _make_route_result(score=None, distance_meters=None, status="ERROR")
    motion_ok = _make_motion_result(score=0.15)
    a1 = engine.evaluate("u", route_result=route_fail, motion_result=motion_ok)
    assert a1.risk_vector.route_anomaly is None

    # Motion failure
    route_ok = _make_route_result(score=0.15)
    motion_fail = _make_motion_result(score=None, status="INSUFFICIENT_DATA")
    a2 = engine.evaluate("u", route_result=route_ok, motion_result=motion_fail)
    assert a2.risk_vector.kinematic_anomaly is None

    # Both failure
    a3 = engine.evaluate("u", route_result=None, motion_result=None)
    assert a3.risk_vector.route_anomaly is None
    assert a3.risk_vector.kinematic_anomaly is None


# ---------------------------------------------------------------------------
# Section 5 — Targeted confidence policy tests (Reviewer Feedback Scenarios)
# ---------------------------------------------------------------------------


def test_single_motion_anomaly_high_vs_low_detector_confidence():
    """
    Verify single motion anomaly scaling with motion detector confidence:
    - High motion detector confidence (0.85) yields high assessment confidence (0.85).
    - Low motion detector confidence (0.25) lowers assessment confidence (0.25).
    - Very low motion detector confidence (0.05) preserves 0.05 without an artificial 0.20 clamp.
    All remain at UNUSUAL / MONITOR with identical signals and risk vectors.
    """
    engine = RiskEngine()
    route_normal = _make_route_result(score=0.10)

    motion_high = _make_motion_result(
        score=0.80, confidence=0.85, motion_state="abrupt_motion"
    )
    a_high = engine.evaluate(
        "usr_test_001", route_result=route_normal, motion_result=motion_high
    )

    assert a_high.risk_level == RiskLevel.UNUSUAL
    assert a_high.recommended_action == RecommendedAction.MONITOR
    assert a_high.signals == (SIGNAL_UNUSUAL_MOTION,)
    assert a_high.confidence == 0.85
    assert a_high.risk_vector.kinematic_anomaly == 0.80
    assert a_high.risk_vector.route_anomaly == 0.10

    motion_low = _make_motion_result(
        score=0.80, confidence=0.25, motion_state="abrupt_motion"
    )
    a_low = engine.evaluate(
        "usr_test_001", route_result=route_normal, motion_result=motion_low
    )

    assert a_low.risk_level == RiskLevel.UNUSUAL
    assert a_low.recommended_action == RecommendedAction.MONITOR
    assert a_low.signals == (SIGNAL_UNUSUAL_MOTION,)
    assert a_low.confidence == 0.25
    assert a_low.confidence < a_high.confidence
    assert a_low.risk_vector.kinematic_anomaly == 0.80
    assert a_low.risk_vector.route_anomaly == 0.10

    motion_very_low = _make_motion_result(
        score=0.80, confidence=0.05, motion_state="abrupt_motion"
    )
    a_very_low = engine.evaluate(
        "usr_test_001", route_result=route_normal, motion_result=motion_very_low
    )

    assert a_very_low.risk_level == RiskLevel.UNUSUAL
    assert a_very_low.recommended_action == RecommendedAction.MONITOR
    assert a_very_low.signals == (SIGNAL_UNUSUAL_MOTION,)
    assert a_very_low.confidence == 0.05
    assert a_very_low.confidence < 0.20
    assert a_very_low.risk_vector.kinematic_anomaly == 0.80
    assert a_very_low.risk_vector.route_anomaly == 0.10


def test_co_occurring_anomalies_high_vs_low_motion_confidence():
    """
    Verify co-occurring anomalies without an artificial 0.70 confidence floor:
    - High motion confidence (0.90) yields (0.85 + 0.90) / 2 = 0.875 confidence.
    - Low motion confidence (0.20) yields (0.85 + 0.20) / 2 = 0.525 confidence.
      The confidence is strictly lower than 0.70 and reflects the detector uncertainty.
    Both escalate to ELEVATED / USER_CHECK with identical active signals and risk vectors.
    """
    engine = RiskEngine()
    route_anom = _make_route_result(score=0.85)

    motion_high = _make_motion_result(
        score=0.80, confidence=0.90, motion_state="abrupt_motion"
    )
    a_high = engine.evaluate(
        "usr_test_001", route_result=route_anom, motion_result=motion_high
    )

    assert a_high.risk_level == RiskLevel.ELEVATED
    assert a_high.recommended_action == RecommendedAction.USER_CHECK
    assert set(a_high.signals) == {SIGNAL_ROUTE_DEVIATION, SIGNAL_UNUSUAL_MOTION}
    assert a_high.confidence == 0.875
    assert a_high.risk_vector.route_anomaly == 0.85
    assert a_high.risk_vector.kinematic_anomaly == 0.80

    motion_low = _make_motion_result(
        score=0.80, confidence=0.20, motion_state="abrupt_motion"
    )
    a_low = engine.evaluate(
        "usr_test_001", route_result=route_anom, motion_result=motion_low
    )

    assert a_low.risk_level == RiskLevel.ELEVATED
    assert a_low.recommended_action == RecommendedAction.USER_CHECK
    assert set(a_low.signals) == {SIGNAL_ROUTE_DEVIATION, SIGNAL_UNUSUAL_MOTION}
    assert a_low.confidence == 0.525
    assert (
        a_low.confidence < 0.70
    ), "Confidence must not be clamped by a 0.70 floor when motion confidence is low"
    assert a_low.confidence < a_high.confidence
    assert a_low.risk_vector.route_anomaly == 0.85
    assert a_low.risk_vector.kinematic_anomaly == 0.80


def test_single_route_anomaly_with_unavailable_motion_maintains_standard_confidence():
    """
    When route is anomalous and motion is unavailable (None), motion confidence does not exist.
    Risk assessment confidence is 0.75 (nominal single-route anomaly confidence).
    """
    engine = RiskEngine()
    route_anom = _make_route_result(score=0.75)

    a = engine.evaluate("usr_test_001", route_result=route_anom, motion_result=None)

    assert a.risk_level == RiskLevel.UNUSUAL
    assert a.recommended_action == RecommendedAction.MONITOR
    assert a.signals == (SIGNAL_ROUTE_DEVIATION,)
    assert a.confidence == 0.75
    assert a.risk_vector.route_anomaly == 0.75
    assert a.risk_vector.kinematic_anomaly is None


def test_motion_detector_confidence_out_of_bounds_clamped():
    """
    Detector confidence below 0.0 or above 1.0 is clamped to [0.0, 1.0].
    - confidence = -0.5 is clamped to 0.0.
    - confidence = 1.5 is clamped to 1.0 (single anomaly capped at 0.90; co-occurring (0.85+1.0)/2 = 0.925).
    """
    engine = RiskEngine()
    route_normal = _make_route_result(score=0.10)
    route_anom = _make_route_result(score=0.85)

    # Negative confidence
    motion_neg = _make_motion_result(
        score=0.80, confidence=-0.5, motion_state="abrupt_motion"
    )
    a_neg_single = engine.evaluate(
        "usr_test_001", route_result=route_normal, motion_result=motion_neg
    )
    assert a_neg_single.confidence == 0.0

    a_neg_co = engine.evaluate(
        "usr_test_001", route_result=route_anom, motion_result=motion_neg
    )
    assert a_neg_co.confidence == (0.85 + 0.0) / 2.0

    # Over 1.0 confidence
    motion_over = _make_motion_result(
        score=0.80, confidence=1.5, motion_state="abrupt_motion"
    )
    a_over_single = engine.evaluate(
        "usr_test_001", route_result=route_normal, motion_result=motion_over
    )
    assert a_over_single.confidence == 0.90  # capped at single-motion maximum

    a_over_co = engine.evaluate(
        "usr_test_001", route_result=route_anom, motion_result=motion_over
    )
    assert a_over_co.confidence == (0.85 + 1.0) / 2.0


def test_motion_detector_confidence_non_finite_fallback_to_zero():
    """
    Non-finite detector confidence (NaN, +inf, -inf) falls back safely to 0.0.
    Does not crash RiskAssessment construction or produce NaN/Inf.
    """
    engine = RiskEngine()
    route_normal = _make_route_result(score=0.10)
    route_anom = _make_route_result(score=0.85)

    for non_finite_val in [float("nan"), float("inf"), float("-inf")]:
        motion_nf = _make_motion_result(
            score=0.80, confidence=non_finite_val, motion_state="abrupt_motion"
        )
        a_single = engine.evaluate(
            "usr_test_001", route_result=route_normal, motion_result=motion_nf
        )
        assert a_single.risk_level == RiskLevel.UNUSUAL
        assert a_single.confidence == 0.0

        a_co = engine.evaluate(
            "usr_test_001", route_result=route_anom, motion_result=motion_nf
        )
        assert a_co.risk_level == RiskLevel.ELEVATED
        assert a_co.confidence == (0.85 + 0.0) / 2.0


def test_motion_detector_none_confidence_fallback():
    """
    When motion_result.confidence is None, conservative nominal fallbacks apply:
    - Single motion anomaly: 0.75
    - Co-occurring anomalies: (0.85 + 0.80) / 2.0 = 0.825
    """
    engine = RiskEngine()
    route_normal = _make_route_result(score=0.10)
    route_anom = _make_route_result(score=0.85)

    motion_none_conf = _make_motion_result(
        score=0.80, confidence=None, motion_state="abrupt_motion"
    )
    a_single = engine.evaluate(
        "usr_test_001", route_result=route_normal, motion_result=motion_none_conf
    )
    assert a_single.confidence == 0.75

    a_co = engine.evaluate(
        "usr_test_001", route_result=route_anom, motion_result=motion_none_conf
    )
    assert a_co.confidence == (0.85 + 0.80) / 2.0


# ---------------------------------------------------------------------------
# Section 7 — Detector failure / corrupted-input regression tests
# ---------------------------------------------------------------------------


def test_route_computation_error_with_normal_motion_never_yields_normal():
    """
    Regression: Route detector reports COMPUTATION_ERROR (score=None) while
    motion detector reports validated normal (score < threshold).
    Engine must NEVER produce NORMAL because a failed detector does not
    constitute a validated normal observation.
    """
    engine = RiskEngine()
    route_res = _make_route_result(
        score=None,
        distance_meters=None,
        status="COMPUTATION_ERROR",
    )
    motion_res = _make_motion_result(score=0.15, motion_state="walking")

    a = engine.evaluate(
        user_id="usr_test_001",
        route_result=route_res,
        motion_result=motion_res,
    )

    assert a.risk_level == RiskLevel.UNUSUAL, (
        "Route COMPUTATION_ERROR + normal motion must yield UNUSUAL, not NORMAL. "
        "A failed detector is not a validated normal observation."
    )
    assert a.recommended_action == RecommendedAction.MONITOR
    assert a.confidence <= 0.40
    assert a.risk_vector.route_anomaly is None
    assert a.risk_vector.kinematic_anomaly == 0.15
    assert a.telemetry_summary.route_status == "COMPUTATION_ERROR"
    assert a.telemetry_summary.motion_status == "SUCCESS"


def test_motion_invalid_data_with_normal_route_never_yields_normal():
    """
    Regression: Motion detector reports INVALID_DATA (score=None) while
    route detector reports validated normal (score < threshold).
    Engine must NEVER produce NORMAL because a failed detector does not
    constitute a validated normal observation.
    """
    engine = RiskEngine()
    route_res = _make_route_result(score=0.20, distance_meters=50.0)
    motion_res = _make_motion_result(
        score=None,
        status="INVALID_DATA",
        motion_state="unknown",
    )

    a = engine.evaluate(
        user_id="usr_test_001",
        route_result=route_res,
        motion_result=motion_res,
    )

    assert a.risk_level == RiskLevel.UNUSUAL, (
        "Normal route + motion INVALID_DATA must yield UNUSUAL, not NORMAL. "
        "A failed detector is not a validated normal observation."
    )
    assert a.recommended_action == RecommendedAction.MONITOR
    assert a.confidence <= 0.40
    assert a.risk_vector.route_anomaly == 0.20
    assert a.risk_vector.kinematic_anomaly is None
    assert a.telemetry_summary.motion_status == "INVALID_DATA"
    assert a.telemetry_summary.route_status == "SUCCESS"


def test_both_detectors_failed_yields_unusual_not_normal():
    """
    Both detectors report failure statuses (COMPUTATION_ERROR + INVALID_DATA).
    Both scores are None. This falls into the all-signals-missing branch.
    Must yield UNUSUAL / MONITOR with confidence 0.20.
    """
    engine = RiskEngine()
    route_res = _make_route_result(
        score=None, distance_meters=None, status="COMPUTATION_ERROR"
    )
    motion_res = _make_motion_result(
        score=None, status="INVALID_DATA", motion_state="unknown"
    )

    a = engine.evaluate(
        user_id="usr_test_001",
        route_result=route_res,
        motion_result=motion_res,
    )

    assert a.risk_level == RiskLevel.UNUSUAL
    assert a.recommended_action == RecommendedAction.MONITOR
    assert a.confidence == 0.20
    assert a.risk_vector.route_anomaly is None
    assert a.risk_vector.kinematic_anomaly is None


def test_anomalous_route_with_motion_failure_escalates_to_unusual():
    """
    Route is anomalous (score >= threshold) while motion detector failed.
    The anomalous signal takes precedence through the single-anomaly branch.
    Must yield UNUSUAL / MONITOR, never NORMAL or ELEVATED.
    """
    engine = RiskEngine()
    route_res = _make_route_result(score=0.75, distance_meters=200.0)
    motion_res = _make_motion_result(
        score=None, status="INVALID_DATA", motion_state="unknown"
    )

    a = engine.evaluate(
        user_id="usr_test_001",
        route_result=route_res,
        motion_result=motion_res,
    )

    assert a.risk_level == RiskLevel.UNUSUAL
    assert a.recommended_action == RecommendedAction.MONITOR
    assert SIGNAL_ROUTE_DEVIATION in a.signals
    assert a.risk_vector.route_anomaly == 0.75
    assert a.risk_vector.kinematic_anomaly is None


def test_anomalous_motion_with_route_failure_escalates_to_unusual():
    """
    Motion is anomalous (score >= threshold) while route detector failed.
    The anomalous signal takes precedence through the single-anomaly branch.
    Must yield UNUSUAL / MONITOR, never NORMAL or ELEVATED.
    """
    engine = RiskEngine()
    route_res = _make_route_result(
        score=None, distance_meters=None, status="COMPUTATION_ERROR"
    )
    motion_res = _make_motion_result(score=0.70, motion_state="abrupt_motion")

    a = engine.evaluate(
        user_id="usr_test_001",
        route_result=route_res,
        motion_result=motion_res,
    )

    assert a.risk_level == RiskLevel.UNUSUAL
    assert a.recommended_action == RecommendedAction.MONITOR
    assert SIGNAL_UNUSUAL_MOTION in a.signals
    assert a.risk_vector.kinematic_anomaly == 0.70
    assert a.risk_vector.route_anomaly is None


# ---------------------------------------------------------------------------
# Section 8 — Terminal trip-state mapping regression tests
# ---------------------------------------------------------------------------


def test_normal_assessment_maps_correctly_to_risk_level():
    """
    Verify that a dual-normal assessment produces NORMAL with high confidence.
    This is the only path that could eventually map to COMPLETED_NORMAL
    when full inference coverage tracking is implemented.
    """
    engine = RiskEngine()
    route_res = _make_route_result(score=0.10)
    motion_res = _make_motion_result(score=0.05)

    a = engine.evaluate(
        user_id="usr_test_001",
        route_result=route_res,
        motion_result=motion_res,
    )

    assert a.risk_level == RiskLevel.NORMAL
    assert a.recommended_action == RecommendedAction.NONE
    assert a.confidence == 0.88
    assert len(a.signals) == 0


def test_assessment_with_signals_always_has_nonempty_signals_tuple():
    """
    When an anomaly is detected, the signals tuple must contain
    the corresponding authoritative signal identifier.
    """
    engine = RiskEngine()

    # Route anomaly
    a_route = engine.evaluate(
        user_id="usr_test_001",
        route_result=_make_route_result(score=0.70),
        motion_result=_make_motion_result(score=0.10),
    )
    assert SIGNAL_ROUTE_DEVIATION in a_route.signals
    assert SIGNAL_UNUSUAL_MOTION not in a_route.signals

    # Motion anomaly
    a_motion = engine.evaluate(
        user_id="usr_test_001",
        route_result=_make_route_result(score=0.10),
        motion_result=_make_motion_result(score=0.70),
    )
    assert SIGNAL_UNUSUAL_MOTION in a_motion.signals
    assert SIGNAL_ROUTE_DEVIATION not in a_motion.signals

    # Both anomalous
    a_both = engine.evaluate(
        user_id="usr_test_001",
        route_result=_make_route_result(score=0.70),
        motion_result=_make_motion_result(score=0.70),
    )
    assert set(a_both.signals) == {SIGNAL_ROUTE_DEVIATION, SIGNAL_UNUSUAL_MOTION}


# ---------------------------------------------------------------------------
# Section 9 — Edge case and input sanitization regression tests
# ---------------------------------------------------------------------------


def test_score_of_zero_is_preserved_and_not_confused_with_none():
    """
    Item 15: A valid observation has a score of zero.
    Must NOT be confused with None. Both modalities 0.0 -> NORMAL with confidence 0.88.
    Raw score and calibrated score must be 0.0, not None.
    """
    engine = RiskEngine()
    route_res = _make_route_result(score=0.0, distance_meters=0.0)
    motion_res = _make_motion_result(score=0.0, motion_state="still")

    a = engine.evaluate(
        user_id="usr_test_zero",
        route_result=route_res,
        motion_result=motion_res,
        speed_mps=0.0,
    )

    assert a.risk_level == RiskLevel.NORMAL
    assert a.recommended_action == RecommendedAction.NONE
    assert a.confidence == 0.88
    assert a.risk_vector.route_anomaly == 0.0
    assert a.risk_vector.kinematic_anomaly == 0.0
    assert a.calibration_metadata.raw_score == 0.0
    assert a.calibration_metadata.calibrated_score == 0.0
    assert a.telemetry_summary.speed_mps == 0.0


def test_non_finite_or_out_of_bounds_detector_score_handled_safely():
    """
    Item 16: A detector returns an extreme or non-finite score (NaN, Inf, > 1.0).
    Must not crash RiskVector construction with unhandled ValueError;
    must be sanitized to None and treated as a detector failure (UNUSUAL / MONITOR).
    """
    engine = RiskEngine()

    for invalid_val in [float("nan"), float("inf"), float("-inf"), 1.5, -0.1]:
        # Case A: Route detector returns invalid score despite status=SUCCESS
        route_bad = _make_route_result(score=invalid_val)
        motion_ok = _make_motion_result(score=0.10)

        a_route = engine.evaluate(
            user_id="usr_test_nan",
            route_result=route_bad,
            motion_result=motion_ok,
        )
        assert a_route.risk_level == RiskLevel.UNUSUAL
        assert a_route.recommended_action == RecommendedAction.MONITOR
        assert a_route.risk_vector.route_anomaly is None
        assert a_route.risk_vector.kinematic_anomaly == 0.10

        # Case B: Motion detector returns invalid score despite status=SUCCESS
        route_ok = _make_route_result(score=0.10)
        motion_bad = _make_motion_result(score=invalid_val)

        a_motion = engine.evaluate(
            user_id="usr_test_nan",
            route_result=route_ok,
            motion_result=motion_bad,
        )
        assert a_motion.risk_level == RiskLevel.UNUSUAL
        assert a_motion.recommended_action == RecommendedAction.MONITOR
        assert a_motion.risk_vector.kinematic_anomaly is None
        assert a_motion.risk_vector.route_anomaly == 0.10


def test_speed_mps_sanitization():
    """
    Negative, NaN, inf, or non-numeric speed values are sanitized to None.
    """
    engine = RiskEngine()
    route_res = _make_route_result(score=0.10)
    motion_res = _make_motion_result(score=0.10)

    for bad_speed in [-1.0, float("nan"), float("inf"), "fast", True]:
        a = engine.evaluate(
            user_id="usr_test_speed",
            route_result=route_res,
            motion_result=motion_res,
            speed_mps=bad_speed,  # type: ignore
        )
        assert a.telemetry_summary.speed_mps is None


def test_repeated_evaluation_is_strictly_deterministic():
    """
    Item 18: Evaluating identical inputs repeatedly produces identical results.
    """
    engine = RiskEngine()
    route_res = _make_route_result(score=0.25, distance_meters=60.0)
    motion_res = _make_motion_result(score=0.20, motion_state="walking")

    res1 = engine.evaluate(
        user_id="usr_test_det",
        route_result=route_res,
        motion_result=motion_res,
        speed_mps=1.4,
    )
    res2 = engine.evaluate(
        user_id="usr_test_det",
        route_result=route_res,
        motion_result=motion_res,
        speed_mps=1.4,
    )

    assert res1.risk_level == res2.risk_level
    assert res1.confidence == res2.confidence
    assert res1.signals == res2.signals
    assert res1.recommended_action == res2.recommended_action
    assert res1.risk_vector == res2.risk_vector
    assert res1.telemetry_summary.speed_mps == res2.telemetry_summary.speed_mps
    assert res1.calibration_metadata == res2.calibration_metadata
