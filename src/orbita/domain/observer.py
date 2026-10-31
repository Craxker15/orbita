"""Ground points and the observer location (DESIGN.md §4.4 and §4.5)."""

from __future__ import annotations

from dataclasses import dataclass

from orbita.domain.elements import require_in_range
from orbita.domain.errors import DataValidationError, InvalidLocationError

MAX_LATITUDE_DEG = 90.0
MAX_LONGITUDE_DEG = 180.0
MAX_ALTITUDE_KM = 100_000.0


@dataclass(frozen=True, slots=True, repr=False)
class GroundPoint:
    """A point above the Earth, for example a satellite position or a point of its ground track."""

    latitude: float
    longitude: float
    altitude_km: float = 0.0

    def __post_init__(self) -> None:
        """Validate the coordinates and the altitude."""
        require_in_range(self.latitude, -MAX_LATITUDE_DEG, MAX_LATITUDE_DEG, "latitude")
        require_in_range(self.longitude, -MAX_LONGITUDE_DEG, MAX_LONGITUDE_DEG, "longitude")
        require_in_range(self.altitude_km, 0.0, MAX_ALTITUDE_KM, "altitude_km")


@dataclass(frozen=True, slots=True, repr=False)
class Observer:
    """The user's location from the browser. It lives only in memory (SEC-03, DESIGN.md §4.5)."""

    latitude: float
    longitude: float

    def __post_init__(self) -> None:
        """Validate the location. The error text never contains the coordinates."""
        try:
            require_in_range(self.latitude, -MAX_LATITUDE_DEG, MAX_LATITUDE_DEG, "latitude")
            require_in_range(self.longitude, -MAX_LONGITUDE_DEG, MAX_LONGITUDE_DEG, "longitude")
        except DataValidationError as error:
            raise InvalidLocationError(str(error)) from error

    def __repr__(self) -> str:
        """Hide the coordinates so a log line or a traceback never shows them (SEC-03)."""
        return "Observer(<hidden>)"
