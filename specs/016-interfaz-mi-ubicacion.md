# 016 - Interfaz: "Mi ubicación"

## Objetivo

Al terminar, el usuario puede pulsar "Mi ubicación" y aceptar el permiso del navegador. La página lee la ubicación una
sola vez, la valida con la regla de `DESIGN.md` §4.5, la guarda solo en memoria (`st.session_state`) como `Observer` y
muestra el marcador en el mapa, la precisión que informa el navegador y las distancias a cada satélite (RF-10, RF-11).
Junto al botón aparece el texto de privacidad (SEC-05). Si el permiso se niega, la página sigue funcionando sin distancias
(RF-12).

## Depende de

- 006 (validación de la ubicación, `Observer`), 015 (la página y el mapa, que ya saben dibujar el marcador).

## Archivos rectores aplicables

- `ADR-004` (componente `streamlit-geolocation` para la lectura de una vez; revisión de la fuente, la licencia y los
  issues antes de fijarlo, SEC-22).
- `security-rules.md` SEC-01 (la ubicación se lee solo tras el botón y el permiso), SEC-02 (solo en `st.session_state`,
  sin adaptadores), SEC-03 (nunca en logs; `Observer` oculta sus coordenadas), SEC-05 (texto de privacidad junto al
  botón), SEC-14 (validación antes de usar; precisión finita y ≥ 0), SEC-24 (la precisión se muestra junto al marcador).
- `ARCHITECTURE.md` §2 (`orbita.ui` es la única capa que usa el componente), §7.1 (el componente solo está en la interfaz).
- `docs/00-requirements.es.md` RF-10, RF-11, RF-12, RNF-05.

## Archivos a crear

1. `src/orbita/ui/location.py`
2. `tests/ui/test_location.py`

Son dos archivos nuevos en la capa `ui`, más un cambio de 3 líneas en `src/orbita/ui/page.py` (paso 3), que es el único
archivo de la spec 015 que cambia. Total: tres archivos de código.

## Dependencias externas

- `streamlit-geolocation`, versión exacta, con `uv add`. Antes de fijarlo se registra en `docs/adr/ADR-004` la versión, la
  fecha de su última publicación y sus issues abiertos (SEC-22), como exige el propio ADR.

## Contenido exacto de los archivos

### `src/orbita/ui/location.py`

```python
"""'My location' support through streamlit-geolocation (ADR-004, RF-10).

The reading lives only in st.session_state as a validated Observer (SEC-01, SEC-02). It is never logged, never written
to disk (SEC-03) and never sent to any service. Values that fail validation are ignored (SEC-14).
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from typing import Any, Final

import streamlit as st  # type: ignore[import-untyped]
from streamlit_geolocation import streamlit_geolocation  # type: ignore[import-untyped]

from orbita.domain.errors import InvalidLocationError
from orbita.domain.observer import Observer

OBSERVER_KEY: Final = "observer"
ACCURACY_KEY: Final = "accuracy_m"


def observer_from_reading(reading: Mapping[str, Any] | None) -> Observer | None:
    """Turn the component output into a validated Observer, or None (SEC-14, DESIGN.md §4.5)."""
    if not reading:
        return None
    latitude = reading.get("latitude")
    longitude = reading.get("longitude")
    if not _is_number(latitude) or not _is_number(longitude):
        return None
    try:
        return Observer(latitude=float(latitude), longitude=float(longitude))
    except InvalidLocationError:
        return None


def accuracy_from_reading(reading: Mapping[str, Any] | None) -> float | None:
    """Return the accuracy in meters if it is a finite number not below zero; otherwise None (SEC-14)."""
    if not reading:
        return None
    accuracy = reading.get("accuracy")
    if not _is_number(accuracy) or float(accuracy) < 0:
        return None
    return float(accuracy)


def location_section(texts: Mapping[str, str]) -> None:
    """Draw the privacy text, the button and the accuracy. The observer is kept only in memory (SEC-02)."""
    st.caption(texts["location_privacy"])
    reading = streamlit_geolocation()
    observer = observer_from_reading(reading)
    if observer is not None:
        st.session_state[OBSERVER_KEY] = observer
        st.session_state[ACCURACY_KEY] = accuracy_from_reading(reading)
    accuracy = st.session_state.get(ACCURACY_KEY)
    if st.session_state.get(OBSERVER_KEY) is not None and accuracy is not None:
        st.caption(texts["location_accuracy"].format(meters=round(accuracy)))


def _is_number(value: object) -> bool:
    """Return True for a finite int or float that is not a boolean."""
    if isinstance(value, bool) or not isinstance(value, int | float):
        return False
    return math.isfinite(value)
```

### `tests/ui/test_location.py`

```python
"""Tests of the validation of the browser location reading (spec 016). No browser and no Streamlit session needed."""

from __future__ import annotations

import math

import pytest

from orbita.ui.location import accuracy_from_reading, observer_from_reading


def test_valid_reading_becomes_an_observer() -> None:
    observer = observer_from_reading({"latitude": 3.45, "longitude": -76.53})
    assert observer is not None
    assert observer.latitude == 3.45


def test_limit_values_are_accepted() -> None:
    assert observer_from_reading({"latitude": 90.0, "longitude": 180.0}) is not None


@pytest.mark.parametrize(
    "reading",
    [
        None,
        {},
        {"latitude": 90.1, "longitude": 0.0},
        {"latitude": 0.0, "longitude": -180.1},
        {"latitude": "3.4", "longitude": 1.0},
        {"latitude": True, "longitude": 1.0},
        {"latitude": math.nan, "longitude": 0.0},
    ],
)
def test_invalid_readings_give_no_observer(reading: dict[str, object] | None) -> None:
    assert observer_from_reading(reading) is None


def test_accuracy_is_kept_when_finite_and_not_negative() -> None:
    assert accuracy_from_reading({"accuracy": 12.5}) == 12.5


@pytest.mark.parametrize("reading", [None, {}, {"accuracy": -1.0}, {"accuracy": math.nan}, {"accuracy": "10"}])
def test_invalid_accuracy_is_ignored(reading: dict[str, object] | None) -> None:
    assert accuracy_from_reading(reading) is None


def test_observer_representation_hides_the_coordinates() -> None:
    observer = observer_from_reading({"latitude": 3.45, "longitude": -76.53})
    assert observer is not None
    assert "3.45" not in repr(observer)
    assert "76.53" not in repr(observer)
```

