"""S7 -- Goodbye. The highest-reward moment of the session, and laid out like it.

**The child's own destination leads** (panel ruling, 2026-08-23). 09 section 1
concludes from four JABA component analyses that the antecedent cue is inert,
and from Castillo et al. (2018) that the aversive event at an ending is the
*destination* thinning out. The design implication is 09's own sentence: "the
Goodbye screen must be the highest-reward moment of the session." What shipped
was the inverse -- the headline was about counting, the two largest things on
screen were a sun and that count, and the child's chosen next thing was a
24 mm icon on the bottom edge, appended last and spoken as the tail of a
sentence about something else (forum #24, #30, #51).

So, top to bottom:

1. **the chosen picture, large** (:data:`NEXT_AFTER_ICON_MM`, >= 40 mm) and
   "Ready to go outside?" as the headline -- Coco's Videos' exact move;
2. **what was made**: the thumbnails, and one line of descriptive feedback
   computed from this session's Journal entries
   (:mod:`kidnix_shell.feedback` -- SYNTHESIS E1, the one informational-
   competence channel in the product);
3. the two buttons.

And it is **spoken in that order with the destination last**, as its own
utterance, because the sentence that matters most must not arrive as the tail
of a sentence about counting.

Three smaller rulings live here too:

* **"Show a grown-up" is always visible.** It used to be hidden by
  ``set_visible(bool(made))`` -- the same condition that emptied the headline
  -- so a child who made nothing got a return promise over a void with the
  co-use invitation withdrawn, on their flattest day. Co-use is the strongest
  protective moderator in 02 and this is the only place kidnix builds it
  (forum #28, #52). With nothing made today it points at earlier days.
* **No return promises anywhere.** "See you next time" is gone; the headline
  with no destination chosen is :data:`~kidnix_shell.resting.ALL_DONE_HEADLINE`.
  suggestions.py's own docstring has forbidden that phrasing all along (D6).
* **"Goodnight" is only called Goodnight at bedtime**
  (:func:`kidnix_shell.resting.goodnight_label`).

It asks. It never instructs. Coco's found children who took the machine's
statements as inviolable rules ("Coco will make you do it"), so nothing here is
phrased as an obligation on the child or on the family. The reward is the
artefact (SYNTHESIS E1): no points, no streak, no "come back tomorrow".
"""

from __future__ import annotations

from datetime import datetime

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk  # noqa: E402

from ..feedback import (  # noqa: E402
    MadeSummary,
    count_colours,
    count_phrase,
    descriptive_line,
    words_for,
)
from ..journal import Entry  # noqa: E402
from ..resting import ALL_DONE_HEADLINE, goodnight_label  # noqa: E402
from ..suggestions import offline_suggestion  # noqa: E402
from ..theme import points_for  # noqa: E402
from ..widgets import ChildButton, big_label, icon_image, page_label_fit  # noqa: E402
from . import Screen  # noqa: E402

__all__ = ["MAX_THUMBNAILS", "GoodbyeScreen", "count_phrase"]

MAX_THUMBNAILS = 3
#: The picture the child chose on S1b. It was 24 mm, beside a quiet line, at
#: the bottom of the screen; the ruling makes it the biggest thing here and
#: never under 40 mm -- Home's own tile floor, which is the size this child
#: already knows means "a thing you choose".
NEXT_AFTER_ICON_MM = 40.0
#: theme.css ``button.ritual``: 28 px of padding and a 3 px border either side.
RITUAL_CHROME_X_PX = 62
#: Thumbnails of the day's work. Smaller than the destination on purpose --
#: this is the hierarchy the ruling inverts.
THUMBNAIL_MM = 24.0


