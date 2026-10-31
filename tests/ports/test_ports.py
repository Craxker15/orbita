"""Port protocol and state validation tests (spec 008)."""

from __future__ import annotations

import math
from datetime import UTC, datetime

import pytest

from orbita.domain.errors import DataValidationError
from orbita.domain.observer import GroundPoint
from orbita.domain.state import DownloadAttempts, SatelliteState
from orbita.ports.propagation import Clock, OrbitPropagator
from orbita.ports.satellite_data import SatelliteDataSource, SatelliteDataStore

NOW = datetime(2026, 10, 30, 12, 0, tzinfo=UTC)


class FakeSource:
    def download_elements(self, norad: int) -> str:
        return "[]"

    def download_catalog(self, norad: int) -> str:
        return "[]"


class FakeStore:
    def load_elements(self) -> None:
        return None

    def save_elements(self, dataset: object) -> None:
        return None

    def load_catalog(self) -> None:
        return None

    def save_catalog(self, catalog: object) -> None:
        return None

    def load_attempts(self) -> DownloadAttempts:
        return DownloadAttempts()

    def save_attempts(self, attempts: DownloadAttempts) -> None:
        return None


class FakePropagator:
    def state(self, elements: object, moment: datetime) -> SatelliteState:
        return SatelliteState(norad=25544, point=GroundPoint(0.0, 0.0, 400.0), speed_km_s=7.66)

    def ground_track(
        self, elements: object, moments: tuple[datetime, ...]
    ) -> tuple[GroundPoint, ...]:
        return ()


class FakeClock:
    def now(self) -> datetime:
        return NOW


class ClockWithoutNow:
    pass


def test_fake_source_satisfies_the_source_port() -> None:
    assert isinstance(FakeSource(), SatelliteDataSource)


def test_fake_store_satisfies_the_store_port() -> None:
    assert isinstance(FakeStore(), SatelliteDataStore)


def test_fake_propagator_satisfies_the_propagator_port() -> None:
    assert isinstance(FakePropagator(), OrbitPropagator)


def test_fake_clock_satisfies_the_clock_port() -> None:
    assert isinstance(FakeClock(), Clock)


def test_object_without_the_methods_does_not_satisfy_the_clock_port() -> None:
    assert not isinstance(ClockWithoutNow(), Clock)


def test_satellite_state_rejects_negative_speed() -> None:
    with pytest.raises(DataValidationError):
        SatelliteState(norad=25544, point=GroundPoint(0.0, 0.0), speed_km_s=-1.0)


def test_satellite_state_rejects_nan_speed() -> None:
    with pytest.raises(DataValidationError):
        SatelliteState(norad=25544, point=GroundPoint(0.0, 0.0), speed_km_s=math.nan)


def test_satellite_state_rejects_non_positive_norad() -> None:
    with pytest.raises(DataValidationError):
        SatelliteState(norad=0, point=GroundPoint(0.0, 0.0), speed_km_s=7.5)


def test_download_attempts_accept_missing_values() -> None:
    attempts = DownloadAttempts()
    assert attempts.elements is None and attempts.catalog is None


def test_download_attempts_reject_naive_time() -> None:
    with pytest.raises(DataValidationError):
        DownloadAttempts(elements=datetime(2026, 10, 30, 12, 0))
