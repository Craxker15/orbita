"""Tests of the Sun and Moon positions (low-precision formulas, no network)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from orbita.domain.sky import moon_subpoint, sun_subpoint


def test_sun_is_overhead_near_the_equator_at_the_march_equinox_noon_utc() -> None:
    lat, lon = sun_subpoint(datetime(2026, 3, 20, 12, 0, tzinfo=UTC))
    assert abs(lat) < 1.0
    assert abs(lon) < 5.0


def test_sun_declination_is_about_23_degrees_at_the_june_solstice() -> None:
    lat, _ = sun_subpoint(datetime(2026, 6, 21, 12, 0, tzinfo=UTC))
    assert 23.0 < lat < 23.6


def test_sun_moves_west_about_15_degrees_per_hour() -> None:
    _, first = sun_subpoint(datetime(2026, 3, 20, 12, 0, tzinfo=UTC))
    _, second = sun_subpoint(datetime(2026, 3, 20, 13, 0, tzinfo=UTC))
    step = (second - first + 180.0) % 360.0 - 180.0
    assert -15.5 < step < -14.5


def test_moon_latitude_stays_within_its_orbit_tilt() -> None:
    start = datetime(2026, 1, 1, tzinfo=UTC)
    for hours in range(0, 24 * 30, 7):
        lat, _ = moon_subpoint(start + timedelta(hours=hours))
        assert abs(lat) <= 29.0


def test_naive_moment_is_rejected() -> None:
    with pytest.raises(ValueError):
        sun_subpoint(datetime(2026, 3, 20, 12))
