"""Tests of the system clock adapter (spec 013)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from orbita.adapters.system_clock import SystemClock
from orbita.ports.propagation import Clock


def test_system_clock_returns_utc_time() -> None:
    assert SystemClock().now().utcoffset() == timedelta(0)


def test_system_clock_is_between_two_real_readings() -> None:
    before = datetime.now(UTC)
    moment = SystemClock().now()
    after = datetime.now(UTC)
    assert before <= moment <= after


def test_system_clock_satisfies_the_clock_port() -> None:
    assert isinstance(SystemClock(), Clock)
