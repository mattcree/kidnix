"""Coarse pixel reading, standard library only.

QEMU's ``screendump`` writes a binary PPM (P6) when the filename does not end
in ``.png``, and a P6 is a nine-byte header followed by RGB triples -- which
means the harness can look at the framebuffer without ImageMagick, PIL or any
other thing a CI runner might not have.

Everything here is deliberately coarse. Pixel-exact comparison against a
golden image would break on every font hint and every theme tweak, and would
tell us nothing a human wants to know. What these helpers answer is
"is the screen mostly cream, and is there a big dark shape in the middle of
it" -- questions whose answers change only when the shell genuinely changes.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Image:
    width: int
    height: int
    data: bytes  # RGB triples, row major

    def pixel(self, x: int, y: int) -> tuple:
        offset = 3 * (y * self.width + x)
        return tuple(self.data[offset : offset + 3])


def read_ppm(path: str | Path) -> Image:
    """Parse a binary PPM (P6). Raises ValueError on anything else."""
    raw = Path(path).read_bytes()
    if not raw.startswith(b"P6"):
        raise ValueError(f"{path} is not a binary PPM (P6)")

    fields = []
    index = 2
    while len(fields) < 3:
        while index < len(raw) and raw[index : index + 1].isspace():
            index += 1
        if raw[index : index + 1] == b"#":  # a comment runs to end of line
            while index < len(raw) and raw[index : index + 1] not in (b"\n", b"\r"):
                index += 1
            continue
        start = index
        while index < len(raw) and not raw[index : index + 1].isspace():
            index += 1
        fields.append(int(raw[start:index]))
    index += 1  # exactly one whitespace byte after maxval

    width, height, maxval = fields
    if maxval != 255:
        raise ValueError(f"{path}: only 8-bit PPMs are supported (maxval {maxval})")
    return Image(width, height, raw[index : index + 3 * width * height])


def _box(image: Image, box: tuple | None) -> tuple:
    if box is None:
        return (0, 0, image.width, image.height)
    left, top, right, bottom = box
    return (max(0, left), max(0, top), min(image.width, right), min(image.height, bottom))


def mean_colour(image: Image, box: tuple | None = None) -> tuple:
    """Average RGB over ``box`` (left, top, right, bottom), sampled every 2 px."""
    left, top, right, bottom = _box(image, box)
    totals = [0, 0, 0]
    count = 0
    for y in range(top, bottom, 2):
        row = 3 * y * image.width
        for x in range(left, right, 2):
            offset = row + 3 * x
            totals[0] += image.data[offset]
            totals[1] += image.data[offset + 1]
            totals[2] += image.data[offset + 2]
            count += 1
    if not count:
        return (0, 0, 0)
    return tuple(total // count for total in totals)


def dark_fraction(image: Image, box: tuple | None = None, threshold: int = 110) -> float:
    """What proportion of ``box`` is darker than ``threshold`` (mean of RGB)."""
    left, top, right, bottom = _box(image, box)
    dark = 0
    count = 0
    for y in range(top, bottom, 2):
        row = 3 * y * image.width
        for x in range(left, right, 2):
            offset = row + 3 * x
            if (
                image.data[offset] + image.data[offset + 1] + image.data[offset + 2]
            ) // 3 < threshold:
                dark += 1
            count += 1
    return dark / count if count else 0.0


def dark_centroid(image: Image, box: tuple | None = None, threshold: int = 110) -> tuple | None:
    """Centroid and bounding box of the dark pixels in ``box``.

    Returns ``(cx, cy, count, (left, top, right, bottom))`` or ``None`` when
    there is nothing dark to speak of. Used to find the one big black shape on
    a screen -- the child's avatar on Who's here? -- without hard-coding a
    pixel position that a re-layout would invalidate.
    """
    left, top, right, bottom = _box(image, box)
    total_x = total_y = count = 0
    min_x, min_y, max_x, max_y = right, bottom, left, top
    for y in range(top, bottom, 2):
        row = 3 * y * image.width
        for x in range(left, right, 2):
            offset = row + 3 * x
            grey = (image.data[offset] + image.data[offset + 1] + image.data[offset + 2]) // 3
            if grey < threshold:
                total_x += x
                total_y += y
                count += 1
                min_x, max_x = min(min_x, x), max(max_x, x)
                min_y, max_y = min(min_y, y), max(max_y, y)
    if count < 50:
        return None
    return (total_x // count, total_y // count, count, (min_x, min_y, max_x, max_y))


def differs(before: Image, after: Image, box: tuple, tolerance: int = 12) -> float:
    """Fraction of ``box`` whose colour moved by more than ``tolerance``.

    A cheap "did anything happen here?" for the visual side of an interaction
    the journal also records.
    """
    left, top, right, bottom = _box(before, box)
    changed = 0
    count = 0
    for y in range(top, bottom, 2):
        row = 3 * y * before.width
        for x in range(left, right, 2):
            offset = row + 3 * x
            delta = max(
                abs(before.data[offset + channel] - after.data[offset + channel])
                for channel in (0, 1, 2)
            )
            if delta > tolerance:
                changed += 1
            count += 1
    return changed / count if count else 0.0


# --------------------------------------------------------------------------- #
# Finding the shell's widgets in a screenshot
# --------------------------------------------------------------------------- #
#
# The shell will not tell us where it put things: it has no debug endpoint and
# it logs its *metrics* (tile size, band height, grid shape) but not its
# *geometry*. Computing geometry from the metrics gets the rows right and the
# columns wrong -- Gtk.Grid columns are not homogeneous, so a column is as wide
# as its widest label ("Letters and ..." is 275 px where "Library" is 186), and
# a computed 4-column grid lands a click one tile off. Ask the pixels instead.
#
# Every child-facing control in kidnix is a rounded box with a 2 px border, a
# 5 px bottom edge and a paper-coloured interior on a paper-coloured surface.
# So: the *interiors* are invisible (they are the same colour as the page) and
# the *borders* are the only signal. A border line runs the whole width or
# height of its box; a glyph never does. Counting non-interior pixels down a
# column, or across a row, separates the two cleanly and needs no thresholds
# anybody has to tune.

#: A pixel that is part of a paper-coloured surface or the inside of a control.
#: Generous on purpose: @kid-paper is #fbf7ef and a hovered control turns pure
#: white, and both have to read as "interior".
INTERIOR_MIN = (244, 240, 232)


def _is_interior(pixel: tuple) -> bool:
    return (
        pixel[0] >= INTERIOR_MIN[0] and pixel[1] >= INTERIOR_MIN[1] and pixel[2] >= INTERIOR_MIN[2]
    )


def band_height_from(metrics_line: str, default: int = 96) -> int:
    """Pull the band's height out of the shell's own ``display metrics:`` line.

    Since v0.1.5 the band is a separate toplevel that gnome-kiosk pins to the
    top strip, and everything else -- the shell's content window *and every
    activity* -- is locked into the area below it. So "where does Tux Paint
    start?" is no longer 0, and hard-coding 96 would break the day the fit
    backstop shaves a pixel off the band (it settles at 97 on this panel).

    ``Metrics.describe()`` prints ``... band 97 px (button 19.2 mm) ...``.
    """
    match = re.search(r"\bband (\d+) px", metrics_line)
    return int(match.group(1)) if match else default


def content_top(image: Image) -> int:
    """The first row below the band, i.e. below the solid coloured strip."""
    width = image.width
    for y in range(image.height):
        solid = sum(1 for x in range(0, width, 8) if not _is_interior(image.pixel(x, y)))
        if solid < width // 16:  # mostly paper: we are past the band
            return y
    return 0


def _group(values: list, tolerance: int = 3) -> list:
    """Consecutive-ish integers to (first, last) groups."""
    if not values:
        return []
    groups = []
    start = previous = values[0]
    for value in values[1:]:
        if value - previous > tolerance:
            groups.append((start, previous))
            start = value
        previous = value
    groups.append((start, previous))
    return groups


def _edge_rows(image: Image, top: int, bottom: int, coverage: float, min_run: int) -> list:
    """Rows that look like the horizontal edge of a box, as (first, last) groups."""
    width = image.width
    edges = []
    for y in range(top, bottom):
        count = 0
        run = longest = 0
        for x in range(0, width, 2):
            if _is_interior(image.pixel(x, y)):
                run = 0
            else:
                count += 1
                run += 1
                longest = max(longest, run)
        if count > coverage * (width / 2) and longest * 2 >= min_run:
            edges.append(y)
    return _group(edges, tolerance=4)


def horizontal_bands(
    image: Image, top: int, bottom: int, coverage: float = 0.40, min_run: int = 120
) -> list:
    """(top, bottom) of every row of controls between ``top`` and ``bottom``.

    Every child-facing box in theme.css carries a **thin top edge and a thick
    bottom one** -- ``border: 2px`` with ``border-bottom-width: 6px`` plus a
    4 px shadow for a tile, 3/8/5 for a ritual button. That asymmetry is a
    design decision (the boxes sit *on* the page rather than float in it) and
    it is also exactly the signal needed here: a run of border rows two to four
    deep opens a band and the next run six or more deep closes it.

    Two filters keep glyphs out. ``coverage`` is how much of the width has to
    be non-interior, and ``min_run`` is how long an unbroken horizontal run has
    to be -- a 24 pt letter stroke is under 40 px, a box edge is at least 150.
    """
    bands = []
    opened = None
    for start, end in _edge_rows(image, top, bottom, coverage, min_run):
        depth = end - start + 1
        if depth <= 4 and opened is None:
            opened = start
        elif depth >= 6 and opened is not None:
            if 40 <= end - opened <= 420:
                bands.append((opened, end))
            opened = None
    return bands


def boxes_in_band(image: Image, band: tuple, min_width: int = 60) -> list:
    """(left, right) of every box in the horizontal band ``(top, bottom)``.

    A box's left and right edges are vertical border lines spanning the whole
    band; a glyph inside the box never does. Boxes whose *interior* is not
    paper-coloured (the "All done" tile is lavender) read as one wide edge
    group, which is the box itself.
    """
    top, bottom = band
    height = bottom - top + 1
    # Only the middle of the band. Every box is generously rounded (28 px on a
    # tile, 32 px on a ritual button), so its left and right borders simply do
    # not exist near the corners -- measuring the full height would find a
    # ritual button's edge present for barely half of it.
    inset = int(height * 0.3)
    first, last = top + inset, bottom - inset
    span = max(1, last - first + 1)
    columns = []
    for x in range(image.width):
        count = sum(1 for y in range(first, last + 1) if not _is_interior(image.pixel(x, y)))
        if count > 0.9 * span:
            columns.append(x)
    groups = _group(columns, tolerance=3)

    boxes = []
    thin = []
    for start, end in groups:
        if end - start > 20:  # a solid box, not an edge
            boxes.append((start, end))
        else:
            thin.append((start, end))
    for index in range(len(thin) - 1):
        left = thin[index][1]
        right = thin[index + 1][0]
        if min_width <= right - left <= 520 and _has_lid(image, top, bottom, left, right):
            boxes.append((left, right))
    return sorted(boxes)


def _has_lid(image: Image, top: int, bottom: int, left: int, right: int) -> bool:
    """Is the span between two vertical edges a box, or the gap between two?

    A box has a horizontal border across the top of it. A gap has the page.
    Without this check the 83 px of paper between "Finish this one" and "One
    last little thing" reads as a third button.
    """
    first, last = left + 8, right - 8
    if last <= first:
        return False
    for y in (top + 1, top + 2, bottom - 4, bottom - 3):
        if not 0 <= y < image.height:
            continue
        solid = sum(1 for x in range(first, last) if not _is_interior(image.pixel(x, y)))
        if solid > 0.7 * (last - first):
            return True
    return False


#: Tried in order, highest first. A full 4-column Home grid covers 65% of the
#: width; a single Journal card covers 21%. One threshold cannot see both
#: without also seeing the "All done" tile's lavender fill as an edge, so the
#: densest reading that finds anything wins.
COVERAGE_LADDER = (0.40, 0.18, 0.10)


def find_grid(image: Image, top: int = 0) -> list:
    """Every box on the surface, as rows of ``(left, top, right, bottom)``.

    Row 0 first, left to right within a row -- the order the shell lays its
    Home grid out in, so ``grid[row][column]`` is the tile at that cell.
    """
    start = top or content_top(image)
    for coverage in COVERAGE_LADDER:
        rows = []
        for band in horizontal_bands(image, start, image.height, coverage=coverage):
            boxes = boxes_in_band(image, band)
            if boxes:
                rows.append([(left, band[0], right, band[1]) for left, right in boxes])
        if rows:
            return rows
    return []


def centre(box: tuple) -> tuple:
    """The middle of a ``(left, top, right, bottom)`` rectangle."""
    left, top, right, bottom = box
    return ((left + right) // 2, (top + bottom) // 2)


def band_buttons(image: Image, band_height: int) -> list:
    """The band's buttons: paper-coloured boxes on the profile-coloured strip.

    The inverse of :func:`boxes_in_band` -- up here the *interiors* are the
    signal and the surround is solid colour.
    """
    top, bottom = 6, max(10, band_height - 7)
    height = bottom - top
    columns = []
    for x in range(image.width):
        count = sum(1 for y in range(top, bottom) if _is_interior(image.pixel(x, y)))
        if count > 0.3 * height:
            columns.append(x)
    return [(left, top, right, bottom) for left, right in _group(columns, 3) if right - left > 20]
