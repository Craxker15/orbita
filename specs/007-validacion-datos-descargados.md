# 007 - Validación de los datos descargados

## Objetivo

Al terminar, el dominio puede decidir qué parte de una respuesta de CelesTrak es aceptable antes de guardarla: tamaño
máximo, JSON sin `NaN` ni `Infinity`, campos con rango, números NORAD de la lista, fecha de época razonable, nombres
sin caracteres peligrosos y variación de movimiento medio menor o igual al 5 %. Además, esta spec corrige un hueco de
la spec 003: `OrbitalElements` no guardaba los campos que SGP4 necesita para calcular la posición (RAAN, argumento del
perigeo, anomalía media, BSTAR y las derivadas del movimiento medio). Sin ellos la spec 013 no puede construir el
satélite.

## Depende de

- 003 (tipos y errores). La lista de satélites de la spec 010 no hace falta: la validación recibe los números permitidos
  como argumento.

## Archivos rectores aplicables

- `security-rules.md` SEC-10 (validación de cada campo, límite de 5 MB), SEC-28 (sin `NaN`, `Infinity` ni anidamiento
  excesivo; máximo 50 registros), SEC-29 (variación del 5 % del movimiento medio), SEC-30 (los logs solo contienen
  números NORAD), SEC-38 (batería de entradas maliciosas), SEC-13 (texto como texto plano).
- `ARCHITECTURE.md` §2 (el dominio usa solo la biblioteca estándar), §6 (errores con `OrbitaError`).
- `DESIGN.md` §4.2 (la frescura se calcula con la fecha de época real, no con la de descarga).

## Archivos a crear

1. `src/orbita/domain/validation.py`
2. `tests/domain/test_validation.py`

## Archivos a modificar

3. `src/orbita/domain/elements.py` (corrección a la spec 003: se añaden seis campos a `OrbitalElements`).
4. `src/orbita/domain/errors.py` (se añaden `DownloadError`, usado por el adaptador en la spec 011, y
   `PropagationError`, usado en la spec 013).
5. `tests/domain/test_types.py` (solo el diccionario de valores de `make_elements`, ver el paso 3).

Son cinco archivos de código, dentro del límite de la regla 3 del índice. Todos están en la capa `domain` y sus tests.

## Dependencias externas

Ninguna. Solo `json`, `datetime` y `collections.abc` de la biblioteca estándar.

## Contenido exacto de los archivos

### `src/orbita/domain/errors.py`

