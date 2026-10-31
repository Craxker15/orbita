r"""Composition root and entry point: builds the adapters and use cases once, then starts the page.

Run from the project folder with: uv run streamlit run src\orbita\main.py
This is the only module that knows every layer (ARCHITECTURE.md §2, rules 5 and 6).
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Final

import httpx
import streamlit as st

from orbita.adapters.celestrak_source import CelestrakSource
from orbita.adapters.json_file_store import JsonFileStore
from orbita.adapters.skyfield_propagator import SkyfieldPropagator
from orbita.adapters.system_clock import SystemClock
from orbita.app.get_live_view import GetLiveView
from orbita.app.refresh_satellite_data import RefreshSatelliteData
from orbita.domain.satellites import SATELLITE_NORADS
from orbita.ports.satellite_data import SatelliteDataSource
from orbita.settings import load_settings, load_texts
from orbita.ui.page import PageDependencies, render_page

REPO_ROOT: Final = Path(__file__).resolve().parents[2]
ENV_FILE: Final = REPO_ROOT / ".env"
TEXTS_FILE: Final = REPO_ROOT / "locales" / "es.json"
BASEMAP_FILE: Final = REPO_ROOT / "assets" / "ne_110m_countries.geojson"
LOG_FORMAT: Final = "%(asctime)s %(levelname)s %(name)s %(message)s"

logger = logging.getLogger(__name__)


def build_dependencies(
    data_dir: Path, refresh_seconds: int, source: SatelliteDataSource | None = None
) -> PageDependencies:
    """Create every adapter and use case once, with their ports injected (ARCHITECTURE.md §6).

    Preconditions: data_dir is a validated path inside the project (SEC-11).
    Postconditions: the only network client is the one given to CelestrakSource (SEC-15).
    """
    clock = SystemClock()
    store = JsonFileStore(data_dir)
    if source is None:
        source = CelestrakSource(httpx.Client())
    return PageDependencies(
        refresh=RefreshSatelliteData(source, store, clock, SATELLITE_NORADS),
        live=GetLiveView(store, SkyfieldPropagator(), clock, SATELLITE_NORADS),
        texts=load_texts(TEXTS_FILE),
        basemap_path=BASEMAP_FILE,
        refresh_seconds=refresh_seconds,
    )


@st.cache_resource
def _cached_dependencies(data_dir: str, refresh_seconds: int) -> PageDependencies:
    """Build the object graph once per process; Streamlit reruns the script on each interaction."""
    return build_dependencies(Path(data_dir), refresh_seconds)


def main() -> None:
    """Read the configuration and draw the page.

    A configuration error stops the start before anything is drawn, with the variable name in the
    traceback (SEC-09). Any other failure is logged and shown with the unexpected_error text, so the
    page never shows a stack trace to the visitor (ARCHITECTURE.md §6).
    """
    settings = load_settings(os.environ, ENV_FILE, REPO_ROOT)
    logging.basicConfig(level=settings.log_level, format=LOG_FORMAT)
    texts = load_texts(TEXTS_FILE)
    try:
        render_page(_cached_dependencies(str(settings.data_dir), settings.refresh_s))
    except Exception:  # noqa: BLE001 - last defence: logged, then shown as text (ARCHITECTURE.md §6)
        logger.exception("app_failed")
        st.error(texts["unexpected_error"])


if __name__ == "__main__":
    main()
