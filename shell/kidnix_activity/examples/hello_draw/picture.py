"""A PNG, written by hand, so the example needs no image library.

Not a general encoder: one solid colour, 8-bit RGB, no interlacing, one IDAT.
That is enough for what hello_draw is demonstrating and it keeps the example's
dependency list at zero, which is the point -- an example that needed Pillow
would be teaching the wrong lesson about what an activity may install.

Real activities draw with Cairo through GTK and save with GdkPixbuf, both of
which are on the image already.
"""

from __future__ import annotations

import struct
import zlib
from pathlib import Path

__all__ = ["COLOURS", "solid_png", "write_square"]

#: The four colours the button cycles through. Named, because the caption says
#: the name out loud and a child who cannot read "teal" can still hear it. They
#: are the shell's own palette, so a hello_draw square looks like it belongs in
#: My Things next to everything else.
COLOURS: tuple[tuple[str, tuple[int, int, int]], ...] = (
    ("teal", (0x0F, 0x8A, 0x8A)),
    ("pink", (0xF0, 0x62, 0x92)),
    ("yellow", (0xFF, 0xD2, 0x3F)),
    ("ink", (0x16, 0x18, 0x1D)),
)

#: Big enough to look like a picture in a 20 mm Journal card and small enough
#: that generating one is instant.
SIZE = 256


def _chunk(tag: bytes, data: bytes) -> bytes:
    return (
        struct.pack(">I", len(data))
        + tag
        + data
        + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
    )


def solid_png(colour: tuple[int, int, int], size: int = SIZE) -> bytes:
    """``size`` x ``size`` of one colour, as PNG bytes."""
    size = max(1, int(size))
    row = b"\x00" + bytes(colour) * size  # filter byte 0 (None), then the pixels
    header = struct.pack(">IIBBBBB", size, size, 8, 2, 0, 0, 0)
    return (
        b"\x89PNG\r\n\x1a\n"
        + _chunk(b"IHDR", header)
        + _chunk(b"IDAT", zlib.compress(row * size))
        + _chunk(b"IEND", b"")
    )


def write_square(path: Path, index: int, size: int = SIZE) -> str:
    """Write colour ``index`` (wrapping) to ``path``. Returns the colour's name."""
    name, colour = COLOURS[index % len(COLOURS)]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(solid_png(colour, size))
    return name
