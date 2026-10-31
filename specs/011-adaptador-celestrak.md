# 011 - Adaptador `CelestrakSource` y batería de entradas maliciosas

## Objetivo

Al terminar, el único módulo del proyecto que abre conexiones de red es `CelestrakSource`. Descarga la respuesta de
CelesTrak de un satélite cada vez, sin reintentos, con HTTPS, tiempo máximo de 10 s, sin seguir redirecciones y con un
límite de 5 MB contado sobre los bytes descomprimidos mientras se leen. Además, una batería de tests comprueba que ocho
entradas maliciosas (SEC-38) terminan en un error o en un satélite rechazado, y nunca en un archivo cambiado.

## Depende de

- 007 (`MAX_DOWNLOAD_BYTES`, `DownloadError`, `DataValidationError`, y el análisis de la respuesta).
- 008 (el puerto `SatelliteDataSource`).

## Archivos rectores aplicables

- `security-rules.md` SEC-10 (límite de 5 MB), SEC-15 (solo este módulo abre conexiones y importa `httpx`), SEC-16 (HTTPS,
  10 s, sin reintentos), SEC-26 (TLS verificado, sin redirecciones), SEC-27 (límite sobre bytes descomprimidos, leyendo en
  trozos), SEC-30 (en el log solo NORAD, tamaños y estados), SEC-38 (batería de entradas maliciosas).
- `ADR-003` (formato JSON, una petición por satélite, intervalo desde el último intento, cualquier respuesta distinta de
  200 detiene el intento).
- `DESIGN.md` §6 (`httpx` es el cliente HTTP).

## Dependencias externas

- `httpx` (cliente HTTP de la lista de tecnologías de `DESIGN.md` §6). Se añade con `uv add` y versión exacta: el paso 1
  dice cómo. Es una dependencia de ejecución nueva: la regla SEC-39 pide que esté en `DESIGN.md` §6, y ya lo está.

## Archivos a crear

1. `src/orbita/adapters/celestrak_source.py`
2. `tests/adapters/test_celestrak_source.py`
3. `tests/adapters/test_malicious_input.py`

Son tres archivos y están en la capa `adapters` y sus tests.

## Contenido exacto de los archivos

### `src/orbita/adapters/celestrak_source.py`

```python
"""CelesTrak adapter: the only module that opens network connections (SEC-15, ADR-003)."""

from __future__ import annotations

import logging
from typing import Final

import httpx

from orbita.domain.errors import DataValidationError, DownloadError
from orbita.domain.validation import MAX_DOWNLOAD_BYTES

logger = logging.getLogger(__name__)

CELESTRAK_BASE_URL: Final = "https://celestrak.org"
ELEMENTS_PATH: Final = "/NORAD/elements/gp.php"
CATALOG_PATH: Final = "/satcat/records.php"
REQUEST_TIMEOUT_S: Final = 10.0
OK_STATUS: Final = 200


class CelestrakSource:
    """Downloads one satellite at a time from CelesTrak, without retries (ADR-003, SEC-16).

    Preconditions: the client was created with TLS verification on (the default of httpx).
    Postconditions: every returned text is at most 5 MB and was decoded as UTF-8.
    """

    def __init__(self, client: httpx.Client) -> None:
        """Keep the HTTP client, which the composition root creates and injects."""
        self._client = client

    def download_elements(self, norad: int) -> str:
        """Return the raw JSON text of the orbital elements of one satellite (SatelliteDataSource)."""
        return self._get(ELEMENTS_PATH, norad, "elements")

    def download_catalog(self, norad: int) -> str:
        """Return the raw JSON text of the SATCAT record of one satellite (SatelliteDataSource)."""
        return self._get(CATALOG_PATH, norad, "catalog")

    def _get(self, path: str, norad: int, kind: str) -> str:
        """Request one satellite and return its body as text.

        Raises:
            DownloadError: on a non-200 response, a redirect, a timeout, a connection error or a body larger
                than 5 MB.
            DataValidationError: if the body is not UTF-8 text.
        """
        url = f"{CELESTRAK_BASE_URL}{path}"
        params = {"CATNR": str(norad), "FORMAT": "JSON"}
        try:
            with self._client.stream(
                "GET",
                url,
                params=params,
                timeout=REQUEST_TIMEOUT_S,
                follow_redirects=False,
            ) as response:
                if response.status_code != OK_STATUS:
                    raise DownloadError(
                        f"CelesTrak answered {response.status_code} for {kind} of NORAD {norad}"
                    )
                body = _read_limited(response)
        except httpx.HTTPError as error:
            raise DownloadError(
                f"{kind} download of NORAD {norad} failed: {type(error).__name__}"
            ) from error
        logger.info("download_ok kind=%s norad=%d bytes=%d", kind, norad, len(body))
        try:
            return body.decode("utf-8")
        except UnicodeDecodeError as error:
            raise DataValidationError("the downloaded body is not UTF-8 text") from error


def _read_limited(response: httpx.Response) -> bytes:
    """Read the decoded body in chunks, stopping as soon as it exceeds 5 MB (SEC-27)."""
    chunks: list[bytes] = []
    total = 0
    for chunk in response.iter_bytes():
        total += len(chunk)
        if total > MAX_DOWNLOAD_BYTES:
            raise DownloadError("the response is larger than 5 MB")
        chunks.append(chunk)
    return b"".join(chunks)
```

