# 015 - Interfaz: mapa pydeck, fichas y avisos

## Objetivo

Al terminar, la página muestra el mapa mundial con la trayectoria de la ISS y los 20 satélites, actualizado cada segundo
dentro de un fragmento de Streamlit; al tocar un satélite en el mapa aparece su ficha (nombre, altura, velocidad, tipo
de órbita, periodo, distancia si hay ubicación, país y fecha de lanzamiento); y se muestran los avisos de datos viejos,
sin datos o satélites sin datos. Todo el texto sale de `locales/es.json` (RNF-04). La interfaz dibuja: no decide ninguna
regla (ARCHITECTURE.md §7.1).

## Depende de

- 009 (textos en `locales/es.json`), 014 (`LiveView`, `GetLiveView`, `RefreshSatelliteData`).

## Archivos rectores aplicables

- `ARCHITECTURE.md` §7.1 (la interfaz dibuja y no decide; dos partes: página completa y fragmento de un segundo), §7.2
  (textos en `es.json`), §2 (`orbita.ui` solo importa dominio, app y bibliotecas de interfaz).
- `ADR-002` (pydeck con `st.pydeck_chart`, `map_provider=None`, contornos de Natural Earth locales; tooltips con
  `text`, nunca `html`).
- `security-rules.md` SEC-13 (texto de datos descargados como texto plano, sin `unsafe_allow_html`), SEC-23 (aviso de
  aproximación siempre visible), SEC-24 (las distancias llevan "≈"), SEC-25 (sin posiciones con datos de más de 14 días),
  SEC-32 (sin campos de texto libre).
- `docs/00-requirements.es.md` RF-01, RF-02, RF-03, RF-05, RF-06, RF-08, RF-09, RNF-06 (1366 × 768 sin desplazamiento
  horizontal).

## Archivos a crear

1. `src/orbita/ui/map_view.py`
2. `src/orbita/ui/cards.py`
3. `src/orbita/ui/page.py`
4. `tests/ui/test_map_view.py`
5. `tests/ui/test_cards.py`

Son cinco archivos, en la capa `ui` y sus tests. Está en el límite de la regla 3 del índice.

## Dependencias externas

- `streamlit` y `pydeck`, ya fijadas en `pyproject.toml` por la spec 001 (`pydeck` llega con `streamlit`). Antes de
  escribir el código, el paso 1 comprueba que la versión de pydeck permite `map_provider=None` (0.9 o posterior).

## Contenido exacto de los archivos

### `src/orbita/ui/map_view.py`

```python
"""Builds the pydeck map from a LiveView (ADR-002). Pure functions: they do not call Streamlit."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Final

import pydeck  # type: ignore[import-untyped]

from orbita.app.live_view import LiveView
from orbita.domain.errors import ConfigError
from orbita.domain.observer import GroundPoint, Observer

BASEMAP_LAYER_ID: Final = "basemap"
TRACK_LAYER_ID: Final = "iss_track"
SATELLITE_LAYER_ID: Final = "satellites"
OBSERVER_LAYER_ID: Final = "observer"
SATELLITE_RADIUS_M: Final = 60_000
OBSERVER_RADIUS_M: Final = 80_000


def load_basemap(path: Path) -> dict[str, Any]:
    """Read the offline country outlines, which must be a GeoJSON FeatureCollection (ADR-002, SEC-09).

    Raises:
        ConfigError: if the file cannot be read or is not a FeatureCollection.
    """
    try:
        content = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise ConfigError(f"{path.name} cannot be read as JSON") from error
    if not isinstance(content, dict) or content.get("type") != "FeatureCollection":
        raise ConfigError(f"{path.name} must be a GeoJSON FeatureCollection")
    return content


def satellite_rows(view: LiveView) -> list[dict[str, Any]]:
    """One row per satellite, with the position in [longitude, latitude] order as pydeck expects it."""
    return [
        {
            "norad": item.norad,
            "name": item.name,
            "position": [item.point.longitude, item.point.latitude],
        }
        for item in view.satellites
    ]


def track_path(track: tuple[GroundPoint, ...]) -> list[list[float]]:
    """The ISS ground track as [longitude, latitude] pairs."""
    return [[point.longitude, point.latitude] for point in track]


def build_deck(view: LiveView, observer: Observer | None, basemap: dict[str, Any]) -> pydeck.Deck:
    """Build the map: offline outlines, the ISS track, the satellites and, when known, the user's marker.

    Postconditions: no tile server is used (map_provider=None, ADR-002); the tooltip is plain text (SEC-13).
    """
    layers: list[Any] = [
        pydeck.Layer(
            "GeoJsonLayer",
            id=BASEMAP_LAYER_ID,
            data=basemap,
            stroked=True,
            filled=False,
            get_line_color=[120, 120, 120],
            get_line_width=1,
            line_width_min_pixels=1,
            pickable=False,
        ),
        pydeck.Layer(
            "PathLayer",
            id=TRACK_LAYER_ID,
            data=[{"path": track_path(view.iss_track)}],
            get_path="path",
            get_color=[255, 200, 0],
            width_min_pixels=2,
            pickable=False,
        ),
        pydeck.Layer(
            "ScatterplotLayer",
            id=SATELLITE_LAYER_ID,
            data=satellite_rows(view),
            get_position="position",
            get_fill_color=[0, 200, 255],
            get_radius=SATELLITE_RADIUS_M,
            radius_min_pixels=5,
            pickable=True,
            auto_highlight=True,
        ),
    ]
    if observer is not None:
        layers.append(
            pydeck.Layer(
                "ScatterplotLayer",
                id=OBSERVER_LAYER_ID,
                data=[{"position": [observer.longitude, observer.latitude]}],
                get_position="position",
                get_fill_color=[255, 60, 60],
                get_radius=OBSERVER_RADIUS_M,
                radius_min_pixels=7,
                pickable=False,
            )
        )
    return pydeck.Deck(
        layers=layers,
        initial_view_state=pydeck.ViewState(latitude=0.0, longitude=0.0, zoom=1),
        map_provider=None,
        tooltip={"text": "{name}"},
    )
```

