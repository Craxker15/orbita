# 000 - Setup de Python y herramientas de calidad

## Objetivo

La carpeta `orbita` solo tiene documentos. Al terminar: es un repositorio git con la rama `main`, existe el paquete
instalable `orbita` (estructura `src/`), con Python 3.12 gestionado por `uv`, todas las dependencias fijadas con `==`
y resueltas en `uv.lock`, y ruff, mypy estricto, pytest con cobertura y pip-audit configurados con los límites de
`ARCHITECTURE.md` §6.

## Depende de

Ninguna.

## Archivos rectores aplicables

- `ARCHITECTURE.md` §5 (estructura), §6 (Tamaño: `PLR0915` = 20, `PLR0913` = 6, `C901` = 8, `PLR0912` = 8; Tipos:
  `mypy --strict`, `from __future__ import annotations`; Docstrings estilo Google; sin `print`).
- `security-rules.md` SEC-08 (`.gitignore`), SEC-12 (`eval`, `exec`, `shell=True`), SEC-19 (`==` y `uv.lock`),
  SEC-20 (pip-audit), SEC-34 (reglas `S` de ruff), SEC-39 (solo las dependencias de `DESIGN.md` §6).
- ADR-002 (pydeck), ADR-003 (httpx), ADR-004 (`streamlit-geolocation`).

## Archivos a crear

1. `pyproject.toml`
2. `uv.lock` (lo genera `uv lock`; no se edita a mano)
3. `.gitignore`
4. `.gitattributes`
5. `src/orbita/__init__.py`

## Requisitos previos

En la terminal de VS Code (PowerShell), cada comando debe mostrar una versión:

```powershell
git --version
uv --version
```

- Sin git: instalar Git for Windows desde https://git-scm.com y reabrir VS Code.
- Sin uv: `powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"` y reabrir VS Code.

La carpeta `orbita` está abierta en VS Code (**File → Open Folder**) y contiene los documentos así:

```
orbita/
├── ARCHITECTURE.md  DESIGN.md  security-rules.md
├── docs/  (00-requirements.md, 00-requirements.es.md, ARCHITECTURE.es.md, DESIGN.es.md,
│           security-rules.es.md, adr/ con los 6 ADR y README.es.md)
└── specs/ (README.md, 000-setup-python-calidad.md)
```

## Dependencias externas

Ejecución (`[project] dependencies`), las de `DESIGN.md` §6: `streamlit`, `pydeck`, `skyfield`, `httpx`,
`python-dotenv`, `streamlit-geolocation`.

Desarrollo (`[dependency-groups] dev`): `pytest`, `pytest-cov`, `ruff`, `mypy`, `pre-commit`, `pip-audit`.

Las versiones exactas no se pudieron verificar desde el entorno de diseño (sin acceso a PyPI), así que se fijan en
el paso 6 con las que resuelve `uv` y se anotan en esta tabla al implementar:

| Paquete | Versión fijada |
|---|---|
| `uv_build` (igual a la versión de `uv`) | 0.12.13 |
| `streamlit` | 1.66.1 |
| `pydeck` | 0.9.3 |
| `skyfield` | 1.55 |
| `httpx` | 0.28.1 |
| `python-dotenv` | 1.2.4 |
| `streamlit-geolocation` | 0.0.10 |
| `pytest` | 9.2.0 |
| `pytest-cov` | 7.1.0 |
| `ruff` | 0.17.3 |
| `mypy` | 2.4.1 |
| `pre-commit` | 4.7.0 |
| `pip-audit` | 2.10.1 |

## Contenido exacto de los archivos

### `.gitignore` (una ruta por línea, en este orden)

```
.env
.venv/
__pycache__/
.pytest_cache/
.mypy_cache/
.ruff_cache/
.coverage
data/
*.log
.streamlit/secrets.toml
```

### `.gitattributes`

```
* text=auto eol=lf
```

Motivo: Windows usa saltos de línea CRLF y Linux LF; sin esta línea, git mostraría archivos "cambiados" sin
cambios reales.

### `src/orbita/__init__.py`

