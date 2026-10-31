# 013 - Adaptadores `SkyfieldPropagator` y `SystemClock`

## Objetivo

Al terminar, el proyecto puede calcular la posición, la altura, la velocidad y la trayectoria de cualquier satélite de
la lista a partir de sus elementos orbitales, con SGP4 a través de Skyfield, y puede leer la hora real en UTC. Ambos son
adaptadores de los puertos `OrbitPropagator` y `Clock` (spec 008).

## Depende de

- 008 (los puertos `OrbitPropagator` y `Clock`).
- 010 (la lista de satélites, para las pruebas con datos reales de la spec 017; las pruebas de esta spec usan un satélite
  sintético y no dependen de la lista).

## Archivos rectores aplicables

- `security-rules.md` SEC-17 (Skyfield usa `load.timescale(builtin=True)` y no descarga nada), SEC-30 (sin datos de
  texto en los logs), SEC-02 (sin `Observer`).
- `ARCHITECTURE.md` §4 (adaptador `SkyfieldPropagator`), §6 (los tipos de librerías sin tipar se encapsulan con
  `# type: ignore[<código>]` con código explícito).
- `DESIGN.md` §4.4 (la distancia usa la misma geometría de la esfera), §6 (Skyfield como librería de cálculo).
- `docs/00-requirements.es.md` RF-01 (dos posiciones con 1 s de diferencia separadas entre 7 y 8 km), RF-02 (la trayectoria
  de la ISS tiene 91 puntos), RNF-01 (100 ms por refresco).

## Dependencias externas

- `skyfield`, versión exacta, añadida con `uv add`. Es una dependencia de ejecución: `DESIGN.md` §6 la lista como
  "Yes, official docs". Su versión y la firma de `EarthSatellite.from_omm` se verifican en el paso 1.

## Archivos a crear

1. `src/orbita/adapters/skyfield_propagator.py`
2. `src/orbita/adapters/system_clock.py`
3. `tests/adapters/test_skyfield_propagator.py`
4. `tests/adapters/test_system_clock.py`

Son cuatro archivos en la capa `adapters` y sus tests.

## Contenido exacto de los archivos

### `src/orbita/adapters/skyfield_propagator.py`

```python
"""Skyfield adapter: satellite positions computed locally with SGP4 (DESIGN.md §6, SEC-17)."""

from __future__ import annotations

import math
import threading
from datetime import datetime
from typing import Any, Final

from skyfield.api import EarthSatellite, load, wgs84  # type: ignore[import-untyped]

from orbita.domain.elements import OrbitalElements
from orbita.domain.errors import DataValidationError, PropagationError
from orbita.domain.observer import GroundPoint
from orbita.domain.state import SatelliteState

TRACK_ALTITUDE_KM: Final = 0.0


class SkyfieldPropagator:
    """Computes positions with Skyfield's SGP4 model.

    Preconditions: elements are valid OrbitalElements; moments are timezone-aware UTC datetimes.
    Postconditions: the altitude is measured above the spherical Earth of wgs84.subpoint.
    """

    def __init__(self) -> None:
        """Load the time scale from Skyfield's built-in data, so no file is downloaded (SEC-17)."""
        self._timescale: Any = load.timescale(builtin=True)
        self._lock = threading.Lock()
        self._satellites: dict[int, tuple[OrbitalElements, Any]] = {}

    def state(self, elements: OrbitalElements, moment: datetime) -> SatelliteState:
        """Return the position and the speed of one satellite at one instant (OrbitPropagator).

        Raises:
            PropagationError: if the orbit cannot be computed for that instant, for example after re-entry.
        """
        satellite = self._satellite_for(elements)
        try:
            geocentric = satellite.at(self._timescale.from_datetime(moment))
            subpoint = wgs84.subpoint(geocentric)
            point = GroundPoint(
                latitude=float(subpoint.latitude.degrees),
                longitude=float(subpoint.longitude.degrees),
                altitude_km=float(subpoint.elevation.km),
            )
            velocity = [float(component) for component in geocentric.velocity.km_per_s]
        except (ValueError, ArithmeticError, DataValidationError) as error:
            raise PropagationError(
                f"the orbit of NORAD {elements.norad} cannot be computed"
            ) from error
        speed = math.sqrt(sum(component * component for component in velocity))
        return SatelliteState(norad=elements.norad, point=point, speed_km_s=speed)

    def ground_track(
        self, elements: OrbitalElements, moments: tuple[datetime, ...]
    ) -> tuple[GroundPoint, ...]:
        """Return the point under the satellite at each moment, at altitude zero (OrbitPropagator).

        Raises:
            PropagationError: if the orbit cannot be computed for one of the moments.
        """
        satellite = self._satellite_for(elements)
        track: list[GroundPoint] = []
        for moment in moments:
            try:
                subpoint = wgs84.subpoint(satellite.at(self._timescale.from_datetime(moment)))
                track.append(
                    GroundPoint(
                        latitude=float(subpoint.latitude.degrees),
                        longitude=float(subpoint.longitude.degrees),
                        altitude_km=TRACK_ALTITUDE_KM,
                    )
                )
            except (ValueError, ArithmeticError) as error:
                raise PropagationError(
                    f"the ground track of NORAD {elements.norad} cannot be computed"
                ) from error
        return tuple(track)

    def _satellite_for(self, elements: OrbitalElements) -> Any:
        """Return the Skyfield satellite for these elements, building it once per change (ARCHITECTURE.md §6)."""
        with self._lock:
            cached = self._satellites.get(elements.norad)
            if cached is not None and cached[0] == elements:
                return cached[1]
            try:
                satellite = EarthSatellite.from_omm(self._timescale, _omm_fields(elements))
            except (ValueError, KeyError, TypeError) as error:
                raise PropagationError(
                    f"the elements of NORAD {elements.norad} cannot be used"
                ) from error
            self._satellites[elements.norad] = (elements, satellite)
            return satellite


def _omm_fields(elements: OrbitalElements) -> dict[str, object]:
    """Map the domain elements to the OMM field names that Skyfield's from_omm expects."""
    return {
        "OBJECT_NAME": elements.name,
        "NORAD_CAT_ID": elements.norad,
        "EPOCH": elements.epoch.replace(tzinfo=None).isoformat(timespec="microseconds"),
        "MEAN_MOTION": elements.mean_motion_rev_day,
        "ECCENTRICITY": elements.eccentricity,
        "INCLINATION": elements.inclination_deg,
        "RA_OF_ASC_NODE": elements.raan_deg,
        "ARG_OF_PERICENTER": elements.arg_perigee_deg,
        "MEAN_ANOMALY": elements.mean_anomaly_deg,
        "MEAN_MOTION_DOT": elements.mean_motion_dot,
        "MEAN_MOTION_DDOT": elements.mean_motion_ddot,
        "BSTAR": elements.bstar,
        "EPHEMERIS_TYPE": 0,
        "CLASSIFICATION_TYPE": "U",
        "ELEMENT_SET_NO": 999,
        "REV_AT_EPOCH": 0,
    }
```

