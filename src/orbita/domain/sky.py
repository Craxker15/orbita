"""Sun and Moon positions for the globe, from low-precision formulas (ADR-002).

Works offline: no ephemeris file is downloaded. The Sun is accurate to about 0.01 degrees and the
Moon to about 0.3 degrees, which is enough to show where each one is overhead. Not for navigation.
"""

from __future__ import annotations

import math
from datetime import UTC, datetime

_J2000 = datetime(2000, 1, 1, 12, tzinfo=UTC)


def _days_since_j2000(when: datetime) -> float:
    """Return the days elapsed since 2000-01-01 12:00 UTC.

    Raises:
        ValueError: if the moment has no time zone.
    """
    if when.utcoffset() is None:
        raise ValueError("the moment must be timezone-aware")
    return (when.astimezone(UTC) - _J2000).total_seconds() / 86400.0


def _wrap_longitude(degrees: float) -> float:
    """Return a longitude in the range [-180, 180)."""
    return (degrees + 180.0) % 360.0 - 180.0


def _subpoint(right_ascension: float, declination: float, days: float) -> tuple[float, float]:
    """Return (latitude, longitude) in degrees of the point where the body is overhead."""
    sidereal = (280.46061837 + 360.98564736629 * days) % 360.0
    longitude = _wrap_longitude(math.degrees(right_ascension) - sidereal)
    return math.degrees(declination), longitude


def sun_subpoint(when: datetime) -> tuple[float, float]:
    """Return (latitude, longitude) in degrees of the point with the Sun overhead.

    Raises:
        ValueError: if the moment has no time zone.
    """
    days = _days_since_j2000(when)
    mean_longitude = math.radians((280.460 + 0.9856474 * days) % 360.0)
    mean_anomaly = math.radians((357.528 + 0.9856003 * days) % 360.0)
    ecliptic = (
        mean_longitude
        + math.radians(1.915) * math.sin(mean_anomaly)
        + math.radians(0.020) * math.sin(2 * mean_anomaly)
    )
    obliquity = math.radians(23.439 - 0.0000004 * days)
    right_ascension = math.atan2(math.cos(obliquity) * math.sin(ecliptic), math.cos(ecliptic))
    declination = math.asin(math.sin(obliquity) * math.sin(ecliptic))
    return _subpoint(right_ascension, declination, days)


def moon_subpoint(when: datetime) -> tuple[float, float]:
    """Return (latitude, longitude) in degrees of the point with the Moon overhead.

    Raises:
        ValueError: if the moment has no time zone.
    """
    days = _days_since_j2000(when)
    mean_longitude = math.radians((218.316 + 13.176396 * days) % 360.0)
    mean_anomaly = math.radians((134.963 + 13.064993 * days) % 360.0)
    argument_of_latitude = math.radians((93.272 + 13.229350 * days) % 360.0)
    ecliptic_longitude = mean_longitude + math.radians(6.289) * math.sin(mean_anomaly)
    ecliptic_latitude = math.radians(5.128) * math.sin(argument_of_latitude)
    obliquity = math.radians(23.439 - 0.0000004 * days)
    right_ascension = math.atan2(
        math.sin(ecliptic_longitude) * math.cos(obliquity)
        - math.tan(ecliptic_latitude) * math.sin(obliquity),
        math.cos(ecliptic_longitude),
    )
    declination = math.asin(
        math.sin(ecliptic_latitude) * math.cos(obliquity)
        + math.cos(ecliptic_latitude) * math.sin(obliquity) * math.sin(ecliptic_longitude)
    )
    return _subpoint(right_ascension, declination, days)
