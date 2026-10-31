# 012 - Adaptador `JsonFileStore`

## Objetivo

Al terminar, los datos válidos se guardan en tres archivos con nombre fijo dentro de `data/`: los elementos orbitales,
el catálogo y los instantes de los últimos intentos de descarga. Cada escritura reemplaza el archivo de forma atómica,
para que un lector nunca vea un archivo a medias. Las lecturas se guardan en memoria mientras el archivo no cambie, para
que la vista en vivo (que se refresca cada segundo) no lea el disco en cada refresco.

## Depende de

- 007 (`OrbitalDataset`, `Catalog` y sus validaciones).
- 008 (el puerto `SatelliteDataStore` y el tipo `DownloadAttempts`).

## Archivos rectores aplicables

- `security-rules.md` SEC-11 (las rutas se construyen con nombres fijos del código, nunca con contenido descargado),
  SEC-02 (nada de la ubicación del usuario se escribe en disco), SEC-08 (`data/` no se versiona).
- `ARCHITECTURE.md` §6 (escritura en archivo temporal y renombrado con `Path.replace`; `Lock` para el estado compartido).
- `DESIGN.md` §7.1 (el archivo descargado se valida antes de reemplazar al anterior).

## Archivos a crear

1. `src/orbita/adapters/json_file_store.py`
2. `tests/adapters/test_json_file_store.py`

Son dos archivos en la capa `adapters` y su test.

## Dependencias externas

Ninguna. Solo `json`, `threading` y `pathlib` de la biblioteca estándar.

## Contenido exacto de los archivos

### `src/orbita/adapters/json_file_store.py`

