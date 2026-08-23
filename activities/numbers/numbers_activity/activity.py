"""The window: a picture that flashes, a frame to fill, and a row of numerals.

Everything this activity *knows* is in the pure modules beside this one --
:mod:`~numbers_activity.arrange` (where the dots go),
:mod:`~numbers_activity.items` (what is asked and in what order),
:mod:`~numbers_activity.words` (everything that is said),
:mod:`~numbers_activity.keys` (what a key press meant),
:mod:`~numbers_activity.settings` (what a grown-up chose) and
:mod:`~numbers_activity.draw` (the pictures, in cairo). None of them imports
GTK; all of them are tested headless. This module is wiring, and wiring is the
part that needs a display.

The screen never changes shape
------------------------------

One prompt at the top, one picture in the middle, one row of numerals along the
bottom, item after item after item. The row of numerals is built **once** and
outlives every item: B1's spatial stability is not a nicety here, it is the
difference between a child who has learnt where the four is and a child who has
to search for it eight times in eight minutes. Only the middle changes.

What the SDK is doing underneath every control
----------------------------------------------

:class:`kidnix_shell.widgets.ChildButton` -- which is what a number tile and a
frame box both are underneath -- brings SYNTHESIS section 2A with it: every
mouse button does the same thing, the press fires on *press*, eight clicks a
second produce one action, and there is no double-click, right-click or
long-press anywhere in this activity because there is no code path here that
could add one. Sizes come from :class:`~kidnix_activity.metrics.ContentArea`, so
a numeral tile and a ten-frame box are both 20 mm of real panel on any monitor.

And what it deliberately does not do: no score, no star, no streak, no
"well done", no red, no countdown, no adaptive ladder, and no way out of its own
-- Back is the band's, one screen up, in every activity
(``docs/design/activity-sdk.md`` section 3.4).
"""

from __future__ import annotations

import argparse
import logging
import random
import tempfile
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
from gi.repository import Gdk, GLib, Gtk  # noqa: E402
from kidnix_activity.app import ActivityApplication, ActivityWindow  # noqa: E402
from kidnix_activity.journal import JournalError  # noqa: E402
from kidnix_activity.keyboard import ActivityKeyboard  # noqa: E402
from kidnix_activity.metrics import ContentArea  # noqa: E402
from kidnix_activity.widgets import BigButton, GrownUpTurn, Prompt  # noqa: E402
from kidnix_shell.sound import TAP  # noqa: E402
from kidnix_shell.widgets import ChildButton, SpeechUI, fit_gtk_label, next_key  # noqa: E402

from . import ACTIVITY_ID, TITLE  # noqa: E402
from .arrange import Arrangement  # noqa: E402
from .draw import (  # noqa: E402
    draw_arrangement,
    draw_bond_frame,
    draw_pattern,
    frame_geometry,
    render_card,
)
from .items import (  # noqa: E402
    HowMany,
    Item,
    MakeBond,
    Practised,
    Response,
    grownup_numbers,
    respond,
    session,
)
from .keys import number_for_keyval  # noqa: E402
from .settings import Frame, ParentSettings, load_settings  # noqa: E402
from .words import (  # noqa: E402
    bond_ask_again,
    bond_prompt,
    bond_sentence,
    count_aloud,
    end_line,
    grownup_body,
    grownup_title,
    how_many_prompt,
    look_again,
    numeral,
    tell_line,
    tile_speech,
    yes_line,
)

log = logging.getLogger(__name__)

__all__ = ["BondFrame", "DotCard", "NumberTile", "NumbersActivity", "main"]

#: Our own stylesheet, loaded after the shell's and the SDK's.
ACTIVITY_CSS = Path(__file__).parent / "activity.css"
#: The tile the shell draws on Home.
ICON = Path(__file__).parent / "icon.svg"
#: The picture on the "Again" button: an eye. No control here is text-only
#: (SDK section 12), and a pre-reader has to be able to find this one.
LOOK_ICON = Path(__file__).parent / "look.svg"

