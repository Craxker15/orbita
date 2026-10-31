"""Time rules: conversion to Colombia time (DESIGN.md §4.3)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from orbita.domain.elements import require_utc

COLOMBIA_TIMEZONE = timezone(timedelta(hours=-5))
DISPLAY_FORMAT = "%Y-%m-%d %H:%M"


def to_colombia_time(moment_utc: datetime) -> datetime:
    """Return the same instant in Colombia time: UTC − 5 hours, with no daylight saving time."""
    require_utc(moment_utc, "moment_utc")
    return moment_utc.astimezone(COLOMBIA_TIMEZONE)


def format_colombia_time(moment_utc: datetime) -> str:
    """Return the Colombia time as `YYYY-MM-DD HH:MM`, the text shown to the user (RF-09)."""
    return to_colombia_time(moment_utc).strftime(DISPLAY_FORMAT)
