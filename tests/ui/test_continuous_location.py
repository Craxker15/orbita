"""Tests of the continuous-location component file (spec 020, ADR-007, SEC-04)."""

from __future__ import annotations

from pathlib import Path

HTML = (
    Path(__file__).resolve().parents[2]
    / "src" / "orbita" / "ui" / "static" / "geowatch" / "index.html"
).read_text(encoding="utf-8")

FORBIDDEN = ["fetch(", "XMLHttpRequest", "WebSocket", "sendBeacon", "eval(", "http://", "https://"]


def test_component_can_watch_and_stop_the_position() -> None:
    assert "watchPosition" in HTML
    assert "clearWatch" in HTML


def test_component_keeps_the_one_time_reading() -> None:
    assert "getCurrentPosition" in HTML


def test_component_makes_no_network_requests_and_no_eval() -> None:
    for token in FORBIDDEN:
        assert token not in HTML, token


def test_component_stops_the_watch_when_the_page_closes() -> None:
    assert "pagehide" in HTML
