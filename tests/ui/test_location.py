"""Tests of the browser location reading validation (spec 016). No browser or Streamlit needed."""

from __future__ import annotations

import math

import pytest

from orbita.ui.location import accuracy_from_reading, observer_from_reading


def test_valid_reading_becomes_an_observer() -> None:
    observer = observer_from_reading({"latitude": 3.45, "longitude": -76.53})
    assert observer is not None
    assert observer.latitude == 3.45


def test_limit_values_are_accepted() -> None:
    assert observer_from_reading({"latitude": 90.0, "longitude": 180.0}) is not None


@pytest.mark.parametrize(
    "reading",
    [
        None,
        {},
        {"latitude": 90.1, "longitude": 0.0},
        {"latitude": 0.0, "longitude": -180.1},
        {"latitude": "3.4", "longitude": 1.0},
        {"latitude": True, "longitude": 1.0},
        {"latitude": math.nan, "longitude": 0.0},
    ],
)
def test_invalid_readings_give_no_observer(reading: dict[str, object] | None) -> None:
    assert observer_from_reading(reading) is None


def test_accuracy_is_kept_when_finite_and_not_negative() -> None:
    assert accuracy_from_reading({"accuracy": 12.5}) == 12.5


@pytest.mark.parametrize(
    "reading", [None, {}, {"accuracy": -1.0}, {"accuracy": math.nan}, {"accuracy": "10"}]
)
def test_invalid_accuracy_is_ignored(reading: dict[str, object] | None) -> None:
    assert accuracy_from_reading(reading) is None


def test_observer_representation_hides_the_coordinates() -> None:
    observer = observer_from_reading({"latitude": 3.45, "longitude": -76.53})
    assert observer is not None
    assert "3.45" not in repr(observer)
    assert "76.53" not in repr(observer)
