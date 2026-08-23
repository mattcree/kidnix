"""A shelf -- one more level of Home, and only one (spec 7d #12).

The early-years teacher's blocker was that the "Letters & numbers" tile opened
GCompris' own 198-activity menu: *"18 detailed EYFS/KS1 mappings sit unreachable
behind a wall of everything else."* Wave C made the eighteen curated activities
into ordinary manifests in a subdirectory
(``docs/spikes/panel-wave-c.md`` section 2); this is the screen that draws them.

**It is not a second Home**, and the differences are the whole design:

* **One group to a page**, with the group's name written at the top and spoken
  when the page turns. Six groups of three beats one wall of eighteen: a
  pre-reader choosing between three pictures under a heading somebody read to
  them is making a choice, and choosing between eighteen is scanning.
* **The same tile metrics as Home** -- same size, same label box, same 20 mm
  floor -- so a tile does not change size when a child goes one level in. The
  page budget is :attr:`~kidnix_shell.metrics.Metrics.choice_per_page`, which is
  one row fewer than Home because this screen has a title and Home does not
  (the arithmetic for that already exists: ``Metrics.choice_size``).
* **No "All done" here.** The ending belongs to Home, which is one press away;
  putting a second one on a sub-screen would be two places to reach for the
  control a child reaches for when they have had enough, and 7d #5 pinned it to
  a cell precisely so it is only ever in one place.
* **Back goes Home**, never out of the session, and Back from an activity
  launched here comes back to the shelf.
* **No scrolling** (SYNTHESIS A4): the pager and nothing else.
"""

from __future__ import annotations

from functools import partial

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gtk  # noqa: E402

from ..activities import Activity, ShelfGroup, in_age_band, shelf_groups  # noqa: E402
from ..util import paginate  # noqa: E402
from ..widgets import (  # noqa: E402
    ActivityTile,
    Pager,
    big_label,
    carousel_page,
    page_label_fit,
    quiet_carousel,
)
from . import Screen  # noqa: E402
from .home import NOT_ALLOWED_LINE, NOT_READY_LINE  # noqa: E402