### `tests/adapters/test_celestrak_source.py`

```python
"""Tests of the CelesTrak adapter with simulated responses: no network (spec 011)."""

from __future__ import annotations

import gzip
from collections.abc import Callable

import httpx
import pytest

from orbita.adapters.celestrak_source import CelestrakSource
from orbita.domain.errors import DataValidationError, DownloadError
from orbita.domain.validation import MAX_DOWNLOAD_BYTES

Handler = Callable[[httpx.Request], httpx.Response]


def make_source(handler: Handler) -> tuple[CelestrakSource, list[httpx.Request]]:
    requests: list[httpx.Request] = []

    def recording(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return handler(request)

    client = httpx.Client(transport=httpx.MockTransport(recording))
    return CelestrakSource(client), requests


def test_elements_request_uses_https_catnr_and_json_format() -> None:
    source, requests = make_source(lambda request: httpx.Response(200, text="[]"))
    assert source.download_elements(25544) == "[]"
    url = requests[0].url
    assert url.scheme == "https"
    assert url.host == "celestrak.org"
    assert url.path == "/NORAD/elements/gp.php"
    assert url.params["CATNR"] == "25544"
    assert url.params["FORMAT"] == "JSON"


def test_catalog_request_uses_the_satcat_path() -> None:
    source, requests = make_source(lambda request: httpx.Response(200, text="[]"))
    source.download_catalog(60133)
    assert requests[0].url.path == "/satcat/records.php"


@pytest.mark.parametrize("status", [403, 500, 503])
def test_non_200_response_raises_and_is_not_retried(status: int) -> None:
    source, requests = make_source(lambda request: httpx.Response(status))
    with pytest.raises(DownloadError):
        source.download_elements(25544)
    assert len(requests) == 1


def test_redirect_is_not_followed_and_raises() -> None:
    source, requests = make_source(
        lambda request: httpx.Response(302, headers={"Location": "https://evil.example/"})
    )
    with pytest.raises(DownloadError):
        source.download_elements(25544)
    assert len(requests) == 1


def test_timeout_raises_download_error() -> None:
    def timeout(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("timed out", request=request)

    source, _ = make_source(timeout)
    with pytest.raises(DownloadError):
        source.download_elements(25544)


def test_connection_error_raises_download_error() -> None:
    def refused(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("refused", request=request)

    source, _ = make_source(refused)
    with pytest.raises(DownloadError):
        source.download_elements(25544)


def test_body_larger_than_5_mb_is_rejected() -> None:
    source, _ = make_source(
        lambda request: httpx.Response(200, content=b"x" * (MAX_DOWNLOAD_BYTES + 1))
    )
    with pytest.raises(DownloadError):
        source.download_elements(25544)


def test_body_of_exactly_5_mb_is_accepted() -> None:
    source, _ = make_source(lambda request: httpx.Response(200, content=b"x" * MAX_DOWNLOAD_BYTES))
    assert len(source.download_elements(25544)) == MAX_DOWNLOAD_BYTES


def test_compressed_body_that_expands_beyond_5_mb_is_rejected() -> None:
    compressed = gzip.compress(b"0" * (MAX_DOWNLOAD_BYTES + 1024))
    assert len(compressed) < 1024 * 1024
    source, _ = make_source(
        lambda request: httpx.Response(
            200, headers={"Content-Encoding": "gzip"}, content=compressed
        )
    )
    with pytest.raises(DownloadError):
        source.download_elements(25544)


def test_body_that_is_not_utf8_is_rejected_as_data_error() -> None:
    source, _ = make_source(lambda request: httpx.Response(200, content=b"\xff\xfe\x00"))
    with pytest.raises(DataValidationError):
        source.download_elements(25544)
```

