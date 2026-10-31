"""Skyfield adapter: satellite positions computed locally with SGP4 (DESIGN.md §6, SEC-17)."""

from __future__ import annotations

import math
import threading
from datetime import datetime
from typing import Any, Final

from skyfield.api import EarthSatellite, load, wgs84  # type: ignore[import-untyped]

from orbita.domain.elements import OrbitalElements
from orbita.domain.errors import DataValidationError, PropagationError
from orbita.domain.observer import GroundPoint
from orbita.domain.state import SatelliteState

TRACK_ALTITUDE_KM: Final = 0.0


class SkyfieldPropagator:
    """Computes positions with Skyfield's SGP4 model.

    Preconditions: elements are valid OrbitalElements; moments are timezone-aware UTC datetimes.
    Postconditions: the altitude is measured above the spherical Earth of wgs84.subpoint.
    """

    def __init__(self) -> None:
        """Load the time scale from Skyfield's built-in data, so no file is downloaded (SEC-17)."""
        self._timescale: Any = load.timescale(builtin=True)
        self._lock = threading.Lock()
        self._satellites: dict[int, tuple[OrbitalElements, Any]] = {}

    def state(self, elements: OrbitalElements, moment: datetime) -> SatelliteState:
        """Return the position and the speed of one satellite at one instant (OrbitPropagator).

        Raises:
            PropagationError: if orbit cannot be computed (e.g., re-entry).
        """
        satellite = self._satellite_for(elements)
        try:
            geocentric = satellite.at(self._timescale.from_datetime(moment))
            subpoint = wgs84.subpoint(geocentric)
            point = GroundPoint(
                latitude=float(subpoint.latitude.degrees),
                longitude=float(subpoint.longitude.degrees),
                altitude_km=float(subpoint.elevation.km),
            )
            velocity = [float(component) for component in geocentric.velocity.km_per_s]
        except (ValueError, ArithmeticError, DataValidationError) as error:
            raise PropagationError(
                f"the orbit of NORAD {elements.norad} cannot be computed"
            ) from error
        speed = math.sqrt(sum(component * component for component in velocity))
        return SatelliteState(norad=elements.norad, point=point, speed_km_s=speed)

    def ground_track(
        self, elements: OrbitalElements, moments: tuple[datetime, ...]
    ) -> tuple[GroundPoint, ...]:
        """Return the point under the satellite at each moment, at altitude zero (OrbitPropagator).

        Raises:
            PropagationError: if the orbit cannot be computed for one of the moments.
        """
        satellite = self._satellite_for(elements)
        track: list[GroundPoint] = []
        for moment in moments:
            try:
                subpoint = wgs84.subpoint(satellite.at(self._timescale.from_datetime(moment)))
                track.append(
                    GroundPoint(
                        latitude=float(subpoint.latitude.degrees),
                        longitude=float(subpoint.longitude.degrees),
                        altitude_km=TRACK_ALTITUDE_KM,
                    )
                )
            except (ValueError, ArithmeticError) as error:
                raise PropagationError(
                    f"the ground track of NORAD {elements.norad} cannot be computed"
                ) from error
        return tuple(track)

    def _satellite_for(self, elements: OrbitalElements) -> Any:
        """Return Skyfield satellite, cached per element change (ARCHITECTURE.md §6)."""
        with self._lock:
            cached = self._satellites.get(elements.norad)
            if cached is not None and cached[0] == elements:
                return cached[1]
            try:
                satellite = EarthSatellite.from_omm(self._timescale, _omm_fields(elements))
            except (ValueError, KeyError, TypeError) as error:
                raise PropagationError(
                    f"the elements of NORAD {elements.norad} cannot be used"
                ) from error
            self._satellites[elements.norad] = (elements, satellite)
            return satellite


def _omm_fields(elements: OrbitalElements) -> dict[str, object]:
    """Map the domain elements to the OMM field names that Skyfield's from_omm expects."""
    return {
        "OBJECT_NAME": elements.name,
        # sgp4 reads OBJECT_ID only for the international designator, which positions do not use.
        "OBJECT_ID": "",
        "NORAD_CAT_ID": elements.norad,
        "EPOCH": elements.epoch.replace(tzinfo=None).isoformat(timespec="microseconds"),
        "MEAN_MOTION": elements.mean_motion_rev_day,
        "ECCENTRICITY": elements.eccentricity,
        "INCLINATION": elements.inclination_deg,
        "RA_OF_ASC_NODE": elements.raan_deg,
        "ARG_OF_PERICENTER": elements.arg_perigee_deg,
        "MEAN_ANOMALY": elements.mean_anomaly_deg,
        "MEAN_MOTION_DOT": elements.mean_motion_dot,
        "MEAN_MOTION_DDOT": elements.mean_motion_ddot,
        "BSTAR": elements.bstar,
        "EPHEMERIS_TYPE": 0,
        "CLASSIFICATION_TYPE": "U",
        "ELEMENT_SET_NO": 999,
        "REV_AT_EPOCH": 0,
    }