### `src/orbita/ui/cards.py`

```python
"""Texts of the satellite cards and of the notices, taken from locales/es.json (RNF-04, SEC-13)."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Final

from orbita.app.live_view import SatelliteView
from orbita.domain.elements import Freshness, OrbitType

ORBIT_TEXT_KEYS: Final[Mapping[OrbitType, str]] = {
    OrbitType.GEOSTATIONARY: "orbit_geostationary",
    OrbitType.POLAR: "orbit_polar",
    OrbitType.LOW: "orbit_low",
    OrbitType.OTHER: "orbit_other",
}


def card_rows(view: SatelliteView, texts: Mapping[str, str]) -> tuple[tuple[str, str], ...]:
    """Return the label and the value of each line of the card of one satellite (RF-03)."""
    missing = texts["missing_value"]
    distance = missing if view.distance_km is None else texts["distance_approx"].format(km=view.distance_km)
    launch = missing if view.launch_date is None else view.launch_date.isoformat()
    return (
        (texts["label_altitude"], f"{view.point.altitude_km:.0f} km"),
        (texts["label_speed"], f"{view.speed_km_s:.2f} km/s"),
        (texts["label_orbit_type"], texts[ORBIT_TEXT_KEYS[view.orbit_type]]),
        (texts["label_period"], f"{view.period_minutes} min"),
        (texts["label_distance"], distance),
        (texts["label_country"], country_label(view.owner_code, texts)),
        (texts["label_launch_date"], launch),
        (texts["label_years_in_orbit"], missing),
    )


def country_label(owner_code: str | None, texts: Mapping[str, str]) -> str:
    """Translate a SATCAT owner code with its owner_<CODE> key; an unknown code is shown as it comes (DESIGN.md §4.6)."""
    if owner_code is None:
        return texts["missing_value"]
    return texts.get(f"owner_{owner_code}", owner_code)


def freshness_notice(
    freshness: Freshness | None, age_days: int | None, texts: Mapping[str, str]
) -> str | None:
    """Return the notice for the age of the orbital data, or None when no notice is needed (DESIGN.md §4.2)."""
    if freshness is None:
        return texts["no_orbital_data"]
    if freshness is Freshness.TOO_OLD:
        return texts["too_old_data"]
    if freshness is Freshness.STALE and age_days is not None:
        return texts["stale_data"].format(days=age_days)
    return None
```

### `src/orbita/ui/page.py`