### `tests/adapters/test_malicious_input.py`

```python
"""Malicious input battery of SEC-38: each case ends in an error or a rejected satellite (spec 011)."""

from __future__ import annotations

import gzip
import json
from datetime import UTC, datetime

import httpx
import pytest

from orbita.adapters.celestrak_source import CelestrakSource
from orbita.domain.elements import OrbitalElements
from orbita.domain.errors import DataValidationError, DownloadError
from orbita.domain.validation import (
    MAX_DOWNLOAD_BYTES,
    mean_motion_change_is_plausible,
    parse_elements_payload,
    parse_json_text,
)

NOW = datetime(2026, 10, 30, 12, tzinfo=UTC)
ALLOWED = frozenset({25544})


def record(**changes: object) -> dict[str, object]:
    values: dict[str, object] = {
        "NORAD_CAT_ID": 25544,
        "OBJECT_NAME": "ISS (ZARYA)",
        "EPOCH": "2026-10-30T10:00:00",
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
    values.update(changes)
    return values


def serve(body: bytes, headers: dict[str, str] | None = None) -> CelestrakSource:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, headers=headers, content=body)

    return CelestrakSource(httpx.Client(transport=httpx.MockTransport(handler)))


def run_pipeline(body: bytes) -> tuple[OrbitalElements, ...]:
    """Download, parse and validate, as the use case of spec 014 will do."""
    text = serve(body).download_elements(25544)
    return parse_elements_payload(parse_json_text(text), ALLOWED, NOW).accepted


def test_body_larger_than_5_mb_ends_in_download_error() -> None:
    with pytest.raises(DownloadError):
        run_pipeline(b"[" + b" " * MAX_DOWNLOAD_BYTES + b"]")


def test_compressed_expansion_ends_in_download_error() -> None:
    bomb = gzip.compress(b" " * (MAX_DOWNLOAD_BYTES + 1))
    with pytest.raises(DownloadError):
        serve(bomb, {"Content-Encoding": "gzip"}).download_elements(25544)


@pytest.mark.parametrize("body", [b"[NaN]", b"[Infinity]", b'[{"BSTAR": -Infinity}]'])
def test_nan_and_infinity_end_in_data_error(body: bytes) -> None:
    with pytest.raises(DataValidationError):
        run_pipeline(body)


def test_nesting_of_10000_levels_ends_in_data_error() -> None:
    with pytest.raises(DataValidationError):
        run_pipeline(("[" * 10_000 + "]" * 10_000).encode())


def test_name_with_script_tag_rejects_the_satellite() -> None:
    body = json.dumps([record(OBJECT_NAME="<script>alert(1)</script>")]).encode()
    assert run_pipeline(body) == ()


def test_name_with_line_break_rejects_the_satellite() -> None:
    body = json.dumps([record(OBJECT_NAME="ISS\n2026-10-30 FAKE LOG LINE")]).encode()
    assert run_pipeline(body) == ()


def test_redirect_to_another_host_ends_in_download_error() -> None:
    source = CelestrakSource(
        httpx.Client(
            transport=httpx.MockTransport(
                lambda request: httpx.Response(
                    301, headers={"Location": "https://evil.example/elements"}
                )
            )
        )
    )
    with pytest.raises(DownloadError):
        source.download_elements(25544)


def test_mean_motion_change_of_6_percent_is_rejected_against_the_saved_value() -> None:
    saved = parse_elements_payload([record()], ALLOWED, NOW).accepted[0]
    changed = parse_elements_payload([record(MEAN_MOTION=15.5 * 1.06)], ALLOWED, NOW).accepted[0]
    assert not mean_motion_change_is_plausible(saved, changed)
```

