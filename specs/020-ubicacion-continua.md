# 020 - Ubicación continua (P3)

## Objetivo

Al terminar, con un interruptor visible "Seguir mi ubicación mientras la página está abierta", el navegador envía
posiciones nuevas mientras el usuario se mueve, y las distancias y el marcador se actualizan (RF-15). El interruptor se
puede apagar en cualquier momento (SEC-01). La ubicación sigue viviendo solo en memoria y no sale del navegador hacia
ningún servicio externo (SEC-04).

## Depende de

- 016 (lectura de una vez y validación de la ubicación), 019 (el repositorio ya está en orden antes de la fase de publicación).

## Decisión previa: ADR-007 (obligatorio antes de codificar)

`ADR-004` dice que la ubicación continua necesita un ADR nuevo. `streamlit-geolocation` solo lee una vez
(`getCurrentPosition`), así que la decisión es escribir un componente mínimo propio con `watchPosition`. Se crea el
archivo `docs\adr\ADR-007-continuous-location-own-component.md` con este contenido antes de la rama:

```markdown
# ADR-007 - Continuous location with a minimal own component (P3)

- Status: Accepted (2026-10-31)

## Context

RF-15 needs the user's marker and the distances to follow the user while walking. `streamlit-geolocation` (ADR-004)
calls `getCurrentPosition` once and cannot keep reading. SEC-22 requires reviewing any component before choosing it.

## Decision

Write a minimal Streamlit component of about 60 lines of HTML and JavaScript in `src/orbita/ui/static/geowatch/`.
It calls `navigator.geolocation.watchPosition` with high accuracy, sends each reading to Python with the component
protocol, and stops the watch when the component is removed (the switch turned off or the page closed). It has no
libraries, makes no network request and sends nothing except the reading.

## Rejected alternatives

- Calling `streamlit-geolocation` again on a timer: each call asks the browser for a new position and the page reruns
  every time; it is slower and noisier, and the component is not designed for it.
- `streamlit_js_eval` (ADR-004): it runs arbitrary JavaScript, which is more power than this feature needs.

## Consequences

- The only JavaScript of the project lives in one file, reviewed in the spec 020 tests (no network calls, no `eval`).
- The reading is sent with `postMessage` to the parent page; it is never sent to a server by this component.
- Battery: the watch stops when the switch is off; turning it on again asks for the permission only if the browser
  forgot it.

## Affected governing rules

`security-rules.md` SEC-01, SEC-04, SEC-14, SEC-22, SEC-39; `docs/00-requirements.md` RF-15; `ADR-004`.
```

## Archivos a crear

1. `src/orbita/ui/continuous_location.py`
2. `src/orbita/ui/static/geowatch/index.html`
3. `tests/ui/test_continuous_location.py`

Son tres archivos: dos de código (Python y HTML/JavaScript) y un test. La capa es `ui`.

## Dependencias externas

Ninguna nueva: el componente usa `streamlit.components.v1` de Streamlit.

## Contenido exacto de los archivos

### `src/orbita/ui/continuous_location.py`

```python
"""Continuous location (P3): a minimal browser component keeps watchPosition running while the switch is on (ADR-007).

The component is the only JavaScript of the project. It sends readings only to this page (SEC-04). Turning the
switch off stops the watch (SEC-01). The reading is validated with the same rules as the one-time location (SEC-14).
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any, Final

import streamlit as st  # type: ignore[import-untyped]
import streamlit.components.v1 as components  # type: ignore[import-untyped]

from orbita.ui.location import (
    ACCURACY_KEY,
    OBSERVER_KEY,
    accuracy_from_reading,
    observer_from_reading,
)

STATIC_DIR: Final = Path(__file__).resolve().parent / "static" / "geowatch"
SWITCH_KEY: Final = "continuous_location_switch"
_geowatch: Any = components.declare_component("orbita_geowatch", path=str(STATIC_DIR))


def continuous_location_section(texts: Mapping[str, str]) -> None:
    """Draw the switch and, while it is on, keep the latest valid reading in memory (SEC-02)."""
    enabled = st.toggle(texts["follow_location"], key=SWITCH_KEY)
    if not enabled:
        return
    reading: Any = _geowatch(key="geowatch", default=None)
    observer = observer_from_reading(reading)
    if observer is not None:
        st.session_state[OBSERVER_KEY] = observer
        st.session_state[ACCURACY_KEY] = accuracy_from_reading(reading)
```

### `src/orbita/ui/static/geowatch/index.html`

