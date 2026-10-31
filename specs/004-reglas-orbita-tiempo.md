# 004 - Reglas: tipo de órbita, periodo y hora de Colombia

## Objetivo

Al terminar, el dominio clasifica la órbita de un satélite (geoestacionaria, polar, baja u otra), calcula su periodo
en minutos y convierte un instante UTC a hora de Colombia para mostrarlo al usuario. Son reglas puras: reciben números
o fechas y devuelven un resultado, sin leer el reloj ni la red.

## Depende de

- 003 (los tipos `OrbitType`, `require_utc` y `DataValidationError` ya existen).

## Archivos rectores aplicables

- `DESIGN.md` §4.1 (tipo de órbita, en este orden: geoestacionaria, polar, baja, otra), §4.3 (tiempo: UTC − 5 sin horario
  de verano), §4.6 (periodo = 1440 / movimiento medio, redondeado al entero más cercano).
- `ARCHITECTURE.md` §2 (el dominio no importa nada fuera de la biblioteca estándar y del propio dominio), §6 (el dominio
  no lee el reloj: recibe las fechas como argumento).
- `docs/00-requirements.es.md` RF-03 (vectores de prueba del tipo de órbita y del periodo) y RF-09 (hora de Colombia).

## Archivos a crear

1. `src/orbita/domain/orbit_rules.py`
2. `src/orbita/domain/time_rules.py`
3. `tests/domain/test_rules.py`

Son tres archivos, dentro del límite de la regla 3 del índice.

## Dependencias externas

Ninguna. Se usan `math` y `datetime` de la biblioteca estándar.

## Contenido exacto de los archivos

### `src/orbita/domain/orbit_rules.py`

```python
"""Orbit type and orbital period (DESIGN.md §4.1 and §4.6)."""

from __future__ import annotations

import math

from orbita.domain.elements import OrbitType

GEO_MEAN_MOTION_MIN = 0.99
GEO_MEAN_MOTION_MAX = 1.01
GEO_MAX_INCLINATION_DEG = 10.0
POLAR_MIN_INCLINATION_DEG = 80.0
POLAR_MAX_INCLINATION_DEG = 100.0
LOW_MIN_MEAN_MOTION = 11.25
MINUTES_PER_DAY = 1440.0


def classify_orbit(inclination_deg: float, mean_motion_rev_day: float) -> OrbitType:
    """Return the orbit type. The rules are applied in order and the first one that holds wins."""
    geo_mean_motion = GEO_MEAN_MOTION_MIN <= mean_motion_rev_day <= GEO_MEAN_MOTION_MAX
    if geo_mean_motion and inclination_deg < GEO_MAX_INCLINATION_DEG:
        return OrbitType.GEOSTATIONARY
    if POLAR_MIN_INCLINATION_DEG <= inclination_deg <= POLAR_MAX_INCLINATION_DEG:
        return OrbitType.POLAR
    if mean_motion_rev_day >= LOW_MIN_MEAN_MOTION:
        return OrbitType.LOW
    return OrbitType.OTHER


def period_minutes(mean_motion_rev_day: float) -> int:
    """Return the period of one revolution in whole minutes, rounded half up.

    The mean motion must be greater than 0; OrbitalElements guarantees it.
    """
    return math.floor(MINUTES_PER_DAY / mean_motion_rev_day + 0.5)
```

### `src/orbita/domain/time_rules.py`

```python
"""Time rules: conversion to Colombia time (DESIGN.md §4.3)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from orbita.domain.elements import require_utc

COLOMBIA_TIMEZONE = timezone(timedelta(hours=-5))
DISPLAY_FORMAT = "%Y-%m-%d %H:%M"


def to_colombia_time(moment_utc: datetime) -> datetime:
    """Return the same instant in Colombia time: UTC − 5 hours, with no daylight saving time."""
    require_utc(moment_utc, "moment_utc")
    return moment_utc.astimezone(COLOMBIA_TIMEZONE)


def format_colombia_time(moment_utc: datetime) -> str:
    """Return the Colombia time as `YYYY-MM-DD HH:MM`, the text shown to the user (RF-09)."""
    return to_colombia_time(moment_utc).strftime(DISPLAY_FORMAT)
```

### `tests/domain/test_rules.py`

