"""S7 -- Goodbye.

"You made N things today", up to three thumbnails, and two buttons: Show a
grown-up (opens My Things read-only for two minutes) and Goodnight. Plus the
offline continuation.

**The continuation is the child's own, chosen at the start (spec 7b).** S1b
asked what happens after; this screen shows that picture back and asks "Ready
to go outside?" -- Coco's Videos' exact move, and the one change 09 rates
highest. The generated line in :mod:`kidnix_shell.suggestions` is now the
*fallback*: it runs when the child skipped S1b, when the profile turns S1b off,
or when a grown-up started the session from the gate.

It asks. It never instructs. Coco's found children who took the machine's
statements as inviolable rules ("Coco will make you do it"), so nothing here
is phrased as an obligation on the child or on the family.

The reward is the artefact (SYNTHESIS E1). There are no points here, no streak,
no "come back tomorrow".
"""

from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk  # noqa: E402

from ..journal import Entry  # noqa: E402
from ..suggestions import offline_suggestion  # noqa: E402
from ..theme import points_for  # noqa: E402
from ..widgets import ChildButton, big_label, icon_image, page_label_fit  # noqa: E402
from . import Screen  # noqa: E402

MAX_THUMBNAILS = 3
#: The picture the child chose on S1b, at Goodbye. Big enough to recognise
#: across a room, small enough that the line under it stays on the panel.
NEXT_AFTER_ICON_MM = 24.0
#: theme.css ``button.ritual``: 28 px of padding and a 3 px border either side.
RITUAL_CHROME_X_PX = 62

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
        inner = max(1, metrics.target_mm(60) - RITUAL_CHROME_X_PX)
        base = points_for(metrics, ".big-line")
        # One size across the pair: two buttons side by side at two different
        # sizes read as one of them mattering more.
        points, _ = page_label_fit(
            ("Show a grown-up", "Goodnight"),
            inner,
            base_pt=base,
            floor_pt=metrics.label_floor_pt,
            widget=buttons,
        )

        self.show_button = ChildButton(
            speak_text="Show a grown-up",
            on_activate=self.ctx.host.show_a_grownup,
            speech_ui=self.ctx.speech_ui,
            css_classes=("ritual",),
            width=metrics.target_mm(60),
            height=metrics.target_mm(28),
        )
        self.show_button.set_child(
            big_label(
                "Show a grown-up",
                "big-line",
                width=inner,
                base_pt=base,
                floor_pt=metrics.label_floor_pt,
                points=points,
            )
        )
        buttons.append(self.show_button)

        self.goodnight_button = ChildButton(
            speak_text="Goodnight",
            on_activate=self.ctx.host.goodnight,
            speech_ui=self.ctx.speech_ui,
            css_classes=("ritual",),
            width=metrics.target_mm(60),
            height=metrics.target_mm(28),
        )
        self.goodnight_button.set_child(
            big_label(
                "Goodnight",
                "big-line",
                width=inner,
                base_pt=base,
                floor_pt=metrics.label_floor_pt,
                points=points,
            )
        )
        buttons.append(self.goodnight_button)
        self.append(buttons)

        # The child's own answer from S1b: the picture they picked, above the
        # line that names it. A picture, because this is the part of the ending
        # a pre-reader has to be able to read without the voice.
        #
        # Picture and line sit **side by side** in one box, and both of those
        # are deliberate. Appending them separately cost a whole ``gap * 2`` of
        # the screen's own spacing; stacking them cost the picture's height
        # again. Either one pushed "Ready to go outside?" off the bottom of a
        # 1280x800 panel on a day the child made three things -- the last line
        # of the session, clipped.
        self.continuation = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=metrics.gap)
        self.continuation.set_valign(Gtk.Align.CENTER)
        self.continuation.set_halign(Gtk.Align.CENTER)
        self.next_after_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.next_after_box.set_halign(Gtk.Align.CENTER)
        self.next_after_icon = Gtk.Image()
        self.next_after_icon.set_pixel_size(metrics.mm(NEXT_AFTER_ICON_MM))
        self.next_after_icon.set_halign(Gtk.Align.CENTER)
        self.next_after_box.append(self.next_after_icon)
        self.next_after_box.set_visible(False)
        self.continuation.append(self.next_after_box)

        self.suggestion = big_label("", "quiet-line")
        self.continuation.append(self.suggestion)
        self.append(self.continuation)

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

        line = self.continuation_line(made)
        self.suggestion.set_label(line)
        self.ctx.speech.speak(f"{headline}. {line}")

    def continuation_line(self, made: list[Entry]) -> str:
        """The child's own plan if they made one, the generated line if not.

        Also puts the chosen picture on screen, because this is the part of the
        ending a pre-reader has to be able to read without the voice.
        """
        chosen = self.ctx.next_after
        if chosen is None:
            self.next_after_box.set_visible(False)
            last = made[0] if made else None
            activity_id = last.activity_id if last is not None else ""
            activity = next((a for a in self.ctx.activities if a.id == activity_id), None)
            return offline_suggestion(activity_id, activity.category if activity else "")

        self.next_after_box.remove(self.next_after_icon)
        self.next_after_icon = icon_image(
            chosen.icon,
            chosen.icon_kind,
            self.ctx.metrics.mm(NEXT_AFTER_ICON_MM),
            fallback="kidnix-play",
        )
        self.next_after_icon.set_halign(Gtk.Align.CENTER)
        self.next_after_box.prepend(self.next_after_icon)
        self.next_after_box.set_visible(True)
        return chosen.ready_line