```html
<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <title>Órbita: ubicación continua</title>
</head>
<body>
<script>
  // Streamlit component protocol, no libraries, no network requests (ADR-007, SEC-04).
  (function () {
    var watchId = null;

    function send(type, data) {
      window.parent.postMessage(Object.assign({ isStreamlitMessage: true, type: type }, data), "*");
    }

    function onReading(position) {
      send("streamlit:setComponentValue", {
        value: {
          latitude: position.coords.latitude,
          longitude: position.coords.longitude,
          accuracy: position.coords.accuracy
        },
        dataType: "json"
      });
    }

    function onError() {
      // The error is not sent: it could describe the device. The page keeps the last valid reading.
    }

    function startWatch() {
      if (watchId === null && navigator.geolocation) {
        watchId = navigator.geolocation.watchPosition(onReading, onError, {
          enableHighAccuracy: true,
          maximumAge: 5000
        });
      }
    }

    function stopWatch() {
      if (watchId !== null) {
        navigator.geolocation.clearWatch(watchId);
        watchId = null;
      }
    }

    window.addEventListener("message", function (event) {
      if (event.data && event.data.type === "streamlit:render") {
        startWatch();
      }
    });
    window.addEventListener("pagehide", stopWatch);
    window.addEventListener("beforeunload", stopWatch);

    send("streamlit:componentReady", { apiVersion: 1 });
    send("streamlit:setFrameHeight", { height: 0 });
  })();
</script>
</body>
</html>
```

### `tests/ui/test_continuous_location.py`

```python
"""Tests of the continuous location component (spec 020): the file is present and makes no network calls (SEC-04)."""

from __future__ import annotations

from pathlib import Path

from orbita.ui.continuous_location import STATIC_DIR

INDEX = STATIC_DIR / "index.html"
FORBIDDEN_IN_COMPONENT = (
    "fetch(",
    "XMLHttpRequest",
    "WebSocket",
    "sendBeacon",
    "eval(",
    "http://",
    "https://",
)


def read_index() -> str:
    return Path(INDEX).read_text(encoding="utf-8")


def test_component_file_exists() -> None:
    assert INDEX.is_file()


def test_component_uses_watch_position_and_stops_it() -> None:
    source = read_index()
    assert "watchPosition" in source
    assert "clearWatch" in source


def test_component_makes_no_network_request_and_runs_no_eval() -> None:
    source = read_index()
    for token in FORBIDDEN_IN_COMPONENT:
        assert token not in source, token
```

Cambio en `locales/es.json`: se añade la clave `"follow_location": "Seguir mi ubicación mientras la página está abierta"`.

## Pasos

1. **Crear el ADR:** escribir `docs\adr\ADR-007-continuous-location-own-component.md` con el bloque de arriba, y cambiar
   la sección "Decision" del ADR-004 para enlazarlo. Hacer commit en `main` con `docs: ADR-007 ubicacion continua`.
2. **Crear la rama:** `git switch -c feature/020-ubicacion-continua`.
3. **Crear los tres archivos** y añadir la clave `follow_location` en `locales\es.json`.
4. **Ejecutar los tests:** `uv run pytest -v`.
5. **Probar a mano** con `uv run streamlit run src\orbita\main.py` en `localhost`: activar el interruptor, aceptar el
   permiso, caminar o cambiar la ubicación simulada en las herramientas de desarrollo del navegador (sensores), y ver que el
   marcador se mueve. Apagar el interruptor: el marcador deja de moverse.
6. **Comprobar calidad:** `uv run ruff check .`, `uv run mypy src`, `uv run pre-commit run --all-files`.
7. **Commit y merge** con el mensaje `020: ubicacion continua`.

## Casos borde y manejo de errores

1. El navegador niega el permiso: el componente no envía lectura; la página conserva la última lectura válida de la
   sesión, o muestra `location_unavailable`.
2. El interruptor se apaga: el componente desaparece de la página, y su iframe se elimina con su script (se deja de leer).
3. La página se cierra: `pagehide` detiene el seguimiento.
4. Una lectura con precisión negativa o coordenadas fuera de rango se ignora (SEC-14).

## Tests de aceptación

- El archivo del componente existe, usa `watchPosition` y `clearWatch`, y no contiene llamadas de red, `eval` ni URLs.
- Prueba manual: el marcador se mueve al cambiar la ubicación simulada, y deja de moverse al apagar el interruptor.

## Fuera de alcance

- El historial de ubicaciones: nunca (SEC-02, fuera de alcance del proyecto).
- Las predicciones de pasos: v2.

## Definition of Done

- [ ] `docs\adr\ADR-007-continuous-location-own-component.md` existe y está en `main`.
- [ ] `uv run pytest -v` → todos los tests pasan (los 3 nuevos incluidos).
- [ ] `Select-String -Path src\orbita\ui\static\geowatch\index.html -Pattern 'fetch\(|XMLHttpRequest|https?://|eval\('` → sin salida.
- [ ] La prueba manual del marcador en movimiento está hecha y anotada en esta spec.
- [ ] `git status` → `nothing to commit, working tree clean` después del merge.
