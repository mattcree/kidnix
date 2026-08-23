"""S4 -- My Things (the Journal).

A favourites shelf the child curates (bounded to 8), then Today / Yesterday /
Before as pages of thumbnail-dominant cards. Tapping a card *resumes* it --
Sugar's resume-not-open, the one great uncopied idea (08 section 2.1).

No delete anywhere, no search, no scrolling: big arrows and page dots only.
Day headings are spoken.
"""

from __future__ import annotations

from functools import partial
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gtk  # noqa: E402

from ..journal import Entry, build_pages  # noqa: E402
from ..theme import points_for  # noqa: E402
from ..voice import has_note  # noqa: E402
from ..widgets import (  # noqa: E402
    MIC_AGAIN_SPEAK,
    MIC_SPEAK,
    ChildButton,
    MicButton,
    Pager,
    big_label,
    icon_image,
    next_key,
    quiet_carousel,
)
from . import Screen  # noqa: E402

CARDS_PER_PAGE = 8
CARD_COLUMNS = 4

# S4's cards are deliberately caption-less: the card *is* the thumbnail (08
# section 4.3), and the only title we have for an entry carries a clock time
# ("Draw 14:32"), which there are no digits for anywhere in the child's shell.
# The title is spoken instead, in full. What is written on this screen is the
# headings and the empty state -- and those follow the same no-cut rule as
# every other child-facing label.


def _text_width(screen: Screen) -> int:
    """How wide a line of text may be on My Things before it must wrap."""
    metrics = screen.ctx.metrics
    across = metrics.screen_width or (CARD_COLUMNS * metrics.card_size + 3 * metrics.gap)
    return max(1, across - metrics.gap * 2)


