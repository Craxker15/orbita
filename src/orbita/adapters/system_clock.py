"""System clock adapter: reads real time (ARCHITECTURE.md §6)."""

from __future__ import annotations

from datetime import UTC, datetime


class SystemClock:
    """Returns the current time of the operating system, in UTC (Clock port)."""

    def now(self) -> datetime:
        """Return the current time with tzinfo UTC.

        Preconditions: none.
        Postconditions: the result is timezone-aware and in UTC.
        """
        return datetime.now(UTC)
