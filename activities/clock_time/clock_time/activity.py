"""The window: the clock you play with, and the minute you can see.

Everything this activity *knows* is in the pure modules beside this one --
:mod:`~clock_time.words` (what the hands are showing), :mod:`~clock_time.dial`
(where a tap lands, and the drawing), :mod:`~clock_time.routine` (what happens
when), :mod:`~clock_time.minute` (how a guess went), :mod:`~clock_time.keys`
(what a key press meant). None of them imports GTK; all of them are tested
headless. This module is wiring, and wiring is the part that needs a display.

What the SDK is doing underneath every control here
---------------------------------------------------

:class:`~kidnix_activity.widgets.BigButton`,
:class:`~kidnix_activity.widgets.PictureTile` and
:class:`kidnix_shell.widgets.ChildButton` bring SYNTHESIS section 2A with them:
every mouse button does the same thing, the press fires on *press*, eight
clicks a second produce one action, and there is no double-click, right-click
or long-press anywhere. Sizes come from
:class:`~kidnix_activity.metrics.ContentArea`, so a rim target is 20 mm of real
panel on any monitor.

The one input this activity has that the SDK has no widget for is **the face**,
and it is built to A5's rule rather than around it: the hands can be dragged,
but they never *have* to be, because every position they can take is also a
20 mm target you press once, and because the arrow keys step round the rim.
Drag is the third route, not the first.

And what it deliberately does not do: no score, no star, no streak, no
"well done", no red, no pulse, no countdown with anything at stake, and no way
out of its own -- Back is the band's, one screen up, in every activity
(``docs/design/activity-sdk.md`` section 3.4).
"""

from __future__ import annotations

import argparse
import logging
import math
import tempfile
import time
from collections.abc import Callable
from datetime import datetime
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
from gi.repository import Gdk, GLib, Gtk  # noqa: E402
from kidnix_activity.app import ActivityApplication, ActivityWindow  # noqa: E402
from kidnix_activity.journal import JournalError  # noqa: E402
from kidnix_activity.keyboard import ActivityKeyboard  # noqa: E402
from kidnix_activity.metrics import ContentArea  # noqa: E402
from kidnix_activity.widgets import BigButton, GrownUpTurn, PictureTile, Prompt  # noqa: E402
from kidnix_shell.widgets import ChildButton, fit_gtk_label, next_key  # noqa: E402

from . import ACTIVITY_ID, TITLE  # noqa: E402
from .dial import (  # noqa: E402
    draw_dial,
    draw_disc,
    draw_ghost,
    draw_sky,
    render_card,
    total_from_point,
)
from .keys import Action, Screen, action_for_keyval  # noqa: E402
from .minute import LENGTHS, Length, Phase, disc_geometry, verdict_for  # noqa: E402
from .pictures import picture_for, picture_path  # noqa: E402
from .routine import Routine, RoutineItem, Sky  # noqa: E402
from .settings import ParentSettings, load_settings  # noqa: E402
from .words import ClockTime, Mode, grid_for, minute_words  # noqa: E402

log = logging.getLogger(__name__)

__all__ = ["ClockActivity", "ClockFace", "Disc", "main"]

#: Our own stylesheet, loaded after the shell's and the SDK's.
ACTIVITY_CSS = Path(__file__).parent / "activity.css"
#: The tile the shell draws on Home, and the picture on the Now button.
ICON = Path(__file__).parent / "icon.svg"

#: The brief's floor for the face: at least this much of the content height.
#: It is the subject of the activity, so it gets the room.
FACE_HEIGHT_FRACTION = 0.60
#: How far out the rim targets sit, as a fraction of the drawn radius -- on
#: the tick marks, outside the numerals, so a finger does not cover the number
#: it is aiming at.
RIM_FRACTION = 0.85
#: The three action buttons on the minute screen. Smaller than a 40 mm primary
#: target on purpose: there are six controls in that row and a 40 mm one would
#: not leave the three interval buttons beside it room to be targets at all.
#: Still floored at 20 mm by ContentArea, like everything else a child touches.
SIDE_BUTTON_MM = 34.0
#: The three interval buttons on the minute screen. They are a *setting*, not
#: the thing to press, and size is what says so -- the same argument the
#: grown-up's card makes with typography. Still a target, still floored at
#: 20 mm.
LENGTH_BUTTON_MM = 26.0

#: The "show me" animation, in milliseconds between frames. 20 a second is
#: smooth enough that the disc reads as continuous and slow enough that it
#: costs nothing on the machine kidnix ships for.
FRAME_MS = 50