```python
"""Streamlit page of Orbita: a full run refreshes the data; a fragment redraws the map every N seconds.

orbita.ui draws and does not decide: every rule arrives already applied in LiveView (ARCHITECTURE.md §7.1).
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import streamlit as st  # type: ignore[import-untyped]

from orbita.app.get_live_view import GetLiveView
from orbita.app.live_view import LiveView
from orbita.app.refresh_satellite_data import RefreshSatelliteData
from orbita.domain.observer import Observer
from orbita.ui.cards import card_rows, freshness_notice
from orbita.ui.map_view import SATELLITE_LAYER_ID, build_deck, load_basemap

logger = logging.getLogger(__name__)

OBSERVER_KEY = "observer"


@dataclass(frozen=True, slots=True)
class PageDependencies:
    """What the page receives from the composition root (ARCHITECTURE.md §2, rule 5)."""

    refresh: RefreshSatelliteData
    live: GetLiveView
    texts: dict[str, str]
    basemap_path: Path
    refresh_seconds: int


def render_page(deps: PageDependencies) -> None:
    """Draw the title, the approximation notice, run the refresh once and start the live map."""
    st.set_page_config(page_title=deps.texts["title"], layout="wide")
    st.title(deps.texts["title"])
    st.caption(deps.texts["approximate_notice"])
    deps.refresh.execute()
    _make_live_fragment(deps)()


def _make_live_fragment(deps: PageDependencies) -> Callable[[], None]:
    """Return the fragment that redraws the map every refresh_seconds (ARCHITECTURE.md §7.1)."""

    @st.fragment(run_every=deps.refresh_seconds)
    def live_map() -> None:
        try:
            observer: Observer | None = st.session_state.get(OBSERVER_KEY)
            _draw(deps, deps.live.execute(observer), observer)
        except Exception:  # noqa: BLE001 - a failure must not freeze the map (ARCHITECTURE.md §6)
            logger.exception("live_view_failed")
            st.error(deps.texts["unexpected_error"])

    return live_map


def _draw(deps: PageDependencies, view: LiveView, observer: Observer | None) -> None:
    """Draw the notices, the map and the card of the selected satellite."""
    notice = freshness_notice(view.freshness, view.age_days, deps.texts)
    if notice is not None:
        st.warning(notice)
    if view.freshness is None:
        return
    if observer is None:
        st.info(deps.texts["location_unavailable"])
    if view.missing_norad:
        numbers = ", ".join(str(number) for number in view.missing_norad)
        st.caption(deps.texts["missing_satellites"].format(norad_numbers=numbers))
    if view.downloaded_text is not None:
        st.caption(f"{deps.texts['label_last_download']}: {view.downloaded_text}")
    basemap = load_basemap(deps.basemap_path)
    state: Any = st.pydeck_chart(
        build_deck(view, observer, basemap),
        on_select="rerun",
        selection_mode="single-object",
        key="satellite_map",
        height=520,
    )
    _show_card(deps, view, _selected_norad(state))


def _selected_norad(state: Any) -> int | None:
    """Return the NORAD number of the satellite clicked on the map, if any."""
    selection = getattr(state, "selection", None) or {}
    objects = selection.get("objects", {}).get(SATELLITE_LAYER_ID, [])
    if not objects:
        return None
    norad = objects[0].get("norad")
    return norad if isinstance(norad, int) else None


def _show_card(deps: PageDependencies, view: LiveView, norad: int | None) -> None:
    """Show the card of the selected satellite as plain text (SEC-13)."""
    if norad is None:
        st.caption(deps.texts["select_satellite"])
        return
    chosen = next((item for item in view.satellites if item.norad == norad), None)
    if chosen is None:
        return
    with st.container(border=True):
        st.text(chosen.name)
        for label, value in card_rows(chosen, deps.texts):
            st.text(f"{label}: {value}")
```

### `tests/ui/test_map_view.py`

