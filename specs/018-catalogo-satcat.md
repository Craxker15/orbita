# 018 - Catálogo SATCAT: país, lanzamiento y años en órbita (P2)

## Objetivo

Al terminar, cada ficha muestra el país del satélite (traducido con las claves `owner_<CÓDIGO>` de `locales/es.json`), su
fecha de lanzamiento y los años en órbita, calculados con la regla de `DESIGN.md` §4.6. Sin catálogo guardado, estos
campos muestran "—" (RF-14). La descarga del catálogo ya existe desde la spec 014; aquí solo se añade la regla de años
y la presentación.

## Depende de

- 014 (el catálogo ya se descarga y se entrega en `LiveView`), 015 (las fichas), 017 (la aplicación completa, para la
  comprobación con datos reales).

## Archivos rectores aplicables

- `DESIGN.md` §4.6 (años = (fecha actual − lanzamiento) en días / 365.25, con un decimal; país con `owner_<CÓDIGO>`;
  código desconocido tal como llega).
- `docs/00-requirements.es.md` RF-13 (ejemplo: 2016-10-30 a 2026-10-30 → 10.0 años), RF-14.
- `ARCHITECTURE.md` §4 (adaptador `CelestrakSource`, catálogo a 24 h), §6 (fechas en UTC; la regla vive en el dominio).

## Excepción a la regla 3 del índice

Esta spec toca tres capas: una regla nueva en `domain`, su uso en `app` y su presentación en `ui`. Es un cambio pequeño y
acoplado; el test de arquitectura (`tests/test_architecture.py`) comprueba que las dependencias no se rompen.

## Archivos a crear o modificar

1. `src/orbita/domain/catalog_rules.py` (nuevo).
2. `tests/domain/test_catalog_rules.py` (nuevo).
3. `src/orbita/app/live_view.py` (modificar: un campo nuevo en `SatelliteView`).
4. `src/orbita/app/get_live_view.py` (modificar: calcular los años).
5. `src/orbita/ui/cards.py` (modificar: mostrar los años).

Son cinco archivos de código.

## Dependencias externas

Ninguna.

## Contenido exacto de los archivos

### `src/orbita/domain/catalog_rules.py`

```python
"""Catalog rules: years in orbit from the launch date (DESIGN.md §4.6)."""

from __future__ import annotations

from datetime import date
from typing import Final

from orbita.domain.errors import DataValidationError

DAYS_PER_YEAR: Final = 365.25


def years_in_orbit(launch_date: date, today: date) -> float:
    """Return the years since the launch, with one decimal (DESIGN.md §4.6).

    Preconditions: today is the current UTC date.
    Postconditions: the result is at least 0.0 and has one decimal.
    Raises:
        DataValidationError: if the launch date is after today.
    """
    days = (today - launch_date).days
    if days < 0:
        raise DataValidationError("the launch date is after today")
    return round(days / DAYS_PER_YEAR, 1)
```

### `tests/domain/test_catalog_rules.py`

```python
"""Tests of the years-in-orbit rule (spec 018)."""

from __future__ import annotations

from datetime import date

import pytest

from orbita.domain.catalog_rules import years_in_orbit
from orbita.domain.errors import DataValidationError


def test_ten_years_exactly_is_10_point_0() -> None:
    assert years_in_orbit(date(2016, 10, 30), date(2026, 10, 30)) == 10.0


def test_launch_today_gives_zero_years() -> None:
    assert years_in_orbit(date(2026, 10, 30), date(2026, 10, 30)) == 0.0


def test_result_has_one_decimal() -> None:
    assert years_in_orbit(date(1998, 11, 20), date(2026, 10, 30)) == 27.9


def test_launch_in_the_future_is_rejected() -> None:
    with pytest.raises(DataValidationError):
        years_in_orbit(date(2027, 1, 1), date(2026, 10, 30))
```

### Cambios en los archivos existentes