## Cambio al archivo de la spec 015: `src/orbita/ui/page.py`

Tres cambios exactos. Se aplican sobre el archivo tal como lo deja la spec 015:

1. Se quita la línea `OBSERVER_KEY = "observer"`: la clave ahora la define `location.py`.
2. Se añade el import `from orbita.ui.location import OBSERVER_KEY, location_section`, justo después de la línea
   `from orbita.ui.cards import card_rows, freshness_notice`.
3. En `render_page`, justo después de `deps.refresh.execute()`, se añade la línea `location_section(deps.texts)`.

El resultado es que `render_page` queda así:

```python
def render_page(deps: PageDependencies) -> None:
    """Draw the title, the approximation notice, run the refresh once and start the live map."""
    st.set_page_config(page_title=deps.texts["title"], layout="wide")
    st.title(deps.texts["title"])
    st.caption(deps.texts["approximate_notice"])
    deps.refresh.execute()
    location_section(deps.texts)
    _make_live_fragment(deps)()
```

## Pasos

1. **Crear la rama:** `git switch -c feature/016-interfaz-mi-ubicacion`.
2. **Revisar la fuente del componente (SEC-22) y registrarla en el ADR.** Abrir el repositorio de `streamlit-geolocation`
   en GitHub y PyPI; anotar la versión más reciente, su fecha de publicación, la licencia y los issues abiertos. Escribirlos
   en `docs\adr\ADR-004-browser-location-component.md`, en una sección nueva "Revisión de la versión fijada". No se fija
   una versión sin esta anotación.
3. **Añadir la dependencia:**
   ```powershell
   uv add "streamlit-geolocation==<version>"
   ```
   Sustituir `<version>` por la versión anotada en el paso 2.
4. **Crear los dos archivos** de la sección de contenido.
5. **Aplicar el cambio a `src\orbita\ui\page.py`** descrito arriba (tres líneas).
6. **Comprobar la etiqueta del botón.** Ejecutar la aplicación cuando exista `orbita.main` (spec 017) y mirar el texto del
   botón del componente: debe estar en español (RNF-04). Si el componente muestra un texto en inglés y no admite cambiarlo,
   se anota en `specs\README.md` y se decide con un ADR si se escribe un botón propio. No se improvisa.
7. **Ejecutar los tests:** `uv run pytest -v`.
8. **Comprobar calidad:** `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy src`,
   `uv run pre-commit run --all-files`.
9. **Commit y merge** con el mensaje `016: interfaz mi ubicacion`.

## Casos borde y manejo de errores

1. El usuario niega el permiso: el componente devuelve nada o un error; `observer_from_reading` devuelve `None`, la página
   muestra `location_unavailable` y el mapa sin distancias (RF-12).
2. El navegador da una ubicación fuera de rango (por ejemplo, latitud 91): se ignora (SEC-14).
3. La precisión llega como `NaN` o negativa: no se muestra, pero la ubicación sí se usa si es válida.
4. En un refresco que no es el de pulsar el botón, el componente puede devolver nada: se conserva el `Observer` de la
   sesión, sin volver a pedir permiso.
5. Un `Observer` nunca aparece en un log: su `repr` es `Observer(<hidden>)` (SEC-03).

## Tests de aceptación

- `test_location.py`: una lectura válida da un `Observer`; los límites 90 y 180 se aceptan; latitud 90.1, longitud −180.1,
  texto, booleano y NaN dan `None`; una precisión de 12.5 se acepta; precisión negativa, NaN o texto se ignora; la
  representación de `Observer` no muestra las coordenadas.
- Prueba manual (cuando exista la spec 017): en `localhost`, pulsar el botón, aceptar el permiso, ver el marcador y la
  precisión, y ver las distancias en las fichas. Negar el permiso y ver `location_unavailable`.

## Fuera de alcance

- La ubicación que se actualiza sola mientras el usuario camina (P3): spec 020, con un ADR nuevo.
- La publicación por HTTPS (necesaria para que el navegador dé la ubicación en un celular): spec 021.

## Definition of Done

Todos los comandos en PowerShell, desde la carpeta `orbita`.

- [ ] `docs\adr\ADR-004-browser-location-component.md` tiene la sección "Revisión de la versión fijada" con versión y fecha.
- [ ] `uv run pytest -v` → todos los tests pasan.
- [ ] `Select-String -Path src\orbita\*\*\*.py -Pattern 'Observer' ` → ninguna línea en `adapters` (usar
  `Get-ChildItem -Recurse src\orbita\adapters -Filter *.py | Select-String -Pattern Observer` → sin salida).
- [ ] `Select-String -Path src\orbita\ui\location.py -Pattern 'logger|print\('` → sin salida.
- [ ] `uv run ruff check .`, `uv run mypy src` y `uv run pre-commit run --all-files` sin errores.
- [ ] `uv lock --check` → sin errores.
- [ ] `git status` → `nothing to commit, working tree clean` después del merge.
