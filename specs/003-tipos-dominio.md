# 003 - Tipos del dominio y errores

## Objetivo

Al terminar, el paquete `orbita.domain` tiene los tipos de datos del proyecto y sus errores. Cada tipo es inmutable
(`frozen`) y se valida al construirse: un valor inválido no puede existir en memoria. Esta spec define la forma de los
datos y sus rangos. No define las reglas de negocio (tipo de órbita, frescura, distancia): eso es de las specs 004 a
006.

## Depende de

- 002 (existen los paquetes de capas y el test de la regla de dependencias).

## Archivos rectores aplicables

- `ARCHITECTURE.md` §2 (el dominio usa solo la biblioteca estándar), §6 (tipos: `@dataclass(frozen=True, slots=True)`
  con validación en `__post_init__`; errores: solo subclases de `OrbitaError`; `Observer` no se registra ni se muestra).
- `DESIGN.md` §4.5 (rango de la ubicación), §4.6 (datos del catálogo).
- `security-rules.md` SEC-03 (`Observer` con `__repr__` oculto y campos `latitude` y `longitude`), SEC-09 (errores de
  configuración con `ConfigError`), SEC-10 (rangos de los elementos orbitales).

## Archivos a crear

1. `src/orbita/domain/errors.py`
2. `src/orbita/domain/elements.py`
3. `src/orbita/domain/observer.py`
4. `src/orbita/domain/catalog.py`
5. `tests/domain/test_types.py`

Son cinco archivos, dentro del límite de la regla 3 del índice. Los cuatro primeros están en la capa `domain`; el quinto
es su test.

## Dependencias externas

Ninguna. Solo se usan `dataclasses`, `datetime`, `enum`, `math`, `re` y `datetime.UTC` de la biblioteca estándar.

## Contenido exacto de los archivos

### `src/orbita/domain/errors.py`

```python
"""Project exceptions. Every error raised by Orbita inherits from OrbitaError (ARCHITECTURE.md §6)."""

from __future__ import annotations


class OrbitaError(Exception):
    """Base class of every error raised by the project."""


class DataValidationError(OrbitaError):
    """Downloaded or stored data does not pass validation (SEC-10, RF-07)."""


class ConfigError(OrbitaError):
    """A configuration file or value is invalid (SEC-09)."""


class InvalidLocationError(OrbitaError):
    """A location is outside the valid ranges of DESIGN.md §4.5."""
```

### `src/orbita/domain/elements.py`

