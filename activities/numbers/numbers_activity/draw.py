"""The drawing. Plain counters on plain paper, and nothing else.

This module is cairo and nothing else -- no GTK, no window, no display -- so
every picture in the activity is exercised by the headless tests, including the
one that ends up in the Journal.

**Why it is this plain.** 05 section 2c has a negative finding aimed exactly at
a program like this one: Kaminski & Sloutsky (2013) gave six-to-eight-year-olds
graphs made of countable pictures and found the children counted the pictures
and missed the structure -- "extraneous perceptual information substantially
attenuated learning". Carbonneau et al.'s meta-analysis of 55 manipulative
studies (N = 7,237) finds the same moderator. The synthesis writes the rule down
in four words: **ten-frames and plain counters, not cartoon cupcakes.** So a
counter here is a disc of one colour, the frame is a grid of thin boxes, and
there is not one decorative mark anywhere in this file.

**Colour is never the only difference** (SYNTHESIS B6 -- roughly 8% of boys are
colour-blind and most are undiagnosed). The counters that were already in the
frame are solid; the ones the child put there are rings. A child who sees no
difference in hue sees the difference in fill, and so does a photocopy.

The palette is the shell's, restated. The values are byte-identical to
``kidnix_shell/theme.css`` and a test re-reads that file and fails if they ever
drift.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from pathlib import Path

import cairo

from .arrange import Arrangement, dice, ten_frame
from .settings import FIVE_FRAME, TEN_FRAME, Frame
from .words import bond_sentence, number_word

__all__ = [
    "CARD_HEIGHT",
    "CARD_WIDTH",
    "EDGE",
    "GIVEN",
    "INK",
    "MINE",
    "PAPER",
    "PAPER_DIM",
    "draw_arrangement",
    "draw_bond_frame",
    "draw_counter",
    "draw_paper",
    "draw_pattern",
    "frame_geometry",
    "render_card",
]

#: ``@kid-ink``. The counters on a "how many?" card, and every line of text.
INK = (0x16 / 255, 0x18 / 255, 0x1D / 255)
#: ``@kid-paper``.
PAPER = (0xFB / 255, 0xF7 / 255, 0xEF / 255)
#: ``@kid-paper-dim``. A box that is in the frame but not in this number.
PAPER_DIM = (0xEF / 255, 0xE8 / 255, 0xDA / 255)
#: ``@kid-edge``. The lines of the frame.
EDGE = (0x7E / 255, 0x83 / 255, 0x8C / 255)
#: ``@kid-primary``. The counters that were already there.
GIVEN = (0x0F / 255, 0x8A / 255, 0x8A / 255)
#: ``@kid-secondary``. The counters the child put in.
MINE = (0xF0 / 255, 0x62 / 255, 0x92 / 255)

#: The Journal card. Landscape, because the bonds read as sentences.
CARD_WIDTH = 760
CARD_HEIGHT = 460

#: A counter's radius, as a fraction of the smaller side of the box it sits in.
COUNTER_FRACTION = 0.34
#: A scattered or dice counter's radius, as a fraction of the square it is in.
#: Big, deliberately: a counter is a *thing*, and four things a child can see
#: across a room is what subitising four is made of.
DOT_FRACTION = 0.11


def draw_paper(ctx: cairo.Context, width: float, height: float) -> None:
    """The ground. One flat colour: there is no gradient in this product."""
    ctx.save()
    ctx.set_source_rgb(*PAPER)
    ctx.rectangle(0, 0, width, height)
    ctx.fill()
    ctx.restore()


def _square(width: float, height: float, *, pad: float = 0.03) -> tuple[float, float, float]:
    """Fit the unit square into ``width`` x ``height``. ``(x, y, side)``."""
    side = max(1.0, min(width, height) * (1.0 - 2 * pad))
    return (width - side) / 2.0, (height - side) / 2.0, side


def frame_geometry(width: float, height: float, frame: Frame) -> tuple[float, float, float]:
    """Fit ``frame``'s boxes into the space. ``(x, y, cell)``, cells square.

    Public because the window places its 20 mm targets from exactly these
    numbers. Two modules working out where a box is separately is how a child
    comes to press a box and have nothing happen.
    """
    cell = max(
        4.0, min(width * 0.92 / frame.columns, height * 0.92 / frame.rows)
    )
    used_width = cell * frame.columns
    used_height = cell * frame.rows
    return (width - used_width) / 2.0, (height - used_height) / 2.0, cell


def draw_counter(
    ctx: cairo.Context, x: float, y: float, radius: float, colour, *, hollow: bool = False
) -> None:
    """One counter. ``hollow`` is a ring -- the ones the child put in."""
    ctx.save()
    ctx.arc(x, y, radius, 0, 6.283185307179586)
    if hollow:
        # The child's own counters. A ring rather than a disc, so that "the ones
        # I put in" survives greyscale, a photocopy and colour blindness.
        ctx.set_source_rgb(*PAPER)
        ctx.fill_preserve()
        ctx.set_source_rgb(*colour)
        ctx.set_line_width(max(2.0, radius * 0.34))
        ctx.stroke()
    else:
        ctx.set_source_rgb(*colour)
        ctx.fill()
    ctx.restore()


def _box(ctx: cairo.Context, x: float, y: float, size: float, *, dim: bool = False) -> None:
    inset = size * 0.06
    ctx.save()
    ctx.set_source_rgb(*(PAPER_DIM if dim else PAPER))
    ctx.rectangle(x + inset, y + inset, size - 2 * inset, size - 2 * inset)
    ctx.fill_preserve()
    ctx.set_source_rgb(*EDGE)
    ctx.set_line_width(max(1.5, size * 0.035))
    ctx.stroke()
    ctx.restore()


def draw_arrangement(
    ctx: cairo.Context,
    width: float,
    height: float,
    arrangement: Arrangement,
    *,
    revealed: int | None = None,
    colour=INK,
) -> None:
    """The "how many?" picture: the counters, and the frame if it has one.

    ``revealed`` draws only the first *n* counters. That is what the counting
    reveal uses after a wrong answer -- the dots come back one at a time while
    the voice counts them -- and it is the only animation in this activity.
    """
    shown = arrangement.count if revealed is None else max(0, min(arrangement.count, revealed))

    if arrangement.framed:
        x, y, cell = frame_geometry(width, height, Frame(arrangement.columns, arrangement.rows))
        for row in range(arrangement.rows):
            for column in range(arrangement.columns):
                _box(ctx, x + column * cell, y + row * cell, cell)
        radius = cell * COUNTER_FRACTION
        for px, py in arrangement.points[:shown]:
            draw_counter(
                ctx,
                x + px * cell * arrangement.columns,
                y + py * cell * arrangement.rows,
                radius,
                colour,
            )
        return

    x, y, side = _square(width, height)
    radius = side * DOT_FRACTION
    for px, py in arrangement.points[:shown]:
        draw_counter(ctx, x + px * side, y + py * side, radius, colour)


def draw_bond_frame(
    ctx: cairo.Context,
    width: float,
    height: float,
    frame: Frame,
    *,
    shown: int,
    added: int = 0,
    placed: Iterable[int] = (),
    usable: int = 0,
) -> list[tuple[float, float, float]]:
    """The "make five" frame, and where every box ended up.

    Returns one ``(x, y, size)`` per box in reading order, which is what the
    window puts its 20 mm targets on top of: the boxes are drawn once, here, and
    the pressable rectangles are placed from the same numbers rather than from a
    second set that could disagree with them.

    ``usable`` is how many boxes belong to *this* number. The rest -- the bottom
    row of a ten-frame during a bond to five, when a grown-up has asked for
    ten-frames throughout -- are drawn dim and are not targets.

    The child's own counters are given as ``placed``, a set of **box indices**
    rather than a count, because a counter goes where the finger went. ``added``
    is the shorthand the Journal card uses, where there was no finger and the
    missing counters simply follow on.
    """
    usable = usable or frame.capacity
    mine = set(placed) if placed else set(range(shown, shown + added))
    x, y, cell = frame_geometry(width, height, frame)
    radius = cell * COUNTER_FRACTION
    boxes: list[tuple[float, float, float]] = []
    for index in range(frame.capacity):
        row, column = divmod(index, frame.columns)
        bx, by = x + column * cell, y + row * cell
        _box(ctx, bx, by, cell, dim=index >= usable)
        if index < shown:
            draw_counter(ctx, bx + cell / 2, by + cell / 2, radius, GIVEN)
        elif index in mine:
            draw_counter(ctx, bx + cell / 2, by + cell / 2, radius, MINE, hollow=True)
        boxes.append((bx, by, cell))
    return boxes


def draw_pattern(ctx: cairo.Context, width: float, height: float, number: int) -> None:
    """The little quantity under the numeral on an answer tile.

    B4 wants a picture on every control, and for a number tile the honest
    picture is *that many things*. Up to six it is the dice face the child
    already knows; above six it is a small ten-frame, because a scatter of nine
    on a 20 mm tile is a smudge.
    """
    arrangement = dice(number) if number <= 5 else ten_frame(number)
    draw_arrangement(ctx, width, height, arrangement, colour=GIVEN)


# -- the Journal card --------------------------------------------------------


def _text(
    ctx: cairo.Context,
    line: str,
    x: float,
    y: float,
    size: float,
    *,
    colour=INK,
    bold: bool = False,
) -> None:
    ctx.save()
    ctx.select_font_face(
        "Andika",
        cairo.FONT_SLANT_NORMAL,
        cairo.FONT_WEIGHT_BOLD if bold else cairo.FONT_WEIGHT_NORMAL,
    )
    ctx.set_font_size(size)
    extents = ctx.text_extents(line)
    ctx.move_to(x - extents.width / 2 - extents.x_bearing, y)
    ctx.set_source_rgb(*colour)
    ctx.show_text(line)
    ctx.restore()


def render_card(
    path: Path,
    bonds: Sequence[tuple[int, int, int]],
    counts: Sequence[int] = (),
    *,
    width: int = CARD_WIDTH,
    height: int = CARD_HEIGHT,
) -> Path:
    """Write today's bonds to ``path`` as a PNG. Returns the path.

    What ends up in My Things, and the reason the activity has a Journal entry
    at all. It is a **record of what was practised**, drawn in the same
    ten-frames the child was just looking at, with the sentence under each one so
    that a grown-up reading over their shoulder has something to say back. There
    is no mark on it, no count of anything, and no date-stamped progress: F4's
    boring conventional artefact for an adult, and E1's "the reward is the thing
    you made".

    A session with no bonds in it still gets a card -- the quantities the child
    recognised, as dice faces -- because "we did the how-many one today" is
    still a true and useful thing for a card to say.
    """
    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, width, height)
    ctx = cairo.Context(surface)
    draw_paper(ctx, width, height)

    if bonds:
        _draw_bond_cards(ctx, width, height, bonds)
    else:
        _draw_count_cards(ctx, width, height, counts)

    path.parent.mkdir(parents=True, exist_ok=True)
    surface.write_to_png(str(path))
    return path


def _draw_bond_cards(
    ctx: cairo.Context, width: int, height: int, bonds: Sequence[tuple[int, int, int]]
) -> None:
    chosen = list(bonds)[:4]
    columns = 1 if len(chosen) == 1 else 2
    rows = 1 if len(chosen) <= 2 else 2
    cell_width = width / columns
    cell_height = height / rows
    caption = min(28.0, cell_height * 0.14)

    for index, (shown, missing, total) in enumerate(chosen):
        row, column = divmod(index, columns)
        ox, oy = column * cell_width, row * cell_height
        frame = FIVE_FRAME if total <= FIVE_FRAME.capacity else TEN_FRAME
        ctx.save()
        ctx.translate(ox, oy + cell_height * 0.06)
        draw_bond_frame(
            ctx,
            cell_width,
            cell_height * 0.62,
            frame,
            shown=shown,
            added=missing,
            usable=total,
        )
        ctx.restore()
        _text(
            ctx,
            bond_sentence(shown, missing, total)[:-1],
            ox + cell_width / 2,
            oy + cell_height * 0.86,
            caption,
        )


def _draw_count_cards(
    ctx: cairo.Context, width: int, height: int, counts: Sequence[int]
) -> None:
    chosen = list(counts)[:4] or [5]
    cell_width = width / len(chosen)
    caption = min(28.0, height * 0.09)
    for index, count in enumerate(chosen):
        ox = index * cell_width
        ctx.save()
        ctx.translate(ox, height * 0.04)
        draw_arrangement(
            ctx,
            cell_width,
            height * 0.66,
            dice(count) if count <= 5 else ten_frame(count),
            colour=GIVEN,
        )
        ctx.restore()
        _text(
            ctx,
            number_word(count),
            ox + cell_width / 2,
            height * 0.88,
            caption,
        )
