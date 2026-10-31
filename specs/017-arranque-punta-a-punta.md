# 017 - Arranque (`orbita.main`) y prueba de punta a punta

## Objetivo

Al terminar, `uv run streamlit run src\orbita\main.py` arranca la aplicación completa: lee la configuración, crea una sola
vez los adaptadores y los casos de uso (en `orbita.main`, la única capa que los conoce todos), y dibuja la página. Una
prueba de punta a punta ejecuta el script de Streamlit sin red y comprueba que la página funciona con los archivos
guardados (RF-05), que avisa de datos viejos (RF-06) y que oculta las posiciones con más de 14 días (SEC-25).

## Depende de

- 009 (configuración y textos), 011 (adaptador CelesTrak), 012 (almacén de archivos), 013 (propagador y reloj),
  014 (casos de uso), 015 y 016 (interfaz), 010 (lista de satélites confirmada).

## Archivos rectores aplicables

- `ARCHITECTURE.md` §2 (regla 6: solo `orbita.main` y `orbita.settings` importan todo), §6 (`st.cache_resource` para el
  grafo de objetos; un error no capturado se registra y se muestra con `unexpected_error`, la única excepción genérica
  fuera del fragmento).
- `security-rules.md` SEC-09 (la configuración falla al arrancar con un mensaje claro), SEC-33 (sin detalles de error para
  el visitante en la versión publicada; se completa en la spec 021).
- `DESIGN.md` §8 (variables de configuración).

## Archivos a crear

1. `src/orbita/main.py`
2. `tests/test_end_to_end.py`

Son dos archivos: el punto de entrada (capa de entrada) y su prueba.

## Dependencias externas

Ninguna nueva. `streamlit.testing.v1.AppTest` viene con Streamlit.

## Contenido exacto de los archivos

### `src/orbita/main.py`

```python
"""Composition root and entry point: builds the adapters and the use cases once, then starts the page.

Run from the project folder with: uv run streamlit run src\\orbita\\main.py
This is the only module that knows every layer (ARCHITECTURE.md §2, rules 5 and 6).
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Final

import httpx
import streamlit as st  # type: ignore[import-untyped]

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
    """Create every adapter and use case once, with their ports injected (ARCHITECTURE.md §6, rule 7).

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
    """Build the object graph once per process: Streamlit runs this script again on every interaction."""
    return build_dependencies(Path(data_dir), refresh_seconds)


def main() -> None:
    """Read the configuration and draw the page.

    A configuration error stops the start before anything is drawn, with the variable name in the traceback (SEC-09).
    Any other failure is logged and shown with the unexpected_error text, so the page never shows a stack trace
    to the visitor (ARCHITECTURE.md §6).
    """
    settings = load_settings(os.environ, ENV_FILE, REPO_ROOT)
    logging.basicConfig(level=settings.log_level, format=LOG_FORMAT)
    texts = load_texts(TEXTS_FILE)
    try:
        render_page(_cached_dependencies(str(settings.data_dir), settings.refresh_s))
    except Exception:  # noqa: BLE001 - last line of defence of the process; logged, then shown as text (ARCHITECTURE.md §6)
        logger.exception("app_failed")
        st.error(texts["unexpected_error"])


if __name__ == "__main__":
    main()
```

### `tests/test_end_to_end.py`

```python
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
        OrbitalDataset(downloaded_at=downloaded, elements=(element(25544, downloaded), element(20580, downloaded)))
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
```

## Pasos

1. **Crear la rama:** `git switch -c feature/017-arranque-punta-a-punta`.
2. **Crear los dos archivos** con el contenido de este documento.
3. **Ejecutar los tests:** `uv run pytest -v`. La prueba de punta a punta crea `data_e2e_test` dentro del proyecto y la
   borra al terminar; está en `.gitignore` solo si se añade la regla `data_e2e_test/` (se añade en el paso 4).
4. **Añadir la carpeta de pruebas al `.gitignore`:** agregar la línea `data_e2e_test/` al final del archivo.
5. **Arrancar la aplicación a mano:**
   ```powershell
   uv run streamlit run src\orbita\main.py
   ```
   Se abre `http://localhost:8501`. Comprobar: el título aparece; el aviso de sin datos aparece si `data\` no existe; el
   mapa aparece cuando hay datos; en `data\` aparecen `orbital_elements.json`, `satcat.json` y
   `download_attempts.json` tras una descarga con internet. Parar con `Ctrl + C`.
6. **Comprobar calidad:** `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy src`,
   `uv run pre-commit run --all-files`.
7. **Commit y merge** con el mensaje `017: arranque y prueba de punta a punta`.

## Casos borde y manejo de errores

1. Un `.env` con un valor inválido: la aplicación no dibuja nada y el traceback nombra la variable (SEC-09).
2. Un error inesperado en la página completa: se registra con `app_failed` y se muestra `unexpected_error`.
3. La carpeta de datos no existe y no hay internet: aparece `no_orbital_data`, sin error.
4. Dos pestañas abiertas a la vez comparten los mismos objetos (`st.cache_resource`) y los mismos bloqueos (spec 014).

## Tests de aceptación

- Sin datos y sin red: la página arranca, muestra el título y el aviso `no_orbital_data`.
- Con datos de hace una hora y sin red: la página arranca sin excepción y muestra `location_unavailable`.
- Con datos de hace 4 días: aparece el aviso de datos viejos con los días.
- Con datos de hace 15 días: aparece `too_old_data`.
- El aviso de aproximación aparece siempre (SEC-23).
- Prueba manual: la aplicación arranca con `streamlit run` y el mapa se ve.

## Fuera de alcance

- Las descargas reales de CelesTrak: se comprueban a mano con internet, no en las pruebas automáticas (sin red).
- El país y los años en órbita: spec 018.
- La publicación: spec 021.

## Definition of Done

Todos los comandos en PowerShell, desde la carpeta `orbita`.

- [ ] `uv run pytest -v` → todos los tests pasan, incluidos los 5 de `test_end_to_end.py`.
- [ ] `Test-Path data_e2e_test` → `False` después de los tests.
- [ ] `uv run streamlit run src\orbita\main.py` → la página abre en `localhost:8501` sin errores en la terminal.
- [ ] `Select-String -Path src\orbita\main.py -Pattern 'except Exception'` → una sola línea, con su `noqa` justificado.
- [ ] `uv run ruff check .`, `uv run mypy src` y `uv run pre-commit run --all-files` sin errores.
- [ ] `uv run pytest tests/test_architecture.py -v` → 7 passed.
- [ ] `git status` → `nothing to commit, working tree clean` después del merge.