#: How long the picture stays up before it goes, in milliseconds.
#:
#: Long enough to see, short enough that counting one-by-one does not finish --
#: which is the entire mechanic. The quick-images teaching routine a Reception
#: teacher uses is a second or two of a card held up. There is no evidence for
#: an exact figure and this note says so; what there *is* evidence for is that
#: it must not become a speed test, which is why nothing is ever timed, nothing
#: is scored, and the child may press the "show me again" button as often as
#: they like.
FLASH_MS = 1600
#: Calm mode gets longer. Reduced motion is the setting, but a child who needs
#: the animation slowed needs the flash slowed too, and no child is worse off
#: for seeing the dots for another second.
FLASH_MS_CALM = 2600
#: Between one dot and the next while the voice counts them.
COUNT_MS = 620
#: After an answer, before the next item. A beat, so the sentence lands.
SETTLE_MS = 1500

#: Sizes the numeral row will try, in millimetres, largest first. The last is
#: ADR-0011's floor and the row never goes below it.
TILE_MM: tuple[float, ...] = (36.0, 30.0, 24.0, 20.0)
#: The frame gets at least this much of the content height. It is the subject.
STAGE_HEIGHT_FRACTION = 0.52

#: What the child hears when the save failed (SYNTHESIS C3).
LOST_LINE = "I could not keep that one. Ask a grown-up."
#: The button that brings the picture back. Not a hint and not a penalty: a
#: child who wants another look is doing the right thing.
AGAIN_LABEL = "Look"
#: The button at the end of the loop. Pressed, never automatic (D6: no autoplay).
MORE_LABEL = "Some more"


# -- the picture -------------------------------------------------------------


class DotCard(Gtk.DrawingArea):
    """The "how many?" picture, and the only thing on screen that moves.

    Three states, and no others: showing the arrangement, showing nothing, and
    revealing it one dot at a time while the voice counts. There is no
    transition, no fade and no bounce -- SYNTHESIS B7 allows two animated
    elements and this activity uses one of them, once, for a reason (counting is
    a *sequence*, and a sequence has to be seen happening).
    """

    def __init__(self, area: ContentArea) -> None:
        super().__init__()
        self.area = area
        self.arrangement: Arrangement | None = None
        self.revealed: int | None = None
        self.showing = False
        self.set_hexpand(True)
        self.set_vexpand(True)
        self.set_draw_func(self._draw)
        # A picture, not a control: the ring must not stop on it and a screen
        # reader must not announce it as something to press.
        self.set_accessible_role(Gtk.AccessibleRole.PRESENTATION)

    def show_arrangement(self, arrangement: Arrangement, *, revealed: int | None = None) -> None:
        self.arrangement = arrangement
        self.revealed = revealed
        self.showing = True
        self.queue_draw()

    def hide_arrangement(self) -> None:
        """The flash is over. The card stays; what was on it does not."""
        self.showing = False
        self.queue_draw()

    def reveal(self, count: int) -> None:
        self.revealed = count
        self.showing = True
        self.queue_draw()

    def _draw(self, _widget: Gtk.DrawingArea, ctx, width: int, height: int) -> None:
        if not self.showing or self.arrangement is None:
            return
        draw_arrangement(ctx, width, height, self.arrangement, revealed=self.revealed)


# -- the frame ---------------------------------------------------------------


