"""Tests of the years-in-orbit rule (spec 018)."""

from __future__ import annotations

from datetime import date

import pytest

from orbita.domain.catalog_rules import years_in_orbit
from orbita.domain.errors import DataValidationError


def test_ten_years_exactly_is_10_point_0() -> None:
    assert years_in_orbit(date(2016, 10, 30), date(2026, 10, 30)) == 10.0


def test_launch_today_gives_zero_years() -> None:
    assert years_in_orbit(date(2026, 10, 30), date(2026, 10, 30)) == 0.0


def test_result_has_one_decimal() -> None:
    assert years_in_orbit(date(1998, 11, 20), date(2026, 10, 30)) == 27.9


def test_launch_in_the_future_is_rejected() -> None:
    with pytest.raises(DataValidationError):
        years_in_orbit(date(2027, 1, 1), date(2026, 10, 30))
