"""The night side of the Earth as a transparent PNG, drawn over the photo (offline)."""

from __future__ import annotations

import functools
import math
import os
import struct
import zlib
from pathlib import Path
from typing import Final

WIDTH: Final = 720
HEIGHT: Final = 360
NIGHT_ALPHA: Final = 150
_NIGHT_RGB: Final = (5, 10, 25)
_CLEAR: Final = b"\x00\x00\x00\x00"
_PNG_SIGNATURE: Final = b"\x89PNG\r\n\x1a\n"


def _chunk(kind: bytes, body: bytes) -> bytes:
    """Return one PNG chunk: length, type, data and CRC."""
    crc = zlib.crc32(kind + body) & 0xFFFFFFFF
    return struct.pack(">I", len(body)) + kind + body + struct.pack(">I", crc)


def night_png(sun_lat: float, sun_lon: float) -> bytes:
    """Return a WIDTH x HEIGHT RGBA PNG, dark where the Sun is below the horizon.

    The Sun is overhead at (sun_lat, sun_lon); the horizon lies 90 degrees away from that point.
    """
    declination = math.radians(sun_lat)
    subsolar = math.radians(sun_lon)
    sin_dec, cos_dec = math.sin(declination), math.cos(declination)
    rows = bytearray()
    for y in range(HEIGHT):
        lat = math.radians(90.0 - (y + 0.5) * 180.0 / HEIGHT)
        sin_lat, cos_lat = math.sin(lat), math.cos(lat)
        rows.append(0)
        for x in range(WIDTH):
            lon = math.radians(-180.0 + (x + 0.5) * 360.0 / WIDTH)
            cos_zenith = sin_lat * sin_dec + cos_lat * cos_dec * math.cos(lon - subsolar)
            if cos_zenith < 0.0:
                rows += bytes((*_NIGHT_RGB, NIGHT_ALPHA))
            else:
                rows += _CLEAR
    header = struct.pack(">IIBBBBB", WIDTH, HEIGHT, 8, 6, 0, 0, 0)
    return (
        _PNG_SIGNATURE
        + _chunk(b"IHDR", header)
        + _chunk(b"IDAT", zlib.compress(bytes(rows), 6))
        + _chunk(b"IEND", b"")
    )


@functools.lru_cache(maxsize=4)
def _cached_night_png(sun_lat: float, sun_lon: float) -> bytes:
    """Cache the image for rounded Sun positions: it changes slowly."""
    return night_png(sun_lat, sun_lon)


def write_night_mask(path: Path, sun: tuple[float, float]) -> None:
    """Write the night mask to path (atomic replace) for the Sun at (latitude, longitude).

    Raises:
        OSError: if the file cannot be written.
    """
    sun_lat, sun_lon = sun
    data = _cached_night_png(round(sun_lat * 2) / 2, round(sun_lon * 2) / 2)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_bytes(data)
    os.replace(temporary, path)