#: Sizes the routine strip will try, in millimetres, largest first. The last
#: one is ADR-0011's floor and the strip never goes below it: a ninth moment is
#: dropped by :mod:`clock_time.settings` rather than shrinking the other eight
#: into something a five-year-old cannot hit.
STRIP_MM: tuple[float, ...] = (30.0, 26.0, 24.0, 22.0, 20.0)

PROMPT_CLOCK = "Move the hands. What time is it?"
PROMPT_MINUTE = "How long is a minute?"

#: The co-use moment (SUITE section 3). Addressed to the adult, in the adult's
#: words, and it never blocks the child.
#:
#: It lives on the **minute** screen and not the clock one, which is a layout
#: decision with a reason: the clock screen's four rows -- prompt, face, routine
#: strip, card -- do not fit in the rectangle below the band on any panel kidnix
#: ships for, and of the four the card is the one whose absence costs a child
#: nothing. So the card is one press away, it names both screens, and the clock
#: screen's own co-use prompt is the sentence already written across the top of
#: it ("Home time is at half past three"), which is the thing to talk about.
GROWNUP_BODY = (
    "Ask what happens at the time they made on the clock -- and tell them what "
    "happens at that time in your house. Then guess a minute together: say when "
    "you think it has gone, and let them tell you who was closer."
)
#: What the child hears when the save failed (SYNTHESIS C3).
LOST_LINE = "I could not keep that one. Ask a grown-up."


# -- one correction to the SDK's labels --------------------------------------


def _shrinkable(prompt: Prompt) -> Prompt:
    """Let the prompt line give ground when the window is narrow.

    ``Prompt`` fits its label to ``area.width - gap * 4`` and then pins that as
    the label's character width, which becomes the row's *minimum* -- and the
    row also holds the replay button, so the window ends up asking for fifty
    pixels more than the rectangle it was given. Clearing the character count
    leaves the fitted point size and the wrapping alone and puts the minimum
    back where GTK puts it for any wrapping label: the longest word.
    """
    prompt.label.set_width_chars(-1)
    prompt.label.set_max_width_chars(-1)
    return prompt


def _big(label: str, **kwargs) -> BigButton:
    """A :class:`BigButton` whose label is given the width it was measured at.

    ``fit_gtk_label`` works out how the word wraps and at what point size, and
    then GTK asks the label how wide it would *like* to be -- which it answers
    with ``max-width-chars`` times an average character, a number computed for
    a narrower face than the one kidnix draws in. Inside a centred box that
    answer is also the allocation, so the label re-wraps in about half the room
    it was fitted for and "Watch it" comes out as "W-atc-h it".

    Handing the measured width back as a size request closes the loop. It is a
    local correction rather than a change to the SDK because the SDK's own
    screens have not hit it: their labels are one short word.
    """
    button = BigButton(label, **kwargs)
    area = kwargs.get("area")
    size = area.target(kwargs.get("size_mm", 40.0)) if area is not None else 0
    _measured(button.label, button.fit, max(24, size - 24) if size else 0)
    return button


def _measured(label: Gtk.Label | None, fit: object, cap: int = 0) -> None:
    """Give a fitted label the width it was fitted at, and never more.

    ``cap`` is the room the label actually has inside its control. Without it a
    word too long for the box asks for the width it *would* like, the control
    grows to give it, and eight of those grow the routine strip past the edge
    of the screen -- measured at 1074 px in a 1024 px rectangle.
    """
    width = getattr(fit, "width", 0)
    if label is None or not isinstance(width, int) or width <= 0:
        return
    label.set_size_request(min(width, cap) if cap > 0 else width, -1)


def _tile(picture: Path, area: ContentArea, name: str, size_mm: float, **kwargs) -> PictureTile:
    """A :class:`PictureTile` with the same label correction as :func:`_big`.

    ``PictureTile`` does not keep the :class:`LabelFit` it made, so the fit is
    run again here with the arguments the widget used. That is a duplicated
    spelling and it is the lesser evil: the alternative is eight tiles whose
    names come out as "Brea-kfast".
    """
    tile = PictureTile(picture, label=name, area=area, size_mm=size_mm, **kwargs)
    if tile.label is not None:
        size = area.target(size_mm)
        _measured(
            tile.label,
            fit_gtk_label(
                tile.label,
                name,
                width=max(24, size - 20),
                base_pt=area.points(20.0),
                floor_pt=area.points(18.0),
                max_lines=2,
            ),
            max(24, size - 20),
        )
    return tile


# -- the face ----------------------------------------------------------------