```python
"""Orbital elements, the downloaded dataset, and the orbit and freshness classifications."""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum

from orbita.domain.errors import DataValidationError

MAX_NAME_LENGTH = 80
MAX_INCLINATION_DEG = 180.0
MAX_MEAN_MOTION_REV_DAY = 20.0
MAX_ECCENTRICITY = 1.0


class OrbitType(StrEnum):
    """Orbit type of DESIGN.md §4.1. The rule that chooses it is in spec 004."""

    GEOSTATIONARY = "geostationary"
    POLAR = "polar"
    LOW = "low"
    OTHER = "other"


class Freshness(StrEnum):
    """Freshness of the orbital elements, DESIGN.md §4.2. The rule is in spec 005."""

    NORMAL = "normal"
    STALE = "stale"
    TOO_OLD = "too_old"


def require_utc(value: datetime, field: str) -> None:
    """Raise DataValidationError unless the datetime is timezone-aware and in UTC."""
    if value.utcoffset() != timedelta(0):
        raise DataValidationError(f"{field} must be a timezone-aware UTC datetime")


def require_in_range(
    value: float,
    low: float,
    high: float,
    field: str,
    *,
    low_inclusive: bool = True,
    high_inclusive: bool = True,
) -> None:
    """Raise DataValidationError unless value is a finite number inside the range."""
    if not math.isfinite(value):
        raise DataValidationError(f"{field} must be a finite number")
    above = value >= low if low_inclusive else value > low
    below = value <= high if high_inclusive else value < high
    if not (above and below):
        raise DataValidationError(f"{field} must be between {low} and {high}")


@dataclass(frozen=True, slots=True)
class OrbitalElements:
    """The orbital elements of one satellite, as published by CelesTrak (GP format)."""

    norad: int
    name: str
    inclination_deg: float
    mean_motion_rev_day: float
    eccentricity: float
    epoch: datetime

    def __post_init__(self) -> None:
        """Validate every field with the ranges of SEC-10."""
        if isinstance(self.norad, bool) or not isinstance(self.norad, int) or self.norad <= 0:
            raise DataValidationError("norad must be a positive integer")
        if not isinstance(self.name, str) or not self.name.strip():
            raise DataValidationError("name must not be empty")
        if len(self.name) > MAX_NAME_LENGTH:
            raise DataValidationError(f"name must have at most {MAX_NAME_LENGTH} characters")
        require_in_range(self.inclination_deg, 0.0, MAX_INCLINATION_DEG, "inclination_deg")
        require_in_range(
            self.mean_motion_rev_day,
            0.0,
            MAX_MEAN_MOTION_REV_DAY,
            "mean_motion_rev_day",
            low_inclusive=False,
        )
        require_in_range(
            self.eccentricity, 0.0, MAX_ECCENTRICITY, "eccentricity", high_inclusive=False
        )
        require_utc(self.epoch, "epoch")


@dataclass(frozen=True, slots=True)
class OrbitalDataset:
    """All the orbital elements saved by one successful download."""

    downloaded_at: datetime
    elements: tuple[OrbitalElements, ...]

    def __post_init__(self) -> None:
        """Validate the download time and reject a NORAD number that appears twice."""
        require_utc(self.downloaded_at, "downloaded_at")
        if not isinstance(self.elements, tuple):
            raise DataValidationError("elements must be a tuple")
        norads = [item.norad for item in self.elements]
        if len(set(norads)) != len(norads):
            raise DataValidationError("a NORAD number appears more than once in the dataset")
```

### `src/orbita/domain/observer.py`

```python
"""Ground points and the observer location (DESIGN.md §4.4 and §4.5)."""

from __future__ import annotations

from dataclasses import dataclass

from orbita.domain.elements import require_in_range
from orbita.domain.errors import DataValidationError, InvalidLocationError

MAX_LATITUDE_DEG = 90.0
MAX_LONGITUDE_DEG = 180.0
MAX_ALTITUDE_KM = 100_000.0


@dataclass(frozen=True, slots=True, repr=False)
class GroundPoint:
    """A point above the Earth, for example a satellite position or a point of its ground track."""

    latitude: float
    longitude: float
    altitude_km: float = 0.0

    def __post_init__(self) -> None:
        """Validate the coordinates and the altitude."""
        require_in_range(self.latitude, -MAX_LATITUDE_DEG, MAX_LATITUDE_DEG, "latitude")
        require_in_range(self.longitude, -MAX_LONGITUDE_DEG, MAX_LONGITUDE_DEG, "longitude")
        require_in_range(self.altitude_km, 0.0, MAX_ALTITUDE_KM, "altitude_km")


@dataclass(frozen=True, slots=True, repr=False)
class Observer:
    """The user's location read from the browser. It lives only in memory (SEC-03, DESIGN.md §4.5)."""

    latitude: float
    longitude: float

    def __post_init__(self) -> None:
        """Validate the location. The error text never contains the coordinates."""
        try:
            require_in_range(self.latitude, -MAX_LATITUDE_DEG, MAX_LATITUDE_DEG, "latitude")
            require_in_range(self.longitude, -MAX_LONGITUDE_DEG, MAX_LONGITUDE_DEG, "longitude")
        except DataValidationError as error:
            raise InvalidLocationError(str(error)) from error

    def __repr__(self) -> str:
        """Hide the coordinates so a log line or a traceback never shows them (SEC-03)."""
        return "Observer(<hidden>)"
```