```python
"""Project exceptions. Every Orbita error inherits from OrbitaError (ARCHITECTURE.md §6)."""

from __future__ import annotations


class OrbitaError(Exception):
    """Base class of every error raised by the project."""


class DataValidationError(OrbitaError):
    """Downloaded or stored data does not pass validation (SEC-10, RF-07)."""


class DownloadError(OrbitaError):
    """A CelesTrak download failed or was refused (SEC-16, SEC-26, SEC-27)."""


class PropagationError(OrbitaError):
    """The orbit of a satellite could not be computed (DESIGN.md §4.4)."""


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
MAX_ANGLE_DEG = 360.0
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


def require_finite(value: float, field: str) -> None:
    """Raise DataValidationError unless the value is a finite number."""
    if not math.isfinite(value):
        raise DataValidationError(f"{field} must be a finite number")


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
    require_finite(value, field)
    above = value >= low if low_inclusive else value > low
    below = value <= high if high_inclusive else value < high
    if not (above and below):
        raise DataValidationError(f"{field} must be between {low} and {high}")


@dataclass(frozen=True, slots=True)
class OrbitalElements:
    """The orbital elements of one satellite, as published by CelesTrak (the OMM fields used by SGP4)."""

    norad: int
    name: str
    inclination_deg: float
    mean_motion_rev_day: float
    eccentricity: float
    epoch: datetime
    raan_deg: float
    arg_perigee_deg: float
    mean_anomaly_deg: float
    mean_motion_dot: float
    mean_motion_ddot: float
    bstar: float

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
        require_in_range(
            self.raan_deg, 0.0, MAX_ANGLE_DEG, "raan_deg", high_inclusive=False
        )
        require_in_range(
            self.arg_perigee_deg, 0.0, MAX_ANGLE_DEG, "arg_perigee_deg", high_inclusive=False
        )
        require_in_range(
            self.mean_anomaly_deg, 0.0, MAX_ANGLE_DEG, "mean_anomaly_deg", high_inclusive=False
        )
        require_finite(self.mean_motion_dot, "mean_motion_dot")
        require_finite(self.mean_motion_ddot, "mean_motion_ddot")
        require_finite(self.bstar, "bstar")
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

### `src/orbita/domain/validation.py`

```python
"""Validation of the data downloaded from CelesTrak (SEC-10, SEC-28, SEC-29, SEC-38, RF-07).

The adapter delivers raw text. This module decides what is accepted. It does not read the network,
the disk or the clock: the current time is an argument.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from typing import NoReturn

from orbita.domain.catalog import CatalogEntry
from orbita.domain.elements import OrbitalElements, require_utc
from orbita.domain.errors import DataValidationError

MAX_DOWNLOAD_BYTES = 5 * 1024 * 1024
MAX_RECORDS = 50
MAX_MEAN_MOTION_CHANGE = 0.05
MAX_EPOCH_IN_FUTURE = timedelta(days=1)
FORBIDDEN_NAME_CHARACTERS = frozenset("<>")

ELEMENTS_REQUIRED_KEYS = (
    "NORAD_CAT_ID",
    "OBJECT_NAME",
    "EPOCH",
    "INCLINATION",
    "MEAN_MOTION",
    "ECCENTRICITY",
    "RA_OF_ASC_NODE",
    "ARG_OF_PERICENTER",
    "MEAN_ANOMALY",
    "MEAN_MOTION_DOT",
    "MEAN_MOTION_DDOT",
    "BSTAR",
)
CATALOG_REQUIRED_KEYS = ("NORAD_CAT_ID", "OWNER", "LAUNCH_DATE")


@dataclass(frozen=True, slots=True)
class ParsedRecords[T]:
    """The accepted records of one payload, and the NORAD numbers of the records that were rejected."""

    accepted: tuple[T, ...]
    rejected_norad: tuple[int, ...]


def parse_json_text(text: str) -> object:
    """Parse downloaded text as JSON, rejecting size, NaN, Infinity and very deep nesting.

    Preconditions: text is the complete body of one response.
    Postconditions: the result contains only JSON values; no NaN or Infinity.
    Raises:
        DataValidationError: if the text is larger than 5 MB, is not valid JSON, is nested too
            deeply, or contains NaN, Infinity or -Infinity.
    """
    if len(text.encode("utf-8")) > MAX_DOWNLOAD_BYTES:
        raise DataValidationError("the downloaded text is larger than 5 MB")
    try:
        return json.loads(text, parse_constant=_reject_constant)
    except (ValueError, RecursionError) as error:
        raise DataValidationError("the downloaded text is not valid JSON") from error


def _reject_constant(token: str) -> NoReturn:
    """Reject the JSON constants NaN, Infinity and -Infinity (SEC-28)."""
    raise DataValidationError(f"the JSON constant {token} is not allowed")


def parse_elements_payload(
    payload: object, allowed_norad: frozenset[int], now: datetime
) -> ParsedRecords[OrbitalElements]:
    """Validate a list of orbital element records (CelesTrak GP in JSON).

    A payload that is not a list of at most 50 records is rejected as a whole. A single invalid record only
    rejects its own satellite, so the valid records of the same payload are kept (RF-07, SEC-38).

    Preconditions: now is timezone-aware UTC.
    Postconditions: every accepted element has a NORAD number in allowed_norad, a finite value in each field
        and an epoch at most one day after now.
    Raises:
        DataValidationError: if the payload itself is not a list of at most 50 records.
    """
    require_utc(now, "now")
    records = _top_level_list(payload)
    accepted: list[OrbitalElements] = []
    rejected: list[int] = []
    for record in records:
        try:
            accepted.append(_element_from_record(record, allowed_norad, now))
        except DataValidationError:
            norad = _norad_of(record)
            if norad is not None:
                rejected.append(norad)
    return ParsedRecords(tuple(accepted), tuple(rejected))


def parse_catalog_payload(
    payload: object, allowed_norad: frozenset[int], now: datetime
) -> ParsedRecords[CatalogEntry]:
    """Validate a list of SATCAT records (country code and launch date, DESIGN.md §4.6).

    Preconditions: now is timezone-aware UTC.
    Postconditions: every accepted entry has a NORAD number in allowed_norad and a valid owner code.
    Raises:
        DataValidationError: if the payload itself is not a list of at most 50 records.
    """
    require_utc(now, "now")
    records = _top_level_list(payload)
    accepted: list[CatalogEntry] = []
    rejected: list[int] = []
    for record in records:
        try:
            accepted.append(_catalog_from_record(record, allowed_norad))
        except DataValidationError:
            norad = _norad_of(record)
            if norad is not None:
                rejected.append(norad)
    return ParsedRecords(tuple(accepted), tuple(rejected))


def mean_motion_change_is_plausible(
    previous: OrbitalElements | None, new: OrbitalElements
) -> bool:
    """Return False when the mean motion changed by more than 5 % since the saved value (SEC-29).

    Preconditions: previous, when present, has a mean motion greater than zero (SEC-10).
    Postconditions: True when there is no previous value.
    """
    if previous is None:
        return True
    change = abs(new.mean_motion_rev_day - previous.mean_motion_rev_day)
    return change / previous.mean_motion_rev_day <= MAX_MEAN_MOTION_CHANGE


def _top_level_list(payload: object) -> list[object]:
    """Return the records of the payload, or reject a payload that is not a list of at most 50."""
    if not isinstance(payload, list) or len(payload) > MAX_RECORDS:
        raise DataValidationError("the payload must be a list of at most 50 records")
    return list(payload)


def _element_from_record(
    record: object, allowed_norad: frozenset[int], now: datetime
) -> OrbitalElements:
    """Build one OrbitalElements from a CelesTrak record, or raise DataValidationError."""
    fields = _checked_mapping(record, ELEMENTS_REQUIRED_KEYS)
    norad = _as_int(fields["NORAD_CAT_ID"], "NORAD_CAT_ID")
    if norad not in allowed_norad:
        raise DataValidationError("the NORAD number is not in the satellite list")
    name = _as_text(fields["OBJECT_NAME"], "OBJECT_NAME")
    _check_name(name)
    return OrbitalElements(
        norad=norad,
        name=name,
        inclination_deg=_as_number(fields["INCLINATION"], "INCLINATION"),
        mean_motion_rev_day=_as_number(fields["MEAN_MOTION"], "MEAN_MOTION"),
        eccentricity=_as_number(fields["ECCENTRICITY"], "ECCENTRICITY"),
        epoch=_as_epoch(fields["EPOCH"], now),
        raan_deg=_as_number(fields["RA_OF_ASC_NODE"], "RA_OF_ASC_NODE"),
        arg_perigee_deg=_as_number(fields["ARG_OF_PERICENTER"], "ARG_OF_PERICENTER"),
        mean_anomaly_deg=_as_number(fields["MEAN_ANOMALY"], "MEAN_ANOMALY"),
        mean_motion_dot=_as_number(fields["MEAN_MOTION_DOT"], "MEAN_MOTION_DOT"),
        mean_motion_ddot=_as_number(fields["MEAN_MOTION_DDOT"], "MEAN_MOTION_DDOT"),
        bstar=_as_number(fields["BSTAR"], "BSTAR"),
    )


def _catalog_from_record(record: object, allowed_norad: frozenset[int]) -> CatalogEntry:
    """Build one CatalogEntry from a SATCAT record, or raise DataValidationError."""
    fields = _checked_mapping(record, CATALOG_REQUIRED_KEYS)
    norad = _as_int(fields["NORAD_CAT_ID"], "NORAD_CAT_ID")
    if norad not in allowed_norad:
        raise DataValidationError("the NORAD number is not in the satellite list")
    owner = _as_text(fields["OWNER"], "OWNER")
    launch = _as_text(fields["LAUNCH_DATE"], "LAUNCH_DATE")
    try:
        launch_date = date.fromisoformat(launch)
    except ValueError as error:
        raise DataValidationError("LAUNCH_DATE is not a valid date") from error
    return CatalogEntry(norad=norad, owner_code=owner, launch_date=launch_date)


def _checked_mapping(record: object, required: tuple[str, ...]) -> Mapping[str, object]:
    """Return the record if it is a JSON object with every required key."""
    if not isinstance(record, dict):
        raise DataValidationError("a record is not a JSON object")
    if any(key not in record for key in required):
        raise DataValidationError("a record lacks required fields")
    return record


def _norad_of(record: object) -> int | None:
    """Return the NORAD number of a record if it is an integer, so that a rejection can be logged."""
    if isinstance(record, dict):
        value = record.get("NORAD_CAT_ID")
        if isinstance(value, int) and not isinstance(value, bool):
            return value
    return None


def _as_int(value: object, field: str) -> int:
    """Return an integer field; booleans are rejected."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise DataValidationError(f"{field} must be an integer")
    return value