```python
"""Orbita: real-time map of 20 satellites."""

from __future__ import annotations
```

El archivo debe terminar con un salto de línea después de la última línea. Si `ruff` marca `W292`, ejecutar
`uv run ruff format src\orbita\__init__.py`.

### `pyproject.toml`

Versión temporal del paso 5 (sin versiones). En el paso 6 cada `<...>` se reemplaza por `==<versión>`:

```toml
[build-system]
requires = ["uv_build<...>"]
build-backend = "uv_build"

[project]
name = "orbita"
version = "0.1.0"
description = "Real-time map of 20 satellites with approximate distances to the user"
requires-python = "==3.12.*"
dependencies = [
    "streamlit<...>",
    "pydeck<...>",
    "skyfield<...>",
    "httpx<...>",
    "python-dotenv<...>",
    "streamlit-geolocation<...>",
]

[dependency-groups]
dev = [
    "pytest<...>",
    "pytest-cov<...>",
    "ruff<...>",
    "mypy<...>",
    "pre-commit<...>",
    "pip-audit<...>",
]

[tool.ruff]
target-version = "py312"
line-length = 100
src = ["src", "tests"]

[tool.ruff.lint]
select = ["E", "W", "F", "I", "UP", "B", "C90", "D", "PLR", "S", "T20", "BLE"]

[tool.ruff.lint.per-file-ignores]
"tests/**" = ["S101", "PLR2004", "D"]

[tool.ruff.lint.pydocstyle]
convention = "google"

[tool.ruff.lint.mccabe]
max-complexity = 8

[tool.ruff.lint.pylint]
max-statements = 20
max-args = 6
max-positional-args = 6
max-branches = 8

[tool.ruff.lint.isort]
required-imports = ["from __future__ import annotations"]

[tool.mypy]
python_version = "3.12"
strict = true
mypy_path = "src"

[tool.pytest.ini_options]
testpaths = ["tests"]
```

Qué hace cada bloque de `[tool.ruff.lint]`:

| Regla | Para qué |
|---|---|
| `E`, `W`, `F` | Errores de estilo y de código (variables sin usar, imports rotos) |
| `I` | Imports ordenados |
| `UP` | Sintaxis moderna de Python |
| `B` | Errores comunes (bugbear) |
| `C90` | Complejidad ≤ 8 |
| `D` | Docstrings estilo Google |
| `PLR` | Límites de tamaño: ≤ 20 sentencias, ≤ 6 argumentos, ≤ 8 ramas |
| `S` | Análisis de seguridad (bandit, SEC-34) |
| `T20` | Prohíbe `print` |
| `BLE` | Prohíbe `except Exception` sin justificar |

## Pasos

1. **Iniciar git en `main`:**
   ```powershell
   git init -b main
   git config user.name "Juan José Acevedo"
   git config user.email "<el correo de tu cuenta de GitHub>"
   ```
2. **Primer commit con los documentos:**
   ```powershell
   git add .
   git commit -m "docs: design, requirements, architecture, security rules and ADRs"
   ```
3. **Rama de la spec:**
   ```powershell
   git switch -c feature/000-setup-python-calidad
   ```
4. **Crear** `.gitignore`, `.gitattributes` y `src/orbita/__init__.py` con el contenido exacto de arriba
   (en VS Code: clic derecho en el explorador → **New File**).
5. **Crear `pyproject.toml`** con la versión temporal: copiar el bloque de arriba y borrar todos los `<...>`
   (por ejemplo, `"streamlit<...>"` queda `"streamlit"`). En `requires` de `[build-system]` poner
   `"uv_build==<versión de uv --version>"`, por ejemplo `"uv_build==0.12.19"` si `uv --version` dice `uv 0.12.19`.
6. **Fijar las versiones:**
   ```powershell
   uv lock
   uv tree --depth 1
   ```
   `uv tree` lista cada dependencia directa con la versión resuelta. En `pyproject.toml`, escribir cada una como
   `"<paquete>==<versión>"` (por ejemplo `"streamlit==1.52.0"` si esa fuera la versión mostrada), anotar las 13
   versiones en la tabla de "Dependencias externas" de esta spec, y volver a ejecutar `uv lock`.