**`src/orbita/app/live_view.py`:** en la clase `SatelliteView`, después de la línea `launch_date: date | None`, se añade
la línea `years_in_orbit: float | None`.

**`src/orbita/app/get_live_view.py`:** tres cambios exactos:

1. Se añade el import `from orbita.domain.catalog_rules import years_in_orbit` justo después de
   `from orbita.app.live_view import LiveView, SatelliteView`.
2. En `_view`, antes del `return`, se añade:
   ```python
           years = None if entry is None or entry.launch_date is None else _years(entry.launch_date, now)
   ```
   y en el `return SatelliteView(...)` se añade el argumento `years_in_orbit=years,` después de
   `launch_date=...`.
3. Al final del archivo se añade la función auxiliar:
   ```python
   def _years(launch_date: date, now: datetime) -> float | None:
       """Return the years in orbit, or None when the launch date is not valid for today (catalog data is not trusted)."""
       try:
           return years_in_orbit(launch_date, now.date())
       except DataValidationError:
           logger.warning("years_in_orbit_invalid")
           return None
   ```
   Y el import `from datetime import date, datetime, timedelta` sustituye al actual `from datetime import datetime, timedelta`.

**`src/orbita/ui/cards.py`:** en `card_rows`, la última fila pasa de `(texts["label_years_in_orbit"], missing)` a:
```python
(
    (
        texts["label_years_in_orbit"],
        missing if view.years_in_orbit is None else f"{view.years_in_orbit:.1f}",
    ),
)
```

## Pasos

1. **Crear la rama:** `git switch -c feature/018-catalogo-satcat`.
2. **Crear los dos archivos nuevos** y **aplicar los tres cambios** en los archivos existentes.
3. **Ejecutar los tests:** `uv run pytest -v`. Los tests de `test_use_cases.py` deben seguir pasando; la fecha de
   lanzamiento de su catálogo de prueba es válida.
4. **Comprobar la regla de capas:** `uv run pytest tests/test_architecture.py -v` → 7 passed.
5. **Comprobar con datos reales (manual):** con internet, `uv run streamlit run src\orbita\main.py`; abrir una ficha de la
   ISS y comprobar que el país sale como "Estados Unidos" o como la entrada de `es.json`, y que los años son un número con
   un decimal. Si el código de país no está en `es.json`, se añade la clave `owner_<CÓDIGO>` y se registra en
   `specs\README.md`.
6. **Commit y merge** con el mensaje `018: catalogo satcat, pais y anos en orbita`.

## Casos borde y manejo de errores

1. Un satélite sin entrada en el catálogo muestra "—" en país, fecha y años (RF-14).
2. Una fecha de lanzamiento posterior a hoy (dato corrupto) muestra "—" en años y deja un aviso en el log.
3. Un código de país desconocido se muestra tal cual, sin error.
4. Un año bisiesto no cambia el resultado de forma apreciable: se usa 365.25 días por año.

## Tests de aceptación

- 2016-10-30 a 2026-10-30 da 10.0 años (RF-13).
- Lanzamiento hoy da 0.0.
- Un resultado tiene siempre un decimal: 1998-11-20 a 2026-10-30 da 27.9.
- Lanzamiento futuro se rechaza.
- La prueba manual de la ficha de la ISS muestra país, fecha y años.

## Fuera de alcance

- La lista de códigos de país completa: se añade cuando aparece un satélite que la necesite.
- Los datos del catálogo en la publicación: spec 021.

## Definition of Done

- [ ] `uv run pytest -v` → todos los tests pasan (los 4 nuevos incluidos).
- [ ] `uv run pytest tests/test_architecture.py -v` → 7 passed.
- [ ] `Select-String -Path src\orbita\domain\catalog_rules.py -Pattern 'import (streamlit|httpx|pydeck|skyfield)'` → sin salida.
- [ ] `uv run ruff check .`, `uv run mypy src` y `uv run pre-commit run --all-files` sin errores.
- [ ] `git status` → `nothing to commit, working tree clean` después del merge.
