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
