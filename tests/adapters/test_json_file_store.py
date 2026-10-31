"""Tests of the JSON file store with real files in a temporary folder (spec 012)."""

from __future__ import annotations

from datetime import UTC, date, datetime
from pathlib import Path

import pytest

from orbita.adapters.json_file_store import (
    ATTEMPTS_FILE,
    CATALOG_FILE,
    ELEMENTS_FILE,
    JsonFileStore,
)
from orbita.domain.catalog import Catalog, CatalogEntry
from orbita.domain.elements import OrbitalDataset, OrbitalElements
from orbita.domain.errors import DataValidationError
from orbita.domain.state import DownloadAttempts

NOW = datetime(2026, 10, 30, 12, tzinfo=UTC)


def element(norad: int = 25544) -> OrbitalElements:
    return OrbitalElements(
        norad=norad,
        name="ISS (ZARYA)",
        inclination_deg=51.6,
        mean_motion_rev_day=15.5,
        eccentricity=0.0007,
        epoch=NOW,
        raan_deg=247.0,
        arg_perigee_deg=130.0,
        mean_anomaly_deg=325.0,
        mean_motion_dot=0.0001,
        mean_motion_ddot=0.0,
        bstar=0.0001,
    )


def test_missing_files_give_no_data(tmp_path: Path) -> None:
    store = JsonFileStore(tmp_path)
    assert store.load_elements() is None
    assert store.load_catalog() is None
    assert store.load_attempts() == DownloadAttempts()


def test_elements_round_trip(tmp_path: Path) -> None:
    dataset = OrbitalDataset(downloaded_at=NOW, elements=(element(25544), element(20580)))
    JsonFileStore(tmp_path).save_elements(dataset)
    assert JsonFileStore(tmp_path).load_elements() == dataset


def test_catalog_round_trip(tmp_path: Path) -> None:
    catalog = Catalog(
        downloaded_at=NOW,
        entries=(CatalogEntry(norad=25544, owner_code="ISS", launch_date=date(1998, 11, 20)),),
    )
    JsonFileStore(tmp_path).save_catalog(catalog)
    assert JsonFileStore(tmp_path).load_catalog() == catalog


def test_attempts_round_trip_with_one_missing_value(tmp_path: Path) -> None:
    attempts = DownloadAttempts(elements=NOW, catalog=None)
    JsonFileStore(tmp_path).save_attempts(attempts)
    assert JsonFileStore(tmp_path).load_attempts() == attempts


def test_save_creates_the_missing_data_folder(tmp_path: Path) -> None:
    folder = tmp_path / "nested" / "data"
    JsonFileStore(folder).save_attempts(DownloadAttempts(elements=NOW))
    assert (folder / ATTEMPTS_FILE).is_file()


def test_no_temporary_file_is_left_behind(tmp_path: Path) -> None:
    JsonFileStore(tmp_path).save_elements(OrbitalDataset(downloaded_at=NOW, elements=()))
    assert not (tmp_path / (ELEMENTS_FILE + ".tmp")).exists()


def test_loaded_dataset_is_cached_until_the_file_changes(tmp_path: Path) -> None:
    store = JsonFileStore(tmp_path)
    store.save_elements(OrbitalDataset(downloaded_at=NOW, elements=()))
    first = store.load_elements()
    second = store.load_elements()
    assert first is second


def test_corrupt_file_raises_data_error(tmp_path: Path) -> None:
    (tmp_path / ELEMENTS_FILE).write_text("{bad", encoding="utf-8")
    with pytest.raises(DataValidationError):
        JsonFileStore(tmp_path).load_elements()


def test_stored_time_without_offset_is_rejected(tmp_path: Path) -> None:
    (tmp_path / ELEMENTS_FILE).write_text(
        '{"downloaded_at": "2026-10-30T12:00:00", "elements": []}', encoding="utf-8"
    )
    with pytest.raises(DataValidationError):
        JsonFileStore(tmp_path).load_elements()


def test_only_the_fixed_file_names_are_written(tmp_path: Path) -> None:
    store = JsonFileStore(tmp_path)
    store.save_elements(OrbitalDataset(downloaded_at=NOW, elements=()))
    store.save_catalog(Catalog(downloaded_at=NOW, entries=()))
    store.save_attempts(DownloadAttempts(elements=NOW))
    expected = {ELEMENTS_FILE, CATALOG_FILE, ATTEMPTS_FILE}
    assert {path.name for path in tmp_path.iterdir()} == expected