class BondFrame(Gtk.Overlay):
    """A five- or ten-frame whose empty boxes are 20 mm targets.

    The drawing and the targets come from **one** set of numbers:
    :func:`~numbers_activity.draw.draw_bond_frame` returns where it put every
    box, and the boxes are placed from that. Two modules deriving the same
    geometry separately is how a counter comes to sit half in its box, and how a
    child comes to press a box and have nothing happen.

    Only the empty boxes of *this* number are controls. The counters that were
    already there are a picture -- pressing them would raise the question of
    what taking one away means, and this activity is about putting together. A
    counter the child placed **can** be pressed again to take it back, which is
    C1's recoverability at the only place in the activity where a slip is
    possible.
    """

    def __init__(
        self,
        area: ContentArea,
        item: MakeBond,
        *,
        on_change,
        speech=None,
        speech_ui: SpeechUI | None = None,
    ) -> None:
        super().__init__()
        self.area = area
        self.item = item
        self.frame: Frame = item.frame
        self.placed: set[int] = set()
        self._on_change = on_change

        self.canvas = Gtk.DrawingArea()
        self.canvas.set_hexpand(True)
        self.canvas.set_vexpand(True)
        self.canvas.set_draw_func(self._draw)
        self.canvas.set_accessible_role(Gtk.AccessibleRole.PRESENTATION)
        self.canvas.connect("resize", self._on_resize)
        self.set_child(self.canvas)

        self.boxes = Gtk.Fixed()
        self.add_overlay(self.boxes)
        self.set_measure_overlay(self.boxes, False)

        target = area.min_target
        self.targets: dict[int, ChildButton] = {}
        for index in range(item.shown, item.total):
            button = ChildButton(
                speak_text="Put a counter in.",
                on_activate=lambda i=index: self._pressed(i),
                speech_ui=speech_ui if speech_ui is not None else _ui_of(speech),
                css_classes=("box",),
                key=next_key("box"),
                size=target,
            )
            self.boxes.put(button, 0, 0)
            self.targets[index] = button

    # -- state --

    @property
    def added(self) -> int:
        return len(self.placed)

    def fill(self) -> None:
        """Put every missing counter in at once. What "told" looks like."""
        self.placed = set(range(self.item.shown, self.item.total))
        self._sync()

    def _pressed(self, index: int) -> None:
        if index in self.placed:
            self.placed.discard(index)
        else:
            self.placed.add(index)
        self._sync()
        self._on_change(self.added)

    def _sync(self) -> None:
        for index, button in self.targets.items():
            button.set_speak_text(
                "Take it out again." if index in self.placed else "Put a counter in."
            )
        self.canvas.queue_draw()

    # -- drawing, and the targets that follow it --

    def _draw(self, _widget: Gtk.DrawingArea, ctx, width: int, height: int) -> None:
        # One call, and the counters the child put in go where the finger went:
        # `placed` is a set of box indices, not a count.
        draw_bond_frame(
            ctx,
            width,
            height,
            self.frame,
            shown=self.item.shown,
            placed=self.placed,
            usable=self.item.total,
        )

    def _on_resize(self, _widget: Gtk.DrawingArea, width: int, height: int) -> None:
        x, y, cell = frame_geometry(width, height, self.frame)
        size = self.area.min_target
        for index, button in self.targets.items():
            row, column = divmod(index, self.frame.columns)
            centre_x = x + column * cell + cell / 2
            centre_y = y + row * cell + cell / 2
            self.boxes.move(button, int(centre_x - size / 2), int(centre_y - size / 2))


# -- a numeral ---------------------------------------------------------------


class NumberTile(ChildButton):
    """A big numeral with that many dots underneath it.

    B4 in one control: the **icon** is the quantity, the **label** is the
    numeral, the **audio** is the name of the number. A child who cannot read a
    four presses the tile with four dots; a child who is learning the numerals
    gets the symbol and the quantity in the same 36 mm every time they answer;
    and a grown-up who has set ``numerals = false`` gets the dots alone without
    anything else about the activity changing.
    """

    def __init__(
        self,
        number: int,
        area: ContentArea,
        *,
        numerals: bool = True,
        on_activate=None,
        speech=None,
        speech_ui: SpeechUI | None = None,
        size_mm: float = 36.0,
    ) -> None:
        size = area.target(size_mm)
        super().__init__(
            speak_text=tile_speech(number),
            on_activate=on_activate,
            speech_ui=speech_ui if speech_ui is not None else _ui_of(speech),
            css_classes=("big", "number-tile"),
            key=next_key("number"),
            size=size,
        )
        self.number = number
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        box.set_valign(Gtk.Align.CENTER)
        box.set_halign(Gtk.Align.CENTER)

        self.label: Gtk.Label | None = None
        if numerals:
            self.label = Gtk.Label()
            self.label.add_css_class("numeral")
            fit_gtk_label(
                self.label,
                numeral(number),
                width=max(24, size - 16),
                base_pt=area.points(38.0),
                floor_pt=area.points(24.0),
                max_lines=1,
            )
            box.append(self.label)

        self.pattern = Gtk.DrawingArea()
        inner = max(18, int(size * (0.42 if numerals else 0.78)))
        self.pattern.set_size_request(inner, inner)
        self.pattern.set_draw_func(
            lambda _w, ctx, width, height: draw_pattern(ctx, width, height, number)
        )
        self.pattern.set_accessible_role(Gtk.AccessibleRole.PRESENTATION)
        box.append(self.pattern)
        self.set_child(box)


