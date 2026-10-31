"""Satellite catalog entries: owner, launch date and their validation (DESIGN.md §4.6)."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime

from orbita.domain.elements import require_utc
from orbita.domain.errors import DataValidationError

OWNER_CODE_PATTERN = re.compile(r"[A-Z0-9]{1,10}")
OWNER_CODE_MESSAGE = "owner_code must be 1 to 10 capital letters or digits"


@dataclass(frozen=True, slots=True)
class CatalogEntry:
    """The SATCAT data of one satellite: NORAD number, owner code and launch date."""

    norad: int
    owner_code: str
    launch_date: date

    def __post_init__(self) -> None:
        """Validate the NORAD number, the owner code and the launch date."""
        if isinstance(self.norad, bool) or not isinstance(self.norad, int) or self.norad <= 0:
            raise DataValidationError("norad must be a positive integer")
        if not isinstance(self.owner_code, str):
            raise DataValidationError(OWNER_CODE_MESSAGE)
        if OWNER_CODE_PATTERN.fullmatch(self.owner_code) is None:
            raise DataValidationError(OWNER_CODE_MESSAGE)
        if isinstance(self.launch_date, datetime) or not isinstance(self.launch_date, date):
            raise DataValidationError("launch_date must be a date without time")


@dataclass(frozen=True, slots=True)
class Catalog:
    """All the catalog entries saved by one successful download."""

    downloaded_at: datetime
    entries: tuple[CatalogEntry, ...]

    def __post_init__(self) -> None:
        """Validate the download time and reject a NORAD number that appears twice."""
        require_utc(self.downloaded_at, "downloaded_at")
        if not isinstance(self.entries, tuple):
            raise DataValidationError("entries must be a tuple")
        norads = [item.norad for item in self.entries]
        if len(set(norads)) != len(norads):
            raise DataValidationError("a NORAD number appears more than once in the catalog")
