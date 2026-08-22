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
from ..widgets import (  # noqa: E402
    ChildButton,
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
            speak_text=entry.speak_text,
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
            # grown-up what they made, not starting something new.
            self.ctx.speech.speak(entry.title)
            return
        self.ctx.host.resume_entry(entry)

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
        count = len(self.ctx.journal.entries)
        if count == 0:
            self.ctx.speech.speak("My Things. Nothing here yet.")
        else:
            self.ctx.speech.speak("My Things.")

    def resume_path(self, entry: Entry) -> Path | None:
        return entry.latest_path
