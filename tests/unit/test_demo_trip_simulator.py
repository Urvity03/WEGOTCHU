"""
Unit test for demo_trip_simulator scenarios (Member 2 + End-to-End Integration).
"""

from scripts.demo_trip_simulator import (
    DEMO_USER_ID,
    get_demo_client,
    run_scenario_contact_dispatch,
    run_scenario_high_risk,
    run_scenario_normal,
    run_scenario_timer_expiry,
    seed_reference_trips,
)


def test_demo_simulator_all_scenarios_pass():
    client, headers, SessionLocal = get_demo_client()
    db = SessionLocal()
    try:
        seed_reference_trips(db, DEMO_USER_ID, count=5)
    finally:
        db.close()

    assert run_scenario_normal(client, headers, SessionLocal) is True
    assert run_scenario_high_risk(client, headers, SessionLocal) is True
    assert run_scenario_timer_expiry(client, headers, SessionLocal) is True
    assert run_scenario_contact_dispatch(client, headers, SessionLocal) is True