class ClockFace(Gtk.Overlay):
    """The clock: one drawing, and one 20 mm target per position on the rim.

    Three routes to the same place, which is A5's rule read in the child's
    favour rather than as a minimum:

    * **press a rim target.** Twelve of them in Year 2, two in Year 1 -- one
      per position the year has been taught, each carrying its own spoken name
      ("quarter past", "half past") and each in the Tab ring. This is
      click-move-click with the move taken out.
    * **press anywhere on the face.** The angle is snapped to the same grid,
      so there is no near-miss and no precision to have.
    * **drag a hand.** Short, from wherever it is, and never required.

    The rim targets are invisible on purpose: they sit exactly over the drawn
    numerals and marks, so the child sees a clock rather than a clock with
    twelve buttons stuck to it, and the focus ring is what makes them appear
    when a keyboard is being used.
    """

    def __init__(
        self,
        area: ContentArea,
        mode: Mode,
        *,
        on_move: Callable[[ClockTime], None],
        speech=None,
        speech_ui=None,
    ) -> None:
        super().__init__()
        self.area = area
        self.mode = mode
        self.clock = ClockTime.of(3, 0)
        self.sky = Sky.AFTERNOON
        self._on_move = on_move
        self._radius = 0.0
        self._centre = (0.0, 0.0)

        self.dial = Gtk.DrawingArea()
        self.dial.set_hexpand(True)
        self.dial.set_vexpand(True)
        self.dial.set_draw_func(self._draw)
        self.dial.set_accessible_role(Gtk.AccessibleRole.PRESENTATION)
        self.dial.connect("resize", self._on_resize)
        self.set_child(self.dial)

        # The targets live in a Fixed on top of the drawing. The overlay is not
        # measured, so it never widens the face; `_on_resize` is what puts each
        # target over the mark it belongs to.
        self.marks = Gtk.Fixed()
        self.add_overlay(self.marks)
        self.set_measure_overlay(self.marks, False)

        target = area.min_target
        self.targets: list[tuple[int, ChildButton]] = []
        for minute in grid_for(mode):
            button = ChildButton(
                speak_text=_rim_words(minute),
                on_activate=lambda m=minute: self._rim_pressed(m),
                speech_ui=speech_ui if speech_ui is not None else _ui_of(speech),
                css_classes=("rim",),
                key=next_key("rim"),
                size=target,
            )
            self.marks.put(button, 0, 0)
            self.targets.append((minute, button))

        # One gesture, in the bubble phase, so a press that a rim target has
        # already claimed never arrives twice. `drag-begin` fires on the press
        # itself, which is what makes tapping and dragging the same code.
        drag = Gtk.GestureDrag.new()
        drag.set_button(0)
        drag.set_propagation_phase(Gtk.PropagationPhase.BUBBLE)
        drag.connect("drag-begin", self._on_drag_begin)
        drag.connect("drag-update", self._on_drag_update)
        self.add_controller(drag)
        self._drag_start = (0.0, 0.0)

    # -- state --

    def set_clock(self, clock: ClockTime, sky: Sky) -> None:
        if clock == self.clock and sky is self.sky:
            return
        self.clock, self.sky = clock, sky
        self.dial.queue_draw()

    # -- drawing and layout --

    def _draw(self, _area: Gtk.DrawingArea, ctx, width: int, height: int) -> None:
        draw_sky(ctx, width, height, self.sky)
        self._radius = draw_dial(ctx, width, height, self.clock, mode=self.mode)
        self._centre = (width / 2.0, height / 2.0)

    def _on_resize(self, _area: Gtk.DrawingArea, width: int, height: int) -> None:
        """Put the rim targets where the drawing is going to put the marks."""
        centre_x, centre_y = width / 2.0, height / 2.0
        radius = min(width, height) / 2.0 * 0.92 * RIM_FRACTION
        size = self.area.min_target
        for minute, button in self.targets:
            angle = math.radians(minute * 6.0 - 90.0)
            self.marks.move(
                button,
                centre_x + radius * math.cos(angle) - size / 2.0,
                centre_y + radius * math.sin(angle) - size / 2.0,
            )

    # -- input --

    def _rim_pressed(self, minute: int) -> None:
        """A named position. The hands take the short way round to it."""
        self._commit(total_from_point(*_unit_for(minute), self.clock, self.mode))

    def _on_drag_begin(self, _g: Gtk.GestureDrag, x: float, y: float) -> None:
        self._drag_start = (x, y)
        self._point(x, y)

    def _on_drag_update(self, _g: Gtk.GestureDrag, dx: float, dy: float) -> None:
        self._point(self._drag_start[0] + dx, self._drag_start[1] + dy)

    def _point(self, x: float, y: float) -> None:
        centre_x, centre_y = self._centre if self._radius else (
            self.get_width() / 2.0,
            self.get_height() / 2.0,
        )
        self._commit(total_from_point(x - centre_x, y - centre_y, self.clock, self.mode))

    def _commit(self, clock: ClockTime) -> None:
        if clock == self.clock:
            return
        self._on_move(clock)