### `src/orbita/domain/catalog.py`

```python
"""Satellite catalog entries: owner, launch date and their validation (DESIGN.md §4.6)."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime

from orbita.domain.elements import require_utc
from orbita.domain.errors import DataValidationError

OWNER_CODE_PATTERN = re.compile(r"[A-Z0-9]{1,10}")


@dataclass(frozen=True, slots=True)
class CatalogEntry:
    """The SATCAT data of one satellite: NORAD number, owner code and launch date."""

    norad: int
    owner_code: str
    launch_date: date

    def __post_init__(self) -> None:
        """Validate the NORAD number, the owner code and the launch date."""
        if isinstance(self.norad, bool) or not isinstance(self.norad, int) or self.norad <= 0:
            raise DataValidationError("norad must be a positive integer")
        if not isinstance(self.owner_code, str) or OWNER_CODE_PATTERN.fullmatch(self.owner_code) is None:
            raise DataValidationError("owner_code must be 1 to 10 capital letters or digits")
        if isinstance(self.launch_date, datetime) or not isinstance(self.launch_date, date):
            raise DataValidationError("launch_date must be a date without time")


@dataclass(frozen=True, slots=True)
class Catalog:
    """All the catalog entries saved by one successful download."""

    downloaded_at: datetime
    entries: tuple[CatalogEntry, ...]

    def __post_init__(self) -> None:
        """Validate the download time and reject a NORAD number that appears twice."""
        require_utc(self.downloaded_at, "downloaded_at")
        if not isinstance(self.entries, tuple):
            raise DataValidationError("entries must be a tuple")
        norads = [item.norad for item in self.entries]
        if len(set(norads)) != len(norads):
            raise DataValidationError("a NORAD number appears more than once in the catalog")
```

### `tests/domain/test_types.py`

