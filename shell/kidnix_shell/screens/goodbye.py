"""S7 -- Goodbye.

"You made N things today", up to three thumbnails, and two buttons: Show a
grown-up (opens My Things read-only for two minutes) and Goodnight. Plus one
concrete offline thing to go and do, keyed to the last activity.

The reward is the artefact (SYNTHESIS E1). There are no points here, no streak,
no "come back tomorrow".
"""

from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk  # noqa: E402

from ..suggestions import offline_suggestion  # noqa: E402
from ..widgets import ChildButton, big_label  # noqa: E402
from . import Screen  # noqa: E402

MAX_THUMBNAILS = 3

WORDS = ("nothing", "one thing", "two things", "three things", "four things", "five things")


def count_phrase(count: int) -> str:
    """Words, not digits -- there are no numerals in the child-facing shell."""
    if count < len(WORDS):
        return WORDS[count]
    return f"{count} things"


class GoodbyeScreen(Screen):
    name = "Goodbye"

    def build(self) -> None:
        metrics = self.ctx.metrics
        self.set_valign(Gtk.Align.CENTER)
        self.set_halign(Gtk.Align.CENTER)
        self.set_spacing(metrics.gap * 2)

        self.headline = big_label("", "screen-title")
        self.append(self.headline)

        self.thumbnails = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=metrics.gap)
        self.thumbnails.set_halign(Gtk.Align.CENTER)
        self.append(self.thumbnails)

        buttons = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=metrics.gap * 2)
        buttons.set_halign(Gtk.Align.CENTER)

        self.show_button = ChildButton(
            speak_text="Show a grown-up",
            on_activate=self.ctx.host.show_a_grownup,
            speech_ui=self.ctx.speech_ui,
            css_classes=("ritual",),
            width=metrics.mm(60),
            height=metrics.mm(28),
        )
        self.show_button.set_child(big_label("Show a grown-up", "big-line"))
        buttons.append(self.show_button)

        self.goodnight_button = ChildButton(
            speak_text="Goodnight",
            on_activate=self.ctx.host.goodnight,
            speech_ui=self.ctx.speech_ui,
            css_classes=("ritual",),
            width=metrics.mm(60),
            height=metrics.mm(28),
        )
        self.goodnight_button.set_child(big_label("Goodnight", "big-line"))
        buttons.append(self.goodnight_button)
        self.append(buttons)

        self.suggestion = big_label("", "quiet-line")
        self.append(self.suggestion)

    def on_enter(self) -> None:
        metrics = self.ctx.metrics
        made = self.ctx.journal.made_on_today()
        headline = f"You made {count_phrase(len(made))} today"
        if not made:
            headline = "See you next time"
        self.headline.set_label(headline)
        self.show_button.set_visible(bool(made))

        while (child := self.thumbnails.get_first_child()) is not None:
            self.thumbnails.remove(child)
        for entry in made[:MAX_THUMBNAILS]:
            thumb = entry.thumbnail
            if thumb is None:
                continue
            picture = Gtk.Picture.new_for_filename(str(thumb))
            picture.set_content_fit(Gtk.ContentFit.CONTAIN)
            picture.set_size_request(metrics.mm(35), metrics.mm(35))
            self.thumbnails.append(picture)

        last = made[0] if made else None
        activity_id = last.activity_id if last is not None else ""
        activity = next((a for a in self.ctx.activities if a.id == activity_id), None)
        line = offline_suggestion(activity_id, activity.category if activity else "")
        self.suggestion.set_label(line)

        self.ctx.speech.speak(f"{headline}. {line}")
