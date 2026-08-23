"""Drawing the clock, and the arithmetic that turns a tap into a time.

Cairo, and **not** GTK. The distinction matters: ``cairo`` imports on a machine
with no display, so every line of the drawing is exercised by an ordinary
headless test that renders to an image surface and looks at the pixels, and the
same functions are handed the ``cairo.Context`` that ``Gtk.DrawingArea`` passes
its draw callback. One drawing, two callers, no second implementation to drift
-- which is the same reason the shell has exactly one sun
(``kidnix_shell/band.py``, panel ruling 2026-08-23) rather than three pictures
of one.

The picture is a **teaching clock**, and it looks like the ones on a Year 1
wall: a paper face, twelve numerals, a short fat hour hand and a long thin
minute hand. The two hands differ in length *and* width as well as colour,
because SYNTHESIS B6 says colour is never the sole carrier of anything -- a
child with CVD reads this clock off the geometry.

Every ring is stroked twice, ink inside and paper outside, for the reason
``kidnix_shell.sun`` states at length: the fill cannot carry WCAG 1.4.11
against four different grounds, so the **outline** does. Here the four grounds
are the four skies, and the night one is dark enough that an ink rim alone
would be 1.6:1 against it.
"""

from __future__ import annotations

import math
from pathlib import Path

import cairo

from .minute import (
    SUN_EDGE_INNER,
    SUN_EDGE_INNER_PX,
    SUN_EDGE_OUTER,
    SUN_EDGE_OUTER_PX,
    SUN_FILL,
    DiscGeometry,
)
from .routine import Sky
from .words import ClockTime, Mode

__all__ = [
    "CARD_SIZE",
    "FACE",
    "HOUR_HAND",
    "INK",
    "MINUTE_HAND",
    "PAPER",
    "SKY_COLOURS",
    "draw_dial",
    "draw_disc",
    "draw_ghost",
    "draw_sky",
    "hand_tip",
    "render_card",
    "rgb",
    "total_from_point",
]

# --- the palette, restated from theme.css ----------------------------------
#
# Restated as literals for the reason `kidnix_activity/activity.css` restates
# them: a value you cannot compute is a value nobody checked, and these are the
# numbers the contrast arithmetic in the tests is done against.

#: @kid-ink.
INK = "#16181d"
#: @kid-paper. The face, and the outer stroke on every ring.
PAPER = "#fbf7ef"
#: @kid-edge.
EDGE = "#7e838c"
#: @kid-primary. The long thin minute hand.
MINUTE_HAND = "#0f8a8a"
#: @kid-secondary. The short fat hour hand.
HOUR_HAND = "#f06292"
#: @kid-highlight. The mark the hands are sitting on.
FACE = PAPER

#: What is behind the clock, by time of day. A second, redundant channel for
#: the same fact the picture and the highlight already carry (B6), never the
#: only one. Night is dark enough to read as night and light enough that the
#: paper face still sits on it comfortably.
SKY_COLOURS: dict[Sky, tuple[str, str]] = {
    Sky.MORNING: ("#dcefff", "#f6e7c8"),
    Sky.AFTERNOON: ("#bfe3f2", "#e8f4de"),
    Sky.EVENING: ("#f6d0ac", "#e9a97f"),
    Sky.NIGHT: ("#2b3a5c", "#4a5680"),
}

#: The Journal card's PNG, square. Big enough to look like a picture behind the
#: shell's 256 px thumbnail and small enough that drawing one is instant.
CARD_SIZE = 512


def rgb(colour: str) -> tuple[float, float, float]:
    """``"#0f8a8a"`` -> ``(0.06, 0.54, 0.54)``."""
    text = colour.lstrip("#")
    return tuple(int(text[i : i + 2], 16) / 255.0 for i in (0, 2, 4))  # type: ignore[return-value]


# --- a tap on the rim -------------------------------------------------------


