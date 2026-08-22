"""S5 Ending offer and S6 Put away.

The most evidence-rich pattern in the research (08 section 4.7): the machine
ends the session, at a natural boundary, with a ritual the child has seen
before. No "are you sure?", no bribe to stay, no adult voice saying two
minutes.

S5 at T-6: "The sun is going down", two big choices, and a small "Ask for more
time" that in v0.1 honestly says a grown-up can add time from the gate.

S6 at T-2: no buttons at all. The work animates into My Things with the keep
earcon and the line "Let's keep that." The activity is asked to quit.
"""

from __future__ import annotations

from functools import partial

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gtk  # noqa: E402

from ..sound import KEEP  # noqa: E402
from ..theme import points_for  # noqa: E402
from ..widgets import ChildButton, big_label, icon_image, page_label_fit  # noqa: E402
from . import Screen  # noqa: E402

PUT_AWAY_ANIMATION_MS = 1100

#: theme.css ``button.ritual``: 28 px of padding and a 3 px border either side.
RITUAL_CHROME_X_PX = 62
#: ``button.ritual.secondary``: the same padding, a lighter border.
RITUAL_SECONDARY_CHROME_X_PX = 56


class EndingOfferScreen(Screen):
    name = "The sun is going down"

    def build(self) -> None:
        metrics = self.ctx.metrics
        self.set_valign(Gtk.Align.CENTER)
        self.set_halign(Gtk.Align.CENTER)
        self.set_spacing(metrics.gap * 2)

        sun = icon_image("kidnix-sun", "icon-name", metrics.mm(30))
        sun.set_halign(Gtk.Align.CENTER)
        self.append(sun)
        self.append(big_label("The sun is going down."))

        choices = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=metrics.gap * 2)
        choices.set_halign(Gtk.Align.CENTER)
        # Both endings are read by a child who is being asked to stop. Neither
        # may be cut, and neither may be wider than the other's button, so the
        # pair is fitted to the same width (spec S5, SYNTHESIS B4).
        inner = max(1, metrics.target_mm(60) - RITUAL_CHROME_X_PX)
        choices_text = ("Finish this one", "One last little thing")
        points, _ = page_label_fit(
            choices_text,
            inner,
            base_pt=points_for(metrics, ".big-line"),
            floor_pt=metrics.label_floor_pt,
            widget=choices,
        )
        for label, speak, one_last in (
            (choices_text[0], "Finish this one", False),
            (choices_text[1], "One last little thing", True),
        ):
            button = ChildButton(
                speak_text=speak,
                on_activate=partial(self.ctx.host.dismiss_offer, one_last),
                speech_ui=self.ctx.speech_ui,
                css_classes=("ritual",),
                width=metrics.target_mm(60),
                height=metrics.target_mm(30),
            )
            button.set_child(
                big_label(
                    label,
                    "big-line",
                    width=inner,
                    base_pt=points_for(metrics, ".big-line"),
                    floor_pt=metrics.label_floor_pt,
                    points=points,
                )
            )
            choices.append(button)
        self.append(choices)

        more = ChildButton(
            speak_text="Ask for more time",
            on_activate=self._ask_for_more,
            speech_ui=self.ctx.speech_ui,
            css_classes=("ritual", "secondary"),
            width=metrics.target_mm(50),
            height=metrics.min_target,
        )
        more.set_child(
            big_label(
                "Ask for more time",
                "quiet-line",
                width=max(1, metrics.target_mm(50) - RITUAL_SECONDARY_CHROME_X_PX),
                base_pt=points_for(metrics, "button.ritual.secondary"),
                floor_pt=metrics.label_floor_pt,
            )
        )
        more.set_halign(Gtk.Align.CENTER)
        self.append(more)

    def _ask_for_more(self) -> None:
        # SYNTHESIS D7 wants a grant flow; v0.1 has no Ask queue, and pretending
        # otherwise would be a promise to a five-year-old we cannot keep. It is
        # still an *answer*, so it dismisses the offer like the other two: a
        # child who has gone to find a grown-up should not come back to the
        # same question.
        self.ctx.speech.speak("A grown-up can add more time. Go and ask them.")
        self.ctx.host.dismiss_offer(False)

    def on_enter(self) -> None:
        self.ctx.speech.speak("The sun is going down. Finish this one, or one last little thing?")


class PutAwayScreen(Screen):
    """No buttons. Nothing here is a decision."""

    name = "Let's keep that"

    def build(self) -> None:
        metrics = self.ctx.metrics
        self.set_valign(Gtk.Align.CENTER)
        self.set_halign(Gtk.Align.CENTER)
        self.set_spacing(metrics.gap * 2)

        self._travel = Gtk.Fixed()
        self._travel.set_size_request(metrics.mm(120), metrics.mm(60))
        self._travel.set_halign(Gtk.Align.CENTER)
        self.append(self._travel)

        self._picture = Gtk.Picture()
        self._picture.set_content_fit(Gtk.ContentFit.CONTAIN)
        self._picture.set_size_request(metrics.mm(45), metrics.mm(45))
        self._travel.put(self._picture, metrics.mm(38), 0)

        self.append(big_label("Let's keep that."))
        self._animation: Adw.TimedAnimation | None = None

    def on_enter(self) -> None:
        metrics = self.ctx.metrics
        latest = next(iter(self.ctx.journal.entries), None)
        thumb = latest.thumbnail if latest is not None else None
        if thumb is not None:
            self._picture.set_filename(str(thumb))
            self._picture.set_visible(True)
        else:
            self._picture.set_visible(False)

        self.ctx.speech.speak("Let's keep that.")
        self.ctx.earcons.play(KEEP, speaking=True)

        if not self._picture.get_visible():
            return

        # The work flies up and to the left, towards My Things in the band --
        # "showing the journey" so the child sees where their thing went.
        start_x = float(metrics.mm(38))
        target = Adw.CallbackAnimationTarget.new(self._step)
        self._start_x = start_x
        animation = Adw.TimedAnimation.new(self._travel, 0.0, 1.0, PUT_AWAY_ANIMATION_MS, target)
        animation.set_easing(Adw.Easing.EASE_IN_OUT_CUBIC)
        animation.play()
        self._animation = animation

    def _step(self, value: float) -> None:
        metrics = self.ctx.metrics
        x = self._start_x * (1.0 - value)
        y = -metrics.mm(10) * value
        self._travel.move(self._picture, x, y)
        size = int(metrics.mm(45) * (1.0 - 0.65 * value))
        self._picture.set_size_request(size, size)
        self._picture.set_opacity(1.0 - 0.7 * value)

    def on_leave(self) -> None:
        if self._animation is not None:
            self._animation.pause()
            self._animation = None
        self._picture.set_opacity(1.0)
