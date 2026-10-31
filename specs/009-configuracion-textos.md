# 009 - Configuración y textos

## Objetivo

Al terminar, el programa lee su configuración de `.env` y del entorno con valores validados (`ORBITA_DATA_DIR`,
`ORBITA_REFRESH_S`, `ORBITA_LOG_LEVEL`), y carga todos los textos al usuario desde `locales/es.json`, comprobando que
existen las claves necesarias (RNF-04, SEC-09). Ningún valor de configuración se muestra en los mensajes de error.

## Depende de

- 002 (el paquete `orbita` y la capa de entrada existen).

## Archivos rectores aplicables

- `ARCHITECTURE.md` §7.2 (todo texto al usuario sale de `locales/es.json`), §8 (variables y valores por defecto).
- `security-rules.md` SEC-08 (`.env` no se versiona), SEC-09 (`json.load` y validación con `ConfigError`), SEC-11 (las
  rutas no dependen del contenido descargado), SEC-21 (la configuración se lee solo en `orbita.settings`).
- `docs/00-requirements.es.md` RNF-04.

## Decisión: sin `python-dotenv`

`ARCHITECTURE.md` §8 menciona `python-dotenv`. Esta spec no lo añade: SEC-39 exige un ADR por cada dependencia de
ejecución, y para leer tres variables basta un lector de `KEY=VALUE` de unas líneas. `ARCHITECTURE.md` §8 se corrige
en la siguiente revisión del documento (queda anotado en `specs/README.md`).

## Depende de tests de la capa de entrada

`tests/test_settings.py` lee el archivo real `locales/es.json`. Es la única prueba que depende de un archivo del
repositorio; el resto usa `tmp_path`.

## Archivos a crear

1. `src/orbita/settings.py`
2. `tests/test_settings.py`
3. `locales/es.json`
4. `.env.example`

Son cuatro archivos, dentro del límite de la regla 3 del índice. Tres son código o configuración y uno es el test.

## Dependencias externas

Ninguna. Solo `json`, `pathlib` y `dataclasses` de la biblioteca estándar.

## Contenido exacto de los archivos

### `src/orbita/settings.py`

```python
"""Configuration of the program: the .env file, the environment and the Spanish texts (ARCHITECTURE.md §8)."""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from orbita.domain.errors import ConfigError

DEFAULT_DATA_DIR = "data"
DEFAULT_REFRESH_S = 1
DEFAULT_LOG_LEVEL = "INFO"
MIN_REFRESH_S = 1
MAX_REFRESH_S = 10
ALLOWED_LOG_LEVELS = frozenset({"DEBUG", "INFO", "WARNING", "ERROR"})
REQUIRED_TEXT_KEYS = (
    "title",
    "my_location",
    "location_privacy",
    "location_unavailable",
    "location_accuracy",
    "approximate_notice",
    "no_orbital_data",
    "unexpected_error",
    "stale_data",
    "too_old_data",
    "distance_approx",
    "missing_value",
    "missing_satellites",
    "label_altitude",
    "label_speed",
    "label_orbit_type",
    "label_period",
    "label_distance",
    "label_country",
    "label_launch_date",
    "label_years_in_orbit",
    "label_last_download",
    "orbit_geostationary",
    "orbit_polar",
    "orbit_low",
    "orbit_other",
)


@dataclass(frozen=True, slots=True)
class Settings:
    """Validated configuration, injected into the composition root (ARCHITECTURE.md §8)."""

    data_dir: Path
    refresh_s: int
    log_level: str


def read_env_file(path: Path) -> dict[str, str]:
    """Read KEY=VALUE lines from a file. Comments and blank lines are ignored.

    Preconditions: none; a missing file gives an empty mapping.
    Postconditions: keys and values are stripped of spaces and of one pair of quotes.
    Raises:
        ConfigError: if a line is not KEY=VALUE. The error names the line number, never the value (SEC-09).
    """
    if not path.is_file():
        return {}
    values: dict[str, str] = {}
    for number, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        key, separator, value = line.partition("=")
        if not separator or not key.strip():
            raise ConfigError(f"line {number} of the env file is not KEY=VALUE")
        values[key.strip()] = value.strip().strip("\"'")
    return values


def load_settings(environ: Mapping[str, str], env_file: Path, repo_root: Path) -> Settings:
    """Build the Settings. Values in environ override the values of the env file.

    Preconditions: repo_root is the project root.
    Postconditions: data_dir is inside repo_root; refresh_s is between 1 and 10.
    Raises:
        ConfigError: if a value is invalid; the message names the variable.
    """
    values = {**read_env_file(env_file), **environ}
    return Settings(
        data_dir=_data_dir(values.get("ORBITA_DATA_DIR", DEFAULT_DATA_DIR), repo_root),
        refresh_s=_refresh_seconds(values.get("ORBITA_REFRESH_S", str(DEFAULT_REFRESH_S))),
        log_level=_log_level(values.get("ORBITA_LOG_LEVEL", DEFAULT_LOG_LEVEL)),
    )


def load_texts(path: Path) -> dict[str, str]:
    """Read locales/es.json and check that every required key is present and is text (SEC-09).

    Preconditions: path points to a JSON file.
    Postconditions: every key of REQUIRED_TEXT_KEYS is in the result.
    Raises:
        ConfigError: if the file cannot be read, is not a JSON object, or lacks a key; the message names the
            file and the key.
    """
    try:
        with path.open(encoding="utf-8") as file:
            content = json.load(file)
    except (OSError, ValueError) as error:
        raise ConfigError(f"{path} cannot be read as JSON") from error
    if not isinstance(content, dict):
        raise ConfigError(f"{path} must contain a JSON object")
    for key in REQUIRED_TEXT_KEYS:
        if not isinstance(content.get(key), str):
            raise ConfigError(f"{path}: key {key} is missing or is not text")
    return {
        key: value
        for key, value in content.items()
        if isinstance(key, str) and isinstance(value, str)
    }


def _data_dir(value: str, repo_root: Path) -> Path:
    """Resolve ORBITA_DATA_DIR and reject any path outside the project (SEC-11)."""
    relative = Path(value)
    if relative.is_absolute() or ".." in relative.parts:
        raise ConfigError("ORBITA_DATA_DIR must be a relative path inside the project")
    resolved = (repo_root / relative).resolve()
    if not resolved.is_relative_to(repo_root.resolve()):
        raise ConfigError("ORBITA_DATA_DIR must be a relative path inside the project")
    return resolved


def _refresh_seconds(text: str) -> int:
    """Return ORBITA_REFRESH_S as an integer between MIN_REFRESH_S and MAX_REFRESH_S."""
    try:
        number = int(text)
    except ValueError as error:
        raise ConfigError("ORBITA_REFRESH_S must be an integer") from error
    if not MIN_REFRESH_S <= number <= MAX_REFRESH_S:
        raise ConfigError(f"ORBITA_REFRESH_S must be between {MIN_REFRESH_S} and {MAX_REFRESH_S}")
    return number


def _log_level(text: str) -> str:
    """Return ORBITA_LOG_LEVEL in upper case if it is one of the allowed levels."""
    level = text.upper()
    if level not in ALLOWED_LOG_LEVELS:
        raise ConfigError("ORBITA_LOG_LEVEL must be DEBUG, INFO, WARNING or ERROR")
    return level
```

