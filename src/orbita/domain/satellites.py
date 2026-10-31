"""The 10 satellites tracked by Órbita (DESIGN.md §3.1)."""

from __future__ import annotations

from typing import Final

ISS_NORAD: Final = 25544  # International Space Station (for reference)

SATELLITES: Final = frozenset(
    {
        40930,  # AstroSat
        33591,  # NOAA 19
        56205,  # FACSAT-2
        43010,  # FENGYUN 3D
        40069,  # METEOR-M 2
        44804,  # CARTOSAT-3
        41836,  # HIMAWARI-9
        40732,  # METEOSAT-11
        43873,  # GPS III SV01
        40128,  # GALILEO 5
    }
)
