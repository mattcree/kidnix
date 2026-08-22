"""The band (spec section 2, 08 section 5.2).

``[Back] [Undo] [My Things] ...... [sun] ...... [Ear] [Grown-up]``

96 design px at the top of the screen, clamped to 80-128 px so it can never
grow past the panel (spec 7a). It never hides, never scrolls, never reorders,
and it is tinted in the active child's colours. It is the only piece of chrome
in the shell and the child's fixed point in it.

**Ask is not here.** Spec 7a: an always-disabled control teaches a child that
buttons lie, so the envelope is out of the band entirely until the
ask-a-grown-up flow exists. :data:`SHOW_ASK` is the one-line switch back.
**Undo is** here, on every surface, and says "Nothing to undo" when there is
nothing -- a fixed position the child can rely on beats a control that comes
and goes.

The sun is the timer. It travels left to right and sinks as the session
depletes, warming in the last six minutes. There are no digits: 08 section 4.6
is explicit that a countdown is an anxiety animation, and a continuous analogue
depletion is not.

**The sun answers when you ask it.** 08 section 4.6 also asks for a timer a
child can *tap* to hear how much is left, and v0.1.2's was an image with no
gesture on it. It is a :class:`ChildButton` now, drawn with no button chrome at
all -- what it says comes from
:func:`kidnix_shell.session.time_left_words`, which is comparisons ("about as
long as one story") and never quantities. It is also the timer study's
instrument: how often a child asks the sun is a number worth having.
"""

from __future__ import annotations

import math
from collections.abc import Callable
from dataclasses import dataclass

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import GLib, Gtk  # noqa: E402

from .metrics import BAND_CHROME_PX, Metrics  # noqa: E402
from .session import NOT_RUNNING  # noqa: E402
from .widgets import ChildButton, SpeechUI, icon_image, next_key  # noqa: E402

#: Spec section 2 / SYNTHESIS G2: the grown-up gate is a three-second hold.
#: Sesame's rule -- a hold is only ever appropriate as a deliberate barrier,
#: which is exactly what this is. No child control anywhere uses one.
HOLD_SECONDS = 3.0
HOLD_TICK_MS = 50

#: Spec 7a: hide Ask until the flow exists. Flip to True the day it does --
#: :class:`BandActions` and the icon are both still here.
SHOW_ASK = False


@dataclass
class BandActions:
    """What the band does. The shell supplies these; the band has no policy."""

    on_back: Callable[[], None]
    on_undo: Callable[[], None]
    on_my_things: Callable[[], None]
    on_ear: Callable[[], None]
    on_grownup: Callable[[], None]
    #: Only ever called when :data:`SHOW_ASK` is on.
    on_ask: Callable[[], None] | None = None
    #: Tapping the sun. The *words* come from the button's ``speak_text``,
    #: which :meth:`Band.set_progress` keeps current, so this is only here for
    #: anything the shell wants to do besides speak (nothing, today).
    on_sun: Callable[[], None] | None = None


