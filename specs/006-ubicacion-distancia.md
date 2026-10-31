# 006 - Reglas: distancia al observador

## Objetivo

Al terminar, el dominio calcula la distancia en línea recta entre la ubicación del usuario y un punto sobre la Tierra o
sobre un satélite, y la devuelve redondeada a los 10 km más cercanos (DESIGN.md §4.4). La validación de la ubicación
(DESIGN.md §4.5) ya quedó en la spec 003, en `Observer`; esta spec solo añade el cálculo. El texto "≈ N km" no se
escribe aquí: lo muestra la interfaz desde `locales/es.json` (RNF-04).

## Depende de

- 003 (`Observer`, `GroundPoint` y su validación).

## Archivos rectores aplicables

- `DESIGN.md` §4.4 (Tierra esférica de radio 6371 km; el observador tiene altitud 0; distancia en línea recta; redondeo
  a 10 km), §4.5 (ubicación válida).
- `ARCHITECTURE.md` §2 (el dominio solo usa la biblioteca estándar y su propio paquete), §7.2 (los textos al usuario
  salen de `locales/es.json`).
- `docs/00-requirements.es.md` RF-11 (ejemplos: 400 km y ≈ 9010 km).
- `security-rules.md` SEC-03 (la ubicación no se registra).

## Archivos a crear

1. `src/orbita/domain/distance_rules.py`
2. `tests/domain/test_distance_rules.py`

Son dos archivos, dentro del límite de la regla 3 del índice.

## Dependencias externas

Ninguna. Se usan `math` de la biblioteca estándar.

## Contenido exacto de los archivos

### `src/orbita/domain/distance_rules.py`

```python
"""Straight-line distance from the observer to a satellite (DESIGN.md §4.4)."""

from __future__ import annotations

import math

from orbita.domain.observer import GroundPoint, Observer

EARTH_RADIUS_KM = 6371.0
DISTANCE_STEP_KM = 10


def to_cartesian(point: GroundPoint) -> tuple[float, float, float]:
    """Convert a point above the spherical Earth to x, y, z in km (DESIGN.md §4.4)."""
    radius = EARTH_RADIUS_KM + point.altitude_km
    lat = math.radians(point.latitude)
    lon = math.radians(point.longitude)
    x = radius * math.cos(lat) * math.cos(lon)
    y = radius * math.cos(lat) * math.sin(lon)
    z = radius * math.sin(lat)
    return x, y, z


def straight_distance_km(observer: Observer, point: GroundPoint) -> float:
    """Return the straight-line distance in km between the observer (altitude 0) and the point."""
    surface = GroundPoint(latitude=observer.latitude, longitude=observer.longitude)
    x1, y1, z1 = to_cartesian(surface)
    x2, y2, z2 = to_cartesian(point)
    return math.sqrt((x1 - x2) ** 2 + (y1 - y2) ** 2 + (z1 - z2) ** 2)


def distance_km_rounded(observer: Observer, point: GroundPoint) -> int:
    """Return the distance in km, rounded half up to the nearest 10 km."""
    steps = math.floor(straight_distance_km(observer, point) / DISTANCE_STEP_KM + 0.5)
    return steps * DISTANCE_STEP_KM
```

### `tests/domain/test_distance_rules.py`