### `src/orbita/adapters/system_clock.py`

```python
"""System clock adapter: the only place where the program reads the real time (ARCHITECTURE.md §6)."""

from __future__ import annotations

from datetime import UTC, datetime


class SystemClock:
    """Returns the current time of the operating system, in UTC (Clock port)."""

    def now(self) -> datetime:
        """Return the current time with tzinfo UTC.

        Preconditions: none.
        Postconditions: the result is timezone-aware and in UTC.
        """
        return datetime.now(UTC)
```

### `tests/adapters/test_skyfield_propagator.py`

```python
"""Tests of the Skyfield adapter with a synthetic low orbit: no network (spec 013)."""

from __future__ import annotations

import math
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest

from orbita.adapters.skyfield_propagator import SkyfieldPropagator
from orbita.domain.distance_rules import to_cartesian
from orbita.domain.elements import OrbitalElements
from orbita.domain.errors import PropagationError

EPOCH = datetime(2026, 10, 30, 12, 0, tzinfo=UTC)
NOW = EPOCH + timedelta(hours=1)


def leo(**changes: Any) -> OrbitalElements:
    values: dict[str, Any] = {
        "norad": 25544,
        "name": "SYNTHETIC LEO",
        "inclination_deg": 51.6,
        "mean_motion_rev_day": 15.5,
        "eccentricity": 0.0005,
        "epoch": EPOCH,
        "raan_deg": 0.0,
        "arg_perigee_deg": 0.0,
        "mean_anomaly_deg": 0.0,
        "mean_motion_dot": 0.0,
        "mean_motion_ddot": 0.0,
        "bstar": 0.0,
    }
    values.update(changes)
    return OrbitalElements(**values)


def test_altitude_of_a_low_orbit_is_in_the_expected_range() -> None:
    state = SkyfieldPropagator().state(leo(), NOW)
    assert 300.0 <= state.point.altitude_km <= 500.0


def test_speed_of_a_low_orbit_is_about_7_6_km_per_second() -> None:
    state = SkyfieldPropagator().state(leo(), NOW)
    assert 7.4 <= state.speed_km_s <= 7.9


def test_positions_one_second_apart_are_7_to_8_km_apart() -> None:
    propagator = SkyfieldPropagator()
    first = propagator.state(leo(), NOW).point
    second = propagator.state(leo(), NOW + timedelta(seconds=1)).point
    distance = math.dist(to_cartesian(first), to_cartesian(second))
    assert 7.0 <= distance <= 8.0


def test_ground_track_has_91_points_at_the_surface() -> None:
    moments = tuple(NOW + timedelta(minutes=minute) for minute in range(-45, 46))
    track = SkyfieldPropagator().ground_track(leo(), moments)
    assert len(track) == 91
    assert all(point.altitude_km == 0.0 for point in track)


def test_repeated_calls_give_the_same_state() -> None:
    propagator = SkyfieldPropagator()
    assert propagator.state(leo(), NOW) == propagator.state(leo(), NOW)


def test_naive_moment_is_reported_as_propagation_error() -> None:
    with pytest.raises(PropagationError):
        SkyfieldPropagator().state(leo(), datetime(2026, 10, 30, 13))
```

