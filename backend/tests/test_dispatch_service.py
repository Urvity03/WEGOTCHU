"""
Unit tests for DispatchService (Member 3 Emergency Contact Notification).
"""

from unittest.mock import MagicMock, patch

from backend.app.services.dispatch_service import DispatchResult, DispatchService


def test_dispatch_alert_no_recipients():
    service = DispatchService(force_simulation=True)
    res = service.dispatch_alert(user_id="usr_test_123", recipients=[])
    assert res.status == "no_recipients"
    assert res.recipients_count == 0
    assert res.carrier == "none"
    assert "usr_test_123" in res.message


def test_dispatch_alert_none_recipients():
    service = DispatchService(force_simulation=True)
    res = service.dispatch_alert(user_id="usr_test_123", recipients=None)
    assert res.status == "no_recipients"
    assert res.recipients_count == 0
    assert res.carrier == "none"


def test_dispatch_alert_empty_strings_treated_as_no_recipients():
    service = DispatchService(force_simulation=True)
    res = service.dispatch_alert(user_id="usr_test_123", recipients=["   ", ""])
    assert res.status == "no_recipients"
    assert res.recipients_count == 0


def test_dispatch_alert_simulation_fallback():
    # Without twilio credentials, falls back to simulated dispatch
    service = DispatchService(force_simulation=False)
    recipients = ["+15551234567", "+15559876543"]
    res = service.dispatch_alert(
        user_id="usr_sim_test",
        recipients=recipients,
        source="manual",
        latitude=37.7749,
        longitude=-122.4194,
    )
    assert res.status == "simulated_dispatch"
    assert res.recipients_count == 2
    assert res.carrier == "simulation"
    assert "37.7749" in res.message
    assert "-122.4194" in res.message
    assert "maps.google.com" in res.message


def test_format_sos_message_variations():
    service = DispatchService()

    # With location and note
    msg1 = service.format_sos_message(
        user_id="usr_abc",
        source="manual",
        latitude=40.7128,
        longitude=-74.0060,
        note="Need urgent help",
    )
    assert "MANUAL SOS" in msg1
    assert "usr_abc" in msg1
    assert "maps.google.com/?q=40.712800,-74.006000" in msg1
    assert "Note: Need urgent help" in msg1

    # Timer expired source, without location
    msg2 = service.format_sos_message(
        user_id="usr_xyz",
        source="timer_expired",
        latitude=None,
        longitude=None,
    )
    assert "AUTOMATIC TIMER EXPIRY" in msg2
    assert "usr_xyz" in msg2
    assert "Location unavailable" in msg2


def test_dispatch_alert_with_twilio_success():
    service = DispatchService(
        twilio_account_sid="ACmock",
        twilio_auth_token="authmock",
        twilio_from_number="+15550000000",
        force_simulation=False,
    )

    mock_client = MagicMock()
    mock_messages = MagicMock()
    mock_client.messages = mock_messages

    with patch.dict("sys.modules", {"twilio.rest": MagicMock(Client=lambda sid, tok: mock_client)}):
        res = service.dispatch_alert(
            user_id="usr_tw",
            recipients=["+15551112222", "+15553334444"],
            source="manual",
        )
        assert res.status == "dispatched"
        assert res.recipients_count == 2
        assert res.carrier == "twilio"
        assert mock_messages.create.call_count == 2


def test_dispatch_alert_with_twilio_exception_falls_back():
    service = DispatchService(
        twilio_account_sid="ACmock",
        twilio_auth_token="authmock",
        twilio_from_number="+15550000000",
        force_simulation=False,
    )

    def failing_client(sid, tok):
        raise RuntimeError("Twilio network error")

    with patch.dict("sys.modules", {"twilio.rest": MagicMock(Client=failing_client)}):
        res = service.dispatch_alert(
            user_id="usr_tw_fail",
            recipients=["+15551112222"],
            source="manual",
        )
        # Should gracefully fall back to simulation
        assert res.status == "simulated_dispatch"
        assert res.recipients_count == 1
        assert res.carrier == "simulation"