7. **Instalar:**
   ```powershell
   uv sync --locked
   ```
8. **Comprobar** todo el Definition of Done.
9. **Commit y merge:**
   ```powershell
   git add .
   git commit -m "000: setup de Python y herramientas de calidad"
   git switch main
   git merge --no-ff feature/000-setup-python-calidad -m "Merge spec 000: setup de Python y herramientas de calidad"
   git branch -d feature/000-setup-python-calidad
   ```

## Casos borde y manejo de errores

1. `uv lock` no resuelve: no cambiar ningún paquete ni quitar dependencias; detenerse y reportar la salida exacta.
2. `uv run pip-audit` reporta una vulnerabilidad: no cambiar versiones a mano; reportar paquete, versión e ID. Una
   excepción solo se acepta con un ADR (SEC-20).
3. pip-audit omite `orbita` por no estar en PyPI: es lo esperado. Cualquier otro paquete omitido se reporta.
4. `uv run ruff format --check .` señala archivos `.md`: no reformatear los documentos; reportarlo para corregir la
   configuración en una corrección de esta spec.
5. `uv run pytest` sin tests termina con código 5 ("no tests ran"): en esta spec es el resultado esperado.
6. git avisa "LF will be replaced by CRLF" o al revés: es el efecto de `.gitattributes`; no es un error.
7. PowerShell no reconoce `uv` justo después de instalarlo: cerrar y abrir VS Code.
8. `ruff` marca `W292` (falta salto de línea final) en `src/orbita/__init__.py`: ejecutar `uv run ruff format src\orbita\__init__.py`.

## Tests de aceptación

Esta spec no crea tests de pytest (no añade lógica). Las comprobaciones son los comandos del Definition of Done.

## Fuera de alcance

- `.pre-commit-config.yaml`, gitleaks, `.streamlit/config.toml` y `.vscode/` (spec 001).
- Subpaquetes de capas y `tests/test_architecture.py` (spec 002).
- `.env.example` y `orbita.settings` (spec 009).
- `assets/ne_110m_countries.geojson` (spec 015).

## Definition of Done

Todos los comandos en PowerShell, desde la carpeta `orbita`.

- [ ] `uv lock --check` → código de salida 0 (comprobar con `echo $LASTEXITCODE` → `0`).
- [ ] `uv sync --locked` → código de salida 0.
- [ ] `uv run python --version` → empieza por `Python 3.12`.
- [ ] `uv run python -c "import orbita; print(orbita.__doc__)"` → `Orbita: real-time map of 20 satellites.`
- [ ] `uv run python -c "import streamlit, pydeck, skyfield, httpx, dotenv, streamlit_geolocation; print('ok')"` → `ok`.
- [ ] `uv run ruff check .` → `All checks passed!`
- [ ] `uv run ruff format --check .` → código de salida 0.
- [ ] `uv run mypy src` → `Success: no issues found in 1 source file`.
- [ ] `uv run pytest; echo $LASTEXITCODE` → `5` (0 tests recogidos).
- [ ] `uv run pip-audit` → la salida contiene `No known vulnerabilities found`; el único paquete omitido es `orbita`.
- [ ] `Select-String -Path pyproject.toml -Pattern '>=|~=|<|\^'` → sin salida (todo fijado con `==`).
- [ ] `$req = '.env','.venv/','__pycache__/','.pytest_cache/','.mypy_cache/','.ruff_cache/','.coverage','data/','*.log','.streamlit/secrets.toml'; $req | Where-Object { $_ -notin (Get-Content .gitignore) }` → sin salida.
- [ ] `Get-ChildItem -Recurse src -Filter *.py | Select-String -Pattern 'noqa|type: ignore'` → sin salida.
- [ ] La tabla de versiones de esta spec está completa, con las 13 versiones.
- [ ] `git log --oneline --graph` → muestra el commit de documentos, el commit de la spec 000 y el merge.
- [ ] `git status` → `nothing to commit, working tree clean`.