```python
"""JSON file store: saves the valid data under data/ with fixed file names (SEC-11, ARCHITECTURE.md §6)."""

from __future__ import annotations

import json
import logging
import threading
from collections.abc import Mapping
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Final

from orbita.domain.catalog import Catalog, CatalogEntry
from orbita.domain.elements import OrbitalDataset, OrbitalElements
from orbita.domain.errors import DataValidationError
from orbita.domain.state import DownloadAttempts

logger = logging.getLogger(__name__)

ELEMENTS_FILE: Final = "orbital_elements.json"
CATALOG_FILE: Final = "satcat.json"
ATTEMPTS_FILE: Final = "download_attempts.json"

Signature = tuple[int, int]


class JsonFileStore:
    """Stores the last valid data in three fixed files under the data folder.

    Preconditions: data_dir is the folder of ORBITA_DATA_DIR; it is created on the first save.
    Postconditions: every write replaces its file atomically; a reader sees the old or the new file, never half of one.
    """

    def __init__(self, data_dir: Path) -> None:
        """Remember the folder and create the lock and the read caches."""
        self._data_dir = data_dir
        self._lock = threading.Lock()
        self._elements_cache: tuple[Signature, OrbitalDataset] | None = None
        self._catalog_cache: tuple[Signature, Catalog] | None = None

    def load_elements(self) -> OrbitalDataset | None:
        """Return the saved elements, reading the file again only when it changed (SatelliteDataStore)."""
        with self._lock:
            path = self._data_dir / ELEMENTS_FILE
            signature = _signature(path)
            if signature is None:
                return None
            if self._elements_cache is not None and self._elements_cache[0] == signature:
                return self._elements_cache[1]
            dataset = _dataset_from_json(_read_object(path))
            self._elements_cache = (signature, dataset)
            return dataset

    def save_elements(self, dataset: OrbitalDataset) -> None:
        """Replace the saved elements atomically (SatelliteDataStore)."""
        with self._lock:
            _write_atomic(self._data_dir / ELEMENTS_FILE, _dataset_to_json(dataset))
            self._elements_cache = None

    def load_catalog(self) -> Catalog | None:
        """Return the saved catalog, reading the file again only when it changed (SatelliteDataStore)."""
        with self._lock:
            path = self._data_dir / CATALOG_FILE
            signature = _signature(path)
            if signature is None:
                return None
            if self._catalog_cache is not None and self._catalog_cache[0] == signature:
                return self._catalog_cache[1]
            catalog = _catalog_from_json(_read_object(path))
            self._catalog_cache = (signature, catalog)
            return catalog

    def save_catalog(self, catalog: Catalog) -> None:
        """Replace the saved catalog atomically (SatelliteDataStore)."""
        with self._lock:
            _write_atomic(self._data_dir / CATALOG_FILE, _catalog_to_json(catalog))
            self._catalog_cache = None

    def load_attempts(self) -> DownloadAttempts:
        """Return the times of the last attempts; an empty value when the file does not exist."""
        with self._lock:
            path = self._data_dir / ATTEMPTS_FILE
            if _signature(path) is None:
                return DownloadAttempts()
            content = _read_object(path)
            return DownloadAttempts(
                elements=_optional_time(content.get("elements")),
                catalog=_optional_time(content.get("catalog")),
            )

    def save_attempts(self, attempts: DownloadAttempts) -> None:
        """Replace the times of the last attempts atomically (SatelliteDataStore)."""
        with self._lock:
            _write_atomic(
                self._data_dir / ATTEMPTS_FILE,
                {"elements": _iso(attempts.elements), "catalog": _iso(attempts.catalog)},
            )


def _signature(path: Path) -> Signature | None:
    """Return the modification time and size of a file, or None when it does not exist."""
    try:
        status = path.stat()
    except FileNotFoundError:
        return None
    return (status.st_mtime_ns, status.st_size)


def _read_object(path: Path) -> Mapping[str, object]:
    """Read a JSON object from a file, or raise DataValidationError (SEC-09)."""
    try:
        content = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise DataValidationError(f"{path.name} cannot be read") from error
    if not isinstance(content, dict):
        raise DataValidationError(f"{path.name} must contain a JSON object")
    return content


def _write_atomic(path: Path, payload: Mapping[str, object]) -> None:
    """Write the JSON to a temporary file and rename it over the target (ARCHITECTURE.md §6)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    text = json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False)
    temporary.write_text(text, encoding="utf-8")
    temporary.replace(path)
    logger.info("store_write file=%s", path.name)


def _dataset_to_json(dataset: OrbitalDataset) -> dict[str, object]:
    """Convert the dataset to JSON-friendly values."""
    return {
        "downloaded_at": dataset.downloaded_at.isoformat(),
        "elements": [_element_to_json(item) for item in dataset.elements],
    }


def _element_to_json(element: OrbitalElements) -> dict[str, object]:
    """Convert one set of orbital elements to JSON-friendly values."""
    return {
        "norad": element.norad,
        "name": element.name,
        "inclination_deg": element.inclination_deg,
        "mean_motion_rev_day": element.mean_motion_rev_day,
        "eccentricity": element.eccentricity,
        "epoch": element.epoch.isoformat(),
        "raan_deg": element.raan_deg,
        "arg_perigee_deg": element.arg_perigee_deg,
        "mean_anomaly_deg": element.mean_anomaly_deg,
        "mean_motion_dot": element.mean_motion_dot,
        "mean_motion_ddot": element.mean_motion_ddot,
        "bstar": element.bstar,
    }


def _dataset_from_json(content: Mapping[str, object]) -> OrbitalDataset:
    """Rebuild the dataset; every value goes through the domain constructors again."""
    raw = content.get("elements")
    if not isinstance(raw, list):
        raise DataValidationError("elements must be a list")
    return OrbitalDataset(
        downloaded_at=_time(content.get("downloaded_at")),
        elements=tuple(_element_from_json(item) for item in raw),
    )


def _element_from_json(item: object) -> OrbitalElements:
    """Rebuild one OrbitalElements, validated by its own constructor."""
    if not isinstance(item, dict):
        raise DataValidationError("an element is not a JSON object")
    return OrbitalElements(
        norad=_integer(item, "norad"),
        name=_text(item, "name"),
        inclination_deg=_number(item, "inclination_deg"),
        mean_motion_rev_day=_number(item, "mean_motion_rev_day"),
        eccentricity=_number(item, "eccentricity"),
        epoch=_time(item.get("epoch")),
        raan_deg=_number(item, "raan_deg"),
        arg_perigee_deg=_number(item, "arg_perigee_deg"),
        mean_anomaly_deg=_number(item, "mean_anomaly_deg"),
        mean_motion_dot=_number(item, "mean_motion_dot"),
        mean_motion_ddot=_number(item, "mean_motion_ddot"),
        bstar=_number(item, "bstar"),
    )


def _catalog_to_json(catalog: Catalog) -> dict[str, object]:
    """Convert the catalog to JSON-friendly values."""
    return {
        "downloaded_at": catalog.downloaded_at.isoformat(),
        "entries": [
            {
                "norad": entry.norad,
                "owner_code": entry.owner_code,
                "launch_date": entry.launch_date.isoformat(),
            }
            for entry in catalog.entries
        ],
    }


def _catalog_from_json(content: Mapping[str, object]) -> Catalog:
    """Rebuild the catalog; every entry goes through CatalogEntry again."""
    raw = content.get("entries")
    if not isinstance(raw, list):
        raise DataValidationError("entries must be a list")
    entries = tuple(
        CatalogEntry(
            norad=_integer(item, "norad"),
            owner_code=_text(item, "owner_code"),
            launch_date=_date(item, "launch_date"),
        )
        for item in raw
        if isinstance(item, dict)
    )
    return Catalog(downloaded_at=_time(content.get("downloaded_at")), entries=entries)


def _integer(item: Mapping[str, object], key: str) -> int:
    """Return an integer field; booleans are rejected."""
    value = item.get(key)
    if isinstance(value, bool) or not isinstance(value, int):
        raise DataValidationError(f"{key} must be an integer")
    return value


def _number(item: Mapping[str, object], key: str) -> float:
    """Return a numeric field as float."""
    value = item.get(key)
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise DataValidationError(f"{key} must be a number")
    return float(value)


def _text(item: Mapping[str, object], key: str) -> str:
    """Return a text field."""
    value = item.get(key)
    if not isinstance(value, str):
        raise DataValidationError(f"{key} must be text")
    return value


def _date(item: Mapping[str, object], key: str) -> date:
    """Return a calendar date field in ISO format."""
    try:
        return date.fromisoformat(_text(item, key))
    except ValueError as error:
        raise DataValidationError(f"{key} is not a valid date") from error


def _time(value: object) -> datetime:
    """Return a timezone-aware time converted to UTC; a naive time is rejected."""
    if not isinstance(value, str):
        raise DataValidationError("a time must be text")
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as error:
        raise DataValidationError("a time is not valid ISO 8601") from error
    if parsed.tzinfo is None:
        raise DataValidationError("a stored time must include its UTC offset")
    return parsed.astimezone(UTC)


def _optional_time(value: object) -> datetime | None:
    """Return a stored time, or None when the attempt never happened."""
    return None if value is None else _time(value)


def _iso(value: datetime | None) -> str | None:
    """Return the ISO text of a time, or None."""
    return None if value is None else value.isoformat()
```

