"""Orbit type and orbital period (DESIGN.md §4.1 and §4.6)."""

from __future__ import annotations

import math

from orbita.domain.elements import OrbitType

GEO_MEAN_MOTION_MIN = 0.99
GEO_MEAN_MOTION_MAX = 1.01
GEO_MAX_INCLINATION_DEG = 10.0
POLAR_MIN_INCLINATION_DEG = 80.0
POLAR_MAX_INCLINATION_DEG = 100.0
LOW_MIN_MEAN_MOTION = 11.25
MINUTES_PER_DAY = 1440.0


def classify_orbit(inclination_deg: float, mean_motion_rev_day: float) -> OrbitType:
    """Return the orbit type. The rules are applied in order and the first one that holds wins."""
    geo_mean_motion = GEO_MEAN_MOTION_MIN <= mean_motion_rev_day <= GEO_MEAN_MOTION_MAX
    if geo_mean_motion and inclination_deg < GEO_MAX_INCLINATION_DEG:
        return OrbitType.GEOSTATIONARY
    if POLAR_MIN_INCLINATION_DEG <= inclination_deg <= POLAR_MAX_INCLINATION_DEG:
        return OrbitType.POLAR
    if mean_motion_rev_day >= LOW_MIN_MEAN_MOTION:
        return OrbitType.LOW
    return OrbitType.OTHER


def period_minutes(mean_motion_rev_day: float) -> int:
    """Return the period of one revolution in whole minutes, rounded half up.

    The mean motion must be greater than 0; OrbitalElements guarantees it.
    """
    return math.floor(MINUTES_PER_DAY / mean_motion_rev_day + 0.5)
