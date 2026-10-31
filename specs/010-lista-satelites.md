# 010 - Lista de los 20 satélites con números NORAD confirmados

## Estado

**Bloqueada.** Diez de los veinte números NORAD de `DESIGN.md` §3.1 están marcados "por confirmar". Esta spec no se
puede implementar hasta que el usuario los confirme en CelesTrak (ver el paso 1). La sesión de redacción no pudo consultar
CelesTrak: el proxy devolvió 403 para todas las consultas por nombre.

## Objetivo

Al terminar, el dominio tiene la lista fija de los 20 satélites de `DESIGN.md` §3.1, con su número NORAD y su nombre,
y un test que comprueba que la lista es correcta. Es la única fuente de los números que la validación (spec 007) y los
casos de uso (spec 014) aceptan.

## Depende de

- 003 (paquete `orbita.domain`).

## Archivos rectores aplicables

- `DESIGN.md` §3.1 (la tabla de satélites y los números por confirmar), §8 (validación pendiente).
- `docs/00-requirements.es.md` RF-03 (el tipo de órbita debe salir correcto para cada satélite), RF-13.
- `security-rules.md` SEC-10 (el NORAD de cada registro debe estar en esta lista).

## Números confirmados

| # | Satélite | NORAD | Fuente |
|---|---|---|---|
| 1 | ISS (ZARYA) | 25544 | `DESIGN.md` §3.1 |
| 2 | Tiangong (Tianhe) | 48274 | `DESIGN.md` §3.1 |
| 3 | Hubble | 20580 | `DESIGN.md` §3.1 |
| 7 | NOAA-20 | 43013 | `DESIGN.md` §3.1 |
| 8 | Terra | 25994 | `DESIGN.md` §3.1 |
| 9 | Landsat 9 | 49260 | `DESIGN.md` §3.1 |
| 10 | Sentinel-1A | 39634 | `DESIGN.md` §3.1 |
| 11 | Sentinel-2A | 40697 | `DESIGN.md` §3.1 |
| 12 | Envisat | 27386 | `DESIGN.md` §3.1 |
| 16 | GOES-19 | 60133 | `DESIGN.md` §3.1 |

## Números por confirmar

| # | Satélite | Qué buscar en CelesTrak |
|---|---|---|
| 4 | AstroSat | Nombre `ASTROSAT`, satélite de la India en órbita casi ecuatorial |
| 5 | Un satélite Starlink | Cualquier objeto `STARLINK-` activo; se escoge uno y se anota su nombre exacto |
| 6 | FACSAT-2 | Nombre `FACSAT-2`; si no está en órbita, se escoge otro satélite colombiano y se registra en esta spec |
| 13 | Fengyun-3D | Nombre `FENGYUN 3D` |
| 14 | Meteor-M 2 | Nombre `METEOR-M 2` |
| 15 | Cartosat-3 | Nombre `CARTOSAT-3` |
| 17 | Himawari-9 | Nombre `HIMAWARI-9` |
| 18 | Meteosat-11 | Nombre `METEOSAT-11` |
| 19 | Un satélite GPS III | Nombre `GPS III`, un objeto activo; se anota el nombre exacto |
| 20 | Un satélite Galileo | Nombre `GALILEO`, un objeto activo; se anota el nombre exacto |

## Archivos a crear

1. `src/orbita/domain/satellites.py`
2. `tests/domain/test_satellites.py`

## Dependencias externas

Ninguna.

## Contenido exacto de los archivos

### `src/orbita/domain/satellites.py`

Este bloque NO se extrae automáticamente: tiene diez números sin confirmar. Se completa a mano en el paso 2.

```text
"""The 20 satellites of Orbita (DESIGN.md §3.1). Numbers are fixed by spec 010."""

from __future__ import annotations

from dataclasses import dataclass

from orbita.domain.errors import DataValidationError

MAX_SATELLITE_NAME_LENGTH = 80
ISS_NORAD = 25544
EXPECTED_SATELLITE_COUNT = 20


@dataclass(frozen=True, slots=True)
class SatelliteSpec:
    """A satellite of the list: its NORAD catalog number and the name shown to the user."""

    norad: int
    name: str


SATELLITES: tuple[SatelliteSpec, ...] = (
    SatelliteSpec(25544, "ISS (ZARYA)"),
    SatelliteSpec(48274, "Tiangong (Tianhe)"),
    SatelliteSpec(20580, "Hubble"),
    SatelliteSpec(0, "AstroSat"),  # PENDIENTE: confirmar el NORAD en CelesTrak
    SatelliteSpec(0, "STARLINK-PENDIENTE"),  # PENDIENTE: nombre exacto y NORAD
    SatelliteSpec(0, "FACSAT-2"),  # PENDIENTE: confirmar que sigue en órbita
    SatelliteSpec(43013, "NOAA 20"),
    SatelliteSpec(25994, "Terra"),
    SatelliteSpec(49260, "Landsat 9"),
    SatelliteSpec(39634, "Sentinel-1A"),
    SatelliteSpec(40697, "Sentinel-2A"),
    SatelliteSpec(27386, "Envisat"),
    SatelliteSpec(0, "FENGYUN 3D"),  # PENDIENTE
    SatelliteSpec(0, "METEOR-M 2"),  # PENDIENTE
    SatelliteSpec(0, "CARTOSAT-3"),  # PENDIENTE
    SatelliteSpec(60133, "GOES 19"),
    SatelliteSpec(0, "HIMAWARI-9"),  # PENDIENTE
    SatelliteSpec(0, "METEOSAT-11"),  # PENDIENTE
    SatelliteSpec(0, "GPS III"),  # PENDIENTE
    SatelliteSpec(0, "GALILEO"),  # PENDIENTE
)

SATELLITE_NORADS: frozenset[int] = frozenset(satellite.norad for satellite in SATELLITES)


def check_satellite_list(satellites: tuple[SatelliteSpec, ...]) -> None:
    """Raise DataValidationError unless the list has 20 unique NORAD numbers and unique names."""
    if len(satellites) != EXPECTED_SATELLITE_COUNT:
        raise DataValidationError("the satellite list must contain exactly 20 satellites")
    norads = [satellite.norad for satellite in satellites]
    names = [satellite.name for satellite in satellites]
    if len(set(norads)) != len(norads) or any(norad <= 0 for norad in norads):
        raise DataValidationError("every satellite needs a unique positive NORAD number")
    if len(set(names)) != len(names) or any(
        not name or len(name) > MAX_SATELLITE_NAME_LENGTH for name in names
    ):
        raise DataValidationError("every satellite needs a unique name of at most 80 characters")
```

