"""Fitting a child's label into the room there is, without ever cutting it.

A label a five-year-old cannot read is not a label. SYNTHESIS B4 asks for
icon + label + audio on every affordance, with the label at **>= 18 pt**;
v0.1.1 asked Pango to ellipsise instead, and the 1280x800 panel of the first
real boot put ``Letters & n...`` on the tile that says "Letters & numbers".
A pre-reader who is learning to match a shape to a word cannot match half a
word, and the child cannot widen the tile.

The rule this module implements, in order:

1. **Wrap, never cut.** Wrapping is word-then-character, centred, and
   ``ellipsize`` is ``NONE`` on everything a child looks at.
2. **Two lines is the budget.** The tile reserves two label lines in its own
   height (:attr:`kidnix_shell.metrics.Metrics.tile_label_height`), so a tile
   whose label wraps is exactly as big as one whose label does not and the
   grid never jumps between pages.
3. **Shrink before spilling.** A label too wide for two lines steps down in
   1 pt steps. Lines break *between words*: "Goodnig-ht" across two lines is
   a cut label wearing a hyphen, and a single long word shrinks to the floor
   before it is ever broken between characters.
4. **18 pt is the floor** (SYNTHESIS B4), scaled by the same ``fit`` factor as
   every other point size in the shell -- a panel we had to shrink to fit gets
   the scaled equivalent, not a label that no longer fits the tile.
5. **A third line is the last resort**, taken only when the floor still
   overflows, and it is the one case where the tile grows.

The measuring is pluggable. At runtime :mod:`kidnix_shell.widgets` hands in a
Pango-backed wrapper, so the answer is the one the screen will actually show.
The default is a pure-Python estimate of a humanist sans (Andika, falling back
to Cantarell), deliberately a few percent *wide*: it may say "that does not
fit" when Pango would have squeezed it in, and must never say the opposite.
That is what lets the headless tests prove the ten shipped manifest names fit
on every panel we ship for, on a machine with no display at all.

Everything here is pure Python. No GTK, no Pango, no display.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator
from dataclasses import dataclass

#: GTK renders a CSS ``pt`` at the *font* dpi (``gtk-xft-dpi``, i.e. 96 times
#: the desktop's text-scaling factor), not at the monitor's physical density.
#: kidnix never sets a text-scaling factor, so a point is 4/3 of a pixel on
#: every panel; the monitor's density reaches type through
#: :attr:`~kidnix_shell.metrics.Metrics.fit` instead.
FONT_DPI = 96.0

#: Line box as a multiple of the em. Andika is a tall face (ascent + descent
#: is about 1.42 em); Cantarell is 1.25. We budget for the taller one, because
#: budgeting for the shorter one is how two lines become three on the machine
#: that has the real font installed.
LINE_SPACING = 1.45

#: Everything the estimator measures is padded by this much. A label that the
#: estimate says fits must fit in Pango too, on a font we have not measured.
SAFETY = 1.05

#: Advance widths in ems for a humanist sans, from measuring the shipped face.
#: Coarse on purpose: this is a floor-planning tool, not a text engine.
_NARROW = "ijlI.,:;'!|`"
_WIDE = "mwMW"
_EM_WIDTHS: dict[str, float] = {
    **dict.fromkeys(_NARROW, 0.32),
    **dict.fromkeys(_WIDE, 0.92),
    **dict.fromkeys("frt", 0.38),
    **dict.fromkeys("0123456789", 0.57),
    " ": 0.28,
    "-": 0.36,
    "&": 0.72,
    "?": 0.50,
}
#: Anything not in the table: lowercase is about half an em, capitals more.
_EM_LOWER = 0.56
_EM_UPPER = 0.72


def em_width(text: str) -> float:
    """Width of ``text`` in ems, over-estimated a little on purpose."""
    total = 0.0
    for char in text:
        width = _EM_WIDTHS.get(char)
        if width is None:
            width = _EM_UPPER if char.isupper() else _EM_LOWER
        total += width
    return total * SAFETY


def px_per_point(font_dpi: float = FONT_DPI) -> float:
    return font_dpi / 72.0


def text_width_px(text: str, points: float, font_dpi: float = FONT_DPI) -> int:
    """How wide ``text`` is at ``points``, rounded up."""
    return _ceil(em_width(text) * points * px_per_point(font_dpi))


def line_height_px(points: float, font_dpi: float = FONT_DPI) -> int:
    """One line box at ``points``, rounded up."""
    return _ceil(points * px_per_point(font_dpi) * LINE_SPACING)


def approx_char_px(points: float, font_dpi: float = FONT_DPI) -> float:
    """A pessimistic average character, for ``Gtk.Label.set_max_width_chars``."""
    return max(1.0, _EM_UPPER * points * px_per_point(font_dpi))


def _ceil(value: float) -> int:
    return int(value) if value == int(value) else int(value) + 1


#: ``(lines, widest_line_px)`` for a piece of text at a point size and width.
Wrapper = Callable[[str, float, int], tuple[tuple[str, ...], int]]


def wrap_estimate(text: str, points: float, width: int) -> tuple[tuple[str, ...], int]:
    """Greedy word-then-character wrap, the way Pango's ``WORD_CHAR`` does it.

    Words are kept whole while they fit; a single word wider than the whole
    line is broken between characters rather than allowed to spill, because a
    tile that spills is a tile that gets clipped.
    """
    words = text.split()
    if not words:
        return ("",), 0

    lines: list[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}" if current else word
        if text_width_px(candidate, points) <= width:
            current = candidate
            continue
        if current:
            lines.append(current)
            current = ""
        if text_width_px(word, points) <= width:
            current = word
            continue
        # One word, wider than the line. Break it.
        chunk = ""
        for char in word:
            if chunk and text_width_px(chunk + char, points) > width:
                lines.append(chunk)
                chunk = char
            else:
                chunk += char
        current = chunk
    if current:
        lines.append(current)

    widest = max(text_width_px(line, points) for line in lines)
    return tuple(lines), widest


@dataclass(frozen=True)
class LabelFit:
    """What a label will look like: the lines, and the size they are set at."""

    text: str
    lines: tuple[str, ...]
    points: float
    width: int
    height: int
    #: False only when even the last resort overflows -- the label is still
    #: drawn whole (we never ellipsise), the caller has simply been warned.
    fits: bool

    @property
    def line_count(self) -> int:
        return len(self.lines)

    @property
    def ellipsised(self) -> bool:
        """Always False. Nothing in this module can produce a cut label."""
        return False


def keeps_words_whole(text: str, lines: tuple[str, ...]) -> bool:
    """True when the wrap broke only between words, never inside one.

    Pango's ``WORD_CHAR`` will happily split a word when the line is narrow,
    and "Goodnig-ht" across two lines is a cut label wearing a hyphen. A word
    is broken only when shrinking it to the floor still will not fit.
    """
    return " ".join(line.strip() for line in lines).split() == text.split()


def step_points(base_pt: float, floor_pt: float, step: float = 1.0) -> Iterator[float]:
    """``base``, ``base - 1``, ... down to and including ``floor``.

    Steps are at least 1 pt (spec: "in >= 1 pt steps"), and the floor is
    always tried exactly, however the arithmetic lands.
    """
    floor = min(base_pt, floor_pt)
    point = round(base_pt, 1)
    seen: set[float] = set()
    while point > floor:
        if point not in seen:
            seen.add(point)
            yield point
        point = round(point - step, 1)
    yield round(floor, 1)


def fit_label(
    text: str,
    width: int,
    *,
    base_pt: float,
    floor_pt: float,
    max_lines: int = 2,
    last_resort_lines: int = 3,
    height: int | None = None,
    wrap: Wrapper | None = None,
    line_height: Callable[[float], int] = line_height_px,
) -> LabelFit:
    """The largest size at which ``text`` fits ``width`` whole.

    Tries ``max_lines`` lines from ``base_pt`` down to ``floor_pt`` in 1 pt
    steps; only if none of those fit does it allow ``last_resort_lines``. The
    result is never ellipsised: when nothing fits, the floor is returned with
    ``fits=False`` and the caller (or the layout) gives it the room.
    """
    wrapper = wrap or wrap_estimate
    width = max(1, width)
    sizes = list(step_points(base_pt, floor_pt))

    def attempt(limit: int, box: int | None, whole_words: bool = True) -> LabelFit | None:
        for points in sizes:
            lines, widest = wrapper(text, points, width)
            tall = len(lines) * line_height(points)
            if len(lines) > limit or widest > width:
                continue
            if box is not None and tall > box:
                continue
            if whole_words and not keeps_words_whole(text, lines):
                continue
            return LabelFit(text, lines, points, widest, tall, True)
        return None

    # Two lines of whole words; then a smaller size; then a third line; and
    # only when a single word is wider than the tile at the floor do we let
    # Pango break it between characters.
    found = attempt(max_lines, height)
    if found is None:
        found = attempt(last_resort_lines, None)
    if found is None:
        found = attempt(last_resort_lines, None, whole_words=False)
    if found is not None:
        return found

    floor = round(min(base_pt, floor_pt), 1)
    lines, widest = wrapper(text, floor, width)
    return LabelFit(text, lines, floor, widest, len(lines) * line_height(floor), False)