def _ui_of(speech):
    return getattr(speech, "ui", None) if speech is not None else None


def _unit_for(minute: int) -> tuple[float, float]:
    """A point one unit from the centre, at ``minute``. y is downwards."""
    angle = math.radians(minute * 6.0 - 90.0)
    return (math.cos(angle), math.sin(angle))


def _rim_words(minute: int) -> str:
    """What a rim target is called: "half past", "quarter to", "o'clock".

    The position, not the time -- the time depends on which hour the hands are
    in, and a target whose spoken name changed under the child's finger every
    time they moved the clock would be a different control each press.
    """
    return minute_words(minute)


# -- what happens when ------------------------------------------------------
#
# There is deliberately no separate "scene" widget. An earlier version had one
# -- a card beside the clock with the routine's picture, its name and the sky
# behind it -- and it was cut, for two reasons that turned out to be the same
# reason.
#
# It said nothing that was not already on the screen three times: the prompt
# across the top is the whole sentence ("Home is at half past three"), the
# strip below carries the same picture and the same word with a ring round it,
# and the sky is painted behind the clock face itself. A fourth copy is not
# emphasis, it is clutter -- and 08 section 4.5's argument about unenticing
# controls cuts the same way here, because every object on a screen is one more
# thing a four-year-old has to decide is not the thing to press.
#
# And it did not fit. What was left for it after the face and the two controls
# was a rectangle about sixty pixels tall, in which a picture over a word is a
# word -- measured, on the panel this was first run on.

# -- the minute screen's disc -------------------------------------------------


class Disc(Gtk.DrawingArea):
    """The session sun, borrowed. Shrinks and sinks; never travels, never reddens.

    It is drawn in :data:`Phase.SHOWING` and :data:`Phase.RESULT` and **not**
    while the child is judging: a disc that depleted over exactly the interval
    being guessed would be showing them the answer. See
    :mod:`clock_time.minute`.
    """

    def __init__(self, area: ContentArea) -> None:
        super().__init__()
        self.area = area
        self.fraction = 0.0
        self.phase = Phase.READY
        self.set_hexpand(True)
        self.set_vexpand(True)
        # A *minimum*, and a small one: whatever is left after the prompt, the
        # row of controls and the grown-up card is what the disc actually gets,
        # and a minimum larger than that would push one of them off the screen.
        self.set_content_height(area.min_target)
        self.set_draw_func(self._draw)
        self.set_accessible_role(Gtk.AccessibleRole.PRESENTATION)

    def set_state(self, phase: Phase, fraction: float) -> None:
        self.phase = phase
        self.fraction = max(0.0, min(1.0, fraction))
        self.queue_draw()

    def _draw(self, _a: Gtk.DrawingArea, ctx, width: int, height: int) -> None:
        draw_sky(ctx, width, height, Sky.MORNING)
        if self.phase is Phase.GUESSING:
            # **Nothing depletes while the child is judging.** A disc that ran
            # down over exactly the interval being guessed would be showing
            # them the answer, and this would be a reaction test rather than a
            # question about duration (clock_time.minute, decision 2). What is
            # left is the outline of a whole one, so they can see what they are
            # aiming at without being told when they have got there.
            draw_ghost(ctx, width, height, disc_geometry(0.0, width, height))
            return
        draw_disc(ctx, width, height, disc_geometry(self.fraction, width, height))


# -- the keyboard ------------------------------------------------------------


class ClockKeys:
    """Two keys taken back from the SDK's ring, by composition rather than force.

    :class:`~kidnix_activity.keyboard.ActivityKeyboard` owns a capture-phase
    controller on the window and dispatches through its own ``key`` method. So
    this wraps *that method* on the instance rather than adding a second
    controller and hoping the two orders agree -- there is one dispatcher, and
    the activity is in front of it.

    What it takes: the arrows (they move the hands) and Space (Now, or start
    and stop). What it leaves: Tab and Shift-Tab, which still walk every
    control, so SYNTHESIS A6 is kept; and Escape, which is the shell's.
    """

    def __init__(self, keyboard: ActivityKeyboard, activity: ClockActivity) -> None:
        self._inner = keyboard.key
        self._activity = activity
        keyboard.key = self.key  # type: ignore[method-assign]

    def key(self, keyval: int, shift: bool = False) -> bool:
        if not shift:
            action = action_for_keyval(keyval, self._activity.screen)
            if action is not None:
                self._activity.do_action(action)
                return True
        return self._inner(keyval, shift)


