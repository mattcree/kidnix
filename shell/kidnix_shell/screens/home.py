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
from ..widgets import ActivityTile, Pager, carousel_page, quiet_carousel  # noqa: E402
from . import Screen  # noqa: E402

ALL_DONE_ID = "kidnix.all-done"


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
        """Everything on Home, in order. "All done" is always last (spec 7a)."""
        return [*self.ctx.activities, ALL_DONE]

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

        for index, cell in enumerate(cells):
            grid.attach(self._tile(cell), index % metrics.columns, index // metrics.columns, 1, 1)
        return carousel_page(grid)

    def _tile(self, cell: Cell) -> Gtk.Widget:
        metrics = self.ctx.metrics
        if isinstance(cell, AllDone):
            return ActivityTile(
                cell,
                metrics,
                self.ctx.speech_ui,
                on_activate=self._all_done,
                extra_css=("all-done",),
            )
        allowed = self.ctx.config.is_allowed(cell.id)
        latest = self.ctx.journal.latest_for_activity(cell.id)
        return ActivityTile(
            cell,
            metrics,
            self.ctx.speech_ui,
            on_activate=partial(self._activate, cell, allowed),
            allowed=allowed,
            thumbnail=latest.thumbnail if latest is not None else None,
        )

    def _activate(self, activity: Activity, allowed: bool) -> None:
        if not allowed:
            # SYNTHESIS G3: never a silent denial. v0.1 has no Ask queue yet,
            # so the honest thing is to say so and leave the child on Home.
            self.ctx.speech.speak("Ask a grown-up for this one.")
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
