"""Tests of the Skyfield adapter with a synthetic low orbit: no network (spec 013)."""

from __future__ import annotations

import math
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest

from orbita.adapters.skyfield_propagator import SkyfieldPropagator
from orbita.domain.distance_rules import to_cartesian
from orbita.domain.elements import OrbitalElements
from orbita.domain.errors import PropagationError

EPOCH = datetime(2026, 10, 30, 12, 0, tzinfo=UTC)
NOW = EPOCH + timedelta(hours=1)


def leo(**changes: Any) -> OrbitalElements:
    values: dict[str, Any] = {
        "norad": 25544,
        "name": "SYNTHETIC LEO",
        "inclination_deg": 51.6,
        "mean_motion_rev_day": 15.5,
        "eccentricity": 0.0005,
        "epoch": EPOCH,
        "raan_deg": 0.0,
        "arg_perigee_deg": 0.0,
        "mean_anomaly_deg": 0.0,
        "mean_motion_dot": 0.0,
        "mean_motion_ddot": 0.0,
        "bstar": 0.0,
    }
    values.update(changes)
    return OrbitalElements(**values)


def test_altitude_of_a_low_orbit_is_in_the_expected_range() -> None:
    state = SkyfieldPropagator().state(leo(), NOW)
    assert 300.0 <= state.point.altitude_km <= 500.0


def test_speed_of_a_low_orbit_is_about_7_6_km_per_second() -> None:
    state = SkyfieldPropagator().state(leo(), NOW)
    assert 7.4 <= state.speed_km_s <= 7.9


def test_positions_one_second_apart_are_7_to_8_km_apart() -> None:
    propagator = SkyfieldPropagator()
    first = propagator.state(leo(), NOW).point
    second = propagator.state(leo(), NOW + timedelta(seconds=1)).point
    distance = math.dist(to_cartesian(first), to_cartesian(second))
    assert 7.0 <= distance <= 8.0


def test_ground_track_has_91_points_at_the_surface() -> None:
    moments = tuple(NOW + timedelta(minutes=minute) for minute in range(-45, 46))
    track = SkyfieldPropagator().ground_track(leo(), moments)
    assert len(track) == 91
    assert all(point.altitude_km == 0.0 for point in track)


def test_repeated_calls_give_the_same_state() -> None:
    propagator = SkyfieldPropagator()
    assert propagator.state(leo(), NOW) == propagator.state(leo(), NOW)


def test_naive_moment_is_reported_as_propagation_error() -> None:
    with pytest.raises(PropagationError):
        SkyfieldPropagator().state(leo(), datetime(2026, 10, 30, 13))
