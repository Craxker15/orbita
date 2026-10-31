"""Tests of the orbit, period and time rules of spec 004."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from orbita.domain.elements import OrbitType
from orbita.domain.errors import DataValidationError
from orbita.domain.orbit_rules import classify_orbit, period_minutes
from orbita.domain.time_rules import format_colombia_time, to_colombia_time


@pytest.mark.parametrize(
    ("inclination", "mean_motion", "expected"),
    [
        (0.1, 1.0027, OrbitType.GEOSTATIONARY),
        (98.7, 14.2, OrbitType.POLAR),
        (80.0, 14.0, OrbitType.POLAR),
        (79.9, 14.0, OrbitType.LOW),
        (51.6, 15.5, OrbitType.LOW),
        (55.0, 2.0, OrbitType.OTHER),
        (9.9, 0.99, OrbitType.GEOSTATIONARY),
        (9.9, 1.01, OrbitType.GEOSTATIONARY),
        (9.9, 1.02, OrbitType.OTHER),
        (10.0, 1.0, OrbitType.OTHER),
    ],
)
def test_classify_orbit_applies_the_rules_in_order(
    inclination: float, mean_motion: float, expected: OrbitType
) -> None:
    assert classify_orbit(inclination, mean_motion) is expected


@pytest.mark.parametrize(("mean_motion", "minutes"), [(15.5, 93), (1.0027, 1436)])
def test_period_minutes_is_rounded_to_whole_minutes(mean_motion: float, minutes: int) -> None:
    assert period_minutes(mean_motion) == minutes


def test_colombia_time_is_utc_minus_five() -> None:
    moment = datetime(2026, 10, 30, 3, 0, tzinfo=UTC)
    assert format_colombia_time(moment) == "2026-10-29 22:00"


def test_colombia_time_has_no_daylight_saving() -> None:
    moment = datetime(2026, 6, 15, 12, 0, tzinfo=UTC)
    assert format_colombia_time(moment) == "2026-06-15 07:00"


def test_colombia_time_keeps_the_same_instant() -> None:
    moment = datetime(2026, 10, 30, 3, 0, tzinfo=UTC)
    assert to_colombia_time(moment) == moment


def test_colombia_time_rejects_naive_datetime() -> None:
    with pytest.raises(DataValidationError):
        to_colombia_time(datetime(2026, 10, 30, 3, 0))