class GoodbyeScreen(Screen):
    name = "Goodbye"

    def build(self) -> None:
        metrics = self.ctx.metrics
        self.set_valign(Gtk.Align.CENTER)
        self.set_halign(Gtk.Align.CENTER)
        self.set_spacing(metrics.gap)
        # Nothing on the last screen of the session sits flush against the
        # edge of the panel.
        self.set_margin_bottom(metrics.gap)

        # 1. The destination: the picture first, then the question.
        self.next_after_icon = Gtk.Image()
        self.next_after_icon.set_pixel_size(metrics.mm(NEXT_AFTER_ICON_MM))
        self.next_after_icon.set_halign(Gtk.Align.CENTER)
        self.append(self.next_after_icon)

        self.headline = big_label("", "screen-title")
        self.append(self.headline)

        # 2. What was made, and one descriptive line about it.
        self.thumbnails = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=metrics.gap)
        self.thumbnails.set_halign(Gtk.Align.CENTER)
        self.append(self.thumbnails)

        self.made_line = big_label("", "quiet-line")
        self.append(self.made_line)

        # 3. The two buttons.
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
        self._label_points = points
        self._label_inner = inner
        self._label_base = base

        self.show_button = ChildButton(
            speak_text="Show a grown-up",
            on_activate=self.ctx.host.show_a_grownup,
            speech_ui=self.ctx.speech_ui,
            css_classes=("ritual",),
            width=metrics.target_mm(60),
            height=metrics.target_mm(28),
        )
        self.show_button.set_child(self._button_label("Show a grown-up"))
        buttons.append(self.show_button)

        self.goodnight_button = ChildButton(
            speak_text="Goodnight",
            on_activate=self.ctx.host.goodnight,
            speech_ui=self.ctx.speech_ui,
            css_classes=("ritual",),
            width=metrics.target_mm(60),
            height=metrics.target_mm(28),
        )
        self._goodnight_label = self._button_label("Goodnight")
        self.goodnight_button.set_child(self._goodnight_label)
        buttons.append(self.goodnight_button)
        self.append(buttons)

    def _button_label(self, text: str) -> Gtk.Label:
        return big_label(
            text,
            "big-line",
            width=self._label_inner,
            base_pt=self._label_base,
            floor_pt=self.ctx.metrics.label_floor_pt,
            points=self._label_points,
        )

    # -- content --

    def on_enter(self) -> None:
        metrics = self.ctx.metrics
        now = datetime.now()
        # **What is on this screen is what is in the Journal, and nothing
        # else** (spec 7c). If put away had to kill an activity at the hard
        # stop, whatever was on its canvas was never imported, so it is not
        # counted here, has no thumbnail here, and is not claimed as kept.
        made = self.ctx.journal.made_on_today(now)

        headline = self._show_destination()
        self.headline.set_label(headline)

        while (child := self.thumbnails.get_first_child()) is not None:
            self.thumbnails.remove(child)
        for entry in made[:MAX_THUMBNAILS]:
            thumb = entry.thumbnail
            if thumb is None:
                continue
            picture = Gtk.Picture.new_for_filename(str(thumb))
            picture.set_content_fit(Gtk.ContentFit.CONTAIN)
            # A *box*, not a square: the canvases are landscape, and a square
            # request lets the picture grow taller than the row budgeted for --
            # which is how the two buttons ended up on the panel's bottom edge.
            picture.set_size_request(metrics.mm(THUMBNAIL_MM * 4 / 3), metrics.mm(THUMBNAIL_MM))
            picture.set_vexpand(False)
            picture.set_valign(Gtk.Align.CENTER)
            self.thumbnails.append(picture)

        line = self.made_words(made)
        self.made_line.set_label(line)
        self.made_line.set_visible(bool(line))

        # Never hidden, whatever kind of day it was (forum #28). With nothing
        # made today it is an invitation to look at earlier days together, and
        # co-use is the strongest protective moderator in the corpus.
        self.show_button.set_visible(True)
        self._goodnight_label.set_label(
            goodnight_label(bedtime=self.ctx.session.policy.is_bedtime(now))
        )

        # Spoken in the order the screen is read, and the destination **last**,
        # as its own sentence, after a beat (panel ruling; forum #24).
        if line:
            self.ctx.speech.speak_then(line, headline)
        else:
            self.ctx.speech.speak(headline)

    def made_words(self, made: list[Entry]) -> str:
        """E1's descriptive line, or the generated suggestion, or nothing.

        With work in the Journal this is a fact about what the child did.
        Without it -- and without a chosen destination, which has the headline
        -- it falls back to :mod:`kidnix_shell.suggestions`' offline
        continuation, which is the honest thing left to say.
        """
        if not made:
            if self.ctx.next_after is None:
                return offline_suggestion()
            return ""
        ids = [entry.activity_id for entry in made]
        categories = []
        for entry in made:
            activity = next((a for a in self.ctx.activities if a.id == entry.activity_id), None)
            if activity is not None:
                categories.append(activity.category)
        verb, singular, plural = words_for(ids, categories)
        thumbs = [entry.thumbnail for entry in made if entry.thumbnail is not None]
        return descriptive_line(
            MadeSummary(
                count=len(made),
                verb=verb,
                singular=singular,
                plural=plural,
                colours=count_colours(thumbs) if thumbs else None,
            )
        )

    def _show_destination(self) -> str:
        """Put the chosen picture up, and return the headline that goes with it.

        The child's own plan if they made one; otherwise the picture goes and
        the headline is a warm line about the turn being over -- never a
        promise about the machine's return (D6).
        """
        chosen = self.ctx.next_after
        if chosen is None:
            self.next_after_icon.set_visible(False)
            return ALL_DONE_HEADLINE

        self.remove(self.next_after_icon)
        self.next_after_icon = icon_image(
            chosen.icon,
            chosen.icon_kind,
            self.ctx.metrics.mm(NEXT_AFTER_ICON_MM),
            fallback="kidnix-play",
        )
        self.next_after_icon.set_halign(Gtk.Align.CENTER)
        self.prepend(self.next_after_icon)
        self.next_after_icon.set_visible(True)
        return chosen.ready_line

    # -- kept for the tests and the screenshots --

    def continuation_line(self, made: list[Entry]) -> str:
        """Deprecated alias: what the screen now calls :meth:`made_words`."""
        return self.made_words(made)
