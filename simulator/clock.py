"""Mzigo Virtual Accelerated Clock.

Compresses a full 24-hour delivery schedule into minutes.
"""

from datetime import UTC, datetime


class VirtualClock:
    """Virtual accelerated clock for deterministic simulations."""

    def __init__(self, start_time: datetime | None = None, speedup: float = 60.0):
        self.start_time = start_time or datetime(2026, 10, 20, 8, 0, 0, tzinfo=UTC)
        self.current_time = self.start_time
        self.speedup = speedup

    def advance_seconds(self, seconds: float):
        self.current_time = self.current_time.fromtimestamp(
            self.current_time.timestamp() + seconds, tz=UTC
        )

    def now(self) -> datetime:
        return self.current_time
