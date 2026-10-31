# 014 - Casos de uso `RefreshSatelliteData` y `GetLiveView`

## Objetivo

Al terminar, la aplicación tiene los dos casos de uso que unen las reglas del dominio con los puertos:

- `RefreshSatelliteData` descarga los elementos orbitales y el catálogo cuando su intervalo lo permite (contado desde el
  último intento, correcto o fallido), valida cada respuesta, conserva el dato anterior si la nueva falla y guarda solo lo
  válido.
- `GetLiveView` arma, en cada refresco de un segundo, la vista inmutable que dibuja la interfaz: posiciones, distancias
  (si hay ubicación), tipos de órbita, periodos, la trayectoria de la ISS y los satélites sin datos.

Ninguno de los dos lee el reloj del sistema, ni la red, ni el disco directamente: reciben puertos por el constructor
(ARCHITECTURE.md §6).

## Depende de

- 004 (orbit_rules, time_rules), 005 (freshness_rules, download_rules), 006 (distance_rules), 007 (validación),
  008 (puertos), 010 (`ISS_NORAD` y la lista de satélites).

## Archivos rectores aplicables

- `ARCHITECTURE.md` §3 (flujo principal, pasos 2 y 4), §2 (la capa `app` solo depende de dominio y puertos), §6 (sin
  singletons, sin estado global; `Lock` para el estado compartido).
- `DESIGN.md` §4.2 (intervalos desde el último intento; la frescura desde la última descarga correcta), §4.4 (la
  distancia solo con ubicación válida), §4.6 (datos del catálogo).
- `security-rules.md` SEC-02 (la ubicación entra como argumento y no se guarda), SEC-16 (sin reintentos), SEC-30 (en el
  log solo NORAD, conteos y tipos de error), SEC-31 (los intervalos son globales a todas las sesiones).
- `docs/00-requirements.es.md` RF-04, RF-05, RF-06, RF-07, RF-11, RF-13, RF-14.

## Archivos a crear

1. `src/orbita/app/live_view.py`
2. `src/orbita/app/refresh_satellite_data.py`
3. `src/orbita/app/get_live_view.py`
4. `tests/app/test_use_cases.py`

Son cuatro archivos en la capa `app` y su test.

## Dependencias externas

Ninguna.

## Contenido exacto de los archivos

### `src/orbita/app/live_view.py`

```python
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


@dataclass(frozen=True, slots=True)
class LiveView:
    """One refresh of the map. freshness is None when there is no saved data at all."""

    freshness: Freshness | None
    downloaded_text: str | None
    age_days: int | None
    satellites: tuple[SatelliteView, ...]
    missing_norad: tuple[int, ...]
    iss_track: tuple[GroundPoint, ...]
```

### `src/orbita/app/refresh_satellite_data.py`

```python
"""Use case: download the orbital elements and the SATCAT catalog when their intervals allow it (DESIGN.md §4.2)."""

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
    Postconditions: the attempt time is saved before any request, so a failed attempt also counts (ADR-003); the
        dataset is saved only when at least one satellite was accepted.
    """

    def __init__(
        self,
        source: SatelliteDataSource,
        store: SatelliteDataStore,
        clock: Clock,
        satellites: frozenset[int],
    ) -> None:
        """Keep the ports and the list of satellites; create the lock that makes runs exclusive (SEC-31)."""
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
        """Return the validated element of one satellite, or None when it must keep its old value."""
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
        """Download the SATCAT record of every satellite; merge the accepted ones with the saved ones."""
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
        """Return the saved catalog entries by NORAD number; an unreadable file counts as no data."""
        try:
            catalog = self._store.load_catalog()
        except DataValidationError:
            logger.warning("stored_catalog_unreadable")
            return {}
        if catalog is None:
            return {}
        return {entry.norad: entry for entry in catalog.entries}
```

### `src/orbita/app/get_live_view.py`

