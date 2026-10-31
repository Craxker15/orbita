# Órbita

A web map that shows, in real time, where 20 satellites are, including the International Space Station, your location
(if you allow it), and the approximate distance to each one.

> **Academic prototype.** Positions and distances are approximate (typically a few kilometers of position error and tens
> of kilometers of distance error). Do not use them for space operations.

Spanish version: [README.es.md](README.es.md).

## What it does

- Shows the position of 20 satellites from several countries, updated every second (configurable, see below).
- Draws the ISS trajectory from 45 minutes before to 45 minutes after the current time.
- With the "My location" button (and your permission), shows your point and the distance to each satellite. Your location
  is used only while the page is open and is never stored.
- Works offline with the last saved data, and warns when the data is more than 3 days old.

## How it is calculated

Positions are computed on your computer with SGP4 (Skyfield library) from public orbital elements published by CelesTrak.
No satellite images are used. Details are in `DESIGN.md` and `ARCHITECTURE.md`.

## Installation and use (Windows, PowerShell)

Requirements: Python 3.12, managed with [uv](https://docs.astral.sh/uv/).

```powershell
uv sync --locked
uv run streamlit run src\orbita\main.py
```

Open `http://localhost:8501`. The `data\` folder is created automatically when the data is downloaded.

### Optional configuration

No configuration is required. To change a default, create a file named `.env` in the project root with any of these
lines (default value in parentheses):

- `ORBITA_DATA_DIR=data`: folder where downloaded data is saved.
- `ORBITA_REFRESH_S=1`: seconds between updates, from 1 to 10.
- `ORBITA_LOG_LEVEL=INFO`: log level: `DEBUG`, `INFO`, `WARNING` or `ERROR`.

## Quality and security

- Tests: `uv run pytest -v`. Quality checks: `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy src`.
- Pre-commit hooks (including a secret scanner): `uv run pre-commit run --all-files`.
- Security and privacy rules: `security-rules.md`. How to report a vulnerability: `SECURITY.md`.

## Documentation

- Design: `DESIGN.md` · Requirements: `docs/00-requirements.md` · Architecture: `ARCHITECTURE.md`
- Decisions: `docs/adr/` · Build specifications: `specs/`

Documents in Spanish (`*.es.md`) are study copies; the official version is in English.

## License

Not defined yet. Until a license is added, the code has no explicit permission for reuse.
