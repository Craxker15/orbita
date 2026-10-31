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
    "domain": frozenset(),
    "ports": frozenset({"orbita.domain"}),
    "app": frozenset({"orbita.domain", "orbita.ports"}),
    "adapters": frozenset({"orbita.domain", "orbita.ports", THIRD_PARTY}),
    "ui": frozenset({"orbita.domain", "orbita.app", THIRD_PARTY}),
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
