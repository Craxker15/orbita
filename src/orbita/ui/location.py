"""'My location' button: one browser reading, kept only in memory (ADR-007, RF-10, SEC-14)."""

from __future__ import annotations

import math
from collections.abc import Mapping
from pathlib import Path
from typing import Any, Final

import streamlit as st
import streamlit.components.v1 as components

from orbita.domain.errors import InvalidLocationError
from orbita.domain.observer import Observer

OBSERVER_KEY: Final = "observer"
ACCURACY_KEY: Final = "accuracy_m"
REQUESTED_KEY: Final = "location_requested"
STATIC_DIR: Final = Path(__file__).resolve().parent / "static" / "geowatch"
_geolocate: Any = components.declare_component("orbita_geolocate", path=str(STATIC_DIR))


def _finite_number(value: object) -> float | None:
    """Return the value as a finite float, or None for booleans, text and NaN/Infinity (SEC-14)."""
    if isinstance(value, bool) or not isinstance(value, int | float):
        return None
    number = float(value)
    return number if math.isfinite(number) else None


def observer_from_reading(reading: Mapping[str, Any] | None) -> Observer | None:
    """Turn the component output into a validated Observer, or None (SEC-14, DESIGN.md §4.5)."""
    if not reading:
        return None
    latitude = _finite_number(reading.get("latitude"))
    longitude = _finite_number(reading.get("longitude"))
    if latitude is None or longitude is None:
        return None
    try:
        return Observer(latitude=latitude, longitude=longitude)
    except InvalidLocationError:
        return None


def accuracy_from_reading(reading: Mapping[str, Any] | None) -> float | None:
    """Return accuracy in meters if it is a finite number >= 0; else None (SEC-14)."""
    if not reading:
        return None
    accuracy = _finite_number(reading.get("accuracy"))
    if accuracy is None or accuracy < 0:
        return None
    return accuracy


def location_section(texts: Mapping[str, str]) -> None:
    """Draw the privacy text, the button and the accuracy; the observer stays in memory (SEC-02)."""
    st.caption(texts["location_privacy"])
    if st.button(texts["my_location"]):
        st.session_state[REQUESTED_KEY] = True
    if st.session_state.get(REQUESTED_KEY):
        reading: Any = _geolocate(mode="once", key="geolocate", default=None)
        observer = observer_from_reading(reading)
        if observer is not None:
            st.session_state[OBSERVER_KEY] = observer
            st.session_state[ACCURACY_KEY] = accuracy_from_reading(reading)
    accuracy = st.session_state.get(ACCURACY_KEY)
    if st.session_state.get(OBSERVER_KEY) is not None and accuracy is not None:
        st.caption(texts["location_accuracy"].format(meters=round(accuracy)))
