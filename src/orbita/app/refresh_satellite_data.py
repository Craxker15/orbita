"""Download orbital elements and SATCAT catalog on schedule (DESIGN.md §4.2)."""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass
from datetime import datetime

from orbita.domain.catalog import Catalog, CatalogEntry
from orbita.domain.download_rules import (
    CATALOG_DOWNLOAD_INTERVAL,
    ELEMENTS_DOWNLOAD_INTERVAL,
    is_download_due,
)
from orbita.domain.elements import OrbitalDataset, OrbitalElements
from orbita.domain.errors import DataValidationError, DownloadError
from orbita.domain.state import DownloadAttempts
from orbita.domain.validation import (
    mean_motion_change_is_plausible,
    parse_catalog_payload,
    parse_elements_payload,
    parse_json_text,
)
from orbita.ports.propagation import Clock
from orbita.ports.satellite_data import SatelliteDataSource, SatelliteDataStore

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class RefreshReport:
    """What one refresh did. Failed satellites keep their previous data (RF-07)."""

    elements_attempted: bool
    catalog_attempted: bool
    elements_updated: tuple[int, ...]
    catalog_updated: tuple[int, ...]
    failed_norad: tuple[int, ...]


NOTHING_DONE = RefreshReport(False, False, (), (), ())


class RefreshSatelliteData:
    """Refreshes the saved data for the satellites of the list, respecting the download intervals.

    Preconditions: satellites is the list of DESIGN.md §3.1.
    Postconditions: attempts saved; dataset saved if any satellite accepted (ADR-003).
    """

    def __init__(
        self,
        source: SatelliteDataSource,
        store: SatelliteDataStore,
        clock: Clock,
        satellites: frozenset[int],
    ) -> None:
        """Keep ports, satellite list; create lock for exclusive runs (SEC-31)."""
        self._source = source
        self._store = store
        self._clock = clock
        self._satellites = satellites
        self._run_lock = threading.Lock()

    def execute(self) -> RefreshReport:
        """Refresh what is due. A run already in progress (another session) is skipped, not queued.

        Raises: nothing. Every error is logged and reported in the RefreshReport.
        """
        if not self._run_lock.acquire(blocking=False):
            logger.info("refresh_skipped reason=already_running")
            return NOTHING_DONE
        try:
            return self._run(self._clock.now())
        except DataValidationError:
            logger.warning("refresh_skipped reason=invalid_attempt_times")
            return NOTHING_DONE
        finally:
            self._run_lock.release()

    def _run(self, now: datetime) -> RefreshReport:
        """Decide what is due and refresh it."""
        attempts = self._store.load_attempts()
        elements_due = is_download_due(attempts.elements, now, ELEMENTS_DOWNLOAD_INTERVAL)
        catalog_due = is_download_due(attempts.catalog, now, CATALOG_DOWNLOAD_INTERVAL)
        elements_time = now if elements_due else attempts.elements
        if elements_due:
            self._store.save_attempts(DownloadAttempts(elements=now, catalog=attempts.catalog))
        elements_updated, failed = self._refresh_elements(now) if elements_due else ((), ())
        catalog_updated: tuple[int, ...] = ()
        if catalog_due:
            self._store.save_attempts(DownloadAttempts(elements=elements_time, catalog=now))
            catalog_updated = self._refresh_catalog(now)
        return RefreshReport(
            elements_attempted=elements_due,
            catalog_attempted=catalog_due,
            elements_updated=elements_updated,
            catalog_updated=catalog_updated,
            failed_norad=failed,
        )

    def _refresh_elements(self, now: datetime) -> tuple[tuple[int, ...], tuple[int, ...]]:
        """Download every satellite once; merge the accepted ones with the saved ones."""
        previous = self._previous_elements()
        accepted: dict[int, OrbitalElements] = {}
        failed: list[int] = []
        for norad in sorted(self._satellites):
            element = self._download_element(norad, previous.get(norad), now)
            if element is None:
                failed.append(norad)
            else:
                accepted[norad] = element
        if accepted:
            merged = {**previous, **accepted}
            self._store.save_elements(
                OrbitalDataset(
                    downloaded_at=now,
                    elements=tuple(merged[norad] for norad in sorted(merged)),
                )
            )
        return tuple(sorted(accepted)), tuple(failed)

    def _download_element(
        self, norad: int, previous: OrbitalElements | None, now: datetime
    ) -> OrbitalElements | None:
        """Return validated element or None to keep old value."""
        try:
            text = self._source.download_elements(norad)
            parsed = parse_elements_payload(parse_json_text(text), self._satellites, now)
        except DownloadError as error:
            logger.warning("elements_failed norad=%d error=%s", norad, type(error).__name__)
            return None
        except DataValidationError:
            logger.warning("elements_rejected norad=%d", norad)
            return None
        candidates = [item for item in parsed.accepted if item.norad == norad]
        if not candidates:
            logger.warning("elements_rejected norad=%d", norad)
            return None
        element = candidates[0]
        if not mean_motion_change_is_plausible(previous, element):
            logger.warning("elements_implausible norad=%d", norad)
            return None
        return element

    def _refresh_catalog(self, now: datetime) -> tuple[int, ...]:
        """Download SATCAT records; merge accepted ones with saved."""
        previous = self._previous_catalog()
        accepted: dict[int, CatalogEntry] = {}
        for norad in sorted(self._satellites):
            accepted.update(self._download_entry(norad, now))
        if accepted:
            merged = {**previous, **accepted}
            self._store.save_catalog(
                Catalog(
                    downloaded_at=now,
                    entries=tuple(merged[norad] for norad in sorted(merged)),
                )
            )
        return tuple(sorted(accepted))

    def _download_entry(self, norad: int, now: datetime) -> dict[int, CatalogEntry]:
        """Return the validated catalog entry of one satellite, or an empty mapping on failure."""
        try:
            text = self._source.download_catalog(norad)
            parsed = parse_catalog_payload(parse_json_text(text), self._satellites, now)
        except DownloadError as error:
            logger.warning("catalog_failed norad=%d error=%s", norad, type(error).__name__)
            return {}
        except DataValidationError:
            logger.warning("catalog_rejected norad=%d", norad)
            return {}
        return {item.norad: item for item in parsed.accepted if item.norad == norad}

    def _previous_elements(self) -> dict[int, OrbitalElements]:
        """Return the saved elements by NORAD number; an unreadable file counts as no data."""
        try:
            dataset = self._store.load_elements()
        except DataValidationError:
            logger.warning("stored_elements_unreadable")
            return {}
        if dataset is None:
            return {}
        return {item.norad: item for item in dataset.elements}

    def _previous_catalog(self) -> dict[int, CatalogEntry]:
        """Return saved catalog entries by NORAD; unreadable file = no data."""
        try:
            catalog = self._store.load_catalog()
        except DataValidationError:
            logger.warning("stored_catalog_unreadable")
            return {}
        if catalog is None:
            return {}
        return {entry.norad: entry for entry in catalog.entries}