def total_from_point(dx: float, dy: float, current: ClockTime, mode: Mode) -> ClockTime:
    """Where the hands go when the child touches ``(dx, dy)`` from the centre.

    ``dx``/``dy`` are pixels from the middle of the face, y downwards. The
    angle gives a minute; the *hour* is whichever of the three candidates
    (this hour, the one before, the one after) leaves the hands nearest to
    where they already were. That is what makes tapping twelve from ten to
    four read as four o'clock rather than as three o'clock -- the hands take
    the short way round, as a hand pushed by a finger would.

    A tap on the exact centre, where there is no angle, leaves the clock alone.
    The result is always snapped: there is no near-miss on this rim
    (SYNTHESIS A5 -- the click-move-click route, with the move taken out).
    """
    if abs(dx) < 1e-9 and abs(dy) < 1e-9:
        return current
    # atan2 measured clockwise from twelve o'clock, which is up (-y).
    degrees = math.degrees(math.atan2(dx, -dy)) % 360.0
    minute = degrees / 6.0
    base = current.total - current.minute
    best, best_gap = current.total, 721.0
    # The hour we are already in first, then the one ahead, then the one
    # behind: a tie must not send the hands backwards. Pressing "half past"
    # from three o'clock is half past *three*, not half past two.
    for offset in (0, 60, -60):
        candidate = base + offset + minute
        gap = min((candidate - current.total) % 720, (current.total - candidate) % 720)
        if gap < best_gap:
            best, best_gap = candidate, gap
    return ClockTime(round(best) % 720).snapped(mode)


def hand_tip(centre: tuple[float, float], radius: float, degrees: float) -> tuple[float, float]:
    """The far end of a hand of length ``radius`` at ``degrees`` from twelve."""
    angle = math.radians(degrees - 90.0)
    return (centre[0] + radius * math.cos(angle), centre[1] + radius * math.sin(angle))


# --- drawing ----------------------------------------------------------------


def _ring(
    ctx: cairo.Context, cx: float, cy: float, radius: float, colour: str, width: float
) -> None:
    ctx.set_source_rgb(*rgb(colour))
    ctx.set_line_width(width)
    ctx.arc(cx, cy, max(0.5, radius), 0, 2 * math.pi)
    ctx.stroke()


def draw_sky(ctx: cairo.Context, width: float, height: float, sky: Sky) -> None:
    """The ground behind everything: a vertical wash, top colour to bottom.

    A gradient rather than a flat fill because the one thing a four-year-old
    reliably reads about a sky is that it is lighter near the ground at the
    ends of the day, and because a flat rectangle of colour reads as a *panel*
    -- a thing you press -- rather than as the weather.
    """
    top, bottom = SKY_COLOURS[sky]
    wash = cairo.LinearGradient(0, 0, 0, height)
    wash.add_color_stop_rgb(0.0, *rgb(top))
    wash.add_color_stop_rgb(1.0, *rgb(bottom))
    ctx.set_source(wash)
    ctx.rectangle(0, 0, width, height)
    ctx.fill()


def draw_dial(
    ctx: cairo.Context,
    width: float,
    height: float,
    clock: ClockTime,
    *,
    mode: Mode = Mode.Y1,
    scale: float = 0.92,
) -> float:
    """Draw the whole clock, centred, and return the radius it used.

    ``scale`` is the fraction of the shorter side the face fills. The default
    leaves the outer paper stroke somewhere to be without clipping it.
    """
    cx, cy = width / 2.0, height / 2.0
    radius = min(width, height) / 2.0 * scale
    if radius <= 2:
        return radius

    # The face, and the two rings that make it visible on any sky.
    ctx.set_source_rgb(*rgb(FACE))
    ctx.arc(cx, cy, radius, 0, 2 * math.pi)
    ctx.fill()
    _ring(ctx, cx, cy, radius, INK, radius * 0.035)
    _ring(ctx, cx, cy, radius + radius * 0.030, PAPER, radius * 0.026)

    _draw_marks(ctx, cx, cy, radius, mode)
    _draw_numerals(ctx, cx, cy, radius)
    _draw_hands(ctx, cx, cy, radius, clock)
    return radius