class Sun(Gtk.DrawingArea):
    """The session, drawn as a sun crossing the sky."""

    def __init__(self, metrics: Metrics) -> None:
        super().__init__()
        self._metrics = metrics
        self.fraction = 0.0  # 0 = start of session, 1 = the hard stop
        self.warm = False
        self.set_hexpand(True)
        self.set_content_height(max(24, metrics.band_height - BAND_CHROME_PX))
        self.set_draw_func(self._draw)
        # The drawing itself is decorative; the button around it (Band.sun_button)
        # carries the accessible name and the sentence a tap speaks.
        self.set_accessible_role(Gtk.AccessibleRole.PRESENTATION)

    def set_progress(self, fraction: float, warm: bool) -> None:
        changed = abs(fraction - self.fraction) > 0.001 or warm != self.warm
        self.fraction = max(0.0, min(1.0, fraction))
        self.warm = warm
        if changed:
            self.queue_draw()

    def _draw(self, _area: Gtk.DrawingArea, cr: object, width: int, height: int) -> None:
        ctx = cr  # cairo.Context
        margin = self._metrics.design(24)
        span = max(1, width - 2 * margin)
        radius = max(8, height * 0.28)
        horizon = height - radius * 0.6

        # The path the sun takes, drawn faintly so the journey is visible even
        # at the start: the child can see where it is going.
        ctx.set_line_width(3)  # type: ignore[attr-defined]
        ctx.set_source_rgba(1, 1, 1, 0.35)  # type: ignore[attr-defined]
        steps = 48
        for step in range(steps + 1):
            t = step / steps
            x = margin + t * span
            y = horizon - math.sin(math.pi * t) * (horizon - radius - 2)
            if step == 0:
                ctx.move_to(x, y)  # type: ignore[attr-defined]
            else:
                ctx.line_to(x, y)  # type: ignore[attr-defined]
        ctx.stroke()  # type: ignore[attr-defined]

        # The horizon the sun sinks behind.
        ctx.set_source_rgba(1, 1, 1, 0.55)  # type: ignore[attr-defined]
        ctx.set_line_width(4)  # type: ignore[attr-defined]
        ctx.move_to(margin - 8, horizon + radius * 0.55)  # type: ignore[attr-defined]
        ctx.line_to(width - margin + 8, horizon + radius * 0.55)  # type: ignore[attr-defined]
        ctx.stroke()  # type: ignore[attr-defined]

        t = self.fraction
        x = margin + t * span
        y = horizon - math.sin(math.pi * t) * (horizon - radius - 2)

        # Warm, never red, never pulsing (08 section 4.6).
        if self.warm:
            ctx.set_source_rgb(0.98, 0.62, 0.19)  # type: ignore[attr-defined]
        else:
            ctx.set_source_rgb(1.0, 0.84, 0.31)  # type: ignore[attr-defined]
        ctx.arc(x, y, radius, 0, 2 * math.pi)  # type: ignore[attr-defined]
        ctx.fill()  # type: ignore[attr-defined]
        ctx.set_source_rgba(0, 0, 0, 0.25)  # type: ignore[attr-defined]
        ctx.set_line_width(2.5)  # type: ignore[attr-defined]
        ctx.arc(x, y, radius, 0, 2 * math.pi)  # type: ignore[attr-defined]
        ctx.stroke()  # type: ignore[attr-defined]


class HoldButton(Gtk.Button):
    """Press and hold for three seconds. The parent gate, and nothing else.

    Deliberately not a :class:`ChildButton`: this one must *not* fire on press.
    It still speaks on hover and focus so a child who finds it is told, kindly,
    what it is.
    """

    def __init__(
        self,
        *,
        speak_text: str,
        on_hold: Callable[[], None],
        speech_ui: SpeechUI,
        progress: Gtk.ProgressBar,
        css_classes: tuple[str, ...] = (),
        size: int = 64,
        hold_seconds: float = HOLD_SECONDS,
    ) -> None:
        super().__init__()
        self.speak_text = speak_text
        self._on_hold = on_hold
        self._speech_ui = speech_ui
        self._progress = progress
        self._hold_seconds = hold_seconds
        self._elapsed = 0.0
        self._tick: int | None = None
        self.key = next_key("hold")

        for css in css_classes:
            self.add_css_class(css)
        self.set_size_request(size, size)
        self.update_property([Gtk.AccessibleProperty.LABEL], [speak_text])

        click = Gtk.GestureClick.new()
        click.set_button(0)
        click.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
        click.connect("pressed", lambda g, n, x, y: self._start(g))
        click.connect("released", lambda g, n, x, y: self._stop())
        click.connect("cancel", lambda g, s: self._stop())
        self.add_controller(click)

        speech_ui.register(self.key, self)
        motion = Gtk.EventControllerMotion.new()
        motion.connect("enter", lambda c, x, y: speech_ui.speech.hover_enter(self.key, speak_text))
        motion.connect("leave", self._on_pointer_left)
        self.add_controller(motion)
        focus = Gtk.EventControllerFocus.new()
        focus.connect("enter", lambda c: speech_ui.speech.speak_focus(speak_text, self.key))
        self.add_controller(focus)

        # Keyboard route to the same gate: an adult should not have to hold a
        # mouse button to reach it, but a child pressing Enter should not open
        # it either -- so the keyboard route is the hold's full duration too.
        self.connect("clicked", lambda _b: None)

    def _on_pointer_left(self, _c: Gtk.EventControllerMotion) -> None:
        # Sliding off the gate mid-hold cancels it: a hold has to be deliberate.
        self._speech_ui.speech.hover_leave(self.key)
        self._stop()

    def _start(self, gesture: Gtk.GestureClick) -> None:
        gesture.set_state(Gtk.EventSequenceState.CLAIMED)
        if self._tick is not None:
            return
        self._elapsed = 0.0
        self.add_css_class("holding")
        self._progress.set_visible(True)
        self._progress.set_fraction(0.0)
        self._tick = GLib.timeout_add(HOLD_TICK_MS, self._on_tick)

    def _on_tick(self) -> bool:
        self._elapsed += HOLD_TICK_MS / 1000.0
        self._progress.set_fraction(min(1.0, self._elapsed / self._hold_seconds))
        if self._elapsed >= self._hold_seconds:
            self._stop()
            self._on_hold()
            return False
        return True

    def _stop(self) -> None:
        if self._tick is not None:
            GLib.source_remove(self._tick)
            self._tick = None
        self._elapsed = 0.0
        self.remove_css_class("holding")
        self._progress.set_fraction(0.0)
        self._progress.set_visible(False)