def _as_number(value: object, field: str) -> float:
    """Return a numeric field as float; booleans and strings are rejected."""
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise DataValidationError(f"{field} must be a number")
    return float(value)


def _as_text(value: object, field: str) -> str:
    """Return a text field; anything else is rejected."""
    if not isinstance(value, str):
        raise DataValidationError(f"{field} must be text")
    return value


def _check_name(name: str) -> None:
    """Reject names with angle brackets or control characters (SEC-13, SEC-30, SEC-38)."""
    if any(char in FORBIDDEN_NAME_CHARACTERS or not char.isprintable() for char in name):
        raise DataValidationError("the name contains forbidden characters")


def _as_epoch(value: object, now: datetime) -> datetime:
    """Parse the epoch as UTC; CelesTrak sends it without an offset, which means UTC."""
    text = _as_text(value, "EPOCH")
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError as error:
        raise DataValidationError("EPOCH is not a valid date") from error
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    parsed = parsed.astimezone(UTC)
    if parsed > now + MAX_EPOCH_IN_FUTURE:
        raise DataValidationError("EPOCH is more than one day in the future")
    return parsed
```

### `tests/domain/test_validation.py`

```python
"""Tests of the validation of downloaded data (spec 007)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from orbita.domain.elements import OrbitalElements
from orbita.domain.errors import DataValidationError
from orbita.domain.validation import (
    MAX_DOWNLOAD_BYTES,
    mean_motion_change_is_plausible,
    parse_catalog_payload,
    parse_elements_payload,
    parse_json_text,
)

NOW = datetime(2026, 10, 30, 12, 0, tzinfo=UTC)
ALLOWED = frozenset({25544, 20580})


def elements_record(**changes: object) -> dict[str, object]:
    record: dict[str, object] = {
        "NORAD_CAT_ID": 25544,
        "OBJECT_NAME": "ISS (ZARYA)",
        "EPOCH": "2026-10-30T10:00:00.000000",
        "INCLINATION": 51.6,
        "MEAN_MOTION": 15.5,
        "ECCENTRICITY": 0.0007,
        "RA_OF_ASC_NODE": 247.0,
        "ARG_OF_PERICENTER": 130.0,
        "MEAN_ANOMALY": 325.0,
        "MEAN_MOTION_DOT": 0.0001,
        "MEAN_MOTION_DDOT": 0.0,
        "BSTAR": 0.0001,
    }
    record.update(changes)
    return record


def catalog_record(**changes: object) -> dict[str, object]:
    record: dict[str, object] = {"NORAD_CAT_ID": 25544, "OWNER": "ISS", "LAUNCH_DATE": "1998-11-20"}
    record.update(changes)
    return record


def element_from(**changes: object) -> OrbitalElements:
    return parse_elements_payload([elements_record(**changes)], ALLOWED, NOW).accepted[0]


def test_parse_json_text_accepts_a_list() -> None:
    assert parse_json_text('[{"a": 1}]') == [{"a": 1}]


@pytest.mark.parametrize("text", ["[NaN]", "[Infinity]", '[{"x": -Infinity}]'])
def test_parse_json_text_rejects_nan_and_infinity(text: str) -> None:
    with pytest.raises(DataValidationError):
        parse_json_text(text)


def test_parse_json_text_rejects_text_over_5_mb() -> None:
    with pytest.raises(DataValidationError):
        parse_json_text("[" + " " * MAX_DOWNLOAD_BYTES + "]")


def test_parse_json_text_rejects_deep_nesting() -> None:
    with pytest.raises(DataValidationError):
        parse_json_text("[" * 10_000 + "]" * 10_000)


def test_parse_json_text_rejects_invalid_json() -> None:
    with pytest.raises(DataValidationError):
        parse_json_text("[{")


def test_valid_record_becomes_orbital_elements_in_utc() -> None:
    parsed = parse_elements_payload([elements_record()], ALLOWED, NOW)
    assert parsed.rejected_norad == ()
    assert parsed.accepted[0].epoch.tzinfo == UTC
    assert parsed.accepted[0].raan_deg == 247.0


def test_payload_must_be_a_list_of_at_most_50_records() -> None:
    with pytest.raises(DataValidationError):
        parse_elements_payload({"a": 1}, ALLOWED, NOW)
    with pytest.raises(DataValidationError):
        parse_elements_payload([elements_record()] * 51, ALLOWED, NOW)


@pytest.mark.parametrize(
    "change",
    [
        {"NORAD_CAT_ID": 99999},
        {"NORAD_CAT_ID": True},
        {"NORAD_CAT_ID": "25544"},
        {"OBJECT_NAME": "<script>alert(1)</script>"},
        {"OBJECT_NAME": "ISS\nFAKE LOG LINE"},
        {"OBJECT_NAME": "x" * 81},
        {"EPOCH": "2026-11-05T00:00:00"},
        {"EPOCH": "not a date"},
        {"INCLINATION": 181.0},
        {"MEAN_MOTION": 0.0},
        {"ECCENTRICITY": 1.0},
        {"RA_OF_ASC_NODE": 360.0},
        {"BSTAR": float("nan")},
    ],
)
def test_invalid_record_is_rejected(change: dict[str, object]) -> None:
    parsed = parse_elements_payload([elements_record(**change)], ALLOWED, NOW)
    assert parsed.accepted == ()


def test_record_missing_a_field_is_rejected() -> None:
    record = elements_record()
    del record["BSTAR"]
    assert parse_elements_payload([record], ALLOWED, NOW).accepted == ()


def test_epoch_up_to_one_day_in_the_future_is_accepted() -> None:
    near_future = (NOW + timedelta(hours=23)).replace(tzinfo=None).isoformat()
    assert len(parse_elements_payload([elements_record(EPOCH=near_future)], ALLOWED, NOW).accepted) == 1


def test_good_records_are_kept_when_another_record_is_bad() -> None:
    good = elements_record()
    bad = elements_record(NORAD_CAT_ID=20580, OBJECT_NAME="<b>")
    parsed = parse_elements_payload([good, bad], ALLOWED, NOW)
    assert [item.norad for item in parsed.accepted] == [25544]
    assert parsed.rejected_norad == (20580,)


def test_catalog_record_is_accepted() -> None:
    parsed = parse_catalog_payload([catalog_record()], ALLOWED, NOW)
    assert parsed.accepted[0].owner_code == "ISS"


@pytest.mark.parametrize(
    "change",
    [{"OWNER": "us"}, {"LAUNCH_DATE": "2026-13-01"}, {"NORAD_CAT_ID": 1}],
)
def test_invalid_catalog_record_is_rejected(change: dict[str, object]) -> None:
    parsed = parse_catalog_payload([catalog_record(**change)], ALLOWED, NOW)
    assert parsed.accepted == ()


def test_mean_motion_change_of_1_percent_is_plausible() -> None:
    assert mean_motion_change_is_plausible(element_from(), element_from(MEAN_MOTION=15.655))


def test_mean_motion_change_of_6_percent_is_not_plausible() -> None:
    assert not mean_motion_change_is_plausible(element_from(), element_from(MEAN_MOTION=16.43))


def test_first_download_has_no_previous_value_to_compare() -> None:
    assert mean_motion_change_is_plausible(None, element_from())


def test_orbital_elements_reject_angles_of_360_degrees() -> None:
    with pytest.raises(DataValidationError):
        OrbitalElements(
            norad=25544,
            name="ISS",
            inclination_deg=51.6,
            mean_motion_rev_day=15.5,
            eccentricity=0.0007,
            epoch=NOW,
            raan_deg=360.0,
            arg_perigee_deg=130.0,
            mean_anomaly_deg=325.0,
            mean_motion_dot=0.0,
            mean_motion_ddot=0.0,
            bstar=0.0,
        )
```

## Pasos

1. **Crear la rama:** `git switch -c feature/007-validacion-datos-descargados`.
2. **Crear o reemplazar** `src\orbita\domain\errors.py` y `src\orbita\domain\elements.py` con el contenido de este
   documento. Son reemplazos completos: el código de la spec 003 queda sustituido por este.
3. **Editar `tests\domain\test_types.py`:** en la función `make_elements`, dentro del diccionario `values`, después de
   la línea `"epoch": EPOCH,` añadir estas seis líneas:
   ```python
           "raan_deg": 247.0,
           "arg_perigee_deg": 130.0,
           "mean_anomaly_deg": 325.0,
           "mean_motion_dot": 0.0001,
           "mean_motion_ddot": 0.0,
           "bstar": 0.0001,
   ```
4. **Crear** `src\orbita\domain\validation.py` y `tests\domain\test_validation.py`.
5. **Ejecutar los tests:** `uv run pytest -v`. Deben pasar los 75 tests de la spec 006 (con los de `test_types.py`
   ya ajustados) y los nuevos de `test_validation.py`.
6. **Comprobar calidad:** `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy src`,
   `uv run pre-commit run --all-files`.
7. **Commit y merge** como en la spec 006, con el mensaje `007: validacion de datos descargados`.

## Casos borde y manejo de errores

1. Un registro con un campo `NaN` no llega a la validación: `json.loads` lo rechaza con `parse_constant`.
2. Un nombre con `<` o `>` se rechaza aunque sea texto válido: la ficha lo mostraría como texto, pero el criterio de
   SEC-38 pide rechazar los nombres con marcas HTML.
3. Una época de hoy a las 12:00 con un desfase de un día exacto se acepta; más de un día en el futuro se rechaza.
4. El cambio del movimiento medio se calcula contra el valor guardado, no contra el de la descarga anterior fallida.
5. `OrbitalElements` rechaza ángulos de 360° o más: el rango es `[0, 360)`.

## Tests de aceptación

Los tests de `tests/domain/test_validation.py` cubren: lista JSON válida; `NaN`, `Infinity` y `-Infinity` rechazados;
más de 5 MB rechazado; anidamiento de 10 000 niveles rechazado; JSON inválido rechazado; payload que no es lista o
tiene más de 50 registros; cada campo inválido rechazado (incluido el NORAD fuera de la lista y `True` como NORAD);
nombres con `<script>`, con salto de línea o de 81 caracteres; época en el futuro de más de un día; campo que falta;
registro válido junto a uno malo (el válido se conserva y el NORAD malo se informa); catálogo válido e inválido;
variación del movimiento medio del 1 % (aceptada) y del 6 % (rechazada); primera descarga sin valor anterior.

## Fuera de alcance

- Leer el cuerpo de la respuesta en trozos y cortar a 5 MB: spec 011, adaptador.
- Decidir qué se guarda, mezclar satélites o escribir el archivo: spec 014 y spec 012.
- El registro del aviso de satélite rechazado en el log: spec 014 (solo NORAD, SEC-30).

## Definition of Done

Todos los comandos en PowerShell, desde la carpeta `orbita`.

- [ ] `uv run pytest -v` → todos los tests pasan y el último mensaje es `passed`, sin `failed` ni `error`.
- [ ] `uv run ruff check .` → `All checks passed!`
- [ ] `uv run ruff format --check .; echo $LASTEXITCODE` → `0`.
- [ ] `uv run mypy src` → `Success: no issues found`.
- [ ] `Select-String -Path src\orbita\domain\*.py -Pattern 'import (streamlit|httpx|pydeck|skyfield|requests)'` → sin salida.
- [ ] `Select-String -Path src\orbita\domain\validation.py -Pattern 'json.loads'` → una línea con `parse_constant=`.
- [ ] `uv run pre-commit run --all-files` → todos los hooks en `Passed`.
- [ ] `git status` → `nothing to commit, working tree clean` después del merge.