# -- the keyboard ------------------------------------------------------------


class NumberKeys:
    """The digit keys, taken from the SDK's ring by composition rather than force.

    :class:`~kidnix_activity.keyboard.ActivityKeyboard` owns a capture-phase
    controller on the window and dispatches through its own ``key`` method, so
    this wraps *that method* on the instance rather than adding a second
    controller and hoping the two orders agree. There is one dispatcher, and the
    activity is in front of it.

    What it takes: ``1``-``9`` and ``0`` (which means ten). What it leaves: Tab,
    the arrows, Enter and Space, which still walk and press every control, so
    SYNTHESIS A6 is kept and nothing has become unreachable; and Escape, which
    is the shell's.
    """

    def __init__(self, keyboard: ActivityKeyboard, activity: NumbersActivity) -> None:
        self._inner = keyboard.key
        self._activity = activity
        keyboard.key = self.key  # type: ignore[method-assign]

    def key(self, keyval: int, shift: bool = False) -> bool:
        if not shift:
            number = number_for_keyval(keyval)
            if number is not None:
                self._activity.answer(number, from_key=True)
                return True
        return self._inner(keyval, shift)


# -- the activity ------------------------------------------------------------


class NumbersActivity:
    """The state, and the one screen it draws itself on."""

    def __init__(
        self,
        app: ActivityApplication,
        settings: ParentSettings | None = None,
        *,
        rng: random.Random | None = None,
        scratch: Path | None = None,
    ) -> None:
        self.app = app
        self.settings = settings if settings is not None else load_settings()
        log.info("settings: %s", self.settings.describe())
        self.rng = rng if rng is not None else random.Random()
        self.scratch = scratch if scratch is not None else Path(tempfile.mkdtemp(prefix="numbers-"))

        self.items: tuple[Item, ...] = session(self.settings, self.rng)
        self.index = 0
        self.attempts = 0
        self.practised = Practised()
        self.played = False
        self.finished = False

        self.window: ActivityWindow | None = None
        self.prompt: Prompt | None = None
        self.stage: Gtk.Box | None = None
        self.tiles: dict[int, NumberTile] = {}
        self.tile_row: Gtk.Widget | None = None
        self.card: DotCard | None = None
        self.frame: BondFrame | None = None
        self._timers: list[int] = []

    # -- what is being asked right now --

    @property
    def item(self) -> Item | None:
        if 0 <= self.index < len(self.items):
            return self.items[self.index]
        return None

    @property
    def flash_ms(self) -> int:
        return FLASH_MS_CALM if self.app.access.calm else FLASH_MS

    # -- building the screen --

    def build(self, window: ActivityWindow) -> None:
        self.window = window
        _load_css()
        NumberKeys(window.keys, self)
        area = window.area

        self.prompt = Prompt(how_many_prompt(), speech=window.speech, area=area)
        window.add(self.prompt)

        self.stage = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=area.gap)
        self.stage.set_vexpand(True)
        # A floor, not a fixed height: the picture is the subject of the screen
        # and takes whatever the prompt and the numerals leave, but never less
        # than this -- three targets' worth is the point below which a dice five
        # stops being a dice five.
        self.stage.set_size_request(-1, _stage_height(area))
        window.add(self.stage)

        self.tile_row = self._build_tiles(window)
        window.add(self.tile_row)

        self.start_item()

    def _build_tiles(self, window: ActivityWindow) -> Gtk.Widget:
        """The numerals. Built once, and the same row for the whole session."""
        area = window.area
        choices = self.settings.choices
        size_mm = _tile_mm(area, len(choices))
        grid = Gtk.Grid()
        grid.set_row_spacing(area.gap)
        grid.set_column_spacing(area.gap)
        grid.set_halign(Gtk.Align.CENTER)
        grid.add_css_class("number-row")

        columns = area.columns_for(cell=area.target(size_mm), count=len(choices))
        for position, number in enumerate(choices):
            tile = NumberTile(
                number,
                area,
                numerals=self.settings.numerals,
                on_activate=lambda n=number: self.answer(n),
                speech=window.speech,
                size_mm=size_mm,
            )
            self.tiles[number] = tile
            grid.attach(tile, position % columns, position // columns, 1, 1)
        return grid

    # -- one item --

    def start_item(self) -> None:
        """Put the next question on the screen. The only place ``index`` moves."""
        self._cancel_timers()
        self.attempts = 0
        item = self.item
        if item is None:
            self.end_loop()
            return
        if isinstance(item, HowMany):
            self._start_how_many(item)
        else:
            self._start_bond(item)

    def _start_how_many(self, item: HowMany) -> None:
        window = self.window
        if window is None or self.stage is None:
            return
        self._clear_stage()
        self.frame = None
        area = window.area

        # The picture and the way to see it again, side by side rather than
        # stacked: the card is the subject of the screen and every pixel a
        # button takes off its height is a pixel off the dots.
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=area.gap)
        row.set_vexpand(True)
        self.card = DotCard(area)
        row.append(self.card)
        again = BigButton(
            AGAIN_LABEL,
            icon=str(LOOK_ICON),
            icon_kind="path",
            speak_text="Show me the dots again.",
            on_activate=self.flash_again,
            speech=window.speech,
            area=area,
            size_mm=32.0,
            css_classes=("quiet",),
        )
        again.set_valign(Gtk.Align.CENTER)
        row.append(again)
        self.stage.append(row)
        self.card.show_arrangement(item.arrangement)
        self._refresh_ring()

        self._say(how_many_prompt())
        self._after(self.flash_ms, self._hide_card)

    def flash_again(self) -> None:
        """Another look. Free, unlimited, and not recorded anywhere.

        A child who asks to see it again is doing the thing the activity is for.
        Making that cost something -- a mark, a "hint used", a slower clock --
        would turn a practice into a test, which is the one thing the goal line
        in the manifest promises it is not.
        """
        item = self.item
        if not isinstance(item, HowMany) or self.card is None:
            return
        self._cancel_timers()
        self.card.show_arrangement(item.arrangement)
        self._after(self.flash_ms, self._hide_card)

    def _hide_card(self) -> None:
        if self.card is not None:
            self.card.hide_arrangement()

    def _start_bond(self, item: MakeBond) -> None:
        window = self.window
        if window is None or self.stage is None:
            return
        self._clear_stage()
        self.card = None
        self.frame = BondFrame(
            window.area, item, on_change=self._frame_changed, speech=window.speech
        )
        self.stage.append(self.frame)
        self._refresh_ring()
        self._say(bond_prompt(item.shown, item.total))

    def _frame_changed(self, added: int) -> None:
        """A counter went in or came out. Only "the frame is full" is an answer."""
        item = self.item
        if not isinstance(item, MakeBond):
            return
        self.played = True
        self.app.play(TAP)
        if added == item.missing:
            self._bond_done(item)

    def _bond_done(self, item: MakeBond) -> None:
        self._cancel_timers()
        self.practised.add_bond(item.bond)
        self._say(bond_sentence(*item.bond))
        self._after(SETTLE_MS, self.next_item)

    # -- answering --

    def answer(self, number: int, *, from_key: bool = False) -> None:
        """A numeral was pressed, or a digit key. The one door for both."""
        item = self.item
        if item is None:
            return
        if number not in self.settings.choices:
            # A key for a number this session does not offer. Say it rather than
            # doing nothing: a press that produces silence is a press a child
            # cannot learn anything from (SYNTHESIS A3, C4).
            self._say(tile_speech(number))
            return
        if from_key and number in self.tiles:
            self.tiles[number].fire()
            return
        self.played = True
        outcome = respond(item, number, self.attempts)
        if outcome is not Response.RIGHT:
            self.attempts += 1
        if isinstance(item, HowMany):
            self._answered_how_many(item, outcome)
        else:
            self._answered_bond(item, outcome)

    def _answered_how_many(self, item: HowMany, outcome: Response) -> None:
        self.practised.add_count(item.count)
        if outcome is Response.RIGHT:
            self._say(yes_line(item.count))
            self._after(SETTLE_MS, self.next_item)
            return
        # Not "wrong". The picture comes back and the dots get counted, which is
        # what a grown-up sitting beside them would do.
        self._say(look_again())
        self._after(COUNT_MS, lambda: self._count_out(item, outcome))

    def _count_out(self, item: HowMany, outcome: Response) -> None:
        """Reveal the dots one at a time while the voice counts them.

        One utterance, not one per dot: a new line cancels the old one in the
        SDK's voice (there is exactly one speech-dispatcher connection, by
        design), so counting dot by dot in speech would produce four cut-off
        syllables. The voice says the whole count; the picture is the half that
        happens one at a time.
        """
        if self.card is None:
            return
        self.card.reveal(0)
        self._say(count_aloud(item.count))
        for step in range(1, item.count + 1):
            self._after(COUNT_MS * step, lambda n=step: self._reveal(n))
        end = COUNT_MS * (item.count + 1)
        if outcome is Response.TOLD:
            self._after(end, lambda: self._told_how_many(item))
        else:
            self._after(end, lambda: self._say(how_many_prompt()))

    def _reveal(self, count: int) -> None:
        if self.card is not None:
            self.card.reveal(count)

    def _told_how_many(self, item: HowMany) -> None:
        self._say(tell_line(item.count))
        self._after(SETTLE_MS, self.next_item)

    def _answered_bond(self, item: MakeBond, outcome: Response) -> None:
        if outcome is Response.RIGHT:
            if self.frame is not None:
                self.frame.fill()
            self._bond_done(item)
            return
        if outcome is Response.TRY_AGAIN:
            self._say(bond_ask_again(item.total))
            return
        if self.frame is not None:
            self.frame.fill()
        self._bond_done(item)

    def next_item(self) -> None:
        self.index += 1
        self.start_item()

    # -- the end of the loop --

    def end_loop(self) -> None:
        """Eight items done. A card, a grown-up's turn, and a way to go again."""
        window = self.window
        if window is None or self.stage is None:
            return
        self._cancel_timers()
        self.finished = True
        self._clear_stage()
        self.card = None
        self.frame = None
        if self.tile_row is not None:
            # The numerals are not an answer to anything now. A control that
            # does nothing is worse than no control (C4).
            self.tile_row.set_visible(False)

        area = window.area
        number, total = grownup_numbers(self.items)
        turn = GrownUpTurn(
            grownup_body(number, total),
            title=grownup_title(),
            speech=window.speech,
            area=area,
        )
        self.stage.append(turn)

        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=area.gap)
        row.set_halign(Gtk.Align.CENTER)
        row.append(
            BigButton(
                MORE_LABEL,
                icon="kidnix-one-more",
                speak_text="Some more numbers.",
                on_activate=self.again,
                speech=window.speech,
                area=area,
            )
        )
        self.stage.append(row)
        self._refresh_ring()

        self._keep()
        if self.prompt is not None:
            self.prompt.set_text(end_line())
        self._say(end_line())
        turn.announce()

    def again(self) -> None:
        """Another eight, because the child asked. Never because we offered."""
        self.items = session(self.settings, self.rng)
        self.index = 0
        self.finished = False
        if self.tile_row is not None:
            self.tile_row.set_visible(True)
        self.start_item()

    # -- keeping it --

    def _keep(self) -> None:
        """Write the card of today's bonds into the Journal.

        Called at the end of the loop, and again on the way out for whatever has
        been done since. There is no "are you sure", no filename and no save
        button: continuous, silent, automatic keeping is C1, and the earcon the
        SDK plays is the whole of the notification.
        """
        if self.practised.empty:
            return
        caption = self.practised.caption()
        try:
            png = render_card(
                self.scratch / "numbers.png",
                tuple(self.practised.bonds),
                tuple(self.practised.counts),
            )
            entry = self.app.save_entry(
                "picture",
                [png],
                caption=caption,
                meta={
                    # What was practised. Not how it went: there is no outcome
                    # in this dictionary and there is not going to be one.
                    "bonds": [list(bond) for bond in self.practised.bonds],
                    "counts": list(self.practised.counts),
                    "range": self.settings.range.value,
                    "frames": self.settings.frames.value,
                },
            )
        except JournalError as exc:
            log.error("could not keep the numbers card: %s", exc)
            if self.window is not None:
                self.window.speak(LOST_LINE)
            return
        log.info("kept %s (%s)", entry.id, caption)
        self.practised.clear()

    def finish(self) -> None:
        """SIGTERM: keep whatever has not been kept, and say nothing about it.

        Only if they played. A card in My Things for a session in which nobody
        pressed anything would be a claim about a person that is not true.
        """
        self._cancel_timers()
        if not self.played:
            log.info("finishing: nothing was answered, so nothing is kept")
            return
        self._keep()

    # -- plumbing --

    def _say(self, line: str) -> None:
        if self.prompt is not None:
            self.prompt.set_text(line)
        if self.window is not None:
            self.window.speak(line)

    def _after(self, delay_ms: int, action) -> None:
        """One timer, remembered, so that leaving an item cancels it."""

        def fire() -> bool:
            if handle[0] in self._timers:
                self._timers.remove(handle[0])
            action()
            return GLib.SOURCE_REMOVE

        handle = [0]
        handle[0] = GLib.timeout_add(delay_ms, fire)
        self._timers.append(handle[0])

    def _cancel_timers(self) -> None:
        for timer in self._timers:
            GLib.source_remove(timer)
        self._timers.clear()

    def _clear_stage(self) -> None:
        if self.stage is None:
            return
        child = self.stage.get_first_child()
        while child is not None:
            following = child.get_next_sibling()
            self.stage.remove(child)
            child = following

    def _refresh_ring(self) -> None:
        if self.window is not None:
            self.window.keys.set_content(self.window.content)


