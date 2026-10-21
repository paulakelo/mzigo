"""Mzigo Virtual Accelerated Clock.

Compresses a full 24-hour delivery schedule into minutes for deterministic simulation.
"""

from datetime import UTC, datetime, timedelta


class VirtualClock:
    """Virtual accelerated clock for deterministic simulations."""

    def __init__(self, start_time: datetime | None = None, speedup: float = 60.0):
        self.start_time = start_time or datetime(2026, 10, 20, 8, 0, 0, tzinfo=UTC)
        self.current_time = self.start_time
        self.speedup = speedup

    def advance_seconds(self, seconds: float):
        """Advance virtual clock by a given number of seconds."""
        self.current_time += timedelta(seconds=seconds)

    def advance_minutes(self, minutes: float):
        """Advance virtual clock by a given number of minutes."""
        self.advance_seconds(minutes * 60.0)

    def now(self) -> datetime:
        """Get current virtual time."""
        return self.current_time

    def isoformat(self) -> str:
        """Format current virtual time as ISO 8601 string."""
        return self.current_time.isoformat()
