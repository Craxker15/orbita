"""Validation of the domain types of spec 003."""

from __future__ import annotations

import dataclasses
import math
from datetime import UTC, date, datetime, timedelta, timezone

import pytest

from orbita.domain.catalog import Catalog, CatalogEntry
from orbita.domain.elements import Freshness, OrbitalDataset, OrbitalElements, OrbitType
from orbita.domain.errors import (
    ConfigError,
    DataValidationError,
    InvalidLocationError,
    OrbitaError,
)
from orbita.domain.observer import GroundPoint, Observer

EPOCH = datetime(2026, 10, 30, 12, 0, tzinfo=UTC)


def make_elements(**changes: object) -> OrbitalElements:
    values: dict[str, object] = {
        "norad": 25544,
        "name": "ISS (ZARYA)",
        "inclination_deg": 51.6,
        "mean_motion_rev_day": 15.5,
        "eccentricity": 0.0007,
        "epoch": EPOCH,
        "raan_deg": 247.0,
        "arg_perigee_deg": 130.0,
        "mean_anomaly_deg": 325.0,
        "mean_motion_dot": 0.0001,
        "mean_motion_ddot": 0.0,
        "bstar": 0.0001,
    }
    values.update(changes)
    return OrbitalElements(**values)


def test_valid_elements_are_accepted() -> None:
    assert make_elements().norad == 25544


def test_elements_are_frozen() -> None:
    with pytest.raises(dataclasses.FrozenInstanceError):
        make_elements().norad = 1


@pytest.mark.parametrize(
    ("changes", "field"),
    [
        ({"norad": 0}, "norad"),
        ({"name": "   "}, "name"),
        ({"name": "x" * 81}, "name"),
        ({"inclination_deg": 181.0}, "inclination_deg"),
        ({"inclination_deg": math.nan}, "inclination_deg"),
        ({"mean_motion_rev_day": 0.0}, "mean_motion_rev_day"),
        ({"mean_motion_rev_day": 20.1}, "mean_motion_rev_day"),
        ({"eccentricity": 1.0}, "eccentricity"),
        ({"epoch": datetime(2026, 10, 30)}, "epoch"),
        ({"epoch": datetime(2026, 10, 30, tzinfo=timezone(timedelta(hours=-5)))}, "epoch"),
    ],
)
def test_orbital_elements_reject_invalid_values(changes: dict[str, object], field: str) -> None:
    with pytest.raises(DataValidationError, match=field):
        make_elements(**changes)


def test_dataset_rejects_duplicate_norad() -> None:
    with pytest.raises(DataValidationError, match="more than once"):
        OrbitalDataset(downloaded_at=EPOCH, elements=(make_elements(), make_elements()))


def test_dataset_rejects_naive_download_time() -> None:
    with pytest.raises(DataValidationError, match="downloaded_at"):
        OrbitalDataset(downloaded_at=datetime(2026, 10, 30), elements=())


@pytest.mark.parametrize(
    ("latitude", "longitude"),
    [(3.45, -76.53), (90.0, 180.0), (-90.0, -180.0)],
)
def test_observer_accepts_valid_location(latitude: float, longitude: float) -> None:
    assert Observer(latitude=latitude, longitude=longitude).latitude == latitude


@pytest.mark.parametrize(("latitude", "longitude"), [(90.1, 0.0), (0.0, -180.1), (math.nan, 0.0)])
def test_observer_rejects_invalid_location(latitude: float, longitude: float) -> None:
    with pytest.raises(InvalidLocationError):
        Observer(latitude=latitude, longitude=longitude)


def test_observer_repr_hides_coordinates() -> None:
    assert repr(Observer(latitude=3.45, longitude=-76.53)) == "Observer(<hidden>)"


def test_invalid_location_message_does_not_contain_the_value() -> None:
    with pytest.raises(InvalidLocationError) as info:
        Observer(latitude=91.123, longitude=0.0)
    assert "91.123" not in str(info.value)


def test_ground_point_rejects_negative_altitude() -> None:
    with pytest.raises(DataValidationError, match="altitude_km"):
        GroundPoint(latitude=0.0, longitude=0.0, altitude_km=-1.0)


def test_catalog_entry_accepts_owner_code() -> None:
    entry = CatalogEntry(norad=25544, owner_code="US", launch_date=date(1998, 11, 20))
    assert entry.owner_code == "US"


@pytest.mark.parametrize("owner_code", ["us", "", "ABCDEFGHIJK", "U S"])
def test_catalog_entry_rejects_bad_owner_code(owner_code: str) -> None:
    with pytest.raises(DataValidationError, match="owner_code"):
        CatalogEntry(norad=25544, owner_code=owner_code, launch_date=date(1998, 11, 20))


def test_catalog_entry_rejects_datetime_as_launch_date() -> None:
    with pytest.raises(DataValidationError, match="launch_date"):
        CatalogEntry(norad=25544, owner_code="US", launch_date=datetime(1998, 11, 20, tzinfo=UTC))


def test_catalog_rejects_duplicate_norad() -> None:
    entry = CatalogEntry(norad=25544, owner_code="US", launch_date=date(1998, 11, 20))
    with pytest.raises(DataValidationError, match="more than once"):
        Catalog(downloaded_at=EPOCH, entries=(entry, entry))


@pytest.mark.parametrize("error", [DataValidationError, ConfigError, InvalidLocationError])
def test_project_errors_inherit_from_orbita_error(error: type[OrbitaError]) -> None:
    assert issubclass(error, OrbitaError)


def test_enum_values_match_the_names_of_the_rules() -> None:
    assert OrbitType.GEOSTATIONARY == "geostationary"
    assert Freshness.TOO_OLD == "too_old"
