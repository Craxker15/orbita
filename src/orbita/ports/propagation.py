"""Ports for the orbit computation and the current time (ARCHITECTURE.md §4)."""

from __future__ import annotations

from datetime import datetime
from typing import Protocol, runtime_checkable

from orbita.domain.elements import OrbitalElements
from orbita.domain.observer import GroundPoint
from orbita.domain.state import SatelliteState


@runtime_checkable
class OrbitPropagator(Protocol):
    """Computes satellite positions from orbital elements (SGP4, DESIGN.md §6)."""

    def state(self, elements: OrbitalElements, moment: datetime) -> SatelliteState:
        """Return the position and speed of one satellite at one instant.

        Preconditions: elements is valid; moment is timezone-aware UTC.
        Postconditions: the altitude is in km above the spherical Earth model of the adapter.

        Raises:
            PropagationError: if the orbit cannot be computed for that instant.
        """
        ...

    def ground_track(
        self, elements: OrbitalElements, moments: tuple[datetime, ...]
    ) -> tuple[GroundPoint, ...]:
        """Return the sub-satellite point of one satellite at each instant, in the same order.

        Preconditions: moments is a tuple of timezone-aware UTC datetimes.
        Postconditions: the result has the same length as moments.

        Raises:
            PropagationError: if the orbit cannot be computed for one of the instants.
        """
        ...


@runtime_checkable
class Clock(Protocol):
    """Current time, keeping domain and use cases from reading clock (ARCHITECTURE.md §6)."""

    def now(self) -> datetime:
        """Return the current time as a timezone-aware UTC datetime.

        Preconditions: none.
        Postconditions: the result has tzinfo UTC.
        """
        ...
