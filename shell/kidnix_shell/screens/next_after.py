"""S1b -- "What's next after?" (spec 7b, SYNTHESIS D4).

Between "Who's here?" and Home. Six to nine picture options; one tap picks one;
Goodbye shows it back and asks "Ready to go outside?".

This is the highest-value change in `09-gap-sweep-checkpoint-1.md`, and the
reason it is at the *start* of the session rather than the end is the whole
finding: in Coco's Videos (Hiniker et al., CHI 2018) the child chose the
offline activity **before** they began, and the ending then delivered their own
plan rather than removing something. Castillo et al. (2018) says why that
matters -- what makes a transition hurt is the destination thinning out, not
the announcement that it is coming.

Two things this screen must never become, both taken from the same paper's
failure mode (a child who "could not go to bed because Coco had not said 'Now
it's time for bed'"):

* it is **not a promise**. Nothing here binds the child or the family, and
  Goodbye asks rather than instructs;
* it is **not compulsory**. Back goes to Who's here (spec 7b: no exit friction
  anywhere), and a profile can turn the screen off entirely with
  ``skip_next_choice``.

Tiles are Home's tiles at Home's metrics, deliberately: the child has to learn
one target size, one label size, one gesture.
"""

from __future__ import annotations

from functools import partial

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gtk  # noqa: E402

from ..next_after import NextAfter  # noqa: E402
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

TITLE = "What's next after?"
#: Said once on arrival. Two short sentences, no digits, no obligation (01 #16).
INTRO = "What's next, after the computer? Pick one."


class NextAfterScreen(Screen):
    name = TITLE

    def build(self) -> None:
        metrics = self.ctx.metrics
        self.set_margin_start(metrics.gap * 2)
        self.set_margin_end(metrics.gap * 2)
        self.set_margin_top(metrics.gap)

        title = big_label(TITLE, "screen-title")
        self.append(title)

        self.carousel: Adw.Carousel = quiet_carousel()
        self.carousel.set_vexpand(True)
        self.append(self.carousel)

        self.pager = Pager(metrics, self.ctx.speech_ui, self._on_page, what="things")
        self.pager.set_margin_bottom(metrics.gap)
        self.append(self.pager)

        self._pages: list[Gtk.Widget] = []
        self.refresh()

    # -- content --

    def options(self) -> tuple[NextAfter, ...]:
        return self.ctx.config.next_after

    def refresh(self) -> None:
        for page in self._pages:
            self.carousel.remove(page)
        self._pages = []

        metrics = self.ctx.metrics
        # **A choice screen pages at ``choice_per_page``, not ``per_page``.**
        # Two reasons that turn out to be the same reason. SYNTHESIS B2 asks
        # for at most five options on a screen that asks a question, and this
        # one is Home *plus a 40 pt headline*, so a full Home-sized grid under
        # a title is the tallest thing in the shell -- it is what the content
        # window could not fit. One row fewer answers both.
        pages = paginate(list(self.options()), metrics.choice_per_page)
        for options in pages:
            grid = self._grid(options)
            self.carousel.append(grid)
            self._pages.append(grid)
        self.pager.set_pages(len(pages), 0)

    def _grid(self, options: list[NextAfter]) -> Gtk.Widget:
        metrics = self.ctx.metrics
        grid = Gtk.Grid()
        grid.set_row_spacing(metrics.gap)
        grid.set_column_spacing(metrics.gap)
        grid.set_halign(Gtk.Align.CENTER)
        grid.set_valign(Gtk.Align.CENTER)

        # One type size across the page, as on Home: a grid where one label is
        # 24 pt and its neighbour is 18 reads as a mistake, not as a hierarchy.
        points, label_height = page_label_fit(
            [option.label for option in options],
            metrics.tile_label_width,
            base_pt=metrics.tile_label_pt,
            floor_pt=metrics.label_floor_pt,
            height=metrics.tile_label_height,
            widget=grid,
        )
        for index, option in enumerate(options):
            tile = ActivityTile(
                option,
                metrics,
                self.ctx.speech_ui,
                on_activate=partial(self.ctx.host.choose_next_after, option),
                label_points=points,
                label_height=label_height,
            )
            grid.attach(tile, index % metrics.columns, index // metrics.columns, 1, 1)
        return carousel_page(grid)

    def _on_page(self, page: int) -> None:
        if 0 <= page < len(self._pages):
            self.carousel.scroll_to(self._pages[page], True)

    def on_enter(self) -> None:
        self.refresh()
        self.ctx.speech.speak(INTRO)
