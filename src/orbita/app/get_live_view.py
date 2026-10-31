"""Use case: build the live view for one refresh of the map (ARCHITECTURE.md §3, step 4)."""

from __future__ import annotations

import logging
from datetime import date, datetime, timedelta
from typing import Final

from orbita.app.live_view import LiveView, SatelliteView
from orbita.domain.catalog import CatalogEntry
from orbita.domain.catalog_rules import years_in_orbit
from orbita.domain.distance_rules import distance_km_rounded
from orbita.domain.elements import Freshness, OrbitalDataset, OrbitalElements
from orbita.domain.errors import DataValidationError, PropagationError
from orbita.domain.freshness_rules import classify_freshness
from orbita.domain.observer import GroundPoint, Observer
from orbita.domain.orbit_rules import classify_orbit, period_minutes
from orbita.domain.satellites import ISS_NORAD
from orbita.domain.time_rules import format_colombia_time
from orbita.ports.propagation import Clock, OrbitPropagator
from orbita.ports.satellite_data import SatelliteDataStore

logger = logging.getLogger(__name__)

TRACK_MINUTES_BEFORE: Final = 45
TRACK_MINUTES_AFTER: Final = 45


class GetLiveView:
    """Builds the LiveView of one refresh. It never downloads and never writes.

    Preconditions: satellites is the list of DESIGN.md §3.1.
    Postconditions: stale (>14d) empty; no observer = no distance; failed orbits in missing_norad.
    """

    def __init__(
        self,
        store: SatelliteDataStore,
        propagator: OrbitPropagator,
        clock: Clock,
        satellites: frozenset[int],
    ) -> None:
        """Keep the ports and the list of satellites."""
        self._store = store
        self._propagator = propagator
        self._clock = clock
        self._satellites = satellites

    def execute(self, observer: Observer | None) -> LiveView:
        """Return live view for current time; observer used in memory only (SEC-02)."""
        now = self._clock.now()
        dataset = self._load_dataset()
        if dataset is None:
            return LiveView(None, None, None, (), tuple(sorted(self._satellites)), ())
        try:
            freshness = classify_freshness(dataset.downloaded_at, now)
        except DataValidationError:
            logger.warning("live_view_skipped reason=download_in_future")
            return LiveView(None, None, None, (), tuple(sorted(self._satellites)), ())
        downloaded_text = format_colombia_time(dataset.downloaded_at)
        age_days = (now - dataset.downloaded_at).days
        if freshness is Freshness.TOO_OLD:
            return LiveView(freshness, downloaded_text, age_days, (), (), ())
        catalog = self._catalog_by_norad()
        views, missing = self._views(dataset, now, observer, catalog)
        return LiveView(
            freshness, downloaded_text, age_days, views, missing, self._iss_track(dataset, now)
        )

    def _load_dataset(self) -> OrbitalDataset | None:
        """Return the saved elements; an unreadable file counts as no data."""
        try:
            return self._store.load_elements()
        except DataValidationError:
            logger.warning("stored_elements_unreadable")
            return None

    def _catalog_by_norad(self) -> dict[int, CatalogEntry]:
        """Return the saved catalog entries by NORAD number; missing or unreadable means none."""
        try:
            catalog = self._store.load_catalog()
        except DataValidationError:
            logger.warning("stored_catalog_unreadable")
            return {}
        if catalog is None:
            return {}
        return {entry.norad: entry for entry in catalog.entries}

    def _views(
        self,
        dataset: OrbitalDataset,
        now: datetime,
        observer: Observer | None,
        catalog: dict[int, CatalogEntry],
    ) -> tuple[tuple[SatelliteView, ...], tuple[int, ...]]:
        """Build one view per satellite that has data and a computable orbit."""
        by_norad = {item.norad: item for item in dataset.elements}
        views: list[SatelliteView] = []
        missing: list[int] = []
        for norad in sorted(self._satellites):
            element = by_norad.get(norad)
            if element is None:
                missing.append(norad)
                continue
            try:
                views.append(self._view(element, now, observer, catalog.get(norad)))
            except PropagationError:
                logger.warning("propagation_failed norad=%d", norad)
                missing.append(norad)
        return tuple(views), tuple(missing)

    def _view(
        self,
        element: OrbitalElements,
        now: datetime,
        observer: Observer | None,
        entry: CatalogEntry | None,
    ) -> SatelliteView:
        """Build the view of one satellite from the propagator and the domain rules."""
        state = self._propagator.state(element, now)
        distance = None if observer is None else distance_km_rounded(observer, state.point)
        years = (
            None if entry is None or entry.launch_date is None else _years(entry.launch_date, now)
        )
        return SatelliteView(
            norad=element.norad,
            name=element.name,
            point=state.point,
            speed_km_s=state.speed_km_s,
            orbit_type=classify_orbit(element.inclination_deg, element.mean_motion_rev_day),
            period_minutes=period_minutes(element.mean_motion_rev_day),
            distance_km=distance,
            owner_code=None if entry is None else entry.owner_code,
            launch_date=None if entry is None else entry.launch_date,
            years_in_orbit=years,
        )

    def _iss_track(self, dataset: OrbitalDataset, now: datetime) -> tuple[GroundPoint, ...]:
        """Return the ISS ground track from 45 minutes before to 45 minutes after now (RF-02)."""
        iss = next((item for item in dataset.elements if item.norad == ISS_NORAD), None)
        if iss is None:
            return ()
        moments = tuple(
            now + timedelta(minutes=minute)
            for minute in range(-TRACK_MINUTES_BEFORE, TRACK_MINUTES_AFTER + 1)
        )
        try:
            return self._propagator.ground_track(iss, moments)
        except PropagationError:
            logger.warning("track_failed norad=%d", ISS_NORAD)
            return ()


def _years(launch_date: date, now: datetime) -> float | None:
    """Return the years in orbit, or None when the launch date is not valid for today."""
    try:
        return years_in_orbit(launch_date, now.date())
    except DataValidationError:
        logger.warning("years_in_orbit_invalid")
        return None
