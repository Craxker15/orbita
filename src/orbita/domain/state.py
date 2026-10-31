"""Satellite state and times of last download attempts (ARCHITECTURE.md §2)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from orbita.domain.elements import require_in_range, require_utc
from orbita.domain.errors import DataValidationError
from orbita.domain.observer import GroundPoint

MAX_SPEED_KM_S = 20.0


@dataclass(frozen=True, slots=True)
class SatelliteState:
    """Where a satellite is and how fast it moves at one instant (DESIGN.md §3.2, RF-01)."""

    norad: int
    point: GroundPoint
    speed_km_s: float

    def __post_init__(self) -> None:
        """Validate the NORAD number and the speed."""
        if isinstance(self.norad, bool) or not isinstance(self.norad, int) or self.norad <= 0:
            raise DataValidationError("norad must be a positive integer")
        require_in_range(self.speed_km_s, 0.0, MAX_SPEED_KM_S, "speed_km_s")


@dataclass(frozen=True, slots=True)
class DownloadAttempts:
    """Last download attempt time of each kind (DESIGN.md §4.2, ADR-003)."""

    elements: datetime | None = None
    catalog: datetime | None = None

    def __post_init__(self) -> None:
        """Require timezone-aware UTC times when they are present."""
        if self.elements is not None:
            require_utc(self.elements, "elements")
        if self.catalog is not None:
            require_utc(self.catalog, "catalog")
