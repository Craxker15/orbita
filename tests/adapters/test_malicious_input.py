"""Malicious input battery (SEC-38): error or rejected satellite (spec 013)."""

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
