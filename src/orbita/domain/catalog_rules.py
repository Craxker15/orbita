"""Catalog rules: years in orbit from the launch date (DESIGN.md §4.6)."""

from __future__ import annotations

from datetime import date
from typing import Final

from orbita.domain.errors import DataValidationError

DAYS_PER_YEAR: Final = 365.25


def years_in_orbit(launch_date: date, today: date) -> float:
    """Return the years since the launch, with one decimal (DESIGN.md §4.6).

    Preconditions: today is the current UTC date.
    Postconditions: the result is at least 0.0 and has one decimal.

    Raises:
        DataValidationError: if the launch date is after today.
    """
    days = (today - launch_date).days
    if days < 0:
        raise DataValidationError("the launch date is after today")
    return round(days / DAYS_PER_YEAR, 1)
