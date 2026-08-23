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


#: How dark a pixel has to be to count as "nothing has been painted here".
#: The dimmest surface the shell ever draws is the bedtime Sleeping screen, and
#: that is a colour, not this: an unpainted framebuffer is 0,0,0 everywhere.
UNPAINTED_LEVEL = 16
#: How much of the frame has to be that dark before it is not a screenshot.
UNPAINTED_FRACTION = 0.995


def near_uniform_black(
    image: Image,
    *,
    level: int = UNPAINTED_LEVEL,
    fraction: float = UNPAINTED_FRACTION,
) -> bool:
    """Is this frame the framebuffer *before* anything drew into it?

    QEMU's ``screendump`` answers as soon as the request is queued and will
    happily hand back a frame the guest has not painted yet -- which is how the
    first screenshot of a run came back fully black while every assertion after
    it passed. That is a harness artefact, not a shell state, and telling the
    two apart is possible because nothing kidnix draws is *uniformly* black:
    even the bedtime screen is a colour, and every screen carries a band.
    """
    return dark_fraction(image, threshold=level) >= fraction


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


def colour_centroid(image: Image, box: tuple, predicate) -> tuple | None:
    """Centroid and pixel count of everything in ``box`` matching ``predicate``.

    ``predicate`` takes an ``(r, g, b)`` tuple. Used to find a control by its
    colour when it belongs to somebody else's toolkit and we have no other
    handle on it -- Tux Paint's green "Yes, I'm done!" tick, which is the only
    green thing on a white canvas.
    """
    left, top, right, bottom = _box(image, box)
    total_x = total_y = count = 0
    for y in range(top, bottom, 2):
        row = 3 * y * image.width
        for x in range(left, right, 2):
            offset = row + 3 * x
            if predicate((image.data[offset], image.data[offset + 1], image.data[offset + 2])):
                total_x += x
                total_y += y
                count += 1
    if count < 40:
        return None
    return (total_x // count, total_y // count, count)


def is_tuxpaint_green(pixel: tuple) -> bool:
    """Tux Paint's affirmative button fill: a soft green, on white paper."""
    red, green, blue = pixel
    return green > 150 and green > red + 35 and green > blue + 35


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


#: ``shell geometry ok: band 0,0 1280x92 (wanted 1280x92), content 0,92 ...``
GEOMETRY_RE = re.compile(
    r"shell geometry (?P<verdict>\w+): "
    r"band 0,0 (?P<bw>\d+)x(?P<bh>\d+) \(wanted (?P<wbw>\d+)x(?P<wbh>\d+)\), "
    r"content 0,(?P<cy>\d+) (?P<cw>\d+)x(?P<ch>\d+) \(wanted (?P<wcw>\d+)x(?P<wch>\d+)\)"
)


def shell_geometry(line: str) -> dict:
    """Parse the shell's own report of what the compositor gave its two windows.

    This is the line that would have caught the v0.1.5.0 regression on the
    first run: the band window came up 1280x708 in the *content* rectangle,
    above everything, with the content window invisible underneath it, and no
    pixel assertion in the scenario noticed because the screen was still full
    of shell-coloured pixels.
    """
    match = GEOMETRY_RE.search(line)
    if match is None:
        raise AssertionError(f"could not parse the shell's geometry line: {line!r}")
    parts = {key: int(value) for key, value in match.groupdict().items() if key != "verdict"}
    parts["verdict"] = match.group("verdict")  # type: ignore[assignment]
    return parts


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
    image: Image,
    top: int,
    bottom: int,
    coverage: float = 0.40,
    min_run: int = 120,
    lenient: bool = False,
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
        if lenient:
            # v0.1.6 paints a thick three-layer focus ring around the focused
            # control, which breaks the thin-top/thick-bottom asymmetry for
            # that one box (a single Journal card, say). Any edge run opens a
            # box; the next one closes it if the height is plausible.
            if opened is None:
                opened = start
            elif 40 <= end - opened <= 420:
                bands.append((opened, end))
                opened = None
            else:
                opened = start
            continue
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
    for lenient in (False, True):
        for coverage in COVERAGE_LADDER:
            rows = []
            for band in horizontal_bands(
                image, start, image.height, coverage=coverage, lenient=lenient
            ):
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
    # v0.1.6: the band *window* also holds the paper-coloured caption strip
    # under the control row. Stop at the first row that is paper almost all
    # the way across, or every column looks like a button interior at once.
    for y in range(top + 10, bottom):
        paper = sum(1 for x in range(0, image.width, 4) if _is_interior(image.pixel(x, y)))
        if paper > 0.9 * (image.width // 4):
            bottom = max(10, y - 4)
            break
    height = bottom - top
    columns = []
    for x in range(image.width):
        count = sum(1 for y in range(top, bottom) if _is_interior(image.pixel(x, y)))
        if count > 0.3 * height:
            columns.append(x)
    return [(left, top, right, bottom) for left, right in _group(columns, 3) if right - left > 20]


# --------------------------------------------------------------------------- #
# Finding two more things by colour, for tests/e2e/test_flows.py
# --------------------------------------------------------------------------- #


#: ``theme.css`` ``button.tile.all-done``: #e9e6f7 at rest, #f2f0fb hovered.
#: The only lavender on any kidnix surface, and the only tile whose *fill* is
#: not paper -- which is what makes "find All done" a colour question rather
#: than a grid-arithmetic one. Paper (#fbf7ef) has blue *below* red; the
#: highlight ring (#ffd23f) has blue far below both. Nothing else comes close.
def is_all_done_lavender(pixel: tuple) -> bool:
    red, green, blue = pixel
    return blue >= red + 7 and blue >= green + 7 and blue > 200 and red > 180


#: ``theme.css`` ``.kid-focus``: a 6 px ring of @kid-highlight, #ffd23f. The
#: shell paints it itself (it cannot use ``:focus-visible``, which stops
#: drawing on whichever of the two toplevels the compositor did not focus), so
#: in a screenshot it is the one saturated yellow on the screen -- and
#: therefore the only way to ask "where is the keyboard now?" from outside.
def is_focus_ring_yellow(pixel: tuple) -> bool:
    red, green, blue = pixel
    return red > 200 and 170 < green < 240 and blue < 130


#: ``Metrics.describe()``: ``band 97 px (row 70, captions 27, button 19.2 mm)``.
#: Older builds printed ``band 97 px (button 19.2 mm)`` and have no strip to
#: measure, which is why the caller gets ``None`` rather than a guess.
BAND_PARTS_RE = re.compile(r"\bband (\d+) px \(row (\d+), captions (\d+)")


def band_parts(metrics_line: str) -> tuple | None:
    """``(window, row, captions)`` from the shell's own metrics line, or None."""
    match = BAND_PARTS_RE.search(metrics_line)
    if match is None:
        return None
    return (int(match.group(1)), int(match.group(2)), int(match.group(3)))


def caption_strip_box(metrics_line: str, width: int) -> tuple | None:
    """The rows of the band *window* that carry the caption, inset a little.

    The strip is the bottom :attr:`Metrics.caption_height` of the band window
    (implementation notes 22.2): it is in the band window and not the content
    window precisely so that put-away and the ending offer are readable while
    an activity covers everything else. Inset by a few pixels either way so the
    strip's own 2 px top border is not mistaken for a letter.
    """
    parts = band_parts(metrics_line)
    if parts is None or parts[2] <= 6:
        return None
    _window, row, captions = parts
    return (12, row + 3, width - 12, row + captions - 2)