```python
"""Use case: build the live view for one refresh of the map (ARCHITECTURE.md §3, step 4)."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Final

from orbita.app.live_view import LiveView, SatelliteView
from orbita.domain.catalog import CatalogEntry
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
    Postconditions: positions are empty when the data is older than 14 days (RF-06); distances are None without an
        observer; a satellite without data or whose orbit fails is listed in missing_norad, never silently dropped.
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
        """Return the live view for the current time. The observer is used in memory only (SEC-02)."""
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
```

### `tests/app/test_use_cases.py`

```python
"""Tests of the two use cases with in-memory fakes of the ports: no network, no disk (spec 014)."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest

from orbita.app.get_live_view import GetLiveView
from orbita.app.refresh_satellite_data import RefreshSatelliteData
from orbita.domain.catalog import Catalog, CatalogEntry
from orbita.domain.elements import Freshness, OrbitalDataset, OrbitalElements
from orbita.domain.errors import DownloadError, PropagationError
from orbita.domain.observer import GroundPoint, Observer
from orbita.domain.state import DownloadAttempts, SatelliteState

NOW = datetime(2026, 10, 30, 12, 0, tzinfo=UTC)
SATS = frozenset({25544, 20580})


class FakeClock:
    def __init__(self, now: datetime) -> None:
        self.current = now

    def now(self) -> datetime:
        return self.current


class FakeSource:
    def __init__(
        self,
        elements: dict[int, str | Exception] | None = None,
        catalog: dict[int, str | Exception] | None = None,
        events: list[str] | None = None,
    ) -> None:
        self.elements = elements or {}
        self.catalog = catalog or {}
        self.calls: list[tuple[str, int]] = []
        self.events = events if events is not None else []

    def download_elements(self, norad: int) -> str:
        self.calls.append(("elements", norad))
        self.events.append("download")
        return _answer(self.elements, norad)

    def download_catalog(self, norad: int) -> str:
        self.calls.append(("catalog", norad))
        self.events.append("download")
        return _answer(self.catalog, norad)


def _answer(table: dict[int, str | Exception], norad: int) -> str:
    value = table.get(norad, DownloadError("no answer configured"))
    if isinstance(value, Exception):
        raise value
    return value


class FakeStore:
    def __init__(
        self,
        dataset: OrbitalDataset | None = None,
        catalog: Catalog | None = None,
        attempts: DownloadAttempts | None = None,
        events: list[str] | None = None,
    ) -> None:
        self.dataset = dataset
        self.catalog_data = catalog
        self.attempts = attempts or DownloadAttempts()
        self.events = events if events is not None else []

    def load_elements(self) -> OrbitalDataset | None:
        return self.dataset

    def save_elements(self, dataset: OrbitalDataset) -> None:
        self.dataset = dataset
        self.events.append("save_elements")

    def load_catalog(self) -> Catalog | None:
        return self.catalog_data

    def save_catalog(self, catalog: Catalog) -> None:
        self.catalog_data = catalog
        self.events.append("save_catalog")

    def load_attempts(self) -> DownloadAttempts:
        return self.attempts

    def save_attempts(self, attempts: DownloadAttempts) -> None:
        self.attempts = attempts
        self.events.append("attempt")


class FakePropagator:
    def __init__(self, failing: frozenset[int] = frozenset()) -> None:
        self.failing = failing

    def state(self, elements: OrbitalElements, moment: datetime) -> SatelliteState:
        if elements.norad in self.failing:
            raise PropagationError("orbit cannot be computed")
        return SatelliteState(
            norad=elements.norad, point=GroundPoint(0.0, 0.0, 400.0), speed_km_s=7.66
        )

    def ground_track(
        self, elements: OrbitalElements, moments: tuple[datetime, ...]
    ) -> tuple[GroundPoint, ...]:
        return tuple(GroundPoint(0.0, 0.0) for _ in moments)


def make_element(
    norad: int = 25544, mean_motion: float = 15.5, downloaded: datetime = NOW
) -> OrbitalElements:
    return OrbitalElements(
        norad=norad,
        name=f"SAT {norad}",
        inclination_deg=51.6,
        mean_motion_rev_day=mean_motion,
        eccentricity=0.0005,
        epoch=downloaded,
        raan_deg=0.0,
        arg_perigee_deg=0.0,
        mean_anomaly_deg=0.0,
        mean_motion_dot=0.0,
        mean_motion_ddot=0.0,
        bstar=0.0,
    )


def element_text(norad: int, mean_motion: float = 15.5) -> str:
    record: dict[str, Any] = {
        "NORAD_CAT_ID": norad,
        "OBJECT_NAME": f"SAT {norad}",
        "EPOCH": "2026-10-30T11:00:00",
        "INCLINATION": 51.6,
        "MEAN_MOTION": mean_motion,
        "ECCENTRICITY": 0.0005,
        "RA_OF_ASC_NODE": 0.0,
        "ARG_OF_PERICENTER": 0.0,
        "MEAN_ANOMALY": 0.0,
        "MEAN_MOTION_DOT": 0.0,
        "MEAN_MOTION_DDOT": 0.0,
        "BSTAR": 0.0,
    }
    return json.dumps([record])


def catalog_text(norad: int) -> str:
    return json.dumps([{"NORAD_CAT_ID": norad, "OWNER": "US", "LAUNCH_DATE": "2016-10-30"}])


def refresh(source: FakeSource, store: FakeStore, now: datetime = NOW) -> Any:
    return RefreshSatelliteData(source, store, FakeClock(now), SATS).execute()


def test_first_run_downloads_elements_and_catalog() -> None:
    source = FakeSource(
        elements={25544: element_text(25544), 20580: element_text(20580)},
        catalog={25544: catalog_text(25544), 20580: catalog_text(20580)},
    )
    store = FakeStore()
    report = refresh(source, store)
    assert report.elements_updated == (20580, 25544)
    assert report.catalog_updated == (20580, 25544)
    assert store.dataset is not None and store.dataset.downloaded_at == NOW


def test_attempt_time_is_saved_before_the_first_request() -> None:
    events: list[str] = []
    source = FakeSource(elements={25544: element_text(25544)}, events=events)
    refresh(source, FakeStore(events=events))
    assert events[0] == "attempt"
    assert events[1] == "download"


def test_no_download_within_two_hours() -> None:
    source = FakeSource()
    store = FakeStore(attempts=DownloadAttempts(elements=NOW - timedelta(minutes=119), catalog=NOW))
    refresh(source, store)
    assert source.calls == []


def test_elements_are_due_after_two_hours() -> None:
    source = FakeSource(elements={25544: element_text(25544), 20580: element_text(20580)})
    store = FakeStore(attempts=DownloadAttempts(elements=NOW - timedelta(hours=2), catalog=NOW))
    refresh(source, store)
    assert sorted(call for call in source.calls if call[0] == "elements") == [
        ("elements", 20580),
        ("elements", 25544),
    ]


def test_failed_download_is_not_retried() -> None:
    source = FakeSource(
        elements={25544: DownloadError("403"), 20580: element_text(20580)},
        catalog={},
    )
    store = FakeStore(attempts=DownloadAttempts(catalog=NOW))
    report = refresh(source, store)
    assert report.failed_norad == (25544,)
    assert source.calls.count(("elements", 25544)) == 1


def test_invalid_payload_keeps_the_previous_dataset() -> None:
    previous = OrbitalDataset(
        downloaded_at=NOW - timedelta(days=1), elements=(make_element(25544),)
    )
    store = FakeStore(dataset=previous, attempts=DownloadAttempts(catalog=NOW))
    refresh(FakeSource(elements={25544: "[NaN]", 20580: DownloadError("x")}), store)
    assert store.dataset is previous


def test_mean_motion_change_over_5_percent_is_rejected() -> None:
    previous = OrbitalDataset(
        downloaded_at=NOW - timedelta(days=1), elements=(make_element(25544),)
    )
    store = FakeStore(dataset=previous, attempts=DownloadAttempts(catalog=NOW))
    refresh(
        FakeSource(
            elements={25544: element_text(25544, mean_motion=16.43), 20580: DownloadError("x")}
        ),
        store,
    )
    assert store.dataset is previous


def test_satellite_missing_from_the_new_download_keeps_its_old_value() -> None:
    previous = OrbitalDataset(
        downloaded_at=NOW - timedelta(days=1),
        elements=(make_element(20580), make_element(25544)),
    )
    store = FakeStore(dataset=previous, attempts=DownloadAttempts(catalog=NOW))
    refresh(FakeSource(elements={25544: element_text(25544), 20580: DownloadError("down")}), store)
    assert store.dataset is not None
    assert sorted(item.norad for item in store.dataset.elements) == [20580, 25544]
    assert store.dataset.downloaded_at == NOW


def test_catalog_is_due_after_24_hours_only() -> None:
    source = FakeSource(catalog={25544: catalog_text(25544), 20580: catalog_text(20580)})
    too_early = FakeStore(
        attempts=DownloadAttempts(elements=NOW, catalog=NOW - timedelta(hours=23, minutes=59))
    )
    refresh(source, too_early)
    assert all(call[0] != "catalog" for call in source.calls)
    on_time = FakeStore(attempts=DownloadAttempts(elements=NOW, catalog=NOW - timedelta(hours=24)))
    refresh(source, on_time)
    assert any(call[0] == "catalog" for call in source.calls)


def test_run_while_another_is_in_progress_is_skipped() -> None:
    use_case = RefreshSatelliteData(FakeSource(), FakeStore(), FakeClock(NOW), SATS)
    use_case._run_lock.acquire()
    try:
        report = use_case.execute()
    finally:
        use_case._run_lock.release()
    assert report.elements_attempted is False and report.catalog_attempted is False


def live(
    store: FakeStore, observer: Observer | None = None, failing: frozenset[int] = frozenset()
) -> Any:
    return GetLiveView(store, FakePropagator(failing), FakeClock(NOW), SATS).execute(observer)


def test_no_data_gives_an_empty_view_with_every_satellite_missing() -> None:
    view = live(FakeStore())
    assert view.freshness is None
    assert view.satellites == ()
    assert view.missing_norad == (20580, 25544)


def test_data_older_than_14_days_hides_positions() -> None:
    store = FakeStore(
        dataset=OrbitalDataset(
            downloaded_at=NOW - timedelta(days=15), elements=(make_element(25544),)
        )
    )
    view = live(store)
    assert view.freshness is Freshness.TOO_OLD
    assert view.satellites == ()


def test_data_older_than_3_days_is_stale_but_shows_positions() -> None:
    store = FakeStore(
        dataset=OrbitalDataset(
            downloaded_at=NOW - timedelta(days=4),
            elements=(make_element(25544), make_element(20580)),
        )
    )
    view = live(store)
    assert view.freshness is Freshness.STALE
    assert len(view.satellites) == 2


def test_distance_is_none_without_an_observer() -> None:
    store = FakeStore(dataset=OrbitalDataset(downloaded_at=NOW, elements=(make_element(25544),)))
    assert live(store).satellites[0].distance_km is None


def test_distance_is_computed_with_an_observer() -> None:
    store = FakeStore(dataset=OrbitalDataset(downloaded_at=NOW, elements=(make_element(25544),)))
    view = live(store, observer=Observer(latitude=0.0, longitude=0.0))
    assert view.satellites[0].distance_km == 400


def test_satellite_without_data_is_listed_as_missing() -> None:
    store = FakeStore(dataset=OrbitalDataset(downloaded_at=NOW, elements=(make_element(25544),)))
    assert live(store).missing_norad == (20580,)


def test_propagation_error_marks_the_satellite_as_missing() -> None:
    store = FakeStore(
        dataset=OrbitalDataset(
            downloaded_at=NOW, elements=(make_element(25544), make_element(20580))
        )
    )
    view = live(store, failing=frozenset({20580}))
    assert [item.norad for item in view.satellites] == [25544]
    assert view.missing_norad == (20580,)


def test_iss_track_has_91_points() -> None:
    store = FakeStore(dataset=OrbitalDataset(downloaded_at=NOW, elements=(make_element(25544),)))
    assert len(live(store).iss_track) == 91


def test_catalog_fields_are_attached_to_the_satellite() -> None:
    store = FakeStore(
        dataset=OrbitalDataset(downloaded_at=NOW, elements=(make_element(25544),)),
        catalog=Catalog(
            downloaded_at=NOW,
            entries=(
                CatalogEntry(
                    norad=25544, owner_code="US", launch_date=datetime(2016, 10, 30).date()
                ),
            ),
        ),
    )
    assert live(store).satellites[0].owner_code == "US"


@pytest.mark.parametrize("hours", [0, 1])
def test_fresh_data_shows_downloaded_text_in_colombia_time(hours: int) -> None:
    store = FakeStore(
        dataset=OrbitalDataset(
            downloaded_at=NOW - timedelta(hours=hours), elements=(make_element(25544),)
        )
    )
    assert live(store).downloaded_text is not None
```