### `tests/adapters/test_json_file_store.py`

```python
"""Tests of the JSON file store with real files in a temporary folder (spec 012)."""

from __future__ import annotations

from datetime import UTC, date, datetime
from pathlib import Path

import pytest

from orbita.adapters.json_file_store import (
    ATTEMPTS_FILE,
    CATALOG_FILE,
    ELEMENTS_FILE,
    JsonFileStore,
)
from orbita.domain.catalog import Catalog, CatalogEntry
from orbita.domain.elements import OrbitalDataset, OrbitalElements
from orbita.domain.errors import DataValidationError
from orbita.domain.state import DownloadAttempts

NOW = datetime(2026, 10, 30, 12, tzinfo=UTC)


def element(norad: int = 25544) -> OrbitalElements:
    return OrbitalElements(
        norad=norad,
        name="ISS (ZARYA)",
        inclination_deg=51.6,
        mean_motion_rev_day=15.5,
        eccentricity=0.0007,
        epoch=NOW,
        raan_deg=247.0,
        arg_perigee_deg=130.0,
        mean_anomaly_deg=325.0,
        mean_motion_dot=0.0001,
        mean_motion_ddot=0.0,
        bstar=0.0001,
    )


def test_missing_files_give_no_data(tmp_path: Path) -> None:
    store = JsonFileStore(tmp_path)
    assert store.load_elements() is None
    assert store.load_catalog() is None
    assert store.load_attempts() == DownloadAttempts()


def test_elements_round_trip(tmp_path: Path) -> None:
    dataset = OrbitalDataset(downloaded_at=NOW, elements=(element(25544), element(20580)))
    JsonFileStore(tmp_path).save_elements(dataset)
    assert JsonFileStore(tmp_path).load_elements() == dataset


def test_catalog_round_trip(tmp_path: Path) -> None:
    catalog = Catalog(
        downloaded_at=NOW,
        entries=(CatalogEntry(norad=25544, owner_code="ISS", launch_date=date(1998, 11, 20)),),
    )
    JsonFileStore(tmp_path).save_catalog(catalog)
    assert JsonFileStore(tmp_path).load_catalog() == catalog


def test_attempts_round_trip_with_one_missing_value(tmp_path: Path) -> None:
    attempts = DownloadAttempts(elements=NOW, catalog=None)
    JsonFileStore(tmp_path).save_attempts(attempts)
    assert JsonFileStore(tmp_path).load_attempts() == attempts


def test_save_creates_the_missing_data_folder(tmp_path: Path) -> None:
    folder = tmp_path / "nested" / "data"
    JsonFileStore(folder).save_attempts(DownloadAttempts(elements=NOW))
    assert (folder / ATTEMPTS_FILE).is_file()


def test_no_temporary_file_is_left_behind(tmp_path: Path) -> None:
    JsonFileStore(tmp_path).save_elements(OrbitalDataset(downloaded_at=NOW, elements=()))
    assert not (tmp_path / (ELEMENTS_FILE + ".tmp")).exists()


def test_loaded_dataset_is_cached_until_the_file_changes(tmp_path: Path) -> None:
    store = JsonFileStore(tmp_path)
    store.save_elements(OrbitalDataset(downloaded_at=NOW, elements=()))
    first = store.load_elements()
    second = store.load_elements()
    assert first is second


def test_corrupt_file_raises_data_error(tmp_path: Path) -> None:
    (tmp_path / ELEMENTS_FILE).write_text("{bad", encoding="utf-8")
    with pytest.raises(DataValidationError):
        JsonFileStore(tmp_path).load_elements()


def test_stored_time_without_offset_is_rejected(tmp_path: Path) -> None:
    (tmp_path / ELEMENTS_FILE).write_text(
        '{"downloaded_at": "2026-10-30T12:00:00", "elements": []}', encoding="utf-8"
    )
    with pytest.raises(DataValidationError):
        JsonFileStore(tmp_path).load_elements()


def test_only_the_fixed_file_names_are_written(tmp_path: Path) -> None:
    store = JsonFileStore(tmp_path)
    store.save_elements(OrbitalDataset(downloaded_at=NOW, elements=()))
    store.save_catalog(Catalog(downloaded_at=NOW, entries=()))
    store.save_attempts(DownloadAttempts(elements=NOW))
    assert {path.name for path in tmp_path.iterdir()} == {
        ELEMENTS_FILE,
        CATALOG_FILE,
        ATTEMPTS_FILE,
    }
```