class JournalScreen(Screen):
    name = "My Things"

    #: Set by the host for S7's "Show a grown-up": read-only, no resuming.
    showing_mode = False

    def build(self) -> None:
        metrics = self.ctx.metrics
        self.set_margin_start(metrics.gap)
        self.set_margin_end(metrics.gap)

        text_width = _text_width(self)
        self.shelf_heading = big_label(
            "My favourites",
            "shelf-heading",
            width=text_width,
            base_pt=points_for(metrics, ".shelf-heading"),
            floor_pt=metrics.label_floor_pt,
        )
        self.shelf_heading.set_halign(Gtk.Align.START)
        self.append(self.shelf_heading)

        self.shelf = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=metrics.gap)
        self.shelf.set_halign(Gtk.Align.START)
        self.append(self.shelf)

        self.carousel: Adw.Carousel = quiet_carousel()
        self.carousel.set_vexpand(True)
        self.append(self.carousel)

        self.empty = big_label(
            "Nothing here yet. Go and make something!",
            "big-line",
            width=text_width,
            base_pt=points_for(metrics, ".big-line"),
            floor_pt=metrics.label_floor_pt,
        )
        self.empty.set_vexpand(True)
        self.empty.set_valign(Gtk.Align.CENTER)
        self.append(self.empty)

        self.pager = Pager(metrics, self.ctx.speech_ui, self._on_page, what="things")
        self.pager.set_margin_bottom(metrics.gap)
        self.append(self.pager)

        # **"Tell me about it", in "Show a grown-up" mode** (spec 7d #9).
        #
        # Why only there, and why one button rather than one per card. A card
        # in the ordinary Journal *resumes* -- Sugar's one great uncopied idea
        # (08 section 2.1) -- so tapping one leaves this screen and there is no
        # "the card I am talking about" for a mic to mean. In showing mode the
        # cards are read-only, so tapping one selects it, and "Show a grown-up"
        # is exactly the moment a child wants to say what a thing is. One
        # button under the grid rather than one on each card because a card is
        # ~32 mm and already carries a full-size star: a third 20 mm target on
        # it would be three overlapping targets on one thumbnail.
        self.mic: MicButton | None = None
        self._note_entry: Entry | None = None
        if self.ctx.voice is not None:
            self.mic = MicButton(metrics, self.ctx.speech_ui, self._on_mic)
            self.mic.set_margin_bottom(metrics.gap)
            self.mic.set_visible(False)
            self.append(self.mic)

        self._pages: list[Gtk.Widget] = []
        self._page_labels: list[str] = []

    # -- content --

    def refresh(self) -> None:
        metrics = self.ctx.metrics

        while (child := self.shelf.get_first_child()) is not None:
            self.shelf.remove(child)
        for page in self._pages:
            self.carousel.remove(page)
        self._pages = []
        self._page_labels = []

        favourites = self.ctx.journal.favourites()
        self.shelf_heading.set_visible(bool(favourites))
        self.shelf.set_visible(bool(favourites))
        for entry in favourites:
            self.shelf.append(self._card(entry, size=int(metrics.card_size * 0.7)))

        groups = self.ctx.journal.grouped()
        has_entries = any(entries for _, entries in groups)
        self.empty.set_visible(not has_entries)
        self.carousel.set_visible(has_entries)
        if not has_entries:
            self.pager.set_pages(1, 0)
            return

        for items in build_pages(groups, CARDS_PER_PAGE):
            widget = self._page(items)
            self.carousel.append(widget)
            self._pages.append(widget)
            headings = [str(value) for kind, value in items if kind == "heading"]
            self._page_labels.append(headings[0] if headings else "")
        self.pager.set_pages(len(self._pages), 0)

    def _page(self, items: list[tuple[str, object]]) -> Gtk.Widget:
        metrics = self.ctx.metrics
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=metrics.gap)
        box.set_halign(Gtk.Align.CENTER)
        grid: Gtk.Grid | None = None
        index = 0

        for kind, value in items:
            if kind == "heading":
                heading = big_label(
                    str(value),
                    "day-heading",
                    width=_text_width(self),
                    base_pt=points_for(metrics, ".day-heading"),
                    floor_pt=metrics.label_floor_pt,
                )
                heading.set_halign(Gtk.Align.START)
                box.append(heading)
                grid = Gtk.Grid()
                grid.set_row_spacing(metrics.gap)
                grid.set_column_spacing(metrics.gap)
                box.append(grid)
                index = 0
            elif grid is not None and isinstance(value, Entry):
                grid.attach(
                    self._card(value, metrics.card_size),
                    index % CARD_COLUMNS,
                    index // CARD_COLUMNS,
                    1,
                    1,
                )
                index += 1
        return box

    def _card(self, entry: Entry, size: int) -> Gtk.Widget:
        """Thumbnail-dominant card with the activity icon and a star corner."""
        metrics = self.ctx.metrics
        overlay = Gtk.Overlay()

        card = ChildButton(
            # Not entry.title: what a child hears is the name *and* a
            # child-terms "when", with no clock in it (03 #32).
            speak_text=entry.spoken(),
            on_activate=partial(self._open, entry),
            speech_ui=self.ctx.speech_ui,
            css_classes=("card",),
            size=size,
            key=next_key(f"card-{entry.id}"),
        )
        card.set_child(self._thumbnail(entry, int(size * 0.86)))
        overlay.set_child(card)

        # Activity icon, bottom-left: shape says what it is.
        badge = icon_image(
            self._icon_name(entry.activity_id), "icon-name", max(24, int(size * 0.22))
        )
        badge.set_halign(Gtk.Align.START)
        badge.set_valign(Gtk.Align.END)
        badge.set_margin_start(6)
        badge.set_margin_bottom(6)
        overlay.add_overlay(badge)

        # Star, bottom-right. A full-size target of its own -- it must be
        # impossible to mean "star" and get "resume".
        star_size = max(metrics.min_target, int(size * 0.3))
        star = ChildButton(
            speak_text=self._star_text(entry),
            on_activate=partial(self._toggle_star, entry),
            speech_ui=self.ctx.speech_ui,
            css_classes=("star",),
            size=star_size,
            key=next_key(f"star-{entry.id}"),
        )
        star.set_child(
            icon_image(
                "kidnix-star-filled" if entry.starred else "kidnix-star",
                "icon-name",
                int(star_size * 0.7),
            )
        )
        star.set_halign(Gtk.Align.END)
        star.set_valign(Gtk.Align.END)
        overlay.add_overlay(star)

        # **The ear badge** (spec 7d #9): a small ear, top-right, on a card
        # that has a voice note behind it. A *badge*, not a control -- the card
        # is one target and adding a second small one on it would be two
        # things to hit inside 20 mm. Tapping the card is what plays the note
        # in "Show a grown-up" mode.
        if has_note(entry.directory):
            ear = icon_image("kidnix-ear", "icon-name", max(20, int(size * 0.18)))
            ear.add_css_class("note-badge")
            ear.set_halign(Gtk.Align.END)
            ear.set_valign(Gtk.Align.START)
            ear.set_margin_end(6)
            ear.set_margin_top(6)
            ear.set_accessible_role(Gtk.AccessibleRole.PRESENTATION)
            overlay.add_overlay(ear)
        return overlay

    def _thumbnail(self, entry: Entry, size: int) -> Gtk.Widget:
        thumb = entry.thumbnail
        if thumb is not None:
            picture = Gtk.Picture.new_for_filename(str(thumb))
            picture.set_content_fit(Gtk.ContentFit.COVER)
            picture.set_size_request(size, size)
            picture.set_can_shrink(True)
            return picture
        # No thumbnail (not an image): fall back to the activity's icon.
        return icon_image(self._icon_name(entry.activity_id), "icon-name", size)

    def _icon_name(self, activity_id: str) -> str:
        activity = next((a for a in self.ctx.activities if a.id == activity_id), None)
        if activity is None:
            return "image-missing"
        return activity.icon or "image-missing"

    @staticmethod
    def _star_text(entry: Entry) -> str:
        return "One of my favourites" if entry.starred else "Make this a favourite"

    # -- actions --

    def _open(self, entry: Entry) -> None:
        if self.showing_mode:
            # S7's showing mode is read-only: this is the child showing a
            # grown-up what they made, not starting something new. If they
            # recorded a note about this one, playing it back **is** the
            # showing -- the child's own voice saying what it is, which is
            # what the whole feature is for.
            self._select_for_note(entry)
            if self.ctx.voice is not None and self.ctx.voice.play(entry.directory):
                return
            self.ctx.speech.speak(entry.spoken())
            return
        self.ctx.host.resume_entry(entry)

    # -- the voice note --

    def _select_for_note(self, entry: Entry) -> None:
        """This is the thing the mic is about now. Only in showing mode."""
        if self.mic is None or not self.showing_mode:
            return
        self._note_entry = entry
        self.mic.set_visible(True)
        self.mic.set_recording(False)
        voice = self.ctx.voice
        if voice is not None:
            voice.on_state = self._mic_state
            voice.on_level = self._mic_level
            voice.on_saved = self._note_saved

    def _on_mic(self) -> None:
        voice, entry = self.ctx.voice, self._note_entry
        if voice is None or entry is None:
            return
        if voice.recording:
            voice.stop()
            return
        if has_note(entry.directory):
            # The whole of the retakes UI: one quiet word, and only when there
            # was already a note. A second recording replaces the first.
            self.ctx.speech.speak(MIC_AGAIN_SPEAK)
        voice.start(entry.directory)

    def _mic_state(self, recording: bool) -> None:
        if self.mic is not None:
            self.mic.set_recording(recording)

    def _mic_level(self, level: float) -> None:
        if self.mic is not None:
            self.mic.set_level(level)

    def _note_saved(self, _path: object) -> None:
        """Play it back once, then redraw so the card gets its ear."""
        entry = self._note_entry
        if entry is not None and self.ctx.voice is not None:
            self.ctx.voice.play(entry.directory)
            self.refresh()
            self._note_entry = entry

    def _toggle_star(self, entry: Entry) -> None:
        starred = self.ctx.journal.toggle_star(entry)
        self.ctx.speech.speak(
            "Added to my favourites." if starred else "Taken out of my favourites."
        )
        self.refresh()

    def undo_star(self) -> bool:
        """Band Undo routes here while My Things is open (spec section 2)."""
        favourites = self.ctx.journal.favourites()
        if not favourites:
            return False
        self.ctx.journal.set_starred(favourites[0], False)
        self.ctx.speech.speak("Taken out of my favourites.")
        self.refresh()
        return True

    def _on_page(self, page: int) -> None:
        if 0 <= page < len(self._pages):
            self.carousel.scroll_to(self._pages[page], True)
            label = self._page_labels[page]
            if label:
                self.ctx.speech.speak(label)

    # -- lifecycle --

    def on_enter(self) -> None:
        self.refresh()
        # Nothing is selected on arrival, so there is nothing for the mic to be
        # about yet: it appears when the child picks a thing to talk about.
        self._note_entry = None
        if self.mic is not None:
            self.mic.set_visible(False)
        count = len(self.ctx.journal.entries)
        if count == 0:
            self.ctx.speech.speak("My Things. Nothing here yet.")
        elif self.showing_mode:
            self.ctx.speech.speak_then("My Things.", MIC_SPEAK)
        else:
            self.ctx.speech.speak("My Things.")

    def on_leave(self) -> None:
        if self.ctx.voice is not None and self.ctx.voice.recording:
            self.ctx.voice.stop()

    def resume_path(self, entry: Entry) -> Path | None:
        return entry.latest_path