def _draw_marks(ctx: cairo.Context, cx: float, cy: float, radius: float, mode: Mode) -> None:
    """Twelve hour marks, always; sixty minute marks only in Year 2.

    A Year 1 face has nowhere on it that is not o'clock or half past, so the
    minute ticks would be sixty positions the child is not being asked about
    -- decoration that looks like information, which 05 section 2c
    (Kaminski & Sloutsky) is exactly the finding against.

    **ADR-0013** settles the other half of the same question. The twelve hour
    marks are a labelled grid whose items *are* the task -- the domain bounds
    them, not our taste -- so Year 2 keeps its twelve rim targets on them; the
    default year draws the twelve marks and offers nothing on the five-minute
    rim, neither a tick to look at nor a target to hear
    (:func:`clock_time.words.rim_targets`).
    """
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    if mode is Mode.Y2:
        ctx.set_source_rgb(*rgb(EDGE))
        ctx.set_line_width(max(1.0, radius * 0.012))
        for minute in range(60):
            if minute % 5 == 0:
                continue
            outer = hand_tip((cx, cy), radius * 0.90, minute * 6.0)
            inner = hand_tip((cx, cy), radius * 0.85, minute * 6.0)
            ctx.move_to(*inner)
            ctx.line_to(*outer)
            ctx.stroke()

    ctx.set_source_rgb(*rgb(INK))
    ctx.set_line_width(max(2.0, radius * 0.030))
    for hour in range(12):
        outer = hand_tip((cx, cy), radius * 0.92, hour * 30.0)
        inner = hand_tip((cx, cy), radius * 0.82, hour * 30.0)
        ctx.move_to(*inner)
        ctx.line_to(*outer)
        ctx.stroke()