```python
"""Tests of the pure map functions: no Streamlit needed (spec 015)."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from orbita.app.live_view import LiveView, SatelliteView
from orbita.domain.elements import Freshness, OrbitType
from orbita.domain.errors import ConfigError
from orbita.domain.observer import GroundPoint, Observer
from orbita.ui.map_view import (
    OBSERVER_LAYER_ID,
    SATELLITE_LAYER_ID,
    TRACK_LAYER_ID,
    build_deck,
    load_basemap,
    satellite_rows,
    track_path,
)


def satellite(norad: int = 25544) -> SatelliteView:
    return SatelliteView(
        norad=norad,
        name="ISS (ZARYA)",
        point=GroundPoint(latitude=10.0, longitude=-75.0, altitude_km=420.0),
        speed_km_s=7.66,
        orbit_type=OrbitType.LOW,
        period_minutes=93,
        distance_km=None,
        owner_code=None,
        launch_date=None,
    )


def view(track: tuple[GroundPoint, ...] = ()) -> LiveView:
    return LiveView(
        freshness=Freshness.NORMAL,
        downloaded_text="2026-10-30 07:00",
        age_days=0,
        satellites=(satellite(),),
        missing_norad=(),
        iss_track=track,
    )


def test_load_basemap_accepts_a_feature_collection(tmp_path: Path) -> None:
    path = tmp_path / "countries.geojson"
    path.write_text(json.dumps({"type": "FeatureCollection", "features": []}), encoding="utf-8")
    assert load_basemap(path)["type"] == "FeatureCollection"


def test_load_basemap_rejects_other_json(tmp_path: Path) -> None:
    path = tmp_path / "countries.geojson"
    path.write_text(json.dumps({"type": "Feature"}), encoding="utf-8")
    with pytest.raises(ConfigError):
        load_basemap(path)


def test_satellite_rows_put_longitude_first() -> None:
    assert satellite_rows(view())[0]["position"] == [-75.0, 10.0]


def test_track_path_has_one_pair_per_point() -> None:
    track = tuple(GroundPoint(latitude=0.0, longitude=float(index)) for index in range(91))
    path = track_path(track)
    assert len(path) == 91
    assert path[0] == [0.0, 0.0]


def test_deck_has_three_layers_without_an_observer() -> None:
    deck = build_deck(view(), None, {"type": "FeatureCollection", "features": []})
    assert [layer.id for layer in deck.layers] == ["basemap", TRACK_LAYER_ID, SATELLITE_LAYER_ID]


def test_deck_adds_the_observer_layer_when_the_location_is_known() -> None:
    deck = build_deck(view(), Observer(latitude=3.45, longitude=-76.53), {"type": "FeatureCollection", "features": []})
    assert OBSERVER_LAYER_ID in [layer.id for layer in deck.layers]


def test_deck_tooltip_is_plain_text_and_no_tiles_are_requested() -> None:
    deck = build_deck(view(), None, {"type": "FeatureCollection", "features": []})
    serialized = deck.to_json()
    assert '"html"' not in serialized
    assert '"text"' in serialized
```

### `tests/ui/test_cards.py`

```python
"""Tests of the card and notice texts (spec 015). The texts are a small copy of the keys used here."""

from __future__ import annotations

from datetime import date

from orbita.app.live_view import SatelliteView
from orbita.domain.elements import Freshness, OrbitType
from orbita.domain.observer import GroundPoint
from orbita.ui.cards import card_rows, country_label, freshness_notice

TEXTS = {
    "missing_value": "—",
    "distance_approx": "≈ {km} km",
    "label_altitude": "Altura",
    "label_speed": "Velocidad",
    "label_orbit_type": "Tipo de órbita",
    "label_period": "Periodo",
    "label_distance": "Distancia a ti",
    "label_country": "País",
    "label_launch_date": "Fecha de lanzamiento",
    "label_years_in_orbit": "Años en órbita",
    "orbit_geostationary": "Geoestacionaria",
    "orbit_polar": "Polar",
    "orbit_low": "Baja",
    "orbit_other": "Otra",
    "owner_US": "Estados Unidos",
    "no_orbital_data": "No hay datos orbitales guardados.",
    "too_old_data": "Los datos tienen más de 14 días.",
    "stale_data": "Datos de hace {days} días.",
}


def satellite(distance: int | None = None, owner: str | None = None) -> SatelliteView:
    return SatelliteView(
        norad=25544,
        name="ISS (ZARYA)",
        point=GroundPoint(latitude=10.0, longitude=-75.0, altitude_km=420.4),
        speed_km_s=7.664,
        orbit_type=OrbitType.LOW,
        period_minutes=93,
        distance_km=distance,
        owner_code=owner,
        launch_date=date(1998, 11, 20) if owner else None,
    )


def test_altitude_has_no_decimals_and_speed_has_two() -> None:
    rows = dict(card_rows(satellite(), TEXTS))
    assert rows["Altura"] == "420 km"
    assert rows["Velocidad"] == "7.66 km/s"


def test_distance_row_shows_approximation_sign_when_known() -> None:
    assert dict(card_rows(satellite(distance=400), TEXTS))["Distancia a ti"] == "≈ 400 km"


def test_distance_row_shows_missing_value_without_location() -> None:
    assert dict(card_rows(satellite(), TEXTS))["Distancia a ti"] == "—"


def test_known_owner_code_is_translated_and_unknown_is_kept() -> None:
    assert country_label("US", TEXTS) == "Estados Unidos"
    assert country_label("XYZ", TEXTS) == "XYZ"
    assert country_label(None, TEXTS) == "—"


def test_orbit_type_uses_the_spanish_text() -> None:
    assert dict(card_rows(satellite(), TEXTS))["Tipo de órbita"] == "Baja"


def test_no_notice_for_normal_data() -> None:
    assert freshness_notice(Freshness.NORMAL, 0, TEXTS) is None


def test_stale_notice_shows_the_age_in_days() -> None:
    assert freshness_notice(Freshness.STALE, 4, TEXTS) == "Datos de hace 4 días."


def test_too_old_and_missing_data_have_their_own_notices() -> None:
    assert freshness_notice(Freshness.TOO_OLD, 15, TEXTS) == "Los datos tienen más de 14 días."
    assert freshness_notice(None, None, TEXTS) == "No hay datos orbitales guardados."
```

