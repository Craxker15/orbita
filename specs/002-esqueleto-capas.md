# 002 - Esqueleto de capas y regla de dependencias

## Objetivo

Al terminar, existen los paquetes `orbita.domain`, `orbita.ports`, `orbita.app` y `orbita.adapters`, vacíos salvo su
documentación, y un test que lee con `ast` los `import` de cada módulo y falla si alguno viola la regla de dependencias
de `ARCHITECTURE.md` §2. El test ya conoce la regla de `orbita.ui` y la aplicará cuando ese paquete exista (spec 015).

## Depende de

- 000 (el paquete `orbita` y las herramientas de calidad).

## Archivos rectores aplicables

- `ARCHITECTURE.md` §2 (tabla de capas y reglas obligatorias 1 a 8), §5 (estructura), §6 (tamaños y tipos).
- `security-rules.md` SEC-34 (reglas `S` de ruff, aplicadas al test también).

## Archivos a crear

1. `src/orbita/domain/__init__.py`
2. `src/orbita/ports/__init__.py`
3. `src/orbita/app/__init__.py`
4. `src/orbita/adapters/__init__.py`
5. `tests/test_architecture.py`

Son cinco archivos, dentro del límite de la regla 3. Los cuatro `__init__.py` solo marcan los paquetes; la lógica vive
en el test. El paquete `orbita.ui` no se crea aquí: lo crea la spec 015, porque su primer contenido es la página.

## Dependencias externas

Ninguna nueva. Se usan `ast`, `sys` y `pathlib` de la biblioteca estándar.

## Contenido exacto de los archivos

### `src/orbita/domain/__init__.py`

```python
"""Domain layer: pure rules and types. Standard library only (ARCHITECTURE.md §2)."""

from __future__ import annotations
```

### `src/orbita/ports/__init__.py`

```python
"""Ports: protocols for the external dependencies (ARCHITECTURE.md §4)."""

from __future__ import annotations
```

### `src/orbita/app/__init__.py`

```python
"""Application layer: use cases that depend only on ports (ARCHITECTURE.md §3)."""

from __future__ import annotations
```

### `src/orbita/adapters/__init__.py`

```python
"""Adapters: concrete implementations of the ports."""

from __future__ import annotations
```

### `tests/test_architecture.py`

```python
"""Enforce the dependency rule of ARCHITECTURE.md §2 by reading the import statements with ast."""

from __future__ import annotations

import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
PACKAGE = "orbita"
THIRD_PARTY = "<third-party>"

# Allowed imports per layer. Standard library is always allowed. Entry modules (orbita.main and
# orbita.settings) are not listed: no layer in this table may import them.
ALLOWED: dict[str, frozenset[str]] = {
    "domain": frozenset({"orbita.domain"}),
    "ports": frozenset({"orbita.domain", "orbita.ports"}),
    "app": frozenset({"orbita.domain", "orbita.ports", "orbita.app"}),
    "adapters": frozenset({"orbita.domain", "orbita.ports", "orbita.adapters", THIRD_PARTY}),
    "ui": frozenset({"orbita.domain", "orbita.app", "orbita.ui", THIRD_PARTY}),
}


def module_names(path: Path) -> tuple[str, str]:
    """Return the module name of a file and the package used to resolve its relative imports."""
    parts = list(path.relative_to(SRC).with_suffix("").parts)
    if parts[-1] == "__init__":
        parts.pop()
        return ".".join(parts), ".".join(parts)
    return ".".join(parts), ".".join(parts[:-1])


def resolve(node: ast.ImportFrom, package: str) -> str:
    """Return the absolute name of a `from ... import` statement."""
    if node.level == 0:
        return node.module or ""
    parts = package.split(".")
    base = ".".join(parts[: len(parts) - node.level + 1])
    return f"{base}.{node.module}" if node.module else base


def imported_names(source: str, package: str) -> list[str]:
    """Return every module name imported by the source code."""
    names: list[str] = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            names.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            names.append(resolve(node, package))
    return names


def is_allowed(name: str, allowed: frozenset[str]) -> bool:
    """Tell whether one imported name is permitted for a layer."""
    top = name.split(".")[0]
    if top in sys.stdlib_module_names:
        return True
    if top == PACKAGE:
        return any(name == prefix or name.startswith(prefix + ".") for prefix in allowed)
    return THIRD_PARTY in allowed


def violations(path: Path, source: str) -> list[str]:
    """Return the imports in a file that its layer does not allow."""
    module, package = module_names(path)
    layer = module.split(".")[1] if "." in module else ""
    if layer not in ALLOWED:
        return []
    return [
        name for name in imported_names(source, package) if not is_allowed(name, ALLOWED[layer])
    ]


def test_real_source_respects_layer_rules() -> None:
    found: dict[str, list[str]] = {}
    for path in (SRC / PACKAGE).rglob("*.py"):
        bad = violations(path, path.read_text(encoding="utf-8"))
        if bad:
            found[str(path.relative_to(ROOT))] = bad
    assert found == {}


def test_detects_third_party_import_in_domain() -> None:
    assert violations(SRC / PACKAGE / "domain" / "rules.py", "import streamlit\n") == ["streamlit"]


def test_detects_adapter_import_in_app() -> None:
    source = "from orbita.adapters.celestrak import CelestrakSource\n"
    assert violations(SRC / PACKAGE / "app" / "use_case.py", source) == [
        "orbita.adapters.celestrak"
    ]


def test_detects_relative_import_of_adapters_in_app() -> None:
    assert violations(SRC / PACKAGE / "app" / "use_case.py", "from ..adapters import x\n") == [
        "orbita.adapters"
    ]


def test_allows_domain_import_in_ports() -> None:
    source = "import dataclasses\nfrom orbita.domain.types import Thing\n"
    assert violations(SRC / PACKAGE / "ports" / "source.py", source) == []


def test_allows_third_party_import_in_adapters() -> None:
    assert violations(SRC / PACKAGE / "adapters" / "http.py", "import httpx\n") == []


def test_entry_modules_are_not_checked() -> None:
    assert violations(SRC / PACKAGE / "main.py", "import streamlit\n") == []
```