### `tests/test_settings.py`

```python
"""Tests of the configuration and the Spanish texts (spec 009)."""

from __future__ import annotations

from pathlib import Path

import pytest

from orbita.domain.errors import ConfigError
from orbita.settings import load_settings, load_texts

REPO_ROOT = Path(__file__).resolve().parents[1]
ES_JSON = REPO_ROOT / "locales" / "es.json"


def test_defaults_are_used_when_nothing_is_set(tmp_path: Path) -> None:
    settings = load_settings({}, tmp_path / ".env", tmp_path)
    assert settings.data_dir == (tmp_path / "data").resolve()
    assert settings.refresh_s == 1
    assert settings.log_level == "INFO"


def test_environment_overrides_the_env_file(tmp_path: Path) -> None:
    (tmp_path / ".env").write_text("ORBITA_REFRESH_S=5\n", encoding="utf-8")
    settings = load_settings({"ORBITA_REFRESH_S": "3"}, tmp_path / ".env", tmp_path)
    assert settings.refresh_s == 3


def test_env_file_values_are_used_and_log_level_is_upper_cased(tmp_path: Path) -> None:
    (tmp_path / ".env").write_text("# comment\n\nORBITA_LOG_LEVEL=debug\n", encoding="utf-8")
    settings = load_settings({}, tmp_path / ".env", tmp_path)
    assert settings.log_level == "DEBUG"


@pytest.mark.parametrize("value", ["0", "11", "abc"])
def test_refresh_interval_must_be_an_integer_from_1_to_10(tmp_path: Path, value: str) -> None:
    with pytest.raises(ConfigError, match="ORBITA_REFRESH_S"):
        load_settings({"ORBITA_REFRESH_S": value}, tmp_path / ".env", tmp_path)


@pytest.mark.parametrize("value", ["/etc", "../outside"])
def test_data_dir_must_stay_inside_the_project(tmp_path: Path, value: str) -> None:
    with pytest.raises(ConfigError, match="ORBITA_DATA_DIR"):
        load_settings({"ORBITA_DATA_DIR": value}, tmp_path / ".env", tmp_path)


def test_invalid_log_level_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match="ORBITA_LOG_LEVEL"):
        load_settings({"ORBITA_LOG_LEVEL": "TRACE"}, tmp_path / ".env", tmp_path)


def test_malformed_env_line_error_does_not_show_the_value(tmp_path: Path) -> None:
    (tmp_path / ".env").write_text("SECRET_VALUE_WITHOUT_EQUALS\n", encoding="utf-8")
    with pytest.raises(ConfigError) as info:
        load_settings({}, tmp_path / ".env", tmp_path)
    assert "SECRET_VALUE" not in str(info.value)


def test_spanish_texts_file_has_every_required_key() -> None:
    texts = load_texts(ES_JSON)
    assert texts["approximate_notice"]
    assert texts["stale_data"].count("{days}") == 1


def test_texts_file_missing_a_key_is_rejected_by_name(tmp_path: Path) -> None:
    path = tmp_path / "es.json"
    path.write_text('{"title": "x"}', encoding="utf-8")
    with pytest.raises(ConfigError, match="approximate_notice"):
        load_texts(path)


def test_texts_file_that_is_not_an_object_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "es.json"
    path.write_text("[1, 2]", encoding="utf-8")
    with pytest.raises(ConfigError):
        load_texts(path)
```