class Band(Gtk.Box):
    """The persistent strip. Present on every child-facing surface."""

    def __init__(self, metrics: Metrics, speech_ui: SpeechUI, actions: BandActions) -> None:
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self.add_css_class("band")
        self._metrics = metrics
        self.set_size_request(-1, metrics.band_height)

        row = Gtk.CenterBox()
        row.set_hexpand(True)

        # Both sized to live inside the band's clamped height: a target that
        # does not fit is a target whose top is off the screen (v0.1.0's bug).
        target = metrics.band_target
        small = metrics.band_small_target
        icon_px = int(target * 0.62)

        # Left: Back, Undo, My Things -- >= 80 px, >= 32 px apart (spec).
        left = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=metrics.gap)
        self.back = self._button("Back", "kidnix-back", target, icon_px, actions.on_back, speech_ui)
        self.undo = self._button("Undo", "kidnix-undo", target, icon_px, actions.on_undo, speech_ui)
        self.my_things = self._button(
            "My Things", "kidnix-my-things", target, icon_px, actions.on_my_things, speech_ui
        )
        for widget in (self.back, self.undo, self.my_things):
            left.append(widget)
        row.set_start_widget(left)

        # Centre: the sun -- and it is a target, not a picture (08 section 4.6).
        self.sun = Sun(metrics)
        self.sun_button = ChildButton(
            speak_text=NOT_RUNNING,
            on_activate=actions.on_sun or (lambda: None),
            speech_ui=speech_ui,
            css_classes=("sun",),
            key=next_key("sun"),
        )
        self.sun_button.set_child(self.sun)
        self.sun_button.set_hexpand(True)
        centre = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        centre.set_hexpand(True)
        centre.set_size_request(metrics.chrome(metrics.design(320)), metrics.band_target)
        centre.append(self.sun_button)
        row.set_center_widget(centre)

        # Right: Ear, Grown-up (hold 3 s). Ask is absent (spec 7a).
        right = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=metrics.gap)
        self.ear = self._button(
            "Say it again", "kidnix-ear", target, icon_px, actions.on_ear, speech_ui
        )
        self.ask: ChildButton | None = None
        if SHOW_ASK and actions.on_ask is not None:
            self.ask = self._button(
                "Ask a grown-up", "kidnix-ask", target, icon_px, actions.on_ask, speech_ui
            )
            self.ask.add_css_class("outline-only")

        self.hold_progress = Gtk.ProgressBar()
        self.hold_progress.add_css_class("hold-progress")
        self.hold_progress.set_visible(False)

        self.grownup = HoldButton(
            speak_text="Grown-up. Hold this for three seconds.",
            on_hold=actions.on_grownup,
            speech_ui=speech_ui,
            progress=self.hold_progress,
            css_classes=("grownup-gate",),
            size=small,
        )
        self.grownup.set_child(icon_image("kidnix-grownup", "icon-name", int(small * 0.66)))

        right.append(self.ear)
        if self.ask is not None:
            right.append(self.ask)
        right.append(self.grownup)
        row.set_end_widget(right)

        self.append(row)
        self.append(self.hold_progress)

    def _button(
        self,
        label: str,
        icon: str,
        size: int,
        icon_px: int,
        callback: Callable[[], None],
        speech_ui: SpeechUI,
    ) -> ChildButton:
        button = ChildButton(
            speak_text=label,
            on_activate=callback,
            speech_ui=speech_ui,
            size=size,
        )
        button.set_child(icon_image(icon, "icon-name", icon_px))
        return button

    # -- state --

    def set_progress(self, fraction: float, warm: bool, words: str = NOT_RUNNING) -> None:
        """Move the sun, and keep what it *says* in step with where it is.

        ``speak_text`` is both the accessible name and what a tap or a hover
        reads aloud, so setting it here is all the wiring the tap needs.
        """
        self.sun.set_progress(fraction, warm)
        if words and words != self.sun_button.speak_text:
            self.sun_button.set_speak_text(words)

    def set_journal_sensitive(self, sensitive: bool) -> None:
        """During the ending ritual the child is not sent off to browse."""
        self.my_things.set_sensitive(sensitive)
