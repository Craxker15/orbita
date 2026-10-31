"""Ports for the orbital data: download from CelesTrak and local storage (ARCHITECTURE.md §4)."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from orbita.domain.catalog import Catalog
from orbita.domain.elements import OrbitalDataset
from orbita.domain.state import DownloadAttempts


@runtime_checkable
class SatelliteDataSource(Protocol):
    """Downloads the raw text of CelesTrak responses. The domain validates the text afterwards."""

    def download_elements(self, norad: int) -> str:
        """Return the raw JSON text of the orbital elements of one satellite.

        Preconditions: norad is one of the 20 satellites of DESIGN.md §3.1.
        Postconditions: the text is at most 5 MB and nothing is written to disk.

        Raises:
            DownloadError: on HTTP error, redirect, timeout, connection error, or body > 5 MB.
        """
        ...

    def download_catalog(self, norad: int) -> str:
        """Return the raw JSON text of the SATCAT record of one satellite.

        Preconditions: norad is one of the 20 satellites of DESIGN.md §3.1.
        Postconditions: the text is at most 5 MB and nothing is written to disk.

        Raises:
            DownloadError: under the same conditions as download_elements.
        """
        ...


@runtime_checkable
class SatelliteDataStore(Protocol):
    """Loads and saves the last valid data and the times of the download attempts."""

    def load_elements(self) -> OrbitalDataset | None:
        """Return the saved orbital elements, or None when no file exists.

        Preconditions: none.
        Postconditions: the returned dataset passed the domain validation when it was saved.

        Raises:
            DataValidationError: if the saved file cannot be read as a valid dataset.
        """
        ...

    def save_elements(self, dataset: OrbitalDataset) -> None:
        """Replace the saved orbital elements atomically.

        Preconditions: dataset is valid (its constructor already checked it).
        Postconditions: a reader sees either the old file or the new one, never a half-written file.

        Raises:
            OSError: if the file cannot be written; the previous file is kept.
        """
        ...

    def load_catalog(self) -> Catalog | None:
        """Return the saved SATCAT entries, or None when no file exists.

        Preconditions: none.
        Postconditions: the returned catalog passed the domain validation when it was saved.

        Raises:
            DataValidationError: if the saved file cannot be read as a valid catalog.
        """
        ...

    def save_catalog(self, catalog: Catalog) -> None:
        """Replace the saved SATCAT entries atomically.

        Preconditions: catalog is valid.
        Postconditions: as in save_elements.

        Raises:
            OSError: if the file cannot be written; the previous file is kept.
        """
        ...

    def load_attempts(self) -> DownloadAttempts:
        """Return the times of the last download attempts; empty values when none exists.

        Preconditions: none.
        Postconditions: never None; a missing file gives DownloadAttempts().

        Raises:
            DataValidationError: if the saved file cannot be read.
        """
        ...

    def save_attempts(self, attempts: DownloadAttempts) -> None:
        """Replace the times of the last download attempts atomically.

        Preconditions: attempts has UTC times.
        Postconditions: as in save_elements.

        Raises:
            OSError: if the file cannot be written.
        """
        ...