### `tests/adapters/test_system_clock.py`

```python
"""Tests of the system clock adapter (spec 013)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from orbita.adapters.system_clock import SystemClock
from orbita.ports.propagation import Clock


def test_system_clock_returns_utc_time() -> None:
    assert SystemClock().now().utcoffset() == timedelta(0)


def test_system_clock_is_between_two_real_readings() -> None:
    before = datetime.now(UTC)
    moment = SystemClock().now()
    after = datetime.now(UTC)
    assert before <= moment <= after


def test_system_clock_satisfies_the_clock_port() -> None:
    assert isinstance(SystemClock(), Clock)
```

## Pasos

1. **Crear la rama y añadir `skyfield`:**
   ```powershell
   git switch -c feature/013-adaptadores-skyfield-reloj
   uv add "skyfield==<version>"
   ```
   Sustituir `<version>` por la versión estable que `uv add skyfield` indique. Después comprobar la firma:
   ```powershell
   uv run python -c "from skyfield.api import EarthSatellite; help(EarthSatellite.from_omm)"
   ```
   Si `from_omm` no existe o pide otros campos, se para aquí, se registra en esta spec (Correcciones) y se decide con
   un ADR si hace falta cambiar la forma de construir el satélite. No se improvisa.
2. **Crear los cuatro archivos.**
3. **Ejecutar los tests:** `uv run pytest -v`. Si mypy marca `# type: ignore[import-untyped]` como innecesario, se quita
   ese comentario; si marca `no-any-return` en `_satellite_for`, se anota en la spec antes de añadir una supresión.
4. **Comprobar calidad:** `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy src`,
   `uv run pre-commit run --all-files`.
5. **Comprobar la regla de descarga cero:** `Select-String -Path src\orbita\adapters\skyfield_propagator.py -Pattern 'http|requests|urllib'`
   no debe mostrar nada.
6. **Commit y merge** con el mensaje `013: adaptadores skyfield y reloj`.

## Casos borde y manejo de errores

1. Un satélite cuya órbita ya es inválida (altitud negativa por reentrada) lanza `PropagationError`. El caso de uso
   (spec 014) lo cuenta como satélite ausente y no lo oculta.
2. Una hora sin zona horaria lanza `PropagationError` (Skyfield no la acepta). Los casos de uso solo pasan horas UTC.
3. Dos sesiones calculan a la vez: el `Lock` protege la caché de satélites.
4. Un cambio de elementos (una descarga nueva) reconstruye el satélite; los elementos iguales reutilizan el anterior.

## Tests de aceptación

- Altura de un satélite de órbita baja sintético entre 300 y 500 km.
- Velocidad entre 7.4 y 7.9 km/s.
- Dos posiciones separadas 1 s están entre 7 y 8 km (RF-01).
- La trayectoria tiene 91 puntos en la superficie (RF-02).
- Dos cálculos iguales dan el mismo estado.
- Una hora sin zona da `PropagationError`.
- El reloj devuelve UTC, está entre dos lecturas reales y cumple el puerto `Clock`.

## Fuera de alcance

- Las posiciones de los satélites reales y la precisión de RNF-02: spec 017 (punta a punta) y el sitio de referencia de
  `DESIGN.md` §8.
- La predicción de pasos: v2.

## Definition of Done

- [ ] `uv run python -c "from skyfield.api import EarthSatellite; help(EarthSatellite.from_omm)"` → muestra la firma (el
  paso 1 queda anotado).
- [ ] `uv run pytest -v` → todos los tests pasan.
- [ ] `uv run mypy src` → `Success: no issues found`.
- [ ] `Select-String -Path src\orbita\adapters\*.py -Pattern 'except Exception:'` → sin salida.
- [ ] `uv run ruff check .` y `uv run pre-commit run --all-files` sin errores.
- [ ] `git status` → `nothing to commit, working tree clean` después del merge.