# -- the activity ------------------------------------------------------------


class ClockActivity:
    """The state, and the two screens it draws itself on."""

    def __init__(
        self,
        app: ActivityApplication,
        settings: ParentSettings | None = None,
        *,
        clock: Callable[[], datetime] = datetime.now,
        scratch: Path | None = None,
    ) -> None:
        self.app = app
        self.settings = settings if settings is not None else load_settings()
        self.now = clock
        self.window: ActivityWindow | None = None
        self.screen = Screen.CLOCK

        self.mode: Mode = self.settings.mode
        self.routine: Routine = self.settings.routine
        self.time = ClockTime.of(3, 0).snapped(self.mode)
        #: Has the child done anything? A Journal card for a session nobody
        #: touched would be a claim about a person that is not true.
        self.played = False

        self.length: Length = Length.MINUTE
        self.phase = Phase.READY
        self._started_at = 0.0
        self._tick_id = 0
        self._elapsed = 0.0

        self._scratch = scratch
        self._temporary: tempfile.TemporaryDirectory[str] | None = None

        # widgets, filled in by the builders
        self.face: ClockFace | None = None
        self.prompt: Prompt | None = None
        self.disc: Disc | None = None
        self.go: BigButton | None = None
        self.tiles: dict[str, PictureTile] = {}

        log.info("settings: %s", self.settings.describe())

    # -- scratch --

    @property
    def scratch(self) -> Path:
        """Where the PNG is written before the Journal copies it in."""
        if self._scratch is None:
            self._temporary = tempfile.TemporaryDirectory(prefix="clock-time-")
            self._scratch = Path(self._temporary.name)
        return self._scratch

    # -- what the hands are showing --

    @property
    def now_minutes(self) -> int:
        """What time it really is in the room, in minutes past midnight.

        The hint that resolves a twelve-hour dial (:meth:`Routine.minutes_for`).
        Seven o'clock is getting up or going to bed and the hands cannot say
        which; the room can, and an adult sitting next to the child would use
        exactly this to decide.
        """
        real = self.now()
        return real.hour * 60 + real.minute

    @property
    def item(self) -> RoutineItem:
        return self.routine.at(self.time, self.now_minutes)

    @property
    def sky(self) -> Sky:
        return self.routine.sky_for(self.time, self.now_minutes)

    def set_time(self, clock: ClockTime, *, speak: bool = True, played: bool = True) -> None:
        """Move the hands, repaint the day, and say what it says."""
        self.time = clock
        if played:
            self.played = True
        item, sky = self.item, self.sky
        if self.face is not None:
            self.face.set_clock(clock, sky)
        self._highlight(item)
        if self.prompt is not None:
            self.prompt.set_text(f"{clock.words().capitalize()}. {item.sentence}")
        if speak and self.window is not None:
            self.window.speak(f"{clock.words()}. {item.sentence}")

    def _highlight(self, item: RoutineItem) -> None:
        for key, tile in self.tiles.items():
            if key == item.id:
                tile.add_css_class("current")
            else:
                tile.remove_css_class("current")

    # -- the actions the keyboard and the buttons share --

    def do_action(self, action: Action) -> None:
        if action is Action.MINUTE_FORWARD:
            self.set_time(self.time.stepped(1, self.mode))
        elif action is Action.MINUTE_BACK:
            self.set_time(self.time.stepped(-1, self.mode))
        elif action is Action.NOW:
            self.jump_to_now()
        elif action is Action.START_OR_STOP:
            self.start_or_stop()

    def jump_to_now(self) -> None:
        """The hands go to the real time, and the voice hedges if it must.

        Real time is almost never on the grid, so the hands land where they
        really are and the voice says "about half past three". Saying "half
        past three" at twenty-six minutes past would teach a child that the
        words are looser than they are.
        """
        real = ClockTime.from_time(self.now())
        self.set_time(real, speak=False)
        if self.window is not None:
            self.window.speak(f"Right now it is {real.spoken(self.mode)}. {self.item.sentence}")

    # -- screen one: play with the clock --

    def build(self, window: ActivityWindow) -> None:
        self.window = window
        _load_css()
        ClockKeys(window.keys, self)
        self.build_clock(window)

    def build_clock(self, window: ActivityWindow) -> None:
        self.screen = Screen.CLOCK
        self._stop_ticking()
        window.clear()
        self.disc = self.go = None
        area = window.area

        self.prompt = _shrinkable(Prompt(PROMPT_CLOCK, speech=window.speech, area=area))
        window.add(self.prompt)

        middle = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=area.gap)
        middle.set_vexpand(True)
        self.face = ClockFace(
            area, self.mode, on_move=lambda c: self.set_time(c), speech=window.speech
        )
        self.face.set_hexpand(True)
        self.face.set_vexpand(True)
        middle.append(self.face)

        # Side by side rather than stacked, and vertically centred beside the
        # clock. Two 40 mm buttons one above the other give this column a
        # *minimum* height larger than the face's, and a minimum is not
        # negotiable: the whole layout would then be taller than the rectangle
        # below the band, and what falls off the bottom is the routine strip.
        side = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=area.gap)
        side.set_homogeneous(True)
        side.set_valign(Gtk.Align.CENTER)
        side.append(
            _big(
                "Now",
                icon=str(ICON),
                icon_kind="path",
                speak_text="Show me the time right now.",
                on_activate=self.jump_to_now,
                speech=window.speech,
                area=area,
            )
        )
        side.append(
            _big(
                "Minute",
                speak_text="How long is a minute?",
                on_activate=lambda: self.build_minute(window),
                speech=window.speech,
                area=area,
            )
        )
        middle.append(side)
        window.add(middle)

        strip = self._strip(window, area)
        window.add(strip)

        # Now that every row exists, ask it how short it will let itself be, and
        # give the face what is left. Measuring beats estimating: a Prompt's
        # height depends on how the sentence wrapped and a routine tile's on
        # whether "Breakfast" fitted on one line, neither of which is knowable
        # from ContentArea alone -- and both are what pushed the first version
        # of this window 270 px past the rectangle it had been given.
        reserved = _reserved(area, self.prompt, strip)
        face_size = _face_size(area, reserved)
        self.face.set_size_request(face_size, face_size)
        if area.known:
            side_minimum = _minimum_height(side, area.width - face_size - area.gap)
            if side_minimum > area.height - reserved:
                log.warning(
                    "the side column will not go below %d px and only %d px is left; "
                    "the layout will overflow the %d px it was given",
                    side_minimum,
                    area.height - reserved,
                    area.height,
                )

        self.set_time(self.time, speak=False, played=False)
        window.speak(PROMPT_CLOCK)

    def _strip_mm(self, area: ContentArea) -> float:
        """The largest tile that lets the whole day fit across, in millimetres.

        Never below ADR-0011's floor: a ninth moment is dropped by
        :mod:`clock_time.settings` rather than squeezing eight into targets a
        five-year-old cannot hit.
        """
        if not area.known:
            return STRIP_MM[0]
        # `ContentArea.columns_for` measures against the *screen*, and the
        # strip lives inside the content box's margins -- a difference of two
        # gaps, which on a 1024 px panel is exactly the difference between
        # eight tiles fitting and the window being 50 px too wide.
        count = max(1, len(self.routine))
        available = area.width - area.margin * 2
        for candidate in STRIP_MM:
            cell = area.target(candidate)
            if cell * count + area.gap * (count - 1) <= available:
                return candidate
        return STRIP_MM[-1]

    def _strip(self, window: ActivityWindow, area: ContentArea) -> Gtk.Widget:
        """This family's day, as pictures. **Not** a timeline (09 Q4).

        The child is never asked to order it, nothing in it is draggable, and
        the left-to-right arrangement is convenience -- the hands, the
        highlight and the sky are what carry *when*. Pressing one moves the
        hands to that time, which is the same link read the other way round:
        "bath is at half past six" and "half past six is bath".
        """
        size_mm = self._strip_mm(area)

        strip = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=area.gap)
        strip.add_css_class("routine-strip")
        strip.set_halign(Gtk.Align.CENTER)
        self.tiles = {}
        for item in self.routine:
            tile = _tile(
                picture_path(item),
                area,
                item.name,
                size_mm,
                speak_text=item.sentence,
                on_activate=lambda i=item: self.set_time(i.clock.snapped(self.mode)),
                speech=window.speech,
                css_classes=("routine",),
            )
            self.tiles[item.id] = tile
            strip.append(tile)
        return strip

    # -- screen two: how long is a minute? --

    def build_minute(self, window: ActivityWindow) -> None:
        self.screen = Screen.MINUTE
        self.phase = Phase.READY
        self._elapsed = 0.0
        window.clear()
        self.face = None
        self.tiles = {}
        area = window.area

        self.prompt = _shrinkable(Prompt(PROMPT_MINUTE, speech=window.speech, area=area))
        window.add(self.prompt)

        self.disc = Disc(area)
        window.add(self.disc)

        # One row, not two. Two rows of controls plus a prompt, a disc and the
        # grown-up's card have a combined *minimum* height greater than the
        # rectangle below the band on every panel kidnix ships for, and the
        # thing that gets squeezed out is the disc -- which is the screen.
        # The three lengths are small and carry the `length` style class; the
        # three actions are 30 mm. Size is what separates a setting from a
        # thing to press, which is the same distinction the grown-up's card
        # makes with typography.
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=area.gap)
        row.set_halign(Gtk.Align.CENTER)
        self.go = _big(
            "Start",
            speak_text="Start. Press stop when you think the time has gone.",
            on_activate=self.start_or_stop,
            speech=window.speech,
            area=area,
            size_mm=SIDE_BUTTON_MM,
        )
        row.append(self.go)
        row.append(
            _big(
                "Watch",
                speak_text=f"Watch {self.length.words} go past.",
                on_activate=self.watch,
                speech=window.speech,
                area=area,
                size_mm=SIDE_BUTTON_MM,
            )
        )
        for length in LENGTHS:
            row.append(
                _big(
                    length.label,
                    speak_text=f"Try {length.words}.",
                    on_activate=lambda w=length: self.choose(w),
                    speech=window.speech,
                    area=area,
                    size_mm=LENGTH_BUTTON_MM,
                    css_classes=("length",),
                )
            )
        row.append(
            _big(
                "Clock",
                icon=str(ICON),
                icon_kind="path",
                speak_text="Back to the clock.",
                on_activate=lambda: self.build_clock(window),
                speech=window.speech,
                area=area,
                size_mm=SIDE_BUTTON_MM,
            )
        )
        window.add(row)
        window.add(GrownUpTurn(GROWNUP_BODY, speech=window.speech, area=area))

        self.disc.set_state(Phase.READY, 0.0)
        window.speak(self.length.prompt)

    def choose(self, length: Length) -> None:
        """A different interval. Stops whatever was running, quietly."""
        self._stop_ticking()
        self.length = length
        self.phase = Phase.READY
        if self.disc is not None:
            self.disc.set_state(Phase.READY, 0.0)
        if self.prompt is not None:
            self.prompt.set_text(length.prompt)
        if self.window is not None:
            self.window.speak(length.prompt)

    def watch(self) -> None:
        """Show me a minute. Nobody is being asked anything."""
        self._stop_ticking()
        self.played = True
        self.phase = Phase.SHOWING
        self._started_at = time.monotonic()
        if self.disc is not None:
            self.disc.set_state(Phase.SHOWING, 0.0)
        if self.prompt is not None:
            self.prompt.set_text(f"Watch {self.length.words} go past.")
        if self.window is not None:
            self.window.speak(f"Here is {self.length.words}.")
        self._tick_id = GLib.timeout_add(FRAME_MS, self._frame)

    def start_or_stop(self) -> None:
        """The one button, and the one key, that runs the guess."""
        if self.phase is Phase.GUESSING:
            self._finish_guess()
            return
        self._stop_ticking()
        self.played = True
        self.phase = Phase.GUESSING
        self._started_at = time.monotonic()
        if self.disc is not None:
            self.disc.set_state(Phase.GUESSING, 0.0)
        if self.go is not None:
            self.go.set_speak_text("Stop. That feels like the right time.")
        if self.prompt is not None:
            self.prompt.set_text(self.length.prompt)
        if self.window is not None:
            self.window.speak(self.length.prompt)

    def _finish_guess(self) -> None:
        self._elapsed = time.monotonic() - self._started_at
        self.phase = Phase.RESULT
        verdict = verdict_for(self._elapsed, self.length)
        fraction = min(1.0, self._elapsed / self.length.seconds)
        if self.disc is not None:
            self.disc.set_state(Phase.RESULT, fraction)
        if self.go is not None:
            self.go.set_speak_text("Start. Press stop when you think the time has gone.")
        sentence = verdict.sentence(self.length)
        if self.prompt is not None:
            self.prompt.set_text(sentence)
        if self.window is not None:
            self.window.speak(sentence)
        log.info("minute: %s over %.1fs of %s", verdict.value, self._elapsed, self.length.words)

    def _frame(self) -> bool:
        if self.phase is not Phase.SHOWING:
            self._tick_id = 0
            return GLib.SOURCE_REMOVE
        spent = (time.monotonic() - self._started_at) / self.length.seconds
        if self.disc is not None:
            self.disc.set_state(Phase.SHOWING, spent)
        if spent >= 1.0:
            self.phase = Phase.RESULT
            self._tick_id = 0
            if self.prompt is not None:
                self.prompt.set_text(f"That was {self.length.words}.")
            if self.window is not None:
                self.window.speak(f"That was {self.length.words}.")
            return GLib.SOURCE_REMOVE
        return GLib.SOURCE_CONTINUE

    def _stop_ticking(self) -> None:
        if self._tick_id:
            GLib.source_remove(self._tick_id)
            self._tick_id = 0

    # -- the way out --

    def finish(self) -> None:
        """SIGTERM: keep the clock they made, and say nothing about it.

        Only if they played. A card in My Things saying "half past three" for a
        session in which nobody touched anything would be a claim about a
        person that is not true -- the same rule ``screenshots.py`` keeps.
        """
        self._stop_ticking()
        if not self.played:
            log.info("finishing: nothing was played with, so nothing is kept")
            return
        item = self.item
        caption = self.time.words().capitalize()
        try:
            png = render_card(
                self.scratch / "clock.png", self.time, mode=self.mode, sky=self.sky
            )
            files = [png]
            picture = picture_for(item)
            if picture is not None:
                files.append(picture)
            entry = self.app.save_entry(
                "picture",
                files,
                caption=caption,
                meta={
                    "time": self.time.words(),
                    "mode": self.mode.value,
                    "routine": item.id,
                    "sky": self.sky.value,
                },
            )
        except JournalError as exc:
            log.error("could not keep the clock: %s", exc)
            if self.window is not None:
                self.window.speak(LOST_LINE)
            return
        log.info("kept %s (%s)", entry.id, caption)


