# 008 - Puertos

## Objetivo

Al terminar, el proyecto tiene las interfaces (puertos) que los casos de uso usan para hablar con el mundo exterior:
descargar datos de CelesTrak, guardar y leer archivos locales, calcular posiciones y leer la hora. Los casos de uso
(spec 014) se escribirán contra estos contratos, y los adaptadores (specs 011 a 013) los implementarán. Esta spec no
implementa ningún adaptador: solo define las firmas, los tipos que cruzan los puertos y un test que comprueba que un
objeto falso cumple cada contrato.

## Depende de

- 003 (tipos de dominio, `Catalog`, `OrbitalDataset`, `GroundPoint`, errores).
- 007 (`DownloadError` y `PropagationError` en `errors.py`, y los campos nuevos de `OrbitalElements`).

## Archivos rectores aplicables

- `ARCHITECTURE.md` §2 (los puertos solo importan `orbita.domain` y la biblioteca estándar), §4 (tabla de puertos y
  adaptadores), §6 (puertos con precondiciones, postcondiciones y `Raises` en el docstring).
- `security-rules.md` SEC-02 (la ubicación no cruza ningún puerto: `Observer` no aparece aquí), SEC-17 (Skyfield no
  descarga nada en tiempo de ejecución: el puerto de propagación no lo necesita).

## Excepción a la regla 3 del índice

`SatelliteState` y `DownloadAttempts` son tipos de dominio que `ARCHITECTURE.md` §2 pone en `orbita.domain`. Los puertos
no pueden compilar sin ellos, así que se crean aquí, en `src/orbita/domain/state.py`, y no en una spec aparte. Son dos
archivos de la capa `domain` y tres de la capa `ports` y su test: cuatro archivos de código en total.

## Archivos a crear

1. `src/orbita/domain/state.py`
2. `src/orbita/ports/satellite_data.py`
3. `src/orbita/ports/propagation.py`
4. `tests/ports/test_ports.py`

## Dependencias externas

Ninguna. Solo `typing.Protocol` y `runtime_checkable` de la biblioteca estándar.

## Contenido exacto de los archivos

### `src/orbita/domain/state.py`

```python
"""Satellite state at one instant, and the times of the last download attempts (ARCHITECTURE.md §2)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from orbita.domain.elements import require_in_range, require_utc
from orbita.domain.errors import DataValidationError
from orbita.domain.observer import GroundPoint

MAX_SPEED_KM_S = 20.0


@dataclass(frozen=True, slots=True)
class SatelliteState:
    """Where a satellite is and how fast it moves at one instant (DESIGN.md §3.2, RF-01)."""

    norad: int
    point: GroundPoint
    speed_km_s: float

    def __post_init__(self) -> None:
        """Validate the NORAD number and the speed."""
        if isinstance(self.norad, bool) or not isinstance(self.norad, int) or self.norad <= 0:
            raise DataValidationError("norad must be a positive integer")
        require_in_range(self.speed_km_s, 0.0, MAX_SPEED_KM_S, "speed_km_s")


@dataclass(frozen=True, slots=True)
class DownloadAttempts:
    """Time of the last download attempt of each kind, successful or not (DESIGN.md §4.2, ADR-003)."""

    elements: datetime | None = None
    catalog: datetime | None = None

    def __post_init__(self) -> None:
        """Require timezone-aware UTC times when they are present."""
        if self.elements is not None:
            require_utc(self.elements, "elements")
        if self.catalog is not None:
            require_utc(self.catalog, "catalog")
```

### `src/orbita/ports/satellite_data.py`