## Pasos

1. **Crear la rama:** `git switch -c feature/014-casos-de-uso`.
2. **Crear los cuatro archivos** con el contenido de este documento.
3. **Ejecutar los tests:** `uv run pytest -v`.
4. **Comprobar calidad:** `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy src`,
   `uv run pre-commit run --all-files`.
5. **Comprobar que `app` no importa nada prohibido:** `uv run pytest tests/test_architecture.py -v` → 7 passed.
6. **Commit y merge** con el mensaje `014: casos de uso`.

## Casos borde y manejo de errores

1. Dos sesiones piden actualizar a la vez: la segunda sale con un informe vacío y no espera (SEC-31).
2. Un archivo guardado corrupto se trata como "sin datos" en los dos casos de uso, y no se borra: la siguiente descarga
   válida lo reemplaza.
3. Una descarga que llega con otro número NORAD distinto del pedido se rechaza.
4. Un intento fallido sí cuenta para el intervalo: la siguiente descarga espera 2 h (ADR-003).
5. Si los datos tienen más de 14 días no se calcula ninguna posición, aunque el propagador funcione (RF-06).
6. Si una órbita no se puede calcular, ese satélite pasa a `missing_norad` y los demás se muestran.
7. Una hora de descarga en el futuro (más de lo permitido) hace que la vista sea "sin datos" y se registra un aviso.

