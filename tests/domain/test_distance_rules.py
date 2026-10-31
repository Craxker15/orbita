"""Tests of the observer distance rules of spec 006."""

from __future__ import annotations

import math

from orbita.domain.distance_rules import distance_km_rounded, straight_distance_km, to_cartesian
from orbita.domain.observer import GroundPoint, Observer

ORIGIN = Observer(latitude=0.0, longitude=0.0)


def test_point_directly_above_the_observer_is_at_its_altitude() -> None:
    assert math.isclose(straight_distance_km(ORIGIN, GroundPoint(0.0, 0.0, 400.0)), 400.0)


def test_point_on_the_horizon_is_about_9010_km() -> None:
    assert distance_km_rounded(ORIGIN, GroundPoint(0.0, 90.0, 0.0)) == 9010


def test_distance_is_rounded_to_the_nearest_10_km() -> None:
    assert distance_km_rounded(ORIGIN, GroundPoint(0.0, 0.0, 404.0)) == 400
    assert distance_km_rounded(ORIGIN, GroundPoint(0.0, 0.0, 405.0)) == 410


def test_distance_to_the_same_point_is_zero() -> None:
    assert distance_km_rounded(ORIGIN, GroundPoint(0.0, 0.0, 0.0)) == 0


def test_north_pole_is_on_the_z_axis() -> None:
    x, y, z = to_cartesian(GroundPoint(90.0, 0.0, 0.0))
    assert math.isclose(x, 0.0, abs_tol=1e-6)
    assert math.isclose(y, 0.0, abs_tol=1e-6)
    assert math.isclose(z, 6371.0)
