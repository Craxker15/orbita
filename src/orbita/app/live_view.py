"""Immutable result of one live view refresh, drawn by orbita.ui (ARCHITECTURE.md §3, step 4)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from orbita.domain.elements import Freshness, OrbitType
from orbita.domain.observer import GroundPoint


@dataclass(frozen=True, slots=True)
class SatelliteView:
    """Everything the card and the marker of one satellite need. Built only from domain rules."""

    norad: int
    name: str
    point: GroundPoint
    speed_km_s: float
    orbit_type: OrbitType
    period_minutes: int
    distance_km: int | None
    owner_code: str | None
    launch_date: date | None
    years_in_orbit: float | None


@dataclass(frozen=True, slots=True)
class LiveView:
    """One refresh of the map. freshness is None when there is no saved data at all."""

    freshness: Freshness | None
    downloaded_text: str | None
    age_days: int | None
    satellites: tuple[SatelliteView, ...]
    missing_norad: tuple[int, ...]
    iss_track: tuple[GroundPoint, ...]
