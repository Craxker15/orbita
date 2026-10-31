"""Configuration: .env file, environment and Spanish texts (ARCHITECTURE.md §8)."""

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
        ConfigError: if line is not KEY=VALUE; error names line number, never value (SEC-09).
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
        ConfigError: if file cannot be read, is not JSON object, or lacks key (SEC-09).
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
