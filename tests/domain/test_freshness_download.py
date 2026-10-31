"""Tests of the freshness and download-interval rules of spec 005."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from orbita.domain.download_rules import (
    CATALOG_DOWNLOAD_INTERVAL,
    ELEMENTS_DOWNLOAD_INTERVAL,
    is_download_due,
)
from orbita.domain.elements import Freshness
from orbita.domain.errors import DataValidationError
from orbita.domain.freshness_rules import classify_freshness

NOW = datetime(2026, 10, 30, 12, 0, tzinfo=UTC)
ONE_SECOND = timedelta(seconds=1)


@pytest.mark.parametrize(
    ("age", "expected"),
    [
        (timedelta(days=3), Freshness.NORMAL),
        (timedelta(days=3) + ONE_SECOND, Freshness.STALE),
        (timedelta(days=14), Freshness.STALE),
        (timedelta(days=14) + ONE_SECOND, Freshness.TOO_OLD),
    ],
)
def test_freshness_thresholds_of_rf06(age: timedelta, expected: Freshness) -> None:
    assert classify_freshness(NOW - age, NOW) is expected


def test_freshness_rejects_download_in_the_future() -> None:
    with pytest.raises(DataValidationError, match="later than now"):
        classify_freshness(NOW + ONE_SECOND, NOW)


def test_freshness_rejects_naive_datetime() -> None:
    with pytest.raises(DataValidationError):
        classify_freshness(datetime(2026, 10, 30, 11, 0), NOW)


@pytest.mark.parametrize(
    ("elapsed", "due"),
    [
        (timedelta(hours=1, minutes=59), False),
        (timedelta(hours=2), True),
        (timedelta(hours=3), True),
    ],
)
def test_elements_download_every_two_hours_rf04(elapsed: timedelta, due: bool) -> None:
    last_attempt = NOW - elapsed
    assert is_download_due(last_attempt, NOW, ELEMENTS_DOWNLOAD_INTERVAL) is due


@pytest.mark.parametrize(
    ("elapsed", "due"),
    [
        (timedelta(hours=23, minutes=59), False),
        (timedelta(hours=24), True),
    ],
)
def test_catalog_download_every_24_hours_rf13(elapsed: timedelta, due: bool) -> None:
    last_attempt = NOW - elapsed
    assert is_download_due(last_attempt, NOW, CATALOG_DOWNLOAD_INTERVAL) is due


def test_first_download_is_always_due() -> None:
    assert is_download_due(None, NOW, ELEMENTS_DOWNLOAD_INTERVAL) is True


def test_download_rejects_last_attempt_in_the_future() -> None:
    with pytest.raises(DataValidationError, match="later than now"):
        is_download_due(NOW + ONE_SECOND, NOW, ELEMENTS_DOWNLOAD_INTERVAL)
