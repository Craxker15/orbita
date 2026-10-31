"""The 20 satellites of Orbita (DESIGN.md §3.1). Numbers are fixed by spec 010."""

from __future__ import annotations

from dataclasses import dataclass

from orbita.domain.errors import DataValidationError

MAX_SATELLITE_NAME_LENGTH = 80
ISS_NORAD = 25544
EXPECTED_SATELLITE_COUNT = 20


@dataclass(frozen=True, slots=True)
class SatelliteSpec:
    """A satellite of the list: its NORAD catalog number and the name shown to the user."""

    norad: int
    name: str


SATELLITES: tuple[SatelliteSpec, ...] = (
    SatelliteSpec(25544, "ISS (ZARYA)"),
    SatelliteSpec(48274, "Tiangong (Tianhe)"),
    SatelliteSpec(20580, "Hubble"),
    SatelliteSpec(40930, "AstroSat"),
    SatelliteSpec(33591, "NOAA 19"),
    SatelliteSpec(56205, "FACSAT-2"),
    SatelliteSpec(43013, "NOAA 20"),
    SatelliteSpec(25994, "Terra"),
    SatelliteSpec(49260, "Landsat 9"),
    SatelliteSpec(39634, "Sentinel-1A"),
    SatelliteSpec(40697, "Sentinel-2A"),
    SatelliteSpec(27386, "Envisat"),
    SatelliteSpec(43010, "FENGYUN 3D"),
    SatelliteSpec(40069, "METEOR-M 2"),
    SatelliteSpec(44804, "CARTOSAT-3"),
    SatelliteSpec(60133, "GOES 19"),
    SatelliteSpec(41836, "HIMAWARI-9"),
    SatelliteSpec(40732, "METEOSAT-11"),
    SatelliteSpec(43873, "GPS III SV01"),
    SatelliteSpec(40128, "GALILEO 5"),
)

SATELLITE_NORADS: frozenset[int] = frozenset(satellite.norad for satellite in SATELLITES)


def check_satellite_list(satellites: tuple[SatelliteSpec, ...]) -> None:
    """Raise DataValidationError unless the list has 20 unique NORAD numbers and unique names."""
    if len(satellites) != EXPECTED_SATELLITE_COUNT:
        raise DataValidationError("the satellite list must contain exactly 20 satellites")
    norads = [satellite.norad for satellite in satellites]
    names = [satellite.name for satellite in satellites]
    if len(set(norads)) != len(norads) or any(norad <= 0 for norad in norads):
        raise DataValidationError("every satellite needs a unique positive NORAD number")
    if len(set(names)) != len(names) or any(
        not name or len(name) > MAX_SATELLITE_NAME_LENGTH for name in names
    ):
        raise DataValidationError("every satellite needs a unique name of at most 80 characters")
