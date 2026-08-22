"""S2 -- Home. The only root.

At most 12 tiles on a page in a 4 x 3 grid (08 section 3.2), each 160 design px
and never under 40 mm, with >= 12 mm gaps -- all of it shrunk together if the
panel is too small for the ideal (see :mod:`kidnix_shell.metrics`), and fewer
columns on a genuinely small screen rather than twelve unreadable tiles. More
activities than fit paginate with big arrows and page dots -- never scrolling
(SYNTHESIS A4).

A tile the child has used recently carries a small thumbnail of the last thing
they made there. A tile the parent has not allowed renders outline-only (never
greyed out) and says "Ask a grown-up for this one".

An activity whose program is **not installed** gets no tile at all by default:
a button that flickers and returns you to Home is worse than an absent one
(`docs/spikes/e2e-scenario.md` section 3.1). A manifest that would rather be
seen than hidden sets ``show_when_unavailable = true`` and gets the same
outline-only treatment with "This one isn't ready yet. Ask a grown-up."

**The last tile is always "All done"** (spec 7a, SYNTHESIS D5): a moon, one
tap, no confirmation, and the same ending ritual the clock would have run. A
child who has had enough must be able to say so, and saying so must not need a
grown-up, a hold, or a sentence they cannot read.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import partial

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gtk  # noqa: E402

from ..activities import Activity  # noqa: E402
from ..util import paginate  # noqa: E402
from ..widgets import (  # noqa: E402
    ActivityTile,
    Pager,
    carousel_page,
    page_label_fit,
    quiet_carousel,
)
from . import Screen  # noqa: E402

ALL_DONE_ID = "kidnix.all-done"

#: SYNTHESIS G3: never a silent denial. Two different reasons, two different
#: sentences -- a child told "ask a grown-up" about something that is simply
#: not installed would be sent to ask for something nobody can give them.
NOT_ALLOWED_LINE = "Ask a grown-up for this one."
NOT_READY_LINE = "This one isn't ready yet. Ask a grown-up."


@dataclass(frozen=True)
class AllDone:
    """The "I'm finished" tile, shaped like an activity so it lays out like one."""

    id: str = ALL_DONE_ID
    name: str = "All done"
    icon: str = "kidnix-moon"
    icon_kind: str = "icon-name"
    category: str = "make"
    speak_text: str = "All done for today?"


ALL_DONE = AllDone()

Cell = Activity | AllDone


class HomeScreen(Screen):
    name = "Home"

    def build(self) -> None:
        metrics = self.ctx.metrics
        self.set_margin_start(metrics.gap * 2)
        self.set_margin_end(metrics.gap * 2)
        self.set_margin_top(metrics.gap)

        self.carousel: Adw.Carousel = quiet_carousel()
        self.carousel.set_vexpand(True)
        self.append(self.carousel)

        self.pager = Pager(metrics, self.ctx.speech_ui, self._on_page, what="activities")
        self.pager.set_margin_bottom(metrics.gap)
        self.append(self.pager)

        self._pages: list[Gtk.Widget] = []
        self.refresh()

    # -- content --

    def cells(self) -> list[Cell]:
        """Everything on Home, in manifest ``order``. "All done" is last (spec 7a)."""
        shown = [a for a in self.ctx.activities if getattr(a, "on_home", True)]
        return [*shown, ALL_DONE]

    def refresh(self) -> None:
        """Rebuild the grid. Cheap enough to do on every arrival at Home."""
        for page in self._pages:
            self.carousel.remove(page)
        self._pages = []
        self.ctx.speech_ui.forget_all()

        metrics = self.ctx.metrics
        pages = paginate(self.cells(), metrics.per_page)
        for cells in pages:
            grid = self._grid(cells)
            self.carousel.append(grid)
            self._pages.append(grid)
        self.pager.set_pages(len(pages), 0)

    def _grid(self, cells: list[Cell]) -> Gtk.Widget:
        metrics = self.ctx.metrics
        grid = Gtk.Grid()
        grid.set_row_spacing(metrics.gap)
        grid.set_column_spacing(metrics.gap)
        grid.set_halign(Gtk.Align.CENTER)
        grid.set_valign(Gtk.Align.CENTER)

        # One type size for the whole page, taken from the name that has to
        # shrink most: a grid where "Draw" is 24 pt and "Letters & numbers" is
        # 18 pt reads as a mistake, not as a hierarchy.
        points, label_height = page_label_fit(
            [getattr(cell, "name", "") for cell in cells],
            metrics.tile_label_width,
            base_pt=metrics.tile_label_pt,
            floor_pt=metrics.label_floor_pt,
            height=metrics.tile_label_height,
            widget=grid,
        )
        for index, cell in enumerate(cells):
            grid.attach(
                self._tile(cell, points, label_height),
                index % metrics.columns,
                index // metrics.columns,
                1,
                1,
            )
        return carousel_page(grid)

    def _tile(
        self, cell: Cell, points: float | None = None, label_height: int | None = None
    ) -> Gtk.Widget:
        metrics = self.ctx.metrics
        if isinstance(cell, AllDone):
            return ActivityTile(
                cell,
                metrics,
                self.ctx.speech_ui,
                on_activate=self._all_done,
                extra_css=("all-done",),
                label_points=points,
                label_height=label_height,
            )
        denial = self._denial(cell)
        latest = self.ctx.journal.latest_for_activity(cell.id)
        return ActivityTile(
            cell,
            metrics,
            self.ctx.speech_ui,
            on_activate=partial(self._activate, cell),
            allowed=denial is None,
            denial=denial or NOT_ALLOWED_LINE,
            thumbnail=latest.thumbnail if latest is not None else None,
            label_points=points,
            label_height=label_height,
        )

    def _denial(self, activity: Activity) -> str | None:
        """Why this tile cannot be pressed, in the child's words -- or None."""
        if not self.ctx.config.is_allowed(activity.id):
            return NOT_ALLOWED_LINE
        if not getattr(activity, "available", True):
            return NOT_READY_LINE
        return None

    def _activate(self, activity: Activity) -> None:
        denial = self._denial(activity)
        if denial is not None:
            # SYNTHESIS G3: never a silent denial. v0.1 has no Ask queue yet,
            # so the honest thing is to say so and leave the child on Home.
            self.ctx.speech.speak(denial)
            return
        self.ctx.host.launch(activity)

    def _all_done(self) -> None:
        # One tap, no "are you sure?" (a pre-reader cannot read one, and asking
        # a child to confirm that they have had enough is a bribe to stay).
        # Back on the Put-away screen recovers an accidental tap.
        self.ctx.host.finish_now()

    def _on_page(self, page: int) -> None:
        if 0 <= page < len(self._pages):
            self.carousel.scroll_to(self._pages[page], True)

    def on_enter(self) -> None:
        self.refresh()
        self.ctx.speech.speak("Home. What shall we make?")
