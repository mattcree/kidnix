"""Millimetres, for the part of the screen an activity actually gets.

The shell sizes everything a child touches in millimetres, because a 40 mm tile
on a 1080p 14" panel is 25 mm on a 4K one and a five-year-old's finger does not
care about pixels (``kidnix_shell.metrics``). An activity inherits all of that
arithmetic -- the floors especially -- and changes exactly one thing about it:

**The band is not yours.** Since v0.1.5 the shell is two toplevels on one
application, and ``window-config.ini`` gives the band the strip at the top of
the monitor and everything else the rectangle underneath
(``0,band_height W x (H - band_height)``). An activity's window is placed by
the same catch-all rule, so what the compositor hands it is the content
rectangle and nothing more. A layout budgeted against the monitor's full height
fits on the developer's desktop and is clipped on the machine -- which is
exactly the v0.1.0 bug that put the shell's own band off the top of the first
real boot, wearing somebody else's hat.

So an activity never asks a :class:`~kidnix_shell.metrics.Metrics` for
``screen_height``. It asks a :class:`ContentArea`, which carries the panel's
metrics (for every millimetre, point and floor) *and* the width and height of
the rectangle below the band, and nothing else.

Why a wrapper rather than a shrunken ``Metrics``: ``Metrics.content_height``
already subtracts the band from ``screen_height``. A ``Metrics`` built with
``screen_height = content_height`` would subtract it **again**, so the second
question ("what am I given?") would quietly get a different answer from the
first. The wrapper cannot make that mistake, and
``test_activity_sdk_metrics.py`` pins it.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from kidnix_shell.metrics import (
    GAP_FLOOR_MM,
    MIN_GAP_MM,
    MIN_TARGET_MM,
    PRIMARY_TILE_MM,
    Metrics,
    detect_metrics,
)

__all__ = [
    "BIG_BUTTON_MM",
    "GAP_FLOOR_MM",
    "MIN_GAP_MM",
    "MIN_TARGET_MM",
    "PICTURE_TILE_MM",
    "PROMPT_PT",
    "ContentArea",
]

#: A primary control in an activity: the same 40 mm the shell's Home tile
#: prefers (ADR-0011 -- 20 mm minimum, 24 preferred, 40 for a primary target).
#: An activity's big button is a primary target by definition; it is usually
#: the only thing on the screen a child is meant to press.
BIG_BUTTON_MM = PRIMARY_TILE_MM

#: A picture the child chooses between. Smaller than a big button and larger
#: than the floor: there are several of them on a screen and each one is still
#: a target.
PICTURE_TILE_MM = 30.0

#: A spoken instruction line, in points. ``theme.css``'s ``.big-line`` is 34
#: and ``.quiet-line`` is 22; a prompt sits between them because it is the
#: sentence the activity is asking the child to act on, and it is floored at
#: 18 pt like every other child-facing size (SYNTHESIS B4).
PROMPT_PT = 26.0


@dataclass(frozen=True)
class ContentArea:
    """The rectangle an activity is given, plus the panel's own arithmetic.

    ``width``/``height`` are logical pixels. **Zero means unknown** -- a
    headless test, a build container, a compositor that reports no monitor --
    and every consumer here treats unknown as "do not constrain", exactly as
    :class:`kidnix_shell.metrics.Metrics` does with ``screen_height``.
    """

    metrics: Metrics
    width: int = 0
    height: int = 0

    # -- construction --

    @classmethod
    def from_panel(cls, panel: Metrics) -> ContentArea:
        """The content rectangle of a panel whose metrics we already have."""
        return cls(metrics=panel, width=max(0, panel.screen_width), height=panel.content_height)

    @classmethod
    def detect(cls, override: Any = None, *, captions: bool = True) -> ContentArea:
        """Measure the monitor, subtract the band, once, at start-up.

        ``captions`` must match the shell's ``[access] captions``, because the
        caption strip is part of the band *window* and therefore of what is
        taken off the top. It defaults to True, which is what the shell ships,
        and erring that way costs an activity one strip of height rather than
        overrunning the rectangle it was given.
        """
        return cls.from_panel(detect_metrics(override, captions=captions))

    # -- what the rectangle is --

    @property
    def known(self) -> bool:
        """Do we know how big we are? False on a headless run."""
        return self.width > 0 and self.height > 0

    @property
    def band_height(self) -> int:
        """What the shell took off the top, band plus caption strip.

        An activity has no business drawing there and no way to reach it. It is
        exposed for one reason: a layout that overflows should be able to say
        *by how much and against what* in its own log line.
        """
        return self.metrics.band_window_height

    def fits(self, width: int, height: int) -> bool:
        """Would a tree this size fit in what we were given?"""
        if not self.known:
            return True
        return width <= self.width and height <= self.height

    def columns_for(self, cell: int, count: int, *, gap: int | None = None) -> int:
        """How many cells of ``cell`` px fit across, capped at ``count``.

        The one piece of layout arithmetic every activity repeats: a row of
        pictures, a row of sound buttons, a row of choices. Never returns less
        than one -- a screen too narrow for a single target has already failed
        a floor somewhere else, and returning zero would only turn that into a
        division by zero here.
        """
        count = max(0, count)
        if count == 0:
            return 0
        if not self.known:
            return count
        spacing = self.gap if gap is None else gap
        across = (self.width + spacing) // max(1, cell + spacing)
        return max(1, min(count, int(across)))

    # -- millimetres, points and floors (delegated, deliberately) --

    def mm(self, millimetres: float) -> int:
        """A *preferred* size in millimetres, in logical pixels."""
        return self.metrics.mm(millimetres)

    def mm_floor(self, millimetres: float) -> int:
        """A **floor** in millimetres. Nothing shrinks these."""
        return self.metrics.mm_floor(millimetres)

    def mm_of(self, pixels: float) -> float:
        """How many real millimetres ``pixels`` covers. What a test asserts on."""
        return self.metrics.mm_of(pixels)

    def target(self, millimetres: float = BIG_BUTTON_MM) -> int:
        """Something the child touches: preferred, never below the 20 mm floor."""
        return self.metrics.target_mm(millimetres)

    @property
    def min_target(self) -> int:
        """**The floor.** 20 mm of real panel (ADR-0011)."""
        return self.metrics.min_target

    @property
    def big_button(self) -> int:
        """A primary control: 40 mm, floored."""
        return self.target(BIG_BUTTON_MM)

    @property
    def picture_tile(self) -> int:
        """One of several pictures to choose between: 30 mm, floored."""
        return self.target(PICTURE_TILE_MM)

    @property
    def gap(self) -> int:
        """Dead space between two targets: 12 mm preferred, **8 mm floor**."""
        return self.metrics.gap

    @property
    def margin(self) -> int:
        """The margin around the activity's own content. The same gap."""
        return self.gap

    def points(self, base_pt: float) -> float:
        """A point size for text a **child** reads: 18 pt floor, always."""
        return self.metrics.child_points(base_pt)

    @property
    def prompt_points(self) -> float:
        """What a spoken instruction line is set at."""
        return self.points(PROMPT_PT)

    def line_height(self, points: float) -> int:
        """One line box at ``points``, at the density GTK really draws text at."""
        return self.metrics.line_height(points)

    def describe(self) -> str:
        """One line for the log at start-up. Every number that can bite."""
        return (
            f"content {self.width}x{self.height} px "
            f"(band {self.band_height} px) "
            f"target {self.min_target} px = {self.mm_of(self.min_target):.1f} mm, "
            f"big {self.big_button} px = {self.mm_of(self.big_button):.1f} mm, "
            f"gap {self.gap} px = {self.mm_of(self.gap):.1f} mm, "
            f"prompt {self.prompt_points:.0f} pt"
        )