## Pasos

1. **Comprobar pydeck y la firma de `st.pydeck_chart`:**
   ```powershell
   uv run python -c "import pydeck; print(pydeck.__version__)"
   uv run python -c "import streamlit as st, inspect; print(inspect.signature(st.pydeck_chart))"
   ```
   La versión de pydeck debe ser 0.9 o posterior. La firma debe incluir `on_select` y `selection_mode`. Si no los incluye,
   no se improvisa: se cambia la selección por una lista (`st.selectbox`) y se registra en `specs\README.md`.
2. **Crear la rama:** `git switch -c feature/015-interfaz-mapa-fichas`.
3. **Crear los cinco archivos** con el contenido de este documento. Como `locales/es.json` ya tiene la clave
   `select_satellite` (añadida en la spec 009), no hay que tocarlo.
4. **Ejecutar los tests:** `uv run pytest -v`.
5. **Comprobar calidad:** `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy src`,
   `uv run pre-commit run --all-files`. Si mypy se queja de `pydeck` o `streamlit`, la supresión se escribe con su código
   exacto, como indica `ARCHITECTURE.md` §6.
6. **Comprobar que la interfaz no escribe HTML de datos:**
   `Select-String -Path src\orbita\ui\*.py -Pattern 'unsafe_allow_html|text_input|file_uploader'` no debe mostrar nada.
7. **Commit y merge** con el mensaje `015: interfaz mapa y fichas`.

## Casos borde y manejo de errores

1. Con datos de más de 14 días: el mapa se dibuja sin satélites y aparece el aviso `too_old_data` (SEC-25).
2. Sin datos guardados: no hay mapa, aparece `no_orbital_data`, y el resto de la página sigue funcionando.
3. Un error en el fragmento: se registra con `logger.exception` y aparece `unexpected_error`; el fragmento sigue
   programado, así que el mapa vuelve en el siguiente refresco si el error era transitorio.
4. Un satélite sin datos aparece en la lista "Sin datos de" y no en el mapa.
5. Un nombre de satélite con `<b>` se muestra como texto (SEC-13).
6. Sin ubicación, la ficha muestra "—" en distancia, y el aviso `location_unavailable` aparece una vez (RF-12).

## Tests de aceptación

- `test_map_view.py`: un archivo base válido se acepta y uno que no es `FeatureCollection` se rechaza; las posiciones van
  en orden longitud, latitud; la trayectoria tiene un par por punto; el mapa tiene 3 capas sin ubicación y 4 con ella;
  el tooltip es texto y no HTML.
- `test_cards.py`: altura sin decimales (`420 km`); velocidad con dos (`7.66 km/s`); distancia con "≈" o "—"; país
  traducido o mostrado tal cual; tipo de órbita en español; aviso de datos viejos con los días; sin aviso con datos
  normales.
- Prueba manual (en la spec 017, cuando exista `orbita.main`): el mapa se ve en 1366 × 768 sin desplazamiento
  horizontal, y al tocar un satélite aparece su ficha.

## Fuera de alcance

- El botón "Mi ubicación" y la validación de la ubicación del navegador: spec 016.
- El arranque de la aplicación y la composición de objetos: spec 017.
- El número de años en órbita y el país con datos reales: spec 018.

## Definition of Done

Todos los comandos en PowerShell, desde la carpeta `orbita`.

- [ ] `uv run python -c "import pydeck; print(pydeck.__version__)"` → versión 0.9 o posterior.
- [ ] `uv run pytest -v` → todos los tests pasan.
- [ ] `Select-String -Path src\orbita\ui\*.py -Pattern 'unsafe_allow_html|text_input|file_uploader|chat_input'` → sin salida.
- [ ] `Select-String -Path src\orbita\ui\*.py -Pattern 'orbita\.(adapters|ports)'` → sin salida.
- [ ] `uv run ruff check .`, `uv run mypy src` y `uv run pre-commit run --all-files` sin errores.
- [ ] `uv run pytest tests/test_architecture.py -v` → 7 passed.
- [ ] `git status` → `nothing to commit, working tree clean` después del merge.
