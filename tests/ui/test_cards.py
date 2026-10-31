"""Card and notice text tests (spec 015)."""

from __future__ import annotations

from datetime import date

from orbita.app.live_view import SatelliteView
from orbita.domain.elements import Freshness, OrbitType
from orbita.domain.observer import GroundPoint
from orbita.ui.cards import card_rows, country_label, freshness_notice

TEXTS = {
    "missing_value": "—",
    "distance_approx": "≈ {km} km",
    "label_altitude": "Altura",
    "label_speed": "Velocidad",
    "label_orbit_type": "Tipo de órbita",
    "label_period": "Periodo",
    "label_distance": "Distancia a ti",
    "label_country": "País",
    "label_launch_date": "Fecha de lanzamiento",
    "label_years_in_orbit": "Años en órbita",
    "orbit_geostationary": "Geoestacionaria",
    "orbit_polar": "Polar",
    "orbit_low": "Baja",
    "orbit_other": "Otra",
    "owner_US": "Estados Unidos",
    "no_orbital_data": "No hay datos orbitales guardados.",
    "too_old_data": "Los datos tienen más de 14 días.",
    "stale_data": "Datos de hace {days} días.",
}


def satellite(distance: int | None = None, owner: str | None = None) -> SatelliteView:
    return SatelliteView(
        norad=25544,
        name="ISS (ZARYA)",
        point=GroundPoint(latitude=10.0, longitude=-75.0, altitude_km=420.4),
        speed_km_s=7.664,
        orbit_type=OrbitType.LOW,
        period_minutes=93,
        distance_km=distance,
        owner_code=owner,
        launch_date=date(1998, 11, 20) if owner else None,
    )


def test_altitude_has_no_decimals_and_speed_has_two() -> None:
    rows = dict(card_rows(satellite(), TEXTS))
    assert rows["Altura"] == "420 km"
    assert rows["Velocidad"] == "7.66 km/s"


def test_distance_row_shows_approximation_sign_when_known() -> None:
    assert dict(card_rows(satellite(distance=400), TEXTS))["Distancia a ti"] == "≈ 400 km"


def test_distance_row_shows_missing_value_without_location() -> None:
    assert dict(card_rows(satellite(), TEXTS))["Distancia a ti"] == "—"


def test_known_owner_code_is_translated_and_unknown_is_kept() -> None:
    assert country_label("US", TEXTS) == "Estados Unidos"
    assert country_label("XYZ", TEXTS) == "XYZ"
    assert country_label(None, TEXTS) == "—"


def test_orbit_type_uses_the_spanish_text() -> None:
    assert dict(card_rows(satellite(), TEXTS))["Tipo de órbita"] == "Baja"


def test_no_notice_for_normal_data() -> None:
    assert freshness_notice(Freshness.NORMAL, 0, TEXTS) is None


def test_stale_notice_shows_the_age_in_days() -> None:
    assert freshness_notice(Freshness.STALE, 4, TEXTS) == "Datos de hace 4 días."


def test_too_old_and_missing_data_have_their_own_notices() -> None:
    assert freshness_notice(Freshness.TOO_OLD, 15, TEXTS) == "Los datos tienen más de 14 días."
    assert freshness_notice(None, None, TEXTS) == "No hay datos orbitales guardados."
