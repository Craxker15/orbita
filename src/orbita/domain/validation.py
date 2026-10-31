"""Validation of the data downloaded from CelesTrak (SEC-10, SEC-28, SEC-29, SEC-38, RF-07).

The adapter delivers raw text. This module decides what is accepted. It does not read the network,
the disk or the clock: the current time is an argument.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from typing import NoReturn

from orbita.domain.catalog import CatalogEntry
from orbita.domain.elements import OrbitalElements, require_utc
from orbita.domain.errors import DataValidationError

MAX_DOWNLOAD_BYTES = 5 * 1024 * 1024
MAX_RECORDS = 50
MAX_MEAN_MOTION_CHANGE = 0.05
MAX_EPOCH_IN_FUTURE = timedelta(days=1)
FORBIDDEN_NAME_CHARACTERS = frozenset("<>")

ELEMENTS_REQUIRED_KEYS = (
    "NORAD_CAT_ID",
    "OBJECT_NAME",
    "EPOCH",
    "INCLINATION",
    "MEAN_MOTION",
    "ECCENTRICITY",
    "RA_OF_ASC_NODE",
    "ARG_OF_PERICENTER",
    "MEAN_ANOMALY",
    "MEAN_MOTION_DOT",
    "MEAN_MOTION_DDOT",
    "BSTAR",
)
CATALOG_REQUIRED_KEYS = ("NORAD_CAT_ID", "OWNER", "LAUNCH_DATE")


@dataclass(frozen=True, slots=True)
class ParsedRecords[T]:
    """The accepted records of one payload, and the NORAD numbers of the rejected ones."""

    accepted: tuple[T, ...]
    rejected_norad: tuple[int, ...]


def parse_json_text(text: str) -> object:
    """Parse downloaded text as JSON, rejecting size, NaN, Infinity and very deep nesting.

    Preconditions: text is the complete body of one response.
    Postconditions: the result contains only JSON values; no NaN or Infinity.

    Raises:
        DataValidationError: if the text is larger than 5 MB, is not valid JSON, is nested too
            deeply, or contains NaN, Infinity or -Infinity.
    """
    if len(text.encode("utf-8")) > MAX_DOWNLOAD_BYTES:
        raise DataValidationError("the downloaded text is larger than 5 MB")
    try:
        return json.loads(text, parse_constant=_reject_constant)
    except (ValueError, RecursionError) as error:
        raise DataValidationError("the downloaded text is not valid JSON") from error


def _reject_constant(token: str) -> NoReturn:
    """Reject the JSON constants NaN, Infinity and -Infinity (SEC-28)."""
    raise DataValidationError(f"the JSON constant {token} is not allowed")


def parse_elements_payload(
    payload: object, allowed_norad: frozenset[int], now: datetime
) -> ParsedRecords[OrbitalElements]:
    """Validate a list of orbital element records (CelesTrak GP in JSON).

    A payload that is not a list of at most 50 records is rejected as a whole. A single
    invalid record only rejects its own satellite, so the valid records of the same payload
    are kept (RF-07, SEC-38).

    Preconditions: now is timezone-aware UTC.
    Postconditions: every accepted element has a NORAD number in allowed_norad, a finite
        value in each field and an epoch at most one day after now.

    Raises:
        DataValidationError: if the payload itself is not a list of at most 50 records.
    """
    require_utc(now, "now")
    records = _top_level_list(payload)
    accepted: list[OrbitalElements] = []
    rejected: list[int] = []
    for record in records:
        try:
            accepted.append(_element_from_record(record, allowed_norad, now))
        except DataValidationError:
            norad = _norad_of(record)
            if norad is not None:
                rejected.append(norad)
    return ParsedRecords(tuple(accepted), tuple(rejected))


def parse_catalog_payload(
    payload: object, allowed_norad: frozenset[int], now: datetime
) -> ParsedRecords[CatalogEntry]:
    """Validate a list of SATCAT records (country code and launch date, DESIGN.md §4.6).

    Preconditions: now is timezone-aware UTC.
    Postconditions: every accepted entry has a NORAD number in allowed_norad and a valid owner code.

    Raises:
        DataValidationError: if the payload itself is not a list of at most 50 records.
    """
    require_utc(now, "now")
    records = _top_level_list(payload)
    accepted: list[CatalogEntry] = []
    rejected: list[int] = []
    for record in records:
        try:
            accepted.append(_catalog_from_record(record, allowed_norad))
        except DataValidationError:
            norad = _norad_of(record)
            if norad is not None:
                rejected.append(norad)
    return ParsedRecords(tuple(accepted), tuple(rejected))


def mean_motion_change_is_plausible(previous: OrbitalElements | None, new: OrbitalElements) -> bool:
    """Return False when the mean motion changed by more than 5 % since the saved value (SEC-29).

    Preconditions: previous, when present, has a mean motion greater than zero (SEC-10).
    Postconditions: True when there is no previous value.
    """
    if previous is None:
        return True
    change = abs(new.mean_motion_rev_day - previous.mean_motion_rev_day)
    return change / previous.mean_motion_rev_day <= MAX_MEAN_MOTION_CHANGE


def _top_level_list(payload: object) -> list[object]:
    """Return the records of the payload, or reject a payload that is not a list of at most 50."""
    if not isinstance(payload, list) or len(payload) > MAX_RECORDS:
        raise DataValidationError("the payload must be a list of at most 50 records")
    return list(payload)


def _element_from_record(
    record: object, allowed_norad: frozenset[int], now: datetime
) -> OrbitalElements:
    """Build one OrbitalElements from a CelesTrak record, or raise DataValidationError."""
    fields = _checked_mapping(record, ELEMENTS_REQUIRED_KEYS)
    norad = _as_int(fields["NORAD_CAT_ID"], "NORAD_CAT_ID")
    if norad not in allowed_norad:
        raise DataValidationError("the NORAD number is not in the satellite list")
    name = _as_text(fields["OBJECT_NAME"], "OBJECT_NAME")
    _check_name(name)
    return OrbitalElements(
        norad=norad,
        name=name,
        inclination_deg=_as_number(fields["INCLINATION"], "INCLINATION"),
        mean_motion_rev_day=_as_number(fields["MEAN_MOTION"], "MEAN_MOTION"),
        eccentricity=_as_number(fields["ECCENTRICITY"], "ECCENTRICITY"),
        epoch=_as_epoch(fields["EPOCH"], now),
        raan_deg=_as_number(fields["RA_OF_ASC_NODE"], "RA_OF_ASC_NODE"),
        arg_perigee_deg=_as_number(fields["ARG_OF_PERICENTER"], "ARG_OF_PERICENTER"),
        mean_anomaly_deg=_as_number(fields["MEAN_ANOMALY"], "MEAN_ANOMALY"),
        mean_motion_dot=_as_number(fields["MEAN_MOTION_DOT"], "MEAN_MOTION_DOT"),
        mean_motion_ddot=_as_number(fields["MEAN_MOTION_DDOT"], "MEAN_MOTION_DDOT"),
        bstar=_as_number(fields["BSTAR"], "BSTAR"),
    )


def _catalog_from_record(record: object, allowed_norad: frozenset[int]) -> CatalogEntry:
    """Build one CatalogEntry from a SATCAT record, or raise DataValidationError."""
    fields = _checked_mapping(record, CATALOG_REQUIRED_KEYS)
    norad = _as_int(fields["NORAD_CAT_ID"], "NORAD_CAT_ID")
    if norad not in allowed_norad:
        raise DataValidationError("the NORAD number is not in the satellite list")
    owner = _as_text(fields["OWNER"], "OWNER")
    launch = _as_text(fields["LAUNCH_DATE"], "LAUNCH_DATE")
    try:
        launch_date = date.fromisoformat(launch)
    except ValueError as error:
        raise DataValidationError("LAUNCH_DATE is not a valid date") from error
    return CatalogEntry(norad=norad, owner_code=owner, launch_date=launch_date)


def _checked_mapping(record: object, required: tuple[str, ...]) -> Mapping[str, object]:
    """Return the record if it is a JSON object with every required key."""
    if not isinstance(record, dict):
        raise DataValidationError("a record is not a JSON object")
    if any(key not in record for key in required):
        raise DataValidationError("a record lacks required fields")
    return record


def _norad_of(record: object) -> int | None:
    """Return the NORAD number of a record if it is an integer, to log rejections."""
    if isinstance(record, dict):
        value = record.get("NORAD_CAT_ID")
        if isinstance(value, int) and not isinstance(value, bool):
            return value
    return None


def _as_int(value: object, field: str) -> int:
    """Return an integer field; booleans are rejected."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise DataValidationError(f"{field} must be an integer")
    return value


def _as_number(value: object, field: str) -> float:
    """Return a numeric field as float; booleans and strings are rejected."""
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise DataValidationError(f"{field} must be a number")
    return float(value)


def _as_text(value: object, field: str) -> str:
    """Return a text field; anything else is rejected."""
    if not isinstance(value, str):
        raise DataValidationError(f"{field} must be text")
    return value


def _check_name(name: str) -> None:
    """Reject names with angle brackets or control characters (SEC-13, SEC-30, SEC-38)."""
    if any(char in FORBIDDEN_NAME_CHARACTERS or not char.isprintable() for char in name):
        raise DataValidationError("the name contains forbidden characters")


def _as_epoch(value: object, now: datetime) -> datetime:
    """Parse the epoch as UTC; CelesTrak sends it without an offset, which means UTC."""
    text = _as_text(value, "EPOCH")
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError as error:
        raise DataValidationError("EPOCH is not a valid date") from error
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    parsed = parsed.astimezone(UTC)
    if parsed > now + MAX_EPOCH_IN_FUTURE:
        raise DataValidationError("EPOCH is more than one day in the future")
    return parsed
