# 005 - Reglas: frescura de los datos e intervalos de descarga

## Objetivo

Al terminar, el dominio decide dos cosas con reglas puras: qué tan vieja es una descarga de elementos orbitales
(normal, desactualizada o demasiado vieja) y si ya toca volver a descargar de CelesTrak, según el intervalo mínimo
permitido. Las reglas reciben las fechas como argumento y no leen el reloj.

## Depende de

- 003 (los tipos `Freshness`, `require_utc` y `DataValidationError` ya existen).

## Archivos rectores aplicables

- `DESIGN.md` §4.2 (frescura: edad ≤ 3 días normal; 3 a 14 días con aviso; más de 14 días sin posiciones; intervalos
  contados desde el último intento, correcto o fallido; el catálogo cada 24 horas).
- `docs/00-requirements.es.md` RF-04 (2 horas, sin reintentar), RF-06 (umbrales de frescura), RF-13 (24 horas del catálogo).
- `docs/adr/ADR-003-celestrak-json-by-catalog-number.md` (la política de CelesTrak exige contar desde el último intento
  y no reintentar).
- `security-rules.md` SEC-16 (sin reintentos) y SEC-31 (intervalos globales).

## Archivos a crear

1. `src/orbita/domain/freshness_rules.py`
2. `src/orbita/domain/download_rules.py`
3. `tests/domain/test_freshness_download.py`

Son tres archivos, dentro del límite de la regla 3 del índice.

## Dependencias externas

Ninguna. Se usan `datetime` y `timedelta` de la biblioteca estándar.

## Contenido exacto de los archivos

### `src/orbita/domain/freshness_rules.py`

```python
"""Freshness of the orbital elements (DESIGN.md §4.2, RF-06)."""

from __future__ import annotations

from datetime import datetime, timedelta

from orbita.domain.elements import Freshness, require_utc
from orbita.domain.errors import DataValidationError

FRESH_LIMIT = timedelta(days=3)
STALE_LIMIT = timedelta(days=14)


def classify_freshness(downloaded_at: datetime, now: datetime) -> Freshness:
    """Return how old the orbital elements are, counted from the last successful download.

    A download time later than now is rejected: it means the clock or the data is wrong.
    """
    require_utc(downloaded_at, "downloaded_at")
    require_utc(now, "now")
    age = now - downloaded_at
    if age < timedelta(0):
        raise DataValidationError("the download time is later than now")
    if age <= FRESH_LIMIT:
        return Freshness.NORMAL
    if age <= STALE_LIMIT:
        return Freshness.STALE
    return Freshness.TOO_OLD
```

### `src/orbita/domain/download_rules.py`

```python
"""Download intervals: how often the program may contact CelesTrak (DESIGN.md §4.2, ADR-003)."""

from __future__ import annotations

from datetime import datetime, timedelta

from orbita.domain.elements import require_utc
from orbita.domain.errors import DataValidationError

ELEMENTS_DOWNLOAD_INTERVAL = timedelta(hours=2)
CATALOG_DOWNLOAD_INTERVAL = timedelta(hours=24)


def is_download_due(last_attempt: datetime | None, now: datetime, interval: timedelta) -> bool:
    """Tell whether a new download may start.

    The interval counts from the last attempt, successful or not: a failed attempt is not
    retried before the interval has passed (ADR-003). No previous attempt means it is due.
    """
    require_utc(now, "now")
    if last_attempt is None:
        return True
    require_utc(last_attempt, "last_attempt")
    elapsed = now - last_attempt
    if elapsed < timedelta(0):
        raise DataValidationError("the last attempt is later than now")
    return elapsed >= interval
```

### `tests/domain/test_freshness_download.py`

