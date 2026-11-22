"""
Emergency Dispatch and Trusted Contact Notification Service for WEGOTCHU.

Handles alerting trusted contacts during manual SOS activations,
safety timer expirations, and high-risk proactive escalations.
Supports Twilio SMS when configured, and safe simulated dispatch
for automated testing and academic demonstrations.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Sequence

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class DispatchResult:
    """Outcome of an emergency contact dispatch attempt."""

    status: str
    recipients_count: int
    message: str
    dispatched_at: datetime
    carrier: str
    detail: str | None = None


class DispatchService:
    """
    Orchestrates delivery of emergency alerts to user trusted contacts.

    Invariants:
      - Never fabricates verified carrier delivery if an external carrier was not invoked.
      - Falls back safely to simulated dispatch when live SMS credentials are absent.
      - Formats location coordinates as actionable Google Maps links.
    """

    def __init__(
        self,
        twilio_account_sid: str | None = None,
        twilio_auth_token: str | None = None,
        twilio_from_number: str | None = None,
        force_simulation: bool = False,
    ) -> None:
        self.account_sid = twilio_account_sid or os.getenv("TWILIO_ACCOUNT_SID")
        self.auth_token = twilio_auth_token or os.getenv("TWILIO_AUTH_TOKEN")
        self.from_number = twilio_from_number or os.getenv("TWILIO_FROM_NUMBER")
        self.force_simulation = force_simulation

    def format_sos_message(
        self,
        user_id: str,
        source: str,
        latitude: float | None = None,
        longitude: float | None = None,
        note: str | None = None,
    ) -> str:
        """Compose a concise, high-priority emergency SMS alert."""
        timestamp_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

        location_part = "Location unavailable"
        if latitude is not None and longitude is not None:
            location_part = f"Location: https://maps.google.com/?q={latitude:.6f},{longitude:.6f}"

        note_part = f" Note: {note}" if note else ""
        source_label = "AUTOMATIC TIMER EXPIRY" if "timer" in source.lower() else "MANUAL SOS"

        return (
            f"[WEGOTCHU EMERGENCY ALERT] {source_label} for user '{user_id}'. "
            f"{location_part}. Time: {timestamp_str}.{note_part}"
        )

    def dispatch_alert(
        self,
        user_id: str,
        recipients: Sequence[str] | None,
        source: str = "manual",
        latitude: float | None = None,
        longitude: float | None = None,
        note: str | None = None,
    ) -> DispatchResult:
        """
        Deliver an SOS alert to registered recipient numbers.

        Returns structured DispatchResult indicating status and carrier mode.
        """
        now = datetime.now(timezone.utc)
        clean_recipients = [r.strip() for r in (recipients or []) if r and r.strip()]

        message_body = self.format_sos_message(
            user_id=user_id,
            source=source,
            latitude=latitude,
            longitude=longitude,
            note=note,
        )

        if not clean_recipients:
            logger.info("No trusted contact recipients provided for user '%s'", user_id)
            return DispatchResult(
                status="no_recipients",
                recipients_count=0,
                message=message_body,
                dispatched_at=now,
                carrier="none",
                detail="No trusted contacts configured or provided",
            )

        # Check if live Twilio carrier is configured and not forced to simulation
        if (
            not self.force_simulation
            and self.account_sid
            and self.auth_token
            and self.from_number
        ):
            try:
                # Optional live Twilio dispatch if library installed and configured
                from twilio.rest import Client  # type: ignore

                client = Client(self.account_sid, self.auth_token)
                delivered_count = 0
                for recipient in clean_recipients:
                    client.messages.create(
                        body=message_body,
                        from_=self.from_number,
                        to=recipient,
                    )
                    delivered_count += 1

                logger.warning(
                    "Delivered live SMS alert to %d recipient(s) via Twilio",
                    delivered_count,
                )
                return DispatchResult(
                    status="dispatched",
                    recipients_count=delivered_count,
                    message=message_body,
                    dispatched_at=now,
                    carrier="twilio",
                    detail=f"Dispatched via Twilio to {delivered_count} recipient(s)",
                )
            except Exception as exc:
                logger.error("Twilio SMS dispatch failed (%s); falling back to simulated dispatch", exc)

        # Simulated dispatch for tests and academic demonstration
        logger.warning(
            "[SIMULATED DISPATCH] SOS alert generated for user '%s' to %d recipient(s): %s",
            user_id,
            len(clean_recipients),
            clean_recipients,
        )
        return DispatchResult(
            status="simulated_dispatch",
            recipients_count=len(clean_recipients),
            message=message_body,
            dispatched_at=now,
            carrier="simulation",
            detail=f"Simulated dispatch executed for {len(clean_recipients)} recipient(s)",
        )
