"""End-to-end test: runs the Streamlit script with no network and with saved data (spec 017, RF-05, RF-06, SEC-25)."""

from __future__ import annotations

import shutil
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

import orbita.adapters.celestrak_source as celestrak_module
from orbita.adapters.json_file_store import JsonFileStore
from orbita.domain.elements import OrbitalDataset, OrbitalElements
from orbita.domain.errors import DownloadError
from orbita.main import REPO_ROOT, TEXTS_FILE
from orbita.settings import load_texts

MAIN_FILE = REPO_ROOT / "src" / "orbita" / "main.py"
TEST_DATA_DIR = "data_e2e_test"
TEXTS = load_texts(TEXTS_FILE)


class OfflineSource:
    """Refuses every download, so the page must work from the saved files alone (RF-05)."""

    def download_elements(self, norad: int) -> str:
        raise DownloadError("offline in the test")

    def download_catalog(self, norad: int) -> str:
        raise DownloadError("offline in the test")


@pytest.fixture
def offline(monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    """Point the app to a temporary data folder inside the project and block the network."""
    monkeypatch.setenv("ORBITA_DATA_DIR", TEST_DATA_DIR)
    monkeypatch.setattr(celestrak_module, "CelestrakSource", lambda client: OfflineSource())
    folder = REPO_ROOT / TEST_DATA_DIR
    yield folder
    shutil.rmtree(folder, ignore_errors=True)


def element(norad: int, downloaded: datetime) -> OrbitalElements:
    return OrbitalElements(
        norad=norad,
        name=f"SAT {norad}",
        inclination_deg=51.6,
        mean_motion_rev_day=15.5,
        eccentricity=0.0005,
        epoch=downloaded,
        raan_deg=0.0,
        arg_perigee_deg=0.0,
        mean_anomaly_deg=0.0,
        mean_motion_dot=0.0,
        mean_motion_ddot=0.0,
        bstar=0.0,
    )


def save(folder: Path, downloaded: datetime) -> None:
    JsonFileStore(folder).save_elements(
        OrbitalDataset(
            downloaded_at=downloaded,
            elements=(element(25544, downloaded), element(20580, downloaded)),
        )
    )


def run_app() -> AppTest:
    return AppTest.from_file(str(MAIN_FILE), default_timeout=60).run()


def test_page_starts_offline_with_no_data_and_says_so(offline: Path) -> None:
    app = run_app()
    assert not app.exception
    assert app.title[0].value == TEXTS["title"]
    assert any(TEXTS["no_orbital_data"] in item.value for item in app.warning)


def test_saved_data_is_drawn_without_network(offline: Path) -> None:
    save(offline, datetime.now(UTC) - timedelta(hours=1))
    app = run_app()
    assert not app.exception
    assert any(TEXTS["location_unavailable"] in item.value for item in app.info)


def test_stale_data_shows_its_age(offline: Path) -> None:
    save(offline, datetime.now(UTC) - timedelta(days=4))
    app = run_app()
    assert any("4" in item.value for item in app.warning)


def test_data_older_than_14_days_shows_the_too_old_notice(offline: Path) -> None:
    save(offline, datetime.now(UTC) - timedelta(days=15))
    app = run_app()
    assert any(TEXTS["too_old_data"] in item.value for item in app.warning)


def test_approximation_notice_is_always_shown(offline: Path) -> None:
    app = run_app()
    assert any(TEXTS["approximate_notice"] in item.value for item in app.caption)