```python
"""Tests of the freshness and download-interval rules of spec 005."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from orbita.domain.download_rules import (
    CATALOG_DOWNLOAD_INTERVAL,
    ELEMENTS_DOWNLOAD_INTERVAL,
    is_download_due,
)
from orbita.domain.elements import Freshness
from orbita.domain.errors import DataValidationError
from orbita.domain.freshness_rules import classify_freshness

NOW = datetime(2026, 10, 30, 12, 0, tzinfo=UTC)
ONE_SECOND = timedelta(seconds=1)


@pytest.mark.parametrize(
    ("age", "expected"),
    [
        (timedelta(days=3), Freshness.NORMAL),
        (timedelta(days=3) + ONE_SECOND, Freshness.STALE),
        (timedelta(days=14), Freshness.STALE),
        (timedelta(days=14) + ONE_SECOND, Freshness.TOO_OLD),
    ],
)
def test_freshness_thresholds_of_rf06(age: timedelta, expected: Freshness) -> None:
    assert classify_freshness(NOW - age, NOW) is expected


def test_freshness_rejects_download_in_the_future() -> None:
    with pytest.raises(DataValidationError, match="later than now"):
        classify_freshness(NOW + ONE_SECOND, NOW)


def test_freshness_rejects_naive_datetime() -> None:
    with pytest.raises(DataValidationError):
        classify_freshness(datetime(2026, 10, 30, 11, 0), NOW)


@pytest.mark.parametrize(
    ("elapsed", "due"),
    [
        (timedelta(hours=1, minutes=59), False),
        (timedelta(hours=2), True),
        (timedelta(hours=3), True),
    ],
)
def test_elements_download_every_two_hours_rf04(elapsed: timedelta, due: bool) -> None:
    last_attempt = NOW - elapsed
    assert is_download_due(last_attempt, NOW, ELEMENTS_DOWNLOAD_INTERVAL) is due


@pytest.mark.parametrize(
    ("elapsed", "due"),
    [
        (timedelta(hours=23, minutes=59), False),
        (timedelta(hours=24), True),
    ],
)
def test_catalog_download_every_24_hours_rf13(elapsed: timedelta, due: bool) -> None:
    last_attempt = NOW - elapsed
    assert is_download_due(last_attempt, NOW, CATALOG_DOWNLOAD_INTERVAL) is due


def test_first_download_is_always_due() -> None:
    assert is_download_due(None, NOW, ELEMENTS_DOWNLOAD_INTERVAL) is True


def test_download_rejects_last_attempt_in_the_future() -> None:
    with pytest.raises(DataValidationError, match="later than now"):
        is_download_due(NOW + ONE_SECOND, NOW, ELEMENTS_DOWNLOAD_INTERVAL)
```

## Pasos

1. **Crear la rama de la spec:**
   ```powershell
   git switch -c feature/005-frescura-intervalos
   ```
2. **Verificar que los archivos de código existen** con `Get-ChildItem -Name src\orbita\domain, tests\domain`. Si faltan,
   pegar su contenido desde la spec.
3. **Ejecutar los tests:**
   ```powershell
   uv run pytest -v
   ```
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
   git commit -m "005: reglas de frescura e intervalos de descarga"
   git switch main
   git merge --no-ff feature/005-frescura-intervalos -m "Merge spec 005: reglas de frescura e intervalos de descarga"
   git branch -d feature/005-frescura-intervalos
   ```
6. **Marcar la spec como implementada** en `specs\README.md` con un commit de documentación en `main`.

## Casos borde y manejo de errores

1. Un vector de RF-04, RF-06 o RF-13 falla: comparar primero con la tabla de esta spec y con el requisito. Si el
   requisito tiene otro valor, corregir el requisito y la spec antes que el código (regla 6 del índice).
2. Una descarga con fecha futura lanza `DataValidationError`: no se trata como "normal". Puede ser un reloj mal
   configurado; el error debe verse en el log, no ocultarse.
3. Se cambia la hora del sistema hacia atrás y el intervalo deja de cumplirse: la regla lanza un error en lugar de
   bloquear las descargas en silencio. Reportar el mensaje completo.

## Tests de aceptación

Son los tests de `tests/domain/test_freshness_download.py`: los cuatro umbrales de frescura de RF-06 (3 días exactos,
3 días más 1 segundo, 14 días exactos, 14 días más 1 segundo), el intervalo de 2 horas de RF-04 (1 h 59 min no, 2 h sí),
el intervalo de 24 horas de RF-13 (23 h 59 min no, 24 h sí), la primera descarga siempre permitida, y los rechazos de
fechas futuras y sin zona horaria.

## Fuera de alcance

- Qué hacer con la descarga (descargar, validar el archivo y guardarlo): specs 011 y 012.
- El aviso que se muestra en la pantalla: spec 015.

## Definition of Done

Todos los comandos en PowerShell, desde la carpeta `orbita`.

- [ ] `uv run pytest -v` → todos los tests pasan y `echo $LASTEXITCODE` → `0`.
- [ ] `Select-String -Path src\orbita\domain\freshness_rules.py,src\orbita\domain\download_rules.py -Pattern 'import (streamlit|httpx|pydeck|skyfield)'` → sin salida.
- [ ] `uv run ruff check .` → `All checks passed!`
- [ ] `uv run ruff format --check .; echo $LASTEXITCODE` → `0`.
- [ ] `uv run mypy src` → `Success: no issues found`.
- [ ] `uv run pre-commit run --all-files` → todos los hooks en `Passed`.
- [ ] `git log --oneline --graph` → muestra el commit de la spec 005 y el merge.
- [ ] `git status` → `nothing to commit, working tree clean`.