```python
"""Tests of the orbit, period and time rules of spec 004."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from orbita.domain.elements import OrbitType
from orbita.domain.errors import DataValidationError
from orbita.domain.orbit_rules import classify_orbit, period_minutes
from orbita.domain.time_rules import format_colombia_time, to_colombia_time


@pytest.mark.parametrize(
    ("inclination", "mean_motion", "expected"),
    [
        (0.1, 1.0027, OrbitType.GEOSTATIONARY),
        (98.7, 14.2, OrbitType.POLAR),
        (80.0, 14.0, OrbitType.POLAR),
        (79.9, 14.0, OrbitType.LOW),
        (51.6, 15.5, OrbitType.LOW),
        (55.0, 2.0, OrbitType.OTHER),
        (9.9, 0.99, OrbitType.GEOSTATIONARY),
        (9.9, 1.01, OrbitType.GEOSTATIONARY),
        (9.9, 1.02, OrbitType.OTHER),
        (10.0, 1.0, OrbitType.OTHER),
    ],
)
def test_classify_orbit_applies_the_rules_in_order(
    inclination: float, mean_motion: float, expected: OrbitType
) -> None:
    assert classify_orbit(inclination, mean_motion) is expected


@pytest.mark.parametrize(("mean_motion", "minutes"), [(15.5, 93), (1.0027, 1436)])
def test_period_minutes_is_rounded_to_whole_minutes(mean_motion: float, minutes: int) -> None:
    assert period_minutes(mean_motion) == minutes


def test_colombia_time_is_utc_minus_five() -> None:
    moment = datetime(2026, 10, 30, 3, 0, tzinfo=UTC)
    assert format_colombia_time(moment) == "2026-10-29 22:00"


def test_colombia_time_has_no_daylight_saving() -> None:
    moment = datetime(2026, 6, 15, 12, 0, tzinfo=UTC)
    assert format_colombia_time(moment) == "2026-06-15 07:00"


def test_colombia_time_keeps_the_same_instant() -> None:
    moment = datetime(2026, 10, 30, 3, 0, tzinfo=UTC)
    assert to_colombia_time(moment) == moment


def test_colombia_time_rejects_naive_datetime() -> None:
    with pytest.raises(DataValidationError):
        to_colombia_time(datetime(2026, 10, 30, 3, 0))
```

## Pasos

1. **Crear la rama de la spec:**
   ```powershell
   git switch -c feature/004-reglas-orbita-tiempo
   ```
2. **Crear** los dos módulos de `src/orbita/domain/` y el archivo `tests/domain/test_rules.py`, con el contenido de arriba.
3. **Ejecutar los tests:**
   ```powershell
   uv run pytest -v
   ```
   Deben pasar los 41 tests de las specs anteriores más los nuevos.
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
   git commit -m "004: reglas de tipo de orbita, periodo y hora de Colombia"
   git switch main
   git merge --no-ff feature/004-reglas-orbita-tiempo -m "Merge spec 004: reglas de tipo de orbita, periodo y hora de Colombia"
   git branch -d feature/004-reglas-orbita-tiempo
   ```
6. **Marcar la spec como implementada** en `specs\README.md` con un commit de documentación en `main`.

## Casos borde y manejo de errores

1. Un vector de RF-03 falla: revisar primero la tabla de la spec contra `DESIGN.md` §4.1; si el vector de RF-03 estaba
   mal, corregir la spec y el requisito antes que el código.
2. `period_minutes` recibe 0: no debe ocurrir, porque `OrbitalElements` rechaza un movimiento medio de 0. Si un test
   lo llama con 0, el error es un `ZeroDivisionError` y el test debe reflejarlo como fallo del llamador.
3. `format_colombia_time` produce otra hora: comprobar que el valor de entrada sea UTC. Un valor sin zona horaria lanza
   `DataValidationError` y no se convierte en silencio.
4. Ruff marca `PLR0911` (demasiados `return`) en `classify_orbit`: no pasa, porque tiene cuatro. Si aparece, reportarlo.

## Tests de aceptación

Son los tests de `tests/domain/test_rules.py`: los seis vectores de RF-03 más cuatro de los límites del tipo geoestacionario,
los dos periodos de RF-03 (93 y 1436 minutos), la hora de Colombia para `2026-10-30T03:00:00Z` (RF-09), el caso de junio
sin horario de verano y el rechazo de una fecha sin zona horaria.

## Fuera de alcance

- Frescura de los elementos orbitales y los intervalos de descarga (spec 005).
- Distancia al observador y validación de la ubicación (spec 006).
- Cálculo de la posición de los satélites (spec 013): aquí solo se clasifica a partir de números ya calculados.

## Definition of Done

Todos los comandos en PowerShell, desde la carpeta `orbita`.

- [ ] `uv run pytest -v` → todos los tests pasan y `echo $LASTEXITCODE` → `0`.
- [ ] `Select-String -Path src\orbita\domain\orbit_rules.py,src\orbita\domain\time_rules.py -Pattern 'import (streamlit|httpx|pydeck|skyfield)'` → sin salida.
- [ ] `uv run ruff check .` → `All checks passed!`
- [ ] `uv run ruff format --check .; echo $LASTEXITCODE` → `0`.
- [ ] `uv run mypy src` → `Success: no issues found`.
- [ ] `uv run pre-commit run --all-files` → todos los hooks en `Passed`.
- [ ] `git log --oneline --graph` → muestra el commit de la spec 004 y el merge.
- [ ] `git status` → `nothing to commit, working tree clean`.