# -- helpers -----------------------------------------------------------------


def _minimum_height(widget: Gtk.Widget, width: int) -> int:
    """How short GTK will let ``widget`` be. **Not** how tall it would like.

    The minimum is the number that matters: a control built by the SDK carries
    a ``set_size_request`` of 20 mm or more, which GTK will not go under, so a
    column of them whose minima sum past the content rectangle overflows it
    however the natural sizes are negotiated.
    """
    minimum, _natural, _min_baseline, _nat_baseline = widget.measure(
        Gtk.Orientation.VERTICAL, max(-1, width)
    )
    return int(minimum)


def _reserved(area: ContentArea, prompt: Gtk.Widget, strip: Gtk.Widget) -> int:
    """Everything on the clock screen that is not the face, in pixels.

    The prompt and the routine strip are the rows above and below it. The side
    column shares the face's row and so costs nothing here -- but it *does*
    have a minimum of its own, and if that exceeds what is left the row is
    taller than the face however small the face is made. :meth:`build_clock`
    checks for that and says so in the log.
    """
    rows = _minimum_height(prompt, area.width) + _minimum_height(strip, area.width)
    return area.margin * 2 + area.gap * 2 + rows


def _face_size(area: ContentArea, reserved: int = 0) -> int:
    """Sixty per cent of the content height -- or all that is left, if less.

    The face is the subject of the activity and the brief gives it 60% of the
    height. On a short panel that is a request the rectangle cannot honour, and
    the honest failure is to **yield**, not to overflow: a window that asks for
    more than the compositor is going to give it gets a layout neither side
    agrees on, and under gnome-kiosk what falls off the bottom is the routine
    strip -- the half of this activity that is not a clock.

    So the face takes the smaller of the two, never goes below three targets,
    and the shortfall is logged: ``docs/design/activity-sdk.md`` section 13.3
    asks for exactly that ("an activity that overflows should log the
    difference"), and this is the one place here that can.

    On an unknown screen (a headless run, a build container) there is nothing
    to take a fraction of, so the face falls back to a size that is comfortable
    on the panel kidnix ships for rather than to nothing.
    """
    if not area.known:
        return max(area.big_button * 4, 400)
    wanted = int(area.height * FACE_HEIGHT_FRACTION)
    available = area.height - max(0, reserved)
    size = max(area.min_target * 3, min(wanted, available))
    if size < wanted:
        log.info(
            "the face wanted %d px (%.0f%% of %d) and the rest of the screen left %d; "
            "using %d px",
            wanted,
            FACE_HEIGHT_FRACTION * 100,
            area.height,
            available,
            size,
        )
    return size


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
    parser = argparse.ArgumentParser(prog="kidnix-clock-time", description=TITLE)
    parser.add_argument(
        "--screenshot",
        type=Path,
        help="write clock-play.png and clock-minute.png into this directory and exit",
    )
    args, rest = parser.parse_known_args(argv[1:] if argv else None)

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    app = ActivityApplication(ACTIVITY_ID, TITLE)
    activity = ClockActivity(app)

    if args.screenshot is not None:
        from .screenshots import run_screenshots

        return run_screenshots(app, activity, args.screenshot)

    app.set_build(activity.build)
    app.set_on_finish(activity.finish)
    return app.run([argv[0] if argv else "kidnix-clock-time", *rest])