def _draw_numerals(ctx: cairo.Context, cx: float, cy: float, radius: float) -> None:
    """One to twelve, in the face the shell sets child text in.

    The one place in kidnix a child is shown a digit on purpose. 01 #19 forbids
    digits *for quantities of time* -- "about as long as one story", never
    "twelve minutes" -- and reading the numerals on a clock face is the thing
    Year 1 is being taught. The voice still never says one.
    """
    ctx.select_font_face("Andika", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
    ctx.set_font_size(radius * 0.20)
    ctx.set_source_rgb(*rgb(INK))
    for hour in range(1, 13):
        text = str(hour)
        extents = ctx.text_extents(text)
        point = hand_tip((cx, cy), radius * 0.68, hour * 30.0)
        ctx.move_to(
            point[0] - extents.width / 2.0 - extents.x_bearing,
            point[1] - extents.height / 2.0 - extents.y_bearing,
        )
        ctx.show_text(text)


def _draw_hands(ctx: cairo.Context, cx: float, cy: float, radius: float, clock: ClockTime) -> None:
    """Short and fat for the hour, long and thin for the minute.

    Length and width first, colour second (SYNTHESIS B6). Both are stroked in
    ink underneath so a hand crossing a numeral still has an edge.
    """
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    ctx.set_line_join(cairo.LINE_JOIN_ROUND)

    for length, thickness, colour, degrees in (
        (0.52, 0.075, HOUR_HAND, clock.hour_angle),
        (0.80, 0.045, MINUTE_HAND, clock.minute_angle),
    ):
        tip = hand_tip((cx, cy), radius * length, degrees)
        tail = hand_tip((cx, cy), -radius * 0.10, degrees)
        for stroke_colour, extra in ((INK, radius * 0.022), (colour, 0.0)):
            ctx.set_source_rgb(*rgb(stroke_colour))
            ctx.set_line_width(radius * thickness + extra)
            ctx.move_to(*tail)
            ctx.line_to(*tip)
            ctx.stroke()

    # The pin. Drawn last so both hands run under it.
    ctx.set_source_rgb(*rgb(INK))
    ctx.arc(cx, cy, radius * 0.055, 0, 2 * math.pi)
    ctx.fill()
    ctx.set_source_rgb(*rgb(PAPER))
    ctx.arc(cx, cy, radius * 0.025, 0, 2 * math.pi)
    ctx.fill()


def _horizon(ctx: cairo.Context, width: float, geometry: DiscGeometry) -> None:
    """The line the disc sinks behind. Paper, solid: 3.91:1 on the worst sky."""
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    ctx.set_source_rgb(*rgb(SUN_EDGE_OUTER))
    ctx.set_line_width(4)
    ctx.move_to(width * 0.05, geometry.horizon_y)
    ctx.line_to(width * 0.95, geometry.horizon_y)
    ctx.stroke()


def draw_ghost(
    ctx: cairo.Context, width: float, height: float, geometry: DiscGeometry
) -> None:
    """A whole interval, outlined, with nothing inside it.

    What the minute screen shows while the **child** is doing the timing: the
    size the disc would be if none of it had gone, and the horizon it would
    sink to. It says what is being asked without answering it.
    """
    inner, outer = rgb(SUN_EDGE_INNER), rgb(SUN_EDGE_OUTER)
    for radius, colour, line in (
        (geometry.start_radius, outer, SUN_EDGE_OUTER_PX),
        (geometry.start_radius - SUN_EDGE_OUTER_PX, inner, SUN_EDGE_INNER_PX * 0.6),
    ):
        ctx.set_source_rgb(*colour)
        ctx.set_line_width(line)
        ctx.arc(geometry.centre_x, geometry.start_centre_y, max(0.5, radius), 0, 2 * math.pi)
        ctx.stroke()
    _horizon(ctx, width, geometry)


def draw_disc(
    ctx: cairo.Context,
    width: float,
    height: float,
    geometry: DiscGeometry,
    *,
    ghost: bool = True,
) -> None:
    """The sun, shrunk and sunk. The shell's own drawing, in an activity.

    ``ghost`` draws the outline of where it started, which is what makes the
    shrinking legible as a loss of quantity rather than as a picture that
    happens to be small today (``kidnix_shell/band.py``).
    """
    inner, outer = rgb(SUN_EDGE_INNER), rgb(SUN_EDGE_OUTER)

    def circle(centre_y: float, radius: float, colour: tuple[float, ...], line: float) -> None:
        ctx.set_source_rgb(*colour)
        ctx.set_line_width(line)
        ctx.arc(geometry.centre_x, centre_y, max(0.5, radius), 0, 2 * math.pi)
        ctx.stroke()

    if ghost:
        circle(geometry.start_centre_y, geometry.start_radius, outer, SUN_EDGE_OUTER_PX)
        circle(
            geometry.start_centre_y,
            geometry.start_radius - SUN_EDGE_OUTER_PX,
            inner,
            SUN_EDGE_INNER_PX * 0.6,
        )

    ctx.save()
    ctx.rectangle(0, 0, width, geometry.horizon_y)
    ctx.clip()
    ctx.set_source_rgb(*rgb(SUN_FILL))
    ctx.arc(geometry.centre_x, geometry.centre_y, geometry.radius, 0, 2 * math.pi)
    ctx.fill()
    circle(geometry.centre_y, geometry.radius, inner, SUN_EDGE_INNER_PX)
    circle(
        geometry.centre_y,
        geometry.radius + SUN_EDGE_INNER_PX / 2 + SUN_EDGE_OUTER_PX / 2,
        outer,
        SUN_EDGE_OUTER_PX,
    )
    ctx.restore()

    _horizon(ctx, width, geometry)


# --- the Journal card -------------------------------------------------------


def render_card(
    path: Path,
    clock: ClockTime,
    *,
    mode: Mode = Mode.Y1,
    sky: Sky = Sky.AFTERNOON,
    size: int = CARD_SIZE,
) -> Path:
    """Write the clock, on its sky, to ``path`` as a PNG. Returns the path.

    What ends up in My Things. The sky is in the picture because the card is
    the record of *what the child made the clock say*, and "half past five, in
    the evening" is a more honest record of an afternoon's play than a floating
    dial. The routine picture goes in beside it as the entry's second file.
    """
    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, size, size)
    ctx = cairo.Context(surface)
    draw_sky(ctx, size, size, sky)
    draw_dial(ctx, size, size, clock, mode=mode, scale=0.88)
    path.parent.mkdir(parents=True, exist_ok=True)
    surface.write_to_png(str(path))
    return path
