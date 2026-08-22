"""S2 -- Home. The only root.

At most 12 tiles on a page in a 4 x 3 grid (08 section 3.2), each 160 design px
and never under 40 mm, with >= 12 mm gaps. More than 12 installed activities
paginate with big arrows and page dots -- never scrolling (SYNTHESIS A4).

A tile the child has used recently carries a small thumbnail of the last thing
they made there. A tile the parent has not allowed renders outline-only (never
greyed out) and says "Ask a grown-up for this one".
"""

from __future__ import annotations

from functools import partial

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gtk  # noqa: E402

from ..activities import Activity  # noqa: E402
from ..util import paginate  # noqa: E402
from ..widgets import ActivityTile, Pager, quiet_carousel  # noqa: E402
from . import Screen  # noqa: E402

COLUMNS = 4
ROWS = 3
PER_PAGE = COLUMNS * ROWS  # 12 (spec S2)


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

    def refresh(self) -> None:
        """Rebuild the grid. Cheap enough to do on every arrival at Home."""
        for page in self._pages:
            self.carousel.remove(page)
        self._pages = []
        self.ctx.speech_ui.forget_all()

        pages = paginate(list(self.ctx.activities), PER_PAGE)
        for activities in pages:
            grid = self._grid(activities)
            self.carousel.append(grid)
            self._pages.append(grid)
        self.pager.set_pages(len(pages), 0)

    def _grid(self, activities: list[Activity]) -> Gtk.Widget:
        metrics = self.ctx.metrics
        grid = Gtk.Grid()
        grid.set_row_spacing(metrics.gap)
        grid.set_column_spacing(metrics.gap)
        grid.set_halign(Gtk.Align.CENTER)
        grid.set_valign(Gtk.Align.CENTER)

        for index, activity in enumerate(activities):
            allowed = self.ctx.config.is_allowed(activity.id)
            latest = self.ctx.journal.latest_for_activity(activity.id)
            tile = ActivityTile(
                activity,
                metrics,
                self.ctx.speech_ui,
                on_activate=partial(self._activate, activity, allowed),
                allowed=allowed,
                thumbnail=latest.thumbnail if latest is not None else None,
            )
            grid.attach(tile, index % COLUMNS, index // COLUMNS, 1, 1)
        return grid

    def _activate(self, activity: Activity, allowed: bool) -> None:
        if not allowed:
            # SYNTHESIS G3: never a silent denial. v0.1 has no Ask queue yet,
            # so the honest thing is to say so and leave the child on Home.
            self.ctx.speech.speak("Ask a grown-up for this one.")
            return
        self.ctx.host.launch(activity)

    def _on_page(self, page: int) -> None:
        if 0 <= page < len(self._pages):
            self.carousel.scroll_to(self._pages[page], True)

    def on_enter(self) -> None:
        self.refresh()
        self.ctx.speech.speak("Home. What shall we make?")