```python
"""Ports for the orbital data: download from CelesTrak and local storage (ARCHITECTURE.md §4)."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from orbita.domain.catalog import Catalog
from orbita.domain.elements import OrbitalDataset
from orbita.domain.state import DownloadAttempts


@runtime_checkable
class SatelliteDataSource(Protocol):
    """Downloads the raw text of CelesTrak responses. The domain validates the text afterwards."""

    def download_elements(self, norad: int) -> str:
        """Return the raw JSON text of the orbital elements of one satellite.

        Preconditions: norad is one of the 20 satellites of DESIGN.md §3.1.
        Postconditions: the text is at most 5 MB and nothing is written to disk.
        Raises:
            DownloadError: on a non-200 response, a redirect, a timeout, a connection error or a body
                larger than 5 MB.
        """
        ...

    def download_catalog(self, norad: int) -> str:
        """Return the raw JSON text of the SATCAT record of one satellite.

        Preconditions: norad is one of the 20 satellites of DESIGN.md §3.1.
        Postconditions: the text is at most 5 MB and nothing is written to disk.
        Raises:
            DownloadError: under the same conditions as download_elements.
        """
        ...


@runtime_checkable
class SatelliteDataStore(Protocol):
    """Loads and saves the last valid data and the times of the download attempts."""

    def load_elements(self) -> OrbitalDataset | None:
        """Return the saved orbital elements, or None when no file exists.

        Preconditions: none.
        Postconditions: the returned dataset passed the domain validation when it was saved.
        Raises:
            DataValidationError: if the saved file cannot be read as a valid dataset.
        """
        ...

    def save_elements(self, dataset: OrbitalDataset) -> None:
        """Replace the saved orbital elements atomically.

        Preconditions: dataset is valid (its constructor already checked it).
        Postconditions: a reader sees either the old file or the new one, never a half-written file.
        Raises:
            OSError: if the file cannot be written; the previous file is kept.
        """
        ...

    def load_catalog(self) -> Catalog | None:
        """Return the saved SATCAT entries, or None when no file exists.

        Preconditions: none.
        Postconditions: the returned catalog passed the domain validation when it was saved.
        Raises:
            DataValidationError: if the saved file cannot be read as a valid catalog.
        """
        ...

    def save_catalog(self, catalog: Catalog) -> None:
        """Replace the saved SATCAT entries atomically.

        Preconditions: catalog is valid.
        Postconditions: as in save_elements.
        Raises:
            OSError: if the file cannot be written; the previous file is kept.
        """
        ...

    def load_attempts(self) -> DownloadAttempts:
        """Return the times of the last download attempts; empty values when none exists.

        Preconditions: none.
        Postconditions: never None; a missing file gives DownloadAttempts().
        Raises:
            DataValidationError: if the saved file cannot be read.
        """
        ...

    def save_attempts(self, attempts: DownloadAttempts) -> None:
        """Replace the times of the last download attempts atomically.

        Preconditions: attempts has UTC times.
        Postconditions: as in save_elements.
        Raises:
            OSError: if the file cannot be written.
        """
        ...
```

### `src/orbita/ports/propagation.py`

```python
"""Ports for the orbit computation and the current time (ARCHITECTURE.md §4)."""

from __future__ import annotations

from datetime import datetime
from typing import Protocol, runtime_checkable

from orbita.domain.elements import OrbitalElements
from orbita.domain.observer import GroundPoint
from orbita.domain.state import SatelliteState


@runtime_checkable
class OrbitPropagator(Protocol):
    """Computes satellite positions from orbital elements (SGP4, DESIGN.md §6)."""

    def state(self, elements: OrbitalElements, moment: datetime) -> SatelliteState:
        """Return the position and speed of one satellite at one instant.

        Preconditions: elements is valid; moment is timezone-aware UTC.
        Postconditions: the altitude is in km above the spherical Earth model of the adapter.
        Raises:
            PropagationError: if the orbit cannot be computed for that instant.
        """
        ...

    def ground_track(
        self, elements: OrbitalElements, moments: tuple[datetime, ...]
    ) -> tuple[GroundPoint, ...]:
        """Return the sub-satellite point of one satellite at each instant, in the same order.

        Preconditions: moments is a tuple of timezone-aware UTC datetimes.
        Postconditions: the result has the same length as moments.
        Raises:
            PropagationError: if the orbit cannot be computed for one of the instants.
        """
        ...


@runtime_checkable
class Clock(Protocol):
    """Gives the current time, so that the domain and the use cases never read the clock (ARCHITECTURE.md §6)."""

    def now(self) -> datetime:
        """Return the current time as a timezone-aware UTC datetime.

        Preconditions: none.
        Postconditions: the result has tzinfo UTC.
        """
        ...
```

### `tests/ports/test_ports.py`

