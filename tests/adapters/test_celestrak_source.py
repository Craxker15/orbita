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
    big_content = b"x" * (MAX_DOWNLOAD_BYTES + 1)
    source, _ = make_source(lambda request: httpx.Response(200, content=big_content))
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
