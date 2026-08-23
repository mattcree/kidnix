"""S8 -- Resting (daytime) and Goodnight (bedtime).

One screen, **two vocabularies**, switched on ``policy.is_bedtime(now)``. The
words, the colours and the picture all come from :mod:`kidnix_shell.resting`,
which is where the reasoning lives; the short version is that an ordinary
four-o'clock session used to end in night vocabulary -- a moon, "goodnight",
a yawn -- while bedtime is 19:00-07:00, and sleep-onset cues conditioned to
the moment the nice thing stops are backwards for exactly the children who
find bedtime hardest (forum #17, #31).

Dim, quiet, no controls, nothing to press. The only way out is the session
becoming allowed again, or the grown-up gate in the band. This is the one
state with no visible way back to Home, and that is the point (spec section 2).

Touching it answers -- **at most once every eight seconds, and not at all once
a child has pressed it three times in half a minute**. A crying child hammering
the screen is the population this state exists for, and the old code gave them
a chopped synthetic voice repeating a demand (forum #23). Nothing here asks the
child to do anything, including find an adult.
"""

from __future__ import annotations

import time
from datetime import datetime

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk  # noqa: E402

from ..resting import SLEEPING_LINE, TapSpeechLimiter, rest_line, rest_title  # noqa: E402
from ..widgets import big_label, icon_image  # noqa: E402
from . import Screen  # noqa: E402

__all__ = ["SLEEPING_LINE", "SleepingScreen"]


class SleepingScreen(Screen):
    name = "Resting"

    def build(self) -> None:
        metrics = self.ctx.metrics
        # The class goes on the *window* as well (app._show_state): a box that
        # is halign/valign CENTER paints a rectangle, not a screen.
        self.set_valign(Gtk.Align.CENTER)
        self.set_halign(Gtk.Align.CENTER)
        self.set_spacing(metrics.gap * 2)

        self.moon = icon_image("kidnix-moon", "icon-name", metrics.mm(45))
        self.moon.set_halign(Gtk.Align.CENTER)
        self.append(self.moon)

        self.title = big_label(rest_title(bedtime=False))
        self.append(self.title)
        self.line = big_label("", "quiet-line")
        self.append(self.line)

        self._limiter = TapSpeechLimiter()

        # The whole surface answers, so a child pressing anywhere gets a reply
        # rather than a screen that appears broken -- subject to the limiter.
        click = Gtk.GestureClick.new()
        click.set_button(0)
        click.connect("pressed", lambda g, n, x, y: self._touched())
        self.add_controller(click)

    # -- what it says --

    def bedtime(self, now: datetime | None = None) -> bool:
        return self.ctx.session.policy.is_bedtime(now or datetime.now())

    def line_now(self, now: datetime | None = None) -> str:
        when = now or datetime.now()
        return rest_line(when, self.ctx.session.next_allowed(when), bedtime=self.bedtime(when))

    def on_enter(self) -> None:
        now = datetime.now()
        bedtime = self.bedtime(now)
        self.remove_css_class("resting")
        self.remove_css_class("sleeping")
        self.add_css_class("sleeping" if bedtime else "resting")
        # No moon in the daytime. The picture is the claim a pre-reader reads
        # first, and at four in the afternoon it would be a false one.
        self.moon.set_visible(bedtime)
        self.title.set_label(rest_title(bedtime=bedtime))
        line = self.line_now(now)
        self.line.set_label(line)

        # A refusal at Who's here arrives with its own sentence, and that one
        # is the one that matters: the child asked for a turn and is being told
        # there isn't one. It is spoken instead of the screen's line, once.
        reason, self.ctx.rest_reason = self.ctx.rest_reason, ""
        self._limiter.reset()
        self._limiter.should_speak(time.monotonic())
        self.ctx.speech.speak(reason or line)

    def _touched(self) -> None:
        if self._limiter.should_speak(time.monotonic()):
            self.ctx.speech.speak(self.line_now())
