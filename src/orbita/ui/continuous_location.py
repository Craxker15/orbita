"""Continuous location with watchPosition (ADR-007, SEC-01, SEC-02, SEC-04)."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any, Final

import streamlit as st
import streamlit.components.v1 as components

from orbita.ui.location import (
    ACCURACY_KEY,
    OBSERVER_KEY,
    accuracy_from_reading,
    observer_from_reading,
)

STATIC_DIR: Final = Path(__file__).resolve().parent / "static" / "geowatch"
SWITCH_KEY: Final = "continuous_location_switch"
_geowatch: Any = components.declare_component("orbita_geowatch", path=str(STATIC_DIR))


def continuous_location_section(texts: Mapping[str, str]) -> None:
    """Draw the switch and, while it is on, keep the latest valid reading in memory (SEC-02).

    The component is always rendered with its active flag: turning the switch off makes the
    browser stop the watch (SEC-01).
    """
    enabled = bool(st.toggle(texts["follow_location"], key=SWITCH_KEY))
    reading: Any = _geowatch(mode="watch", active=enabled, key="geowatch", default=None)
    if not enabled:
        return
    observer = observer_from_reading(reading)
    if observer is not None:
        st.session_state[OBSERVER_KEY] = observer
        st.session_state[ACCURACY_KEY] = accuracy_from_reading(reading)
