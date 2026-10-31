"""Texts of the satellite cards and of the notices, taken from locales/es.json (RNF-04, SEC-13)."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Final

from orbita.app.live_view import SatelliteView
from orbita.domain.elements import Freshness, OrbitType

ORBIT_TEXT_KEYS: Final[Mapping[OrbitType, str]] = {
    OrbitType.GEOSTATIONARY: "orbit_geostationary",
    OrbitType.POLAR: "orbit_polar",
    OrbitType.LOW: "orbit_low",
    OrbitType.OTHER: "orbit_other",
}


def card_rows(view: SatelliteView, texts: Mapping[str, str]) -> tuple[tuple[str, str], ...]:
    """Return the label and the value of each line of the card of one satellite (RF-03)."""
    missing = texts["missing_value"]
    distance = (
        missing
        if view.distance_km is None
        else texts["distance_approx"].format(km=view.distance_km)
    )
    launch = missing if view.launch_date is None else view.launch_date.isoformat()
    return (
        (texts["label_altitude"], f"{view.point.altitude_km:.0f} km"),
        (texts["label_speed"], f"{view.speed_km_s:.2f} km/s"),
        (texts["label_orbit_type"], texts[ORBIT_TEXT_KEYS[view.orbit_type]]),
        (texts["label_period"], f"{view.period_minutes} min"),
        (texts["label_distance"], distance),
        (texts["label_country"], country_label(view.owner_code, texts)),
        (texts["label_launch_date"], launch),
        (
            texts["label_years_in_orbit"],
            missing if view.years_in_orbit is None else f"{view.years_in_orbit:.1f}",
        ),
    )


def country_label(owner_code: str | None, texts: Mapping[str, str]) -> str:
    """Translate SATCAT owner code with owner_<CODE> key (DESIGN.md §4.6)."""
    if owner_code is None:
        return texts["missing_value"]
    return texts.get(f"owner_{owner_code}", owner_code)


def freshness_notice(
    freshness: Freshness | None, age_days: int | None, texts: Mapping[str, str]
) -> str | None:
    """Return notice for data age or None if fresh (DESIGN.md §4.2)."""
    if freshness is None:
        return texts["no_orbital_data"]
    if freshness is Freshness.TOO_OLD:
        return texts["too_old_data"]
    if freshness is Freshness.STALE and age_days is not None:
        return texts["stale_data"].format(days=age_days)
    return None