### `tests/domain/test_satellites.py`

Este bloque tampoco se extrae: depende de que los números estén confirmados.

```text
"""Tests of the satellite list (spec 010)."""

from __future__ import annotations

import pytest

from orbita.domain.errors import DataValidationError
from orbita.domain.satellites import (
    ISS_NORAD,
    SATELLITE_NORADS,
    SATELLITES,
    SatelliteSpec,
    check_satellite_list,
)


def test_the_list_has_twenty_satellites_with_unique_norad_numbers() -> None:
    check_satellite_list(SATELLITES)
    assert len(SATELLITE_NORADS) == 20


def test_every_norad_number_is_confirmed() -> None:
    assert all(satellite.norad > 0 for satellite in SATELLITES)


def test_the_iss_is_in_the_list() -> None:
    assert ISS_NORAD in SATELLITE_NORADS


def test_a_list_with_a_duplicate_is_rejected() -> None:
    duplicated = (SatelliteSpec(25544, "ISS"),) * 20
    with pytest.raises(DataValidationError):
        check_satellite_list(duplicated)


def test_a_list_with_nineteen_satellites_is_rejected() -> None:
    with pytest.raises(DataValidationError):
        check_satellite_list(SATELLITES[:19])
```

## Pasos

1. **Confirmar los diez números en CelesTrak** (desde un navegador, no desde código): buscar cada nombre de la tabla
   "Números por confirmar" en `celestrak.org`, comprobar que el satélite sigue en órbita y anotar el número NORAD. Para
   los satélites genéricos (Starlink, GPS III, Galileo) escoger uno activo y anotar su nombre exacto. Anotar aquí los
   números y la fecha de la consulta.
2. **Completar `src\orbita\domain\satellites.py`** reemplazando cada `SatelliteSpec(0, ...)` con su número confirmado y
   quitando el comentario `# PENDIENTE`. Copiar el bloque de este documento y usar la forma `python`, no `text`.
3. **Crear la rama:** `git switch -c feature/010-lista-satelites`.
4. **Crear `tests\domain\test_satellites.py`** y ejecutar `uv run pytest -v`.
5. **Comprobar calidad, commit y merge** como en la spec 007, con el mensaje `010: lista de los 20 satelites`.

## Casos borde y manejo de errores

1. Un satélite que ya no está en órbita (por ejemplo, FACSAT-2): se sustituye por otro satélite colombiano o de un
   país de la lista, y la tabla de la spec se corrige con fecha (ver "Correcciones" en `specs/README.md`).
2. Dos satélites con el mismo número: `check_satellite_list` lo rechaza y el test de duplicados lo confirma.
3. Un nombre vacío o de más de 80 caracteres: se rechaza.

## Tests de aceptación

- La lista tiene 20 satélites con números NORAD únicos y positivos.
- Ningún número es 0.
- La ISS (25544) está en la lista.
- Una lista con un duplicado se rechaza.
- Una lista con 19 satélites se rechaza.

## Fuera de alcance

- Que cada satélite tenga el tipo de órbita esperado: se comprueba con los datos reales en la spec 017 (prueba de punta
  a punta).
- El país de cada satélite: spec 018, con el catálogo SATCAT.

## Definition of Done

- [ ] Los diez números de la tabla "Números por confirmar" están anotados en esta spec, con fecha.
- [ ] `uv run pytest -v` → todos los tests pasan, incluidos los 5 de `test_satellites.py`.
- [ ] `Select-String -Path src\orbita\domain\satellites.py -Pattern 'PENDIENTE'` → sin salida.
- [ ] `uv run ruff check .`, `uv run mypy src` y `uv run pre-commit run --all-files` sin errores.
- [ ] `git status` → `nothing to commit, working tree clean` después del merge.
