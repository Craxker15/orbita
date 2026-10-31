"""Download intervals: how often the program may contact CelesTrak (DESIGN.md §4.2, ADR-003)."""

from __future__ import annotations

from datetime import datetime, timedelta

from orbita.domain.elements import require_utc
from orbita.domain.errors import DataValidationError

ELEMENTS_DOWNLOAD_INTERVAL = timedelta(hours=2)
CATALOG_DOWNLOAD_INTERVAL = timedelta(hours=24)


def is_download_due(last_attempt: datetime | None, now: datetime, interval: timedelta) -> bool:
    """Tell whether a new download may start.

    The interval counts from the last attempt, successful or not: a failed attempt is not
    retried before the interval has passed (ADR-003). No previous attempt means it is due.
    """
    require_utc(now, "now")
    if last_attempt is None:
        return True
    require_utc(last_attempt, "last_attempt")
    elapsed = now - last_attempt
    if elapsed < timedelta(0):
        raise DataValidationError("the last attempt is later than now")
    return elapsed >= interval