## Pasos

1. **Crear la rama:** `git switch -c feature/012-adaptador-json-file-store`.
2. **Crear los dos archivos** con el contenido de este documento.
3. **Ejecutar los tests:** `uv run pytest -v`.
4. **Comprobar calidad:** `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy src`,
   `uv run pre-commit run --all-files`.
5. **Comprobar que la ubicación no llega al almacén:** `Select-String -Path src\orbita\adapters\*.py -Pattern 'Observer'`
   debe mostrar solo líneas de comentario o nada.
6. **Commit y merge** con el mensaje `012: adaptador JsonFileStore`.

## Casos borde y manejo de errores

1. Un archivo `.tmp` que queda de una escritura interrumpida se sobrescribe en la siguiente escritura. No se lee nunca.
2. Un archivo corrupto lanza `DataValidationError`: el caso de uso (spec 014) decide, y no borra el archivo.
3. Dos escrituras casi a la vez: el `Lock` las serializa.
4. La caché se invalida al guardar, y también si la fecha de modificación o el tamaño del archivo cambian.

## Tests de aceptación

- Sin archivos no hay datos y los intentos están vacíos.
- Los elementos, el catálogo y los intentos sobreviven a guardar y leer.
- Se crea la carpeta de datos si no existe.
- No queda ningún archivo temporal.
- La segunda lectura devuelve el mismo objeto (caché).
- Un archivo corrupto o una hora sin zona horaria se rechazan con `DataValidationError`.
- Solo aparecen los tres nombres fijos de archivo.

## Fuera de alcance

- Qué se guarda y cuándo: spec 014.
- La validación de la descarga antes de guardar: spec 007 (funciones) y spec 014 (uso).

## Definition of Done

- [ ] `uv run pytest -v` → todos los tests pasan.
- [ ] `uv run ruff check .`, `uv run mypy src` y `uv run pre-commit run --all-files` sin errores.
- [ ] `Select-String -Path src\orbita\adapters\json_file_store.py -Pattern 'open\(|write_text'` → solo las escrituras de
  `_write_atomic`.
- [ ] `git status` → `nothing to commit, working tree clean` después del merge.