```python
"""Validation of the domain types of spec 003."""

from __future__ import annotations

import dataclasses
import math
from datetime import UTC, date, datetime, timedelta, timezone

import pytest

from orbita.domain.catalog import Catalog, CatalogEntry
from orbita.domain.elements import Freshness, OrbitalDataset, OrbitalElements, OrbitType
from orbita.domain.errors import (
    ConfigError,
    DataValidationError,
    InvalidLocationError,
    OrbitaError,
)
from orbita.domain.observer import GroundPoint, Observer

EPOCH = datetime(2026, 10, 30, 12, 0, tzinfo=UTC)


def make_elements(**changes: object) -> OrbitalElements:
    values: dict[str, object] = {
        "norad": 25544,
        "name": "ISS (ZARYA)",
        "inclination_deg": 51.6,
        "mean_motion_rev_day": 15.5,
        "eccentricity": 0.0007,
        "epoch": EPOCH,
    }
    values.update(changes)
    return OrbitalElements(**values)


def test_valid_elements_are_accepted() -> None:
    assert make_elements().norad == 25544


def test_elements_are_frozen() -> None:
    with pytest.raises(dataclasses.FrozenInstanceError):
        make_elements().norad = 1


@pytest.mark.parametrize(
    ("changes", "field"),
    [
        ({"norad": 0}, "norad"),
        ({"name": "   "}, "name"),
        ({"name": "x" * 81}, "name"),
        ({"inclination_deg": 181.0}, "inclination_deg"),
        ({"inclination_deg": math.nan}, "inclination_deg"),
        ({"mean_motion_rev_day": 0.0}, "mean_motion_rev_day"),
        ({"mean_motion_rev_day": 20.1}, "mean_motion_rev_day"),
        ({"eccentricity": 1.0}, "eccentricity"),
        ({"epoch": datetime(2026, 10, 30)}, "epoch"),
        ({"epoch": datetime(2026, 10, 30, tzinfo=timezone(timedelta(hours=-5)))}, "epoch"),
    ],
)
def test_orbital_elements_reject_invalid_values(changes: dict[str, object], field: str) -> None:
    with pytest.raises(DataValidationError, match=field):
        make_elements(**changes)


def test_dataset_rejects_duplicate_norad() -> None:
    with pytest.raises(DataValidationError, match="more than once"):
        OrbitalDataset(downloaded_at=EPOCH, elements=(make_elements(), make_elements()))


def test_dataset_rejects_naive_download_time() -> None:
    with pytest.raises(DataValidationError, match="downloaded_at"):
        OrbitalDataset(downloaded_at=datetime(2026, 10, 30), elements=())


@pytest.mark.parametrize(("latitude", "longitude"), [(3.45, -76.53), (90.0, 180.0), (-90.0, -180.0)])
def test_observer_accepts_valid_location(latitude: float, longitude: float) -> None:
    assert Observer(latitude=latitude, longitude=longitude).latitude == latitude


@pytest.mark.parametrize(("latitude", "longitude"), [(90.1, 0.0), (0.0, -180.1), (math.nan, 0.0)])
def test_observer_rejects_invalid_location(latitude: float, longitude: float) -> None:
    with pytest.raises(InvalidLocationError):
        Observer(latitude=latitude, longitude=longitude)


def test_observer_repr_hides_coordinates() -> None:
    assert repr(Observer(latitude=3.45, longitude=-76.53)) == "Observer(<hidden>)"


def test_invalid_location_message_does_not_contain_the_value() -> None:
    with pytest.raises(InvalidLocationError) as info:
        Observer(latitude=91.123, longitude=0.0)
    assert "91.123" not in str(info.value)


def test_ground_point_rejects_negative_altitude() -> None:
    with pytest.raises(DataValidationError, match="altitude_km"):
        GroundPoint(latitude=0.0, longitude=0.0, altitude_km=-1.0)


def test_catalog_entry_accepts_owner_code() -> None:
    entry = CatalogEntry(norad=25544, owner_code="US", launch_date=date(1998, 11, 20))
    assert entry.owner_code == "US"


@pytest.mark.parametrize("owner_code", ["us", "", "ABCDEFGHIJK", "U S"])
def test_catalog_entry_rejects_bad_owner_code(owner_code: str) -> None:
    with pytest.raises(DataValidationError, match="owner_code"):
        CatalogEntry(norad=25544, owner_code=owner_code, launch_date=date(1998, 11, 20))


def test_catalog_entry_rejects_datetime_as_launch_date() -> None:
    with pytest.raises(DataValidationError, match="launch_date"):
        CatalogEntry(norad=25544, owner_code="US", launch_date=datetime(1998, 11, 20, tzinfo=UTC))


def test_catalog_rejects_duplicate_norad() -> None:
    entry = CatalogEntry(norad=25544, owner_code="US", launch_date=date(1998, 11, 20))
    with pytest.raises(DataValidationError, match="more than once"):
        Catalog(downloaded_at=EPOCH, entries=(entry, entry))


@pytest.mark.parametrize("error", [DataValidationError, ConfigError, InvalidLocationError])
def test_project_errors_inherit_from_orbita_error(error: type[OrbitaError]) -> None:
    assert issubclass(error, OrbitaError)


def test_enum_values_match_the_names_of_the_rules() -> None:
    assert OrbitType.GEOSTATIONARY == "geostationary"
    assert Freshness.TOO_OLD == "too_old"
```

## Pasos

1. **Crear la rama de la spec:**
   ```powershell
   git switch -c feature/003-tipos-dominio
   ```
2. **Crear** los cuatro archivos de `src/orbita/domain/` con el contenido de arriba (clic derecho en la carpeta
   `domain` → **New File**, o con `code`).