```python
"""Tests that the ports are satisfied by plain objects and that the state types validate (spec 008)."""

from __future__ import annotations

import math
from datetime import UTC, datetime

import pytest

from orbita.domain.errors import DataValidationError
from orbita.domain.observer import GroundPoint
from orbita.domain.state import DownloadAttempts, SatelliteState
from orbita.ports.propagation import Clock, OrbitPropagator
from orbita.ports.satellite_data import SatelliteDataSource, SatelliteDataStore

NOW = datetime(2026, 10, 30, 12, 0, tzinfo=UTC)


class FakeSource:
    def download_elements(self, norad: int) -> str:
        return "[]"

    def download_catalog(self, norad: int) -> str:
        return "[]"


class FakeStore:
    def load_elements(self) -> None:
        return None

    def save_elements(self, dataset: object) -> None:
        return None

    def load_catalog(self) -> None:
        return None

    def save_catalog(self, catalog: object) -> None:
        return None

    def load_attempts(self) -> DownloadAttempts:
        return DownloadAttempts()

    def save_attempts(self, attempts: DownloadAttempts) -> None:
        return None


class FakePropagator:
    def state(self, elements: object, moment: datetime) -> SatelliteState:
        return SatelliteState(norad=25544, point=GroundPoint(0.0, 0.0, 400.0), speed_km_s=7.66)

    def ground_track(self, elements: object, moments: tuple[datetime, ...]) -> tuple[GroundPoint, ...]:
        return ()


class FakeClock:
    def now(self) -> datetime:
        return NOW


class ClockWithoutNow:
    pass


def test_fake_source_satisfies_the_source_port() -> None:
    assert isinstance(FakeSource(), SatelliteDataSource)


def test_fake_store_satisfies_the_store_port() -> None:
    assert isinstance(FakeStore(), SatelliteDataStore)


def test_fake_propagator_satisfies_the_propagator_port() -> None:
    assert isinstance(FakePropagator(), OrbitPropagator)


def test_fake_clock_satisfies_the_clock_port() -> None:
    assert isinstance(FakeClock(), Clock)


def test_object_without_the_methods_does_not_satisfy_the_clock_port() -> None:
    assert not isinstance(ClockWithoutNow(), Clock)


def test_satellite_state_rejects_negative_speed() -> None:
    with pytest.raises(DataValidationError):
        SatelliteState(norad=25544, point=GroundPoint(0.0, 0.0), speed_km_s=-1.0)


def test_satellite_state_rejects_nan_speed() -> None:
    with pytest.raises(DataValidationError):
        SatelliteState(norad=25544, point=GroundPoint(0.0, 0.0), speed_km_s=math.nan)


def test_satellite_state_rejects_non_positive_norad() -> None:
    with pytest.raises(DataValidationError):
        SatelliteState(norad=0, point=GroundPoint(0.0, 0.0), speed_km_s=7.5)


def test_download_attempts_accept_missing_values() -> None:
    attempts = DownloadAttempts()
    assert attempts.elements is None and attempts.catalog is None


def test_download_attempts_reject_naive_time() -> None:
    with pytest.raises(DataValidationError):
        DownloadAttempts(elements=datetime(2026, 10, 30, 12, 0))
```

## Pasos

1. **Crear la rama:** `git switch -c feature/008-puertos`.
2. **Crear los cuatro archivos** de la sección de contenido, con el contenido exacto de este documento.
3. **Ejecutar los tests:** `uv run pytest -v`. Deben pasar los tests de la spec 007 más los nuevos de
   `tests/ports/test_ports.py`.
4. **Comprobar que `orbita.ports` no importa nada prohibido:** `uv run pytest tests/test_architecture.py -v`.
5. **Comprobar calidad:** `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy src` y
   `uv run pre-commit run --all-files`.
6. **Commit y merge** con el mensaje `008: puertos`.

## Casos borde y manejo de errores

1. Un objeto que tiene el método pero con otro nombre no cumple el puerto: `isinstance` con `runtime_checkable` solo
   comprueba que los nombres existan, no sus firmas. Las firmas las comprueba mypy en los casos de uso (spec 014).
2. `DownloadAttempts` sin valores significa "nunca se ha intentado": la regla de intervalos (spec 005) lo trata como
   descarga pendiente.
3. Un `SatelliteState` con altitud negativa no se puede construir por `GroundPoint` (spec 003).

## Tests de aceptación

Los tests de `tests/ports/test_ports.py`: cada objeto falso cumple su puerto; un objeto sin métodos no cumple
`Clock`; `SatelliteState` rechaza velocidad negativa, velocidad `NaN` y NORAD no positivo; `DownloadAttempts` acepta
valores vacíos y rechaza una hora sin zona.

## Fuera de alcance

- Las implementaciones de los puertos: specs 011 (fuente), 012 (almacén), 013 (propagador y reloj).
- Los casos de uso que usan los puertos: spec 014.

## Definition of Done

Todos los comandos en PowerShell, desde la carpeta `orbita`.

- [ ] `uv run pytest -v` → todos los tests pasan.
- [ ] `uv run pytest tests/test_architecture.py -v` → 7 passed.
- [ ] `Select-String -Path src\orbita\ports\*.py -Pattern 'orbita\.(app|adapters|ui)'` → sin salida.
- [ ] `uv run ruff check .` → `All checks passed!`
- [ ] `uv run mypy src` → `Success: no issues found`.
- [ ] `uv run pre-commit run --all-files` → todos los hooks en `Passed`.
- [ ] `git status` → `nothing to commit, working tree clean` después del merge.
