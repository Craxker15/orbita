"""Freshness of the orbital elements (DESIGN.md §4.2, RF-06)."""

from __future__ import annotations

from datetime import datetime, timedelta

from orbita.domain.elements import Freshness, require_utc
from orbita.domain.errors import DataValidationError

FRESH_LIMIT = timedelta(days=3)
STALE_LIMIT = timedelta(days=14)


def classify_freshness(downloaded_at: datetime, now: datetime) -> Freshness:
    """Return how old the orbital elements are, counted from the last successful download.

    A download time later than now is rejected: it means the clock or the data is wrong.
    """
    require_utc(downloaded_at, "downloaded_at")
    require_utc(now, "now")
    age = now - downloaded_at
    if age < timedelta(0):
        raise DataValidationError("the download time is later than now")
    if age <= FRESH_LIMIT:
        return Freshness.NORMAL
    if age <= STALE_LIMIT:
        return Freshness.STALE
    return Freshness.TOO_OLD