## Tests de aceptación

Los tests de `tests/app/test_use_cases.py` cubren, para la descarga: primera descarga completa; intento guardado antes
de la primera petición; no descarga antes de 2 h; descarga a las 2 h; un fallo no se reintenta; una respuesta inválida
conserva el dato anterior; un cambio del movimiento medio mayor del 5 % se rechaza; un satélite que falta conserva su
valor anterior; el catálogo se descarga a las 24 h y no antes; una ejecución simultánea se omite. Para la vista: sin datos;
datos de más de 14 días sin posiciones; datos de más de 3 días con aviso y posiciones; distancia nula sin ubicación;
distancia de 400 km con ubicación de prueba; satélite sin datos en `missing_norad`; error de propagación en
`missing_norad`; trayectoria de la ISS de 91 puntos; país del catálogo adjunto; texto de hora de Colombia.

## Fuera de alcance

- Los textos "Datos de hace N días" y las fichas: spec 015 (interfaz).
- El cálculo del número de años en órbita: spec 018 (P2).
- La inicialización de los objetos: spec 017 (`orbita.main`).

## Definition of Done

Todos los comandos en PowerShell, desde la carpeta `orbita`.

- [ ] `uv run pytest -v` → todos los tests pasan.
- [ ] `uv run pytest tests/test_architecture.py -v` → 7 passed.
- [ ] `Select-String -Path src\orbita\app\*.py -Pattern 'import (streamlit|httpx|pydeck|skyfield)|orbita\.adapters'` → sin salida.
- [ ] `Select-String -Path src\orbita\app\*.py -Pattern 'datetime\.now|time\.time'` → sin salida (el reloj viene del puerto).
- [ ] `uv run ruff check .`, `uv run mypy src` y `uv run pre-commit run --all-files` sin errores.
- [ ] `git status` → `nothing to commit, working tree clean` después del merge.
