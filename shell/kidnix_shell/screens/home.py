"""S2 -- Home. The only root.

Up to 12 tiles on a page in a 4 x 3 grid (08 section 3.2), each 160 design px
and **never under 40 mm**, with >= 8 mm gaps. On a panel that cannot hold
twelve at that size the grid gives way, not the tile: 4 x 2, then 3 x 2, and
what does not fit paginates with big arrows and page dots -- never scrolling
(SYNTHESIS A4, and see :mod:`kidnix_shell.metrics`).

A tile the child has used recently carries a small thumbnail of the last thing
they made there.

Three reasons a tile may not be pressable, and they are deliberately not the
same treatment:

* **Outside the child's age band** (``age_min``/``age_max`` against the
  profile's ``age_band``) -- **no tile at all**. There is nothing to ask a
  grown-up for; the activity simply is not part of this child's computer
  (01 #35, SYNTHESIS B8).
* **Not on the parent's allow-list** (``allowed_activity_ids`` -- **this
  child's own**, and the machine's only when this child has none;
  parent-panel section 7.2) -- outline-only, never greyed out, and it says
  "Ask a grown-up for this one". This is SYNTHESIS G3's affordance and the
  reason the dashed border has to clear 3:1 contrast. Two siblings on one
  machine can therefore see the same tile with two different answers, which
  is the point: it is a tile the grown-up *can* give, to one of them.
* **Not installed, or installed with nothing to open** (``content_required``
  matched nothing) -- hidden by default, because a button that flickers and
  returns you to Home is worse than an absent one
  (`docs/spikes/e2e-scenario.md` section 3.1). A manifest that would rather be
  seen than hidden sets ``show_when_unavailable = true`` and gets the
  outline-only treatment with "This one isn't ready yet. Ask a grown-up." --
  a different sentence, because nobody can give a child a library with no
  books in it.

**"All done" has one cell and never leaves it** (spec 7a, SYNTHESIS D5, and the
panel ruling of 2026-08-23 -- see :data:`ALL_DONE_INDEX`): one tap, no
confirmation, and the same ending ritual the clock would have run. A child who
has had enough must be able to say so, and saying so must not need a grown-up,
a hold, a sentence they cannot read, or a second look at where the button went.

**And Back, on Home, points at it** (ADR-0014). Back here used to say "You're
home." -- true, and no use at all to a five-year-old who wants out, because it
names no action. It now says "To finish, press All done." and
:meth:`HomeScreen.spotlight_all_done` puts the reserved highlight on the tile
for two seconds, which is the only channel a pre-reader actually reads. The
tile does not move, nothing is confirmed, and no state changes: Back on Home
is still a no-op, it has just stopped being a dead end.

Its **picture** follows the clock the way its label already did (forum #17,
:mod:`kidnix_shell.resting`): a tidy-away box during the day, the moon only
inside the bedtime window. It carried the moon at every hour until 2026-08-23,
which put a sleep-onset cue on the one control a four-year-old presses at ten
in the morning -- and did it through the channel a pre-reader actually reads.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass, replace
from datetime import datetime
from functools import partial
from typing import TypeVar

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, GLib, Gtk  # noqa: E402

from ..activities import Activity, in_age_band  # noqa: E402
from ..i18n import N_, _  # noqa: E402
from ..resting import DAYTIME_GOODNIGHT_ICON, goodnight_icon  # noqa: E402
from ..settings import shelf_tile_allowed  # noqa: E402
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

T = TypeVar("T")

#: **Where "All done" lives, forever** (panel ruling, 2026-08-23). It used to
#: be *last in the list* -- ``[*revealed, ALL_DONE]`` -- so progressive
#: disclosure moved it one cell along every fortnight, until the allow-list ran
#: out. Three reviewers and a parent named the same harm (forum #5, #27, #40,
#: #41, #57): a child under seven reaches for a *cell*, not a picture, and this
#: is the control they reach for when they have had enough. "He does not find
#: that button by looking, he finds it by reaching, and it is the one control
#: he uses when he has had enough. Redrawing its position on a schedule he
#: cannot perceive is the worst possible thing to do to the escape hatch."
#:
#: So it is the last cell of the second row -- index 7 on the 4x2 grid and on
#: the 4x3 grid alike -- and the activities grow *around* it.
ALL_DONE_INDEX = 7


def all_done_index(per_page: int) -> int:
    """Which cell "All done" occupies on the first page.

    :data:`ALL_DONE_INDEX` wherever the page can hold it; the last cell of the
    page on the small grids that cannot (3x2 = six cells). Never off the page:
    an escape hatch on page two is not an escape hatch.
    """
    if per_page <= 0:
        return 0
    return min(ALL_DONE_INDEX, per_page - 1)


#: SYNTHESIS G3: never a silent denial. Two different reasons, two different
#: sentences -- a child told "ask a grown-up" about something that is simply
#: not installed would be sent to ask for something nobody can give them.
NOT_ALLOWED_LINE = N_("Ask a grown-up for this one.")
NOT_READY_LINE = N_("This one isn't ready yet. Ask a grown-up.")


#: What Home says on arrival. Not :attr:`Screen.intro`, because Home speaks it
#: after a refresh rather than before one.
HOME_INTRO = N_("Home. What shall we make?")

#: **How long the eye is drawn to "All done"** (ADR-0014). The same shape as
#: the band's arrival highlight (``theme.css`` ``button.offer.kid-new``): the
#: one reserved colour, for a couple of seconds, meaning "this one, now". Two
#: rather than the band's three because nothing is arriving -- the tile was
#: already there and the child is being shown *which* one it is.
SPOTLIGHT_SECONDS = 2
#: How faint the tile gets at the bottom of a breath, and how many steps a
#: breath takes. Stepped in Python rather than left to a CSS animation, for
#: the reason ``band._announce_offer_buttons`` gives: a transition only
#: advances while frames are drawn, and a control parked at "nearly invisible"
#: is the opposite of a spotlight. Every path here ends at full opacity.
SPOTLIGHT_DIM = 0.72
SPOTLIGHT_STEPS = 24


@dataclass(frozen=True)
class AllDone:
    """The "I'm finished" tile, shaped like an activity so it lays out like one."""

    id: str = ALL_DONE_ID
    #: Msgids. A frozen dataclass default is evaluated at import, so the
    #: translation happens in the two properties below.
    name_msgid: str = N_("All done")
    #: **Daytime by default, because most sessions end in daylight.** The moon
    #: is swapped in inside the bedtime window and nowhere else -- see
    #: :meth:`HomeScreen._tile` and :func:`kidnix_shell.resting.goodnight_icon`.
    icon: str = DAYTIME_GOODNIGHT_ICON
    icon_kind: str = "icon-name"
    category: str = "make"
    speak_msgid: str = N_("All done for today?")

    @property
    def name(self) -> str:
        return _(self.name_msgid)

    @property
    def speak_text(self) -> str:
        return _(self.speak_msgid)


ALL_DONE = AllDone()

#: ``None`` is an empty cell: the grid keeps the hole rather than closing it,
#: because closing it is what moved "All done".
Cell = Activity | AllDone | None


def lay_out(activities: Sequence[T], index: int) -> list[T | AllDone | None]:
    """Put the activities on the grid **around** "All done", which never moves.

    Pure, so ``tests/test_shell_bits.py`` can hold the invariant that matters:
    whatever is revealed, ``cells[index] is ALL_DONE``. Cells before it that
    have nothing to put in them stay empty; an activity that would have gone
    there goes after it instead. An empty cell costs a child nothing -- a
    control that moved costs them the one they reach for when they have had
    enough.
    """
    laid: list[T | AllDone | None] = [None] * index
    for position, activity in enumerate(activities[:index]):
        laid[position] = activity
    laid.append(ALL_DONE)
    laid.extend(activities[index:])
    return laid


class HomeScreen(Screen):
    name = N_("Home")

    def build(self) -> None:
        metrics = self.ctx.metrics
        self.set_margin_start(metrics.gap * 2)
        self.set_margin_end(metrics.gap * 2)
        self.set_margin_top(metrics.gap)

        self.carousel: Adw.Carousel = quiet_carousel()
        self.carousel.set_vexpand(True)
        self.append(self.carousel)

        self.pager = Pager(metrics, self.ctx.speech_ui, self._on_page, what=N_("activities"))
        self.pager.set_margin_bottom(metrics.gap)
        self.append(self.pager)

        self._pages: list[Gtk.Widget] = []
        #: The "All done" tile and the page it is on, so Back can point at it
        #: (ADR-0014). Re-found on every :meth:`refresh`, because the grid is
        #: rebuilt from scratch on every arrival at Home.
        self._all_done_tile: Gtk.Widget | None = None
        self._all_done_page = 0
        self._spotlight_handle: int | None = None
        self._spotlight_step = 0
        self.refresh()

    # -- content --

    def cells(self) -> list[Cell]:
        """Everything on Home, in manifest ``order``. "All done" is last (spec 7a).

        Two filters, and the difference between them is the point:

        * **Age band** removes the tile entirely. A four-year-old is not told
          that typed arithmetic exists and that they may not have it -- there
          is nothing there to ask about (01 #35, SYNTHESIS B8).
        * **Allow-list** and **unusable** leave the tile and outline it, because
          a child who has seen Draw every day and finds it dashed today needs
          to be told why (SYNTHESIS G3: never a silent denial).

        Then **progressive disclosure** (spec 7b, SYNTHESIS B2) -- which is
        **off unless a parent turns it on** since 2026-08-23. The argument for
        it ("a child meeting a computer should meet five things and be handed a
        sixth once those five are theirs") is a good one and it is not worth
        what it costs: a grid that grows on a schedule the child cannot
        perceive is an unannounced new button, and for an autistic five-year-old
        that is a ruined afternoon (forum #9, #26). ``show_everything`` now
        defaults to true; ``reveal_every_sessions`` applies only when a parent
        has opted in.
        """
        band = self.ctx.profile.age_range
        shown = [
            a
            for a in self.ctx.activities
            if getattr(a, "on_home", True) and in_age_band(a, band) and self._shelf_has_anything(a)
        ]
        return lay_out(self._revealed(shown), all_done_index(self.ctx.metrics.per_page))

    def _shelf_has_anything(self, activity: Activity) -> bool:
        """A shelf with nothing on it is not a tile (spec 7d #12).

        The same rule as an activity whose program is not installed, applied one
        level up: a tile that opens an empty screen is a tile that lies, and it
        costs a five-year-old a press and a page they cannot read. The children
        were loaded and age-filtered at start-up, so this is a dictionary
        lookup rather than a directory scan on every arrival at Home.
        """
        if not activity.is_shelf:
            return True
        band = self.ctx.profile.age_range
        children = self.ctx.shelves.get(activity.id, [])
        return any(child.on_home and in_age_band(child, band) for child in children)

    def _revealed(self, activities: list[Activity]) -> list[Activity]:
        """The prefix of ``activities`` this child has met. "All done" is free.

        The budget counts "All done" (it is a tile on the grid and it takes a
        tile's room), but "All done" is never the thing that gets cut: a child
        who has had enough must always be able to say so.
        """
        home = self.ctx.config.home
        budget = home.tiles_visible(len(activities) + 1, self.ctx.kid_state.sessions_completed)
        return activities[: max(0, budget - 1)]

    def refresh(self) -> None:
        """Rebuild the grid. Cheap enough to do on every arrival at Home."""
        self._end_spotlight()
        for page in self._pages:
            self.carousel.remove(page)
        self._pages = []
        self._all_done_tile = None
        self._all_done_page = 0
        self.ctx.speech_ui.forget_all()

        metrics = self.ctx.metrics
        pages = paginate(self.cells(), metrics.per_page)
        for number, cells in enumerate(pages):
            grid = self._grid(cells)
            if any(isinstance(cell, AllDone) for cell in cells):
                self._all_done_page = number
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
            [getattr(cell, "name", "") for cell in cells if cell is not None],
            metrics.tile_label_width,
            base_pt=metrics.tile_label_pt,
            floor_pt=metrics.label_floor_pt,
            height=metrics.tile_label_height,
            widget=grid,
        )
        for index, cell in enumerate(cells):
            if cell is None:
                # A reserved hole, so the cells after it keep their addresses.
                continue
            grid.attach(
                self._tile(cell, points, label_height),
                index % metrics.columns,
                index // metrics.columns,
                1,
                1,
            )
        return carousel_page(grid)

    def is_bedtime(self, now: datetime | None = None) -> bool:
        """Is the night vocabulary true right now?

        The same question Goodbye asks before it labels its own ending button
        (``screens/goodbye.py``), asked from the same place -- the session
        policy's ``[bedtime]`` window -- so the tile and the button can never
        disagree about what time of day it is.

        Answered ``False`` if there is no policy to ask. Daytime is the safe
        default of the two: a box where a moon belonged is a picture that is
        merely less apt, while a moon where a box belonged is the sleep-onset
        cue this whole switch exists to keep off an afternoon screen.
        """
        policy = getattr(getattr(self.ctx, "session", None), "policy", None)
        if policy is None:  # pragma: no cover - every real context has one
            return False
        return bool(policy.is_bedtime(now or datetime.now()))

    def all_done_cell(self, now: datetime | None = None) -> AllDone:
        """:data:`ALL_DONE` with the picture this hour of the day deserves.

        A *copy*, made at render time and thrown away with the tile.
        :data:`ALL_DONE` itself stays the one object :meth:`cells` pins into
        the grid, because ``cells[index] is ALL_DONE`` is the invariant that
        keeps the escape hatch where the child left it.
        """
        return replace(ALL_DONE, icon=goodnight_icon(bedtime=self.is_bedtime(now)))

    def _tile(
        self, cell: Activity | AllDone, points: float | None = None, label_height: int | None = None
    ) -> Gtk.Widget:
        metrics = self.ctx.metrics
        if isinstance(cell, AllDone):
            tile = ActivityTile(
                self.all_done_cell(),
                metrics,
                self.ctx.speech_ui,
                on_activate=self._all_done,
                extra_css=("all-done",),
                label_points=points,
                label_height=label_height,
            )
            self._all_done_tile = tile
            return tile
        denial = self._denial(cell)
        latest = self.ctx.journal.latest_for_activity(cell.id)
        return ActivityTile(
            cell,
            metrics,
            self.ctx.speech_ui,
            on_activate=partial(self._activate, cell),
            allowed=denial is None,
            denial=denial or _(NOT_ALLOWED_LINE),
            thumbnail=latest.thumbnail if latest is not None else None,
            label_points=points,
            label_height=label_height,
        )

    def _denial(self, activity: Activity) -> str | None:
        """Why this tile cannot be pressed, in the child's words -- or None.

        Two reasons, two sentences (SYNTHESIS G3). "Ask a grown-up" is only
        ever said about something a grown-up can actually give: a program that
        is not installed, or a Library with no books in it yet, is not that --
        so it gets the other line.
        """
        if not self._allowed(activity):
            return _(NOT_ALLOWED_LINE)
        if not getattr(activity, "usable", True):
            return _(NOT_READY_LINE)
        return None

    def _allowed(self, activity: Activity) -> bool:
        """The allow-list, read the way *Home* has to read it.

        One id for an ordinary tile. For a shelf's tile the list may name the
        shelf, or only something inside it -- and a door is allowed when
        anything behind it is (:func:`kidnix_shell.settings.shelf_tile_allowed`,
        which is where the rule and its reasons live).
        """
        config = self.ctx.config
        if config.is_allowed(activity.id, self.ctx.profile.id):
            return True
        children = self.ctx.shelves.get(activity.id, [])
        if not children:
            return False
        return shelf_tile_allowed(
            config.effective_allow_list(self.ctx.profile.id),
            activity.id,
            [child.id for child in children],
        )

    def _activate(self, activity: Activity) -> None:
        denial = self._denial(activity)
        if denial is not None:
            # SYNTHESIS G3: never a silent denial. v0.1 has no Ask queue yet,
            # so the honest thing is to say so and leave the child on Home.
            self.ctx.speech.speak(denial)
            return
        if activity.is_shelf:
            # A shelf opens a screen, not a program. Its ``exec`` is the
            # fallback for a shell that has not learned about shelves, and on
            # this one it is never run: for GCompris that argv *is* the
            # 198-activity menu the curation exists to close.
            self.ctx.host.open_shelf(activity)
            return
        self.ctx.host.launch(activity)

    def _all_done(self) -> None:
        # One tap, no "are you sure?" (a pre-reader cannot read one, and asking
        # a child to confirm that they have had enough is a bribe to stay).
        # Back on the Put-away screen recovers an accidental tap.
        self.ctx.host.finish_now()

    # -- Back, on Home: "To finish, press All done." (ADR-0014) --------

    def spotlight_all_done(self) -> bool:
        """Put the reserved highlight on the "All done" tile for a moment.

        The picture half of Back-on-Home. The sentence is the shell's
        (``app.TO_FINISH``); this is the part a child who cannot read it gets.

        Three rules, and each of them is somebody's ruling:

        * **the tile does not move** (spec 21.7, and the ruling behind
          :data:`ALL_DONE_INDEX`) -- the ring is drawn around where it already
          is, and nothing is scaled, raised or re-ordered;
        * **the page it is on is brought back**, because a ring on page two is
          not a spotlight. Paging Home is not a state change and Back has not
          navigated anywhere: the child is still on Home, looking at the first
          page of it, which is where "All done" has always lived;
        * **under calm mode, or a desktop with animations off, the ring is
          simply there** -- WCAG 2.2 SC 2.3.3, and the same rule the put-away
          flight follows.

        Returns whether there was a tile to point at, so a caller can tell
        "pointed" from "there is no Home built yet".
        """
        tile = self._all_done_tile
        if tile is None:  # pragma: no cover - Home always has this tile
            return False
        self._end_spotlight()
        tile.add_css_class("kid-new")
        animate = not self.ctx.reduced_motion
        if 0 <= self._all_done_page < len(self._pages):
            self.carousel.scroll_to(self._pages[self._all_done_page], animate)
            self.pager.set_pages(len(self._pages), self._all_done_page)
        if not animate:
            self._spotlight_handle = GLib.timeout_add_seconds(
                SPOTLIGHT_SECONDS, self._end_spotlight
            )
            return True
        self._spotlight_step = 0
        self._spotlight_handle = GLib.timeout_add(
            max(1, SPOTLIGHT_SECONDS * 1000 // SPOTLIGHT_STEPS), self._spotlight_breath
        )
        return True

    def _spotlight_breath(self) -> bool:
        """Two slow breaths of the tile's own opacity, then full and done."""
        self._spotlight_step += 1
        share = min(1.0, self._spotlight_step / SPOTLIGHT_STEPS)
        tile = self._all_done_tile
        if tile is not None:
            # Two full cycles across the whole spotlight, starting and ending
            # at 1.0: ``sin`` of a whole number of half-turns is zero at both
            # ends, so the tile never lands anywhere but full opacity.
            dip = math.sin(share * 2 * math.pi) ** 2
            tile.set_opacity(1.0 - (1.0 - SPOTLIGHT_DIM) * dip)
        if share >= 1.0:
            self._spotlight_handle = None
            self._end_spotlight()
            return False
        return True

    def _end_spotlight(self) -> bool:
        """Take the ring off and put the opacity back. Safe to call twice."""
        if self._spotlight_handle is not None:
            GLib.source_remove(self._spotlight_handle)
            self._spotlight_handle = None
        tile = self._all_done_tile
        if tile is not None:
            tile.remove_css_class("kid-new")
            tile.set_opacity(1.0)
        return False

    def on_leave(self) -> None:
        self._end_spotlight()

    def _on_page(self, page: int) -> None:
        if 0 <= page < len(self._pages):
            self.carousel.scroll_to(self._pages[page], True)

    def on_enter(self) -> None:
        self.refresh()
        self.ctx.speech.speak(_(HOME_INTRO))