### `locales/es.json`

```json
{
  "title": "Órbita: satélites en tiempo real",
  "my_location": "Mi ubicación",
  "location_privacy": "Tu ubicación solo se usa para dibujar el mapa y las distancias. Nunca se guarda.",
  "location_unavailable": "Permite tu ubicación para ver las distancias.",
  "location_accuracy": "Precisión de tu ubicación: ±{meters} m",
  "approximate_notice": "Las posiciones y las distancias son aproximadas. No las uses para operaciones espaciales.",
  "no_orbital_data": "No hay datos orbitales guardados y no hay conexión con CelesTrak.",
  "unexpected_error": "Ocurrió un error inesperado. Intenta recargar la página.",
  "stale_data": "Datos orbitales de hace {days} días: las posiciones pueden ser menos exactas.",
  "too_old_data": "Los datos orbitales tienen más de 14 días: no se muestran posiciones.",
  "distance_approx": "≈ {km} km",
  "missing_value": "—",
  "missing_satellites": "Sin datos de: {norad_numbers}",
  "select_satellite": "Toca un satélite en el mapa para ver su ficha.",
  "label_altitude": "Altura",
  "label_speed": "Velocidad",
  "label_orbit_type": "Tipo de órbita",
  "label_period": "Periodo",
  "label_distance": "Distancia a ti",
  "label_country": "País",
  "label_launch_date": "Fecha de lanzamiento",
  "label_years_in_orbit": "Años en órbita",
  "label_last_download": "Última descarga (hora de Colombia)",
  "orbit_geostationary": "Geoestacionaria",
  "orbit_polar": "Polar",
  "orbit_low": "Baja",
  "orbit_other": "Otra"
}
```

### `.env.example`

```env
# Copy this file to .env. The real .env is never committed (SEC-08).
ORBITA_DATA_DIR=data
ORBITA_REFRESH_S=1
ORBITA_LOG_LEVEL=INFO
```

## Pasos

1. **Crear la rama:** `git switch -c feature/009-configuracion-textos`.
2. **Crear los cuatro archivos** con el contenido de este documento (el `.json` y el `.env.example` se copian tal cual).
3. **Ejecutar los tests:** `uv run pytest -v`.
4. **Comprobar calidad:** `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy src`,
   `uv run pre-commit run --all-files`.
5. **Verificar que `.env` no se versiona:** `git check-ignore -v .env` debe mostrar la regla de `.gitignore`.
6. **Commit y merge** con el mensaje `009: configuracion y textos`.

## Casos borde y manejo de errores

1. Una ruta `ORBITA_DATA_DIR` absoluta o con `..` se rechaza. En Windows, `/etc` se resuelve fuera del proyecto y también
   se rechaza.
2. Si `.env` y el entorno dan valores distintos, gana el entorno (útil en la publicación, spec 021).
3. Un `.env` con una línea sin `=` falla al arrancar con el número de línea, sin mostrar su contenido.
4. `locales/es.json` sin una clave falla al arrancar y nombra la clave.

## Tests de aceptación

Los tests de `tests/test_settings.py`: valores por defecto; el entorno gana al archivo; el nivel de log se normaliza a
mayúsculas; el intervalo de refresco fuera de 1 a 10 o no entero se rechaza; `ORBITA_DATA_DIR` fuera del proyecto se
rechaza; nivel de log inválido se rechaza; una línea mal formada no muestra su valor; el `es.json` real tiene las
claves; un `es.json` sin clave o que no es un objeto se rechaza.

## Fuera de alcance

- Las claves de las fichas de país (`owner_<CÓDIGO>`) llegan en la spec 018.
- Las claves de la ubicación continua llegan en la spec 020.
- El idioma: se añadirá con otro `locales/<idioma>.json` (ARCHITECTURE.md §7.2), fuera de la v1.

## Definition of Done

Todos los comandos en PowerShell, desde la carpeta `orbita`.

- [ ] `uv run pytest -v` → todos los tests pasan.
- [ ] `Select-String -Path src\orbita\*.py -Pattern 'os.environ\[' ` → solo aparece en `settings.py` (o no aparece).
- [ ] `uv run ruff check .` → `All checks passed!`
- [ ] `uv run mypy src` → `Success: no issues found`.
- [ ] `uv run pre-commit run --all-files` → todos los hooks en `Passed`.
- [ ] `git check-ignore -v .env` → muestra la regla de `.gitignore`.
- [ ] `git status` → `nothing to commit, working tree clean` después del merge.