# -- helpers -----------------------------------------------------------------


def _ui_of(speech):
    return getattr(speech, "ui", None)


def _stage_height(area: ContentArea) -> int:
    """At least half the content height for the picture. It is the subject."""
    if not area.known:
        return max(area.big_button * 3, 320)
    return max(area.min_target * 3, int(area.height * STAGE_HEIGHT_FRACTION))


def _tile_mm(area: ContentArea, count: int) -> float:
    """The largest tile size at which ``count`` numerals still fit across.

    Never returns less than the floor -- the last entry in :data:`TILE_MM` is
    ADR-0011's 20 mm, and a row that will not fit ten 20 mm tiles wraps onto a
    second line rather than shrinking them, because a target below the floor is
    not a target.
    """
    if not area.known:
        return TILE_MM[0] if count <= 5 else TILE_MM[2]
    for size_mm in TILE_MM:
        cell = area.target(size_mm)
        if (cell + area.gap) * count <= area.width + area.gap:
            return size_mm
    return TILE_MM[-1]


def _load_css() -> None:
    display = Gdk.Display.get_default()
    if display is None or not ACTIVITY_CSS.is_file():  # pragma: no cover
        return
    provider = Gtk.CssProvider()
    provider.load_from_path(str(ACTIVITY_CSS))
    Gtk.StyleContext.add_provider_for_display(
        display, provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION + 2
    )


# -- entry point -------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="kidnix-numbers", description=TITLE)
    parser.add_argument(
        "--screenshot",
        type=Path,
        help="write numbers-how-many.png and numbers-make-five.png here and exit",
    )
    parser.add_argument(
        "--seed",
        type=int,
        help="make the items reproducible (development and screenshots only)",
    )
    parser.add_argument(
        "--range",
        choices=("five", "ten"),
        help="override the grown-up's range for a development run",
    )
    args, rest = parser.parse_known_args(argv[1:] if argv else None)

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    settings = load_settings()
    if args.range is not None:
        from .settings import NumberRange

        settings = ParentSettings(
            range=NumberRange.parse(args.range),
            numerals=settings.numerals,
            frames=settings.frames,
            source=settings.source,
        )

    app = ActivityApplication(ACTIVITY_ID, TITLE)
    activity = NumbersActivity(
        app, settings, rng=random.Random(args.seed) if args.seed is not None else None
    )

    if args.screenshot is not None:
        from .screenshots import run_screenshots

        return run_screenshots(app, activity, args.screenshot)

    app.set_build(activity.build)
    app.set_on_finish(activity.finish)
    return app.run([argv[0] if argv else "kidnix-numbers", *rest])
