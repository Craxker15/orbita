"""Orbital elements, the downloaded dataset, and the orbit and freshness classifications."""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum

from orbita.domain.errors import DataValidationError

MAX_NAME_LENGTH = 80
MAX_INCLINATION_DEG = 180.0
MAX_ANGLE_DEG = 360.0
MAX_MEAN_MOTION_REV_DAY = 20.0
MAX_ECCENTRICITY = 1.0


class OrbitType(StrEnum):
    """Orbit type of DESIGN.md §4.1. The rule that chooses it is in spec 004."""

    GEOSTATIONARY = "geostationary"
    POLAR = "polar"
    LOW = "low"
    OTHER = "other"


class Freshness(StrEnum):
    """Freshness of the orbital elements, DESIGN.md §4.2. The rule is in spec 005."""

    NORMAL = "normal"
    STALE = "stale"
    TOO_OLD = "too_old"


def require_utc(value: datetime, field: str) -> None:
    """Raise DataValidationError unless the datetime is timezone-aware and in UTC."""
    if value.utcoffset() != timedelta(0):
        raise DataValidationError(f"{field} must be a timezone-aware UTC datetime")


def require_finite(value: float, field: str) -> None:
    """Raise DataValidationError unless the value is a finite number."""
    if not math.isfinite(value):
        raise DataValidationError(f"{field} must be a finite number")


def require_in_range(
    value: float,
    low: float,
    high: float,
    field: str,
    *,
    low_inclusive: bool = True,
    high_inclusive: bool = True,
) -> None:
    """Raise DataValidationError unless value is a finite number inside the range."""
    require_finite(value, field)
    above = value >= low if low_inclusive else value > low
    below = value <= high if high_inclusive else value < high
    if not (above and below):
        raise DataValidationError(f"{field} must be between {low} and {high}")


@dataclass(frozen=True, slots=True)
class OrbitalElements:
    """Orbital elements of one satellite, as CelesTrak publishes them (OMM fields for SGP4)."""

    norad: int
    name: str
    inclination_deg: float
    mean_motion_rev_day: float
    eccentricity: float
    epoch: datetime
    raan_deg: float
    arg_perigee_deg: float
    mean_anomaly_deg: float
    mean_motion_dot: float
    mean_motion_ddot: float
    bstar: float

    def __post_init__(self) -> None:
        """Validate every field with the ranges of SEC-10."""
        if isinstance(self.norad, bool) or not isinstance(self.norad, int) or self.norad <= 0:
            raise DataValidationError("norad must be a positive integer")
        if not isinstance(self.name, str) or not self.name.strip():
            raise DataValidationError("name must not be empty")
        if len(self.name) > MAX_NAME_LENGTH:
            raise DataValidationError(f"name must have at most {MAX_NAME_LENGTH} characters")
        require_in_range(self.inclination_deg, 0.0, MAX_INCLINATION_DEG, "inclination_deg")
        require_in_range(
            self.mean_motion_rev_day,
            0.0,
            MAX_MEAN_MOTION_REV_DAY,
            "mean_motion_rev_day",
            low_inclusive=False,
        )
        require_in_range(
            self.eccentricity, 0.0, MAX_ECCENTRICITY, "eccentricity", high_inclusive=False
        )
        require_in_range(self.raan_deg, 0.0, MAX_ANGLE_DEG, "raan_deg", high_inclusive=False)
        require_in_range(
            self.arg_perigee_deg, 0.0, MAX_ANGLE_DEG, "arg_perigee_deg", high_inclusive=False
        )
        require_in_range(
            self.mean_anomaly_deg, 0.0, MAX_ANGLE_DEG, "mean_anomaly_deg", high_inclusive=False
        )
        require_finite(self.mean_motion_dot, "mean_motion_dot")
        require_finite(self.mean_motion_ddot, "mean_motion_ddot")
        require_finite(self.bstar, "bstar")
        require_utc(self.epoch, "epoch")


@dataclass(frozen=True, slots=True)
class OrbitalDataset:
    """All the orbital elements saved by one successful download."""

    downloaded_at: datetime
    elements: tuple[OrbitalElements, ...]

    def __post_init__(self) -> None:
        """Validate the download time and reject a NORAD number that appears twice."""
        require_utc(self.downloaded_at, "downloaded_at")
        if not isinstance(self.elements, tuple):
            raise DataValidationError("elements must be a tuple")
        norads = [item.norad for item in self.elements]
        if len(set(norads)) != len(norads):
            raise DataValidationError("a NORAD number appears more than once in the dataset")
