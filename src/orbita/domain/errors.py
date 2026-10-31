"""Project exceptions. Every Orbita error inherits from OrbitaError (ARCHITECTURE.md §6)."""

from __future__ import annotations


class OrbitaError(Exception):
    """Base class of every error raised by the project."""


class DataValidationError(OrbitaError):
    """Downloaded or stored data does not pass validation (SEC-10, RF-07)."""


class DownloadError(OrbitaError):
    """A CelesTrak download failed or was refused (SEC-16, SEC-26, SEC-27)."""


class PropagationError(OrbitaError):
    """The orbit of a satellite could not be computed (DESIGN.md §4.4)."""


class ConfigError(OrbitaError):
    """A configuration file or value is invalid (SEC-09)."""


class InvalidLocationError(OrbitaError):
    """A location is outside the valid ranges of DESIGN.md §4.5."""
