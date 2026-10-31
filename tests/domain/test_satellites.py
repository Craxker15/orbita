"""Tests of the satellite list (spec 010)."""

from __future__ import annotations

import pytest

from orbita.domain.errors import DataValidationError
from orbita.domain.satellites import (
    ISS_NORAD,
    SATELLITE_NORADS,
    SATELLITES,
    SatelliteSpec,
    check_satellite_list,
)


def test_the_list_has_twenty_satellites_with_unique_norad_numbers() -> None:
    check_satellite_list(SATELLITES)
    assert len(SATELLITE_NORADS) == 20


def test_every_norad_number_is_confirmed() -> None:
    assert all(satellite.norad > 0 for satellite in SATELLITES)


def test_the_iss_is_in_the_list() -> None:
    assert ISS_NORAD in SATELLITE_NORADS


def test_a_list_with_a_duplicate_is_rejected() -> None:
    duplicated = (SatelliteSpec(25544, "ISS"),) * 20
    with pytest.raises(DataValidationError):
        check_satellite_list(duplicated)


def test_a_list_with_nineteen_satellites_is_rejected() -> None:
    with pytest.raises(DataValidationError):
        check_satellite_list(SATELLITES[:19])