## Pasos

1. **Crear la rama y añadir `httpx`:**
   ```powershell
   git switch -c feature/011-adaptador-celestrak
   uv add "httpx==<version>"
   ```
   Sustituir `<version>` por la última versión estable en PyPI (la que muestre `uv add httpx` sin el `==`). Después,
   `uv tree --depth 1` y anotar la versión en la tabla de dependencias de `DESIGN.md` §6. `uv add` actualiza
   `pyproject.toml` y `uv.lock`.
2. **Crear los tres archivos** con el contenido de este documento.
3. **Ejecutar los tests:** `uv run pytest -v`.
4. **Comprobar calidad:** `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy src`,
   `uv run pre-commit run --all-files`. Si mypy se queja de `httpx`, no se añade `ignore`: se revisa la versión.
5. **Comprobar la regla de red:** `Get-ChildItem -Recurse src -Filter *.py | Select-String -Pattern '^(import|from) httpx'` debe mostrar
   solo `celestrak_source.py`.
6. **Commit y merge** con el mensaje `011: adaptador celestrak y entradas maliciosas`.

## Casos borde y manejo de errores

1. Un código de estado 304 o 204 no es 200: se trata como error y no se reintenta.
2. Un cuerpo de exactamente 5 MB se acepta; uno de un byte más se rechaza.
3. Un `Content-Encoding: gzip` engañoso se detecta porque el límite cuenta los bytes ya descomprimidos.
4. El cliente lo crea el punto de entrada con TLS verificado; este adaptador no acepta `verify=False`.

## Tests de aceptación

- Las peticiones van a `https://celestrak.org` con `CATNR` y `FORMAT=JSON`.
- Un 403, 500 o 503 termina en `DownloadError` y solo hay una petición.
- Una redirección no se sigue y termina en `DownloadError`.
- Un timeout o un error de conexión terminan en `DownloadError`.
- Un cuerpo de más de 5 MB termina en `DownloadError`; uno de exactamente 5 MB se acepta.
- Una descompresión gzip que supera 5 MB termina en `DownloadError`.
- Un cuerpo que no es UTF-8 termina en `DataValidationError`.
- La batería de `test_malicious_input.py` cubre las ocho entradas de SEC-38 y ninguna termina en un satélite aceptado.

## Fuera de alcance

- Guardar el archivo y no cambiarlo si la validación falla: spec 014 (caso de uso) y spec 012 (almacén).
- Intervalos de descarga: spec 005 (regla) y spec 014 (uso).

## Definition of Done

Todos los comandos en PowerShell, desde la carpeta `orbita`.

- [ ] `uv run pytest -v` → todos los tests pasan.
- [ ] `Get-ChildItem -Recurse src -Filter *.py | Select-String -Pattern '^(import|from) httpx'` → solo aparece `celestrak_source.py`.
- [ ] `Get-ChildItem -Recurse src -Filter *.py | Select-String -Pattern 'verify=False|follow_redirects=True'` → sin salida.
- [ ] `Get-ChildItem -Recurse src -Filter *.py | Select-String -Pattern 'except Exception:' ` → sin salida (no se capturan excepciones genéricas).
- [ ] `uv run ruff check .`, `uv run mypy src` y `uv run pre-commit run --all-files` sin errores.
- [ ] `uv lock --check` → sin errores.
- [ ] `git status` → `nothing to commit, working tree clean` después del merge.
