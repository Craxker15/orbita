"""Tests of the night-side image (no network, no Streamlit)."""

from __future__ import annotations

import struct
import zlib
from pathlib import Path

from orbita.ui.night_mask import HEIGHT, NIGHT_ALPHA, WIDTH, night_png, write_night_mask


def _pixels(png: bytes) -> bytes:
    """Return the decompressed image data of a PNG written by night_png."""
    position = 8
    parts: list[bytes] = []
    while position < len(png):
        (length,) = struct.unpack(">I", png[position : position + 4])
        kind = png[position + 4 : position + 8]
        if kind == b"IDAT":
            parts.append(png[position + 8 : position + 8 + length])
        position += 12 + length
    return zlib.decompress(b"".join(parts))


def _alpha(raw: bytes, x: int, y: int) -> int:
    row_size = 1 + WIDTH * 4
    return raw[y * row_size + 1 + x * 4 + 3]


def test_png_has_signature_and_the_expected_size() -> None:
    png = night_png(0.0, 0.0)
    assert png.startswith(b"\x89PNG\r\n\x1a\n")
    width, height = struct.unpack(">II", png[16:24])
    assert (width, height) == (WIDTH, HEIGHT)


def test_the_side_facing_the_sun_is_clear_and_the_far_side_is_dark() -> None:
    raw = _pixels(night_png(0.0, 0.0))
    assert _alpha(raw, WIDTH // 2, HEIGHT // 2) == 0
    assert _alpha(raw, 0, HEIGHT // 2) == NIGHT_ALPHA


def test_write_creates_the_file(tmp_path: Path) -> None:
    target = tmp_path / "night_mask.png"
    write_night_mask(target, (0.0, 0.0))
    assert target.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