Qué hace el test, paso a paso:

- `module_names` convierte la ruta de un archivo en nombre de módulo (`orbita.app.use_case`).
- `resolve` convierte los `from ..x import y` en nombres absolutos, para que la regla se aplique igual.
- `is_allowed` acepta la biblioteca estándar siempre, y las dependencias de terceros solo en las capas que lo permiten.
- `violations` compara los imports de un archivo con la tabla `ALLOWED` de su capa.
- Los cuatro primeros tests de la regla comprueban que el código real cumple, y los demás comprueban que el test sí
  detecta violaciones y no bloquea lo permitido.

## Pasos

1. **Crear la rama de la spec:**
   ```powershell
   git switch -c feature/002-esqueleto-capas
   ```
2. **Crear** los cuatro `__init__.py` con el contenido de arriba. En VS Code, clic derecho en la raíz de `orbita` →
   **New File** y escribe la ruta completa (`src/orbita/domain/__init__.py`, etc.). VS Code crea las carpetas.
3. **Crear** `tests/test_architecture.py` con el contenido de arriba (clic derecho en la raíz → **New File** →
   `tests/test_architecture.py`).
4. **Ejecutar el test:**
   ```powershell
   uv run pytest -v
   ```
   Deben pasar los 7 tests y el código de salida debe ser `0`.
5. **Probar que el test sí detecta una violación.** Abre `src\orbita\domain\__init__.py`, agrega al final la línea
   `import streamlit`, guarda y ejecuta:
   ```powershell
   uv run pytest tests/test_architecture.py::test_real_source_respects_layer_rules
   ```
   Debe fallar mostrando `domain/__init__.py` y `streamlit`. Después borra esa línea, guarda y vuelve a ejecutar el
   comando: debe pasar.
6. **Revisar calidad:**
   ```powershell
   uv run ruff check .
   uv run ruff format --check .
   uv run mypy src
   uv run pre-commit run --all-files
   ```
7. **Commit y merge:**
   ```powershell
   git add .
   git commit -m "002: esqueleto de capas y test de la regla de dependencias"
   git switch main
   git merge --no-ff feature/002-esqueleto-capas -m "Merge spec 002: esqueleto de capas y test de la regla de dependencias"
   git branch -d feature/002-esqueleto-capas
   ```
8. **Marcar la spec como implementada** en `specs\README.md` (fila 002 → `Implementada 2026-10-30`), con commit de
   documentación en `main`.

## Casos borde y manejo de errores

1. `uv run pytest` dice `collected 0 items` o código `5`: la carpeta `tests` o el archivo no están en la raíz; revisar
   la ruta.
2. El test de código real falla en un archivo que no creaste tú: pegar el mensaje completo; no cambiar la tabla
   `ALLOWED` para que pase sin revisar la regla.
3. `sys.stdlib_module_names` no existe: la versión de Python no es 3.12; revisar `uv run python --version`.
4. `ruff` marca `D` o `PLR` en el test: las reglas `D` no aplican a `tests/**`; si aparece otra, reportarla.
5. `ruff` marca `W292` en algún `__init__.py`: ejecutar `uv run ruff format <archivo>`, como en la spec 000.

## Tests de aceptación

Son los siete tests de `tests/test_architecture.py`, más la prueba manual del paso 5.

## Fuera de alcance

- `orbita.ui` (spec 015): la regla de la UI ya está en `ALLOWED` y empieza a verificarse cuando el paquete exista.
- `orbita.main` y `orbita.settings` (specs 009 y 017).
- Los puertos y adaptadores concretos (specs 008 a 013).

## Definition of Done

Todos los comandos en PowerShell, desde la carpeta `orbita`.

- [ ] `uv run pytest -v` → 7 tests `PASSED` y `echo $LASTEXITCODE` → `0`.
- [ ] La prueba del paso 5 falla con `import streamlit` en `domain` y pasa al quitarlo.
- [ ] `Get-ChildItem -Recurse -Name src\orbita` → muestra `__init__.py` en `domain`, `ports`, `app` y `adapters`, más
  el `__init__.py` de `orbita`.
- [ ] `uv run ruff check .` → `All checks passed!`
- [ ] `uv run ruff format --check .; echo $LASTEXITCODE` → `0`.
- [ ] `uv run mypy src` → `Success: no issues found` (el número de archivos puede variar).
- [ ] `uv run pre-commit run --all-files` → todos los hooks en `Passed`.
- [ ] `git log --oneline --graph` → muestra el commit de la spec 002 y el merge.
- [ ] `git status` → `nothing to commit, working tree clean`.