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
        """Return raw JSON of orbital elements (SatelliteDataSource)."""
        return self._get(ELEMENTS_PATH, norad, "elements")

    def download_catalog(self, norad: int) -> str:
        """Return the raw JSON text of the SATCAT record of one satellite (SatelliteDataSource)."""
        return self._get(CATALOG_PATH, norad, "catalog")

    def _get(self, path: str, norad: int, kind: str) -> str:
        """Request one satellite and return its body as text.

        Raises:
            DownloadError: on HTTP error, redirect, timeout, connection error, or body > 5 MB.
            DataValidationError: if body is not UTF-8 text.
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