class ShelfScreen(Screen):
    """One shelf tile's children, a group to a page."""

    name = "Choose a game"

    def build(self) -> None:
        metrics = self.ctx.metrics
        self.set_margin_start(metrics.gap * 2)
        self.set_margin_end(metrics.gap * 2)
        self.set_margin_top(metrics.gap)

        #: Which shelf is open. Set by the host before the screen is entered.
        self.shelf: Activity | None = None
        self._groups: list[ShelfGroup] = []
        self._pages: list[Gtk.Widget] = []
        #: One heading per page, so turning a page can speak where it landed.
        self._page_groups: list[ShelfGroup] = []

        self.title = big_label("", "screen-title")
        self.title.set_margin_bottom(metrics.gap)
        self.append(self.title)

        self.carousel: Adw.Carousel = quiet_carousel()
        self.carousel.set_vexpand(True)
        self.append(self.carousel)

        self.pager = Pager(metrics, self.ctx.speech_ui, self._on_page, what="games")
        self.pager.set_margin_bottom(metrics.gap)
        self.append(self.pager)

    # -- content --

    def set_shelf(self, shelf: Activity | None) -> None:
        """Point the screen at a shelf. Rebuilding is left to ``on_enter``."""
        self.shelf = shelf

    def children(self) -> list[Activity]:
        """This shelf's children, filtered exactly as Home filters its tiles.

        **The age band applies to the children, not to the shelf**: the shelf
        spans its children's bands, and which of the eighteen a particular child
        sees is the children's own business (panel-wave-c section 2). The
        allow-list and availability leave the tile and outline it, as on Home --
        a child who saw a game yesterday and finds it dashed today is owed the
        reason (SYNTHESIS G3).
        """
        if self.shelf is None:
            return []
        band = self.ctx.profile.age_range
        children = self.ctx.shelves.get(self.shelf.id, [])
        return [child for child in children if child.on_home and in_age_band(child, band)]

    def refresh(self) -> None:
        for page in self._pages:
            self.carousel.remove(page)
        self._pages = []
        self._page_groups = []
        self.ctx.speech_ui.forget_all()

        shelf = self.shelf
        self._groups = shelf_groups(self.children(), default_name=shelf.name if shelf else "")
        for group in self._groups:
            # A group bigger than one page is split, and the heading is
            # repeated: a child who paged forward and lost "Counting" would
            # have no idea what they were looking at (the Journal does the
            # same, for the same reason).
            for cells in paginate(list(group.activities), self.ctx.metrics.choice_per_page):
                widget = self._grid(cells)
                self.carousel.append(widget)
                self._pages.append(widget)
                self._page_groups.append(group)
        self.pager.set_pages(len(self._pages), 0)
        self._show_heading(0)

    def _grid(self, cells: list[Activity]) -> Gtk.Widget:
        metrics = self.ctx.metrics
        grid = Gtk.Grid()
        grid.set_row_spacing(metrics.gap)
        grid.set_column_spacing(metrics.gap)
        grid.set_halign(Gtk.Align.CENTER)
        grid.set_valign(Gtk.Align.CENTER)

        # One type size for the page, from the longest name on it -- the same
        # rule Home uses, so a shelf page and a Home page read as one product.
        points, label_height = page_label_fit(
            [cell.name for cell in cells],
            metrics.tile_label_width,
            base_pt=metrics.tile_label_pt,
            floor_pt=metrics.label_floor_pt,
            height=metrics.tile_label_height,
            widget=grid,
        )
        for index, cell in enumerate(cells):
            denial = self._denial(cell)
            grid.attach(
                ActivityTile(
                    cell,
                    metrics,
                    self.ctx.speech_ui,
                    on_activate=partial(self._activate, cell),
                    allowed=denial is None,
                    denial=denial or NOT_ALLOWED_LINE,
                    label_points=points,
                    label_height=label_height,
                ),
                index % metrics.columns,
                index // metrics.columns,
                1,
                1,
            )
        return carousel_page(grid)

    def _denial(self, activity: Activity) -> str | None:
        """Why this game cannot be opened, in the child's words -- or None."""
        if not self.ctx.config.is_allowed(activity.id):
            return NOT_ALLOWED_LINE
        if not activity.usable:
            return NOT_READY_LINE
        return None

    def _activate(self, activity: Activity) -> None:
        denial = self._denial(activity)
        if denial is not None:
            self.ctx.speech.speak(denial)
            return
        # An ordinary launch. Nothing about being on a shelf changes what
        # happens next -- the shell remembers to come back here afterwards.
        self.ctx.host.launch(activity)

    # -- paging --

    def _on_page(self, page: int) -> None:
        if 0 <= page < len(self._pages):
            self.carousel.scroll_to(self._pages[page], True)
            self._show_heading(page, speak=True)

    def _show_heading(self, page: int, speak: bool = False) -> None:
        """Write the group's name, and say it when the page has just turned."""
        shelf = self.shelf
        if not (0 <= page < len(self._page_groups)):
            self.title.set_label(shelf.name if shelf else "")
            return
        group = self._page_groups[page]
        self.title.set_label(group.name)
        if speak:
            self.ctx.speech.speak(group.speak_text or group.name)

    # -- lifecycle --

    def on_enter(self) -> None:
        self.refresh()
        shelf = self.shelf
        if not self._pages:
            # Home does not draw a tile for an empty shelf, so this is only
            # reachable if the children vanished mid-session. Say something
            # true rather than showing a blank page.
            self.title.set_label(shelf.name if shelf else "")
            self.ctx.speech.speak("There's nothing here. Press Back to go home.")
            return
        first = self._page_groups[0]
        self.ctx.speech.speak(f"{shelf.name if shelf else 'Choose a game'}. {first.speak_text}.")

    def on_leave(self) -> None:
        # The heading is rebuilt on every arrival; nothing here outlives the
        # visit, which is what lets one screen serve every shelf.
        self.pager.set_pages(max(1, len(self._pages)), 0)