3. **Crear** `tests/domain/test_types.py`. Primero crear la carpeta: `New-Item -ItemType Directory -Force -Path tests\domain`.
4. **Ejecutar el test:**
   ```powershell
   uv run pytest -v
   ```
   Deben pasar todos los tests, con `34 passed`.
5. **Revisar calidad:**
   ```powershell
   uv run ruff check .
   uv run ruff format --check .
   uv run mypy src
   uv run pre-commit run --all-files
   ```
   Si `ruff format --check` marca algún archivo, ejecutar `uv run ruff format <archivo>` y repetir.
6. **Commit y merge:**
   ```powershell
   git add .
   git commit -m "003: tipos del dominio y errores"
   git switch main
   git merge --no-ff feature/003-tipos-dominio -m "Merge spec 003: tipos del dominio y errores"
   git branch -d feature/003-tipos-dominio
   ```
7. **Marcar la spec como implementada** en `specs\README.md` (fila 003 → `Implementada 2026-10-30`), con commit de
   documentación en `main`.

## Casos borde y manejo de errores

1. `mypy --strict` se queja de `isinstance(self.norad, bool)` o de otra comprobación defensiva: no quitar la
   comprobación (los datos vienen de internet, SEC-10); reportar el mensaje exacto.
2. Ruff marca `PLR2004` (valor mágico) en `src/`: mover el número a una constante con nombre en mayúsculas al inicio del
   módulo.
3. Ruff marca `PLR0912` o `PLR0915` en un `__post_init__`: repartir las comprobaciones en funciones auxiliares; no
   subir el límite.
4. Un test falla con `DataValidationError` cuando debería aceptar un valor: revisar primero el rango de la tabla de
   esta spec; si el rango estaba mal escrito, corregir la spec antes que el código (regla 6 del índice).
5. Un mensaje de error contiene un valor de coordenadas: es un fallo de privacidad (SEC-03). Corregir el mensaje y no
   aceptar el test sin la comprobación `test_invalid_location_message_does_not_contain_the_value`.

## Tests de aceptación

Son los 34 tests de `tests/domain/test_types.py`. Cubren: rangos de cada campo de `OrbitalElements`, fechas con zona
horaria, duplicados en `OrbitalDataset` y `Catalog`, ubicaciones de RF-10 (`(3.45, −76.53)` válida; `(90.0, 180.0)`
válida; `(90.1, 0.0)` y `(0.0, −180.1)` inválidas), `Observer` oculto en el `repr`, el mensaje de error sin
coordenadas, el código de dueño de SATCAT, la jerarquía de errores y los valores de los enumerados.

## Fuera de alcance

- Reglas de negocio: tipo de órbita (spec 004), frescura (spec 005), distancia (spec 006).
- Validación contra la lista de NORAD de `DESIGN.md` §3.1 y de la fecha de época en el futuro (SEC-10 pide "no más de
  1 día en el futuro"): necesitan la lista y el reloj; van en la spec 007.
- `SatelliteState` (estado de un satélite en un instante): se define junto al puerto `OrbitPropagator` en la spec 008.
- La lista de los 20 satélites (spec 010).

## Definition of Done

Todos los comandos en PowerShell, desde la carpeta `orbita`.

- [ ] `uv run pytest -v` → `34 passed` y `echo $LASTEXITCODE` → `0`.
- [ ] `Select-String -Path src\orbita\domain\*.py -Pattern 'import (streamlit|httpx|pydeck|skyfield)'` → sin salida
  (el dominio no importa terceros).
- [ ] `uv run ruff check .` → `All checks passed!`
- [ ] `uv run ruff format --check .; echo $LASTEXITCODE` → `0`.
- [ ] `uv run mypy src` → `Success: no issues found`.
- [ ] `uv run pre-commit run --all-files` → todos los hooks en `Passed`.
- [ ] `git log --oneline --graph` → muestra el commit de la spec 003 y el merge.
- [ ] `git status` → `nothing to commit, working tree clean`.