```python
"""Tests of the observer distance rules of spec 006."""

from __future__ import annotations

import math

from orbita.domain.distance_rules import distance_km_rounded, straight_distance_km, to_cartesian
from orbita.domain.observer import GroundPoint, Observer

ORIGIN = Observer(latitude=0.0, longitude=0.0)


def test_point_directly_above_the_observer_is_at_its_altitude() -> None:
    assert math.isclose(straight_distance_km(ORIGIN, GroundPoint(0.0, 0.0, 400.0)), 400.0)


def test_point_on_the_horizon_is_about_9010_km() -> None:
    assert distance_km_rounded(ORIGIN, GroundPoint(0.0, 90.0, 0.0)) == 9010


def test_distance_is_rounded_to_the_nearest_10_km() -> None:
    assert distance_km_rounded(ORIGIN, GroundPoint(0.0, 0.0, 404.0)) == 400
    assert distance_km_rounded(ORIGIN, GroundPoint(0.0, 0.0, 405.0)) == 410


def test_distance_to_the_same_point_is_zero() -> None:
    assert distance_km_rounded(ORIGIN, GroundPoint(0.0, 0.0, 0.0)) == 0


def test_north_pole_is_on_the_z_axis() -> None:
    x, y, z = to_cartesian(GroundPoint(90.0, 0.0, 0.0))
    assert math.isclose(x, 0.0, abs_tol=1e-6)
    assert math.isclose(y, 0.0, abs_tol=1e-6)
    assert math.isclose(z, 6371.0)
```

## Pasos

1. **Crear la rama de la spec:**
   ```powershell
   git switch -c feature/006-ubicacion-distancia
   ```
2. **Verificar los archivos:** `Get-ChildItem -Name src\orbita\domain, tests\domain`. Si falta alguno, pegar su
   contenido desde la spec.
3. **Ejecutar los tests:**
   ```powershell
   uv run pytest -v
   ```
   Deben pasar los 70 tests anteriores más los 5 nuevos: `75 passed`.
4. **Revisar calidad:**
   ```powershell
   uv run ruff check .
   uv run ruff format --check .; echo $LASTEXITCODE
   uv run mypy src
   uv run pre-commit run --all-files
   ```
5. **Commit y merge:**
   ```powershell
   git add .
   git commit -m "006: reglas de distancia al observador"
   git switch main
   git merge --no-ff feature/006-ubicacion-distancia -m "Merge spec 006: reglas de distancia al observador"
   git branch -d feature/006-ubicacion-distancia
   ```
6. **Marcar la spec como implementada** en `specs\README.md` con un commit de documentación en `main`.

## Casos borde y manejo de errores

1. Un test de distancia falla por un valor de un decimal: el redondeo es a 10 km; comprobar primero el valor esperado
   con la fórmula de `DESIGN.md` §4.4.
2. `straight_distance_km` recibe una ubicación inválida: no puede ocurrir, porque `Observer` rechaza los valores fuera
   de rango al construirse (spec 003).
3. Se pide un texto como "≈ 9010 km" desde el dominio: no se hace aquí; el texto sale de `locales/es.json` en la
   interfaz (spec 015), y el dominio devuelve solo el número.

## Tests de aceptación

Son los cinco tests de `tests/domain/test_distance_rules.py`: la distancia a un punto justo encima del observador
(400 km, RF-11), la distancia al horizonte (≈ 9010 km, RF-11), el redondeo a 10 km en ambos sentidos (404 km → 400 km,
405 km → 410 km), la distancia cero, y la posición del polo norte en el eje z (radio 6371 km).

## Fuera de alcance

- La presentación del texto "≈ N km" y el mensaje de ubicación no disponible: spec 015 y 016.
- El marcador del usuario en el mapa: spec 015.

## Definition of Done

Todos los comandos en PowerShell, desde la carpeta `orbita`.

- [ ] `uv run pytest -v` → `75 passed` y `echo $LASTEXITCODE` → `0`.
- [ ] `Select-String -Path src\orbita\domain\distance_rules.py -Pattern 'import (streamlit|httpx|pydeck|skyfield)'` → sin salida.
- [ ] `uv run ruff check .` → `All checks passed!`
- [ ] `uv run ruff format --check .; echo $LASTEXITCODE` → `0`.
- [ ] `uv run mypy src` → `Success: no issues found`.
- [ ] `uv run pre-commit run --all-files` → todos los hooks en `Passed`.
- [ ] `git log --oneline --graph` → muestra el commit de la spec 006 y el merge.
- [ ] `git status` → `nothing to commit, working tree clean`.
