"""Straight-line distance from the observer to a satellite (DESIGN.md §4.4)."""

from __future__ import annotations

import math

from orbita.domain.observer import GroundPoint, Observer

EARTH_RADIUS_KM = 6371.0
DISTANCE_STEP_KM = 10


def to_cartesian(point: GroundPoint) -> tuple[float, float, float]:
    """Convert a point above the spherical Earth to x, y, z in km (DESIGN.md §4.4)."""
    radius = EARTH_RADIUS_KM + point.altitude_km
    lat = math.radians(point.latitude)
    lon = math.radians(point.longitude)
    x = radius * math.cos(lat) * math.cos(lon)
    y = radius * math.cos(lat) * math.sin(lon)
    z = radius * math.sin(lat)
    return x, y, z


def straight_distance_km(observer: Observer, point: GroundPoint) -> float:
    """Return the straight-line distance in km between the observer (altitude 0) and the point."""
    surface = GroundPoint(latitude=observer.latitude, longitude=observer.longitude)
    x1, y1, z1 = to_cartesian(surface)
    x2, y2, z2 = to_cartesian(point)
    return math.sqrt((x1 - x2) ** 2 + (y1 - y2) ** 2 + (z1 - z2) ** 2)


def distance_km_rounded(observer: Observer, point: GroundPoint) -> int:
    """Return the distance in km, rounded half up to the nearest 10 km."""
    steps = math.floor(straight_distance_km(observer, point) / DISTANCE_STEP_KM + 0.5)
    return steps * DISTANCE_STEP_KM
