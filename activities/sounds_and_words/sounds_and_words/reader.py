"""The Read it screens: a shelf, a book, and one sentence at a time.

The pure half of this module is next door in :mod:`sounds_and_words.reading` --
which books a ceiling admits, how a book paginates, which drawing goes with a
line, and when each word lights up. This file is the wiring, and the wiring is
the part that needs a display to test.

What is deliberately absent
---------------------------

Takacs, Swart & Bus (2015) `[META, 43 studies, 2,147 children]` is the clearest
negative finding in this literature: narration with congruent illustration
helps, and **hotspots, tap-to-animate, embedded mini-games and tap-a-word
dictionaries hurt**. So, on this screen:

* **the sentence is one label.** Not one button per word, not a flow box of
  selectable children -- one ``Gtk.Label`` with markup. A child can tap any
  word on this screen as hard as they like and nothing will happen, because
  there is nothing there to happen. That is not restraint applied by a rule; it
  is restraint applied by there being no widget.
* **the picture is a ``Gtk.Picture``**, which is not a control either. It fades
  in and it does nothing else -- research 10 section 4.1 E's "congruent, gentle
  illustration motion only" -- and calm mode takes even the fade
  (``activity.css``).
* there is no dictionary, no game, no star, no page number, and no reward of
  any kind. What a child gets at the end of a book is a card with the book's
  name on it and a grown-up being asked to listen.

The three controls
------------------

*back*, *next* and *read it to me*. All three are
:class:`~kidnix_activity.widgets.BigButton`, so all three are 40 mm of real
panel (ADR-0011's primary target, comfortably over the 20 mm floor), fire on
press, cannot double-fire, and carry a picture, a word and a sentence in the
ear. **The narration button is never a gate**: the child can read the whole
book without it, or press it on every page. Whether it is there at all is the
parent's ``[read] narration`` (:class:`sounds_and_words.settings.Narration`).
"""

from __future__ import annotations

import logging
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import GLib, Gtk  # noqa: E402
from kidnix_activity.app import ActivityWindow  # noqa: E402
from kidnix_activity.metrics import ContentArea  # noqa: E402
from kidnix_activity.widgets import BigButton, GrownUpTurn, PictureTile, Prompt  # noqa: E402
from kidnix_shell.widgets import next_key  # noqa: E402

from .i18n import _  # noqa: E402
from .reading import (  # noqa: E402
    SHELF_PER_PAGE,
    Page,
    ReadingText,
    WordSpan,
    illustration_for,
    shelf_pages,
    word_spans,
)
from .settings import Narration  # noqa: E402
from .text import (  # noqa: E402
    LISTEN_LABEL,
    LISTEN_SPEAK,
    NEXT_LABEL,
    NEXT_SPEAK,
    PAGE_BACK_LABEL,
    PAGE_BACK_SPEAK,
    PAGE_NEXT_LABEL,
    PAGE_NEXT_SPEAK,
    SHELF_BACK_SPEAK,
    SHELF_NEXT_SPEAK,
    SHELF_TILE_SPEAK,
)

log = logging.getLogger(__name__)

__all__ = ["BookShelf", "ReadIt", "build_read_it", "build_shelf"]

#: The sentence. Research 10 section 4.1 E asks for "big"; ADR-0011 and
#: SYNTHESIS B4 ask for a floor that a small panel cannot erode. 34 pt
#: preferred, **28 pt floor**, which is half again the 18 pt floor the SDK
#: applies to ordinary child-facing text -- this is the text a child is
#: decoding letter by letter, not a label they are glancing at.
READING_PT = 34.0
READING_MIN_PT = 28.0

#: The drawing above the sentence. Big enough to be looked at, small enough
#: that the sentence is still the thing on the screen.
PICTURE_MM = 48.0
#: The shelf's covers. ADR-0011's picture tile, and a title under each one.
COVER_MM = 34.0

#: How long the "lit" word stays lit past its own span before the next tick
#: takes over. Nothing depends on it; it is the tolerance on an estimate.
HIGHLIGHT_TAIL_MS = 60


#: The interface drawings. Beside the module, inside the package, like the
#: scenes and the fifteen nouns -- so a wheel carries them.
ICON_DIR = Path(__file__).resolve().parent / "icons"


def _icon(name: str) -> str:
    return str(ICON_DIR / f"{name}.svg")


def _icon_button(
    window: ActivityWindow,
    icon: str,
    label: str,
    speak: str,
    on_activate,
    *,
    size_mm: float = 40.0,
) -> BigButton:
    return BigButton(
        label,
        icon=_icon(icon),
        speak_text=speak,
        on_activate=on_activate,
        speech=window.speech,
        area=window.area,
        icon_kind="path",
        size_mm=size_mm,
    )


def _illustration(area: ContentArea, name: str, millimetres: float) -> Gtk.Widget:
    """The drawing for one line. A picture, never a control.

    A name with no file behind it gets an empty box rather than a broken frame:
    a child reading a sentence should not be shown a hole where a drawing was
    meant to be, and the *test* that the file is missing is a test, not a
    screen.
    """
    picture = Gtk.Picture()
    picture.add_css_class("reading-picture")
    picture.set_can_shrink(True)
    picture.set_content_fit(Gtk.ContentFit.CONTAIN)
    path = illustration_for(name)
    if path is not None:
        picture.set_filename(str(path))
    else:  # pragma: no cover - a test asserts the list of these is empty
        log.warning("no drawing called %r; the line is shown without one", name)
    size = area.target(millimetres)
    picture.set_size_request(size, size)
    picture.set_halign(Gtk.Align.CENTER)
    return picture


# -- the shelf ---------------------------------------------------------------


class BookShelf:
    """Which book. Five to a page, a picture and a title on each.

    ADR-0013: this is a **choice** the child has to weigh, not a labelled grid
    whose items are the task, so the five-choice ceiling binds and a longer
    shelf pages rather than growing. The tiles speak their own title on hover
    and on focus, which is
    :class:`~kidnix_shell.widgets.ChildButton`'s behaviour and not something
    this screen arranges: a child sweeping the shelf hears what each book is
    called without having to open one.
    """

    def __init__(self, owner, texts: list[ReadingText], on_choose) -> None:
        self.owner = owner
        self.pages = shelf_pages(texts, per_page=SHELF_PER_PAGE)
        self.on_choose = on_choose
        self.index = 0
        self.tiles: list[PictureTile] = []
        self.shelf: Gtk.Box | None = None
        self.column: Gtk.Box | None = None
        self.back: BigButton | None = None
        self.forward: BigButton | None = None

    @property
    def books(self) -> tuple[ReadingText, ...]:
        return self.pages[self.index] if self.pages else ()

    def build(self, window: ActivityWindow) -> Gtk.Widget:
        area = window.area
        self.column = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=area.gap)
        self.column.set_vexpand(True)

        self.prompt = Prompt(
            self.owner.child_text("pick_a_book"),
            speech=window.speech,
            area=area,
        )
        self.column.append(self.prompt)

        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=area.gap)
        row.set_halign(Gtk.Align.CENTER)
        row.set_valign(Gtk.Align.CENTER)
        row.set_vexpand(True)

        if len(self.pages) > 1:
            self.back = _icon_button(
                window, "back", _(PAGE_BACK_LABEL), _(SHELF_BACK_SPEAK), self.previous_page
            )
            row.append(self.back)

        self.shelf = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=area.gap)
        self.shelf.set_halign(Gtk.Align.CENTER)
        row.append(self.shelf)

        if len(self.pages) > 1:
            self.forward = _icon_button(
                window, "next", _(PAGE_NEXT_LABEL), _(SHELF_NEXT_SPEAK), self.next_page
            )
            row.append(self.forward)

        self.column.append(row)
        self.fill(window)
        return self.column

    def fill(self, window: ActivityWindow) -> None:
        """Put this page of books on the shelf. Called again on every turn."""
        if self.shelf is None:  # pragma: no cover - build() has always run
            return
        child = self.shelf.get_first_child()
        while child is not None:
            following = child.get_next_sibling()
            self.shelf.remove(child)
            child = following
        self.tiles = []

        area = window.area
        for book in self.books:
            path = illustration_for(book.cover)
            tile = PictureTile(
                path if path is not None else "",
                # TRANSLATORS: what a book says when the child hovers it.
                _(SHELF_TILE_SPEAK).format(title=book.title),
                label=book.title,
                on_activate=lambda chosen=book: self.choose(chosen),
                speech=window.speech,
                area=area,
                size_mm=COVER_MM,
                css_classes=("book",),
                key=next_key("book"),
            )
            self.tiles.append(tile)
            self.shelf.append(tile)
        self.update_arrows()
        window.keys.set_content(window.content)

    def update_arrows(self) -> None:
        """Grey the arrow that would go nowhere, rather than wrapping around.

        A shelf that wrapped would be a shelf a child could walk round for ever
        without noticing they had seen everything.
        """
        if self.back is not None:
            self.back.set_sensitive(self.index > 0)
        if self.forward is not None:
            self.forward.set_sensitive(self.index < len(self.pages) - 1)

    def next_page(self) -> None:
        if self.index < len(self.pages) - 1:
            self.index += 1
            self.fill(self.owner.window)

    def previous_page(self) -> None:
        if self.index > 0:
            self.index -= 1
            self.fill(self.owner.window)

    def choose(self, book: ReadingText) -> None:
        self.on_choose(book)

    def announce(self) -> None:
        self.owner.window.speak(self.prompt.text)


def build_shelf(window: ActivityWindow, owner, texts: list[ReadingText], on_choose) -> BookShelf:
    """Put the shelf on the screen. Returns it, for the tests."""
    screen = BookShelf(owner, texts, on_choose)
    window.clear()
    window.add(screen.build(window))
    window.keys.set_content(window.content)
    return screen


# -- the book ----------------------------------------------------------------


class ReadIt:
    """One book, one sentence to a page, and the end of it.

    The state is two integers -- which page, and which word is lit -- and both
    of them are readable from a test without a main loop, which is what makes
    the highlight arithmetic in :mod:`sounds_and_words.reading` provable rather
    than merely plausible.
    """

    def __init__(self, owner, text: ReadingText, *, narration: Narration = Narration.OPTIONAL, on_done=None) -> None:
        self.owner = owner
        self.text = text
        self.narration = narration
        self.on_done = on_done
        self.index = 0
        self.lit: int | None = None
        self.finished = False
        self.column: Gtk.Box | None = None
        self.body: Gtk.Box | None = None
        self.picture: Gtk.Widget | None = None
        self.line: Gtk.Label | None = None
        self.listen: BigButton | None = None
        self.back: BigButton | None = None
        self.forward: BigButton | None = None
        self._sources: list[int] = []

    # -- where we are --

    @property
    def page(self) -> Page:
        return self.text.pages[min(self.index, len(self.text) - 1)]

    @property
    def points(self) -> float:
        """The sentence's point size. Never under :data:`READING_MIN_PT`."""
        area = self.owner.window.area
        return max(READING_MIN_PT, area.points(READING_PT))

    # -- the widgets --

    def build(self, window: ActivityWindow) -> Gtk.Widget:
        area = window.area
        self.column = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=area.gap)
        self.column.add_css_class("reading")
        self.column.set_vexpand(True)

        self.body = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=area.gap)
        self.body.set_valign(Gtk.Align.CENTER)
        self.body.set_vexpand(True)
        self.column.append(self.body)

        controls = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=area.gap)
        controls.set_halign(Gtk.Align.CENTER)
        self.back = _icon_button(
            window, "back", _(PAGE_BACK_LABEL), _(PAGE_BACK_SPEAK), self.previous_page
        )
        controls.append(self.back)
        if self.narration.offers_button:
            self.listen = _icon_button(
                window, "listen", _(LISTEN_LABEL), _(LISTEN_SPEAK), self.read_aloud
            )
            controls.append(self.listen)
        self.forward = _icon_button(
            window, "next", _(PAGE_NEXT_LABEL), _(PAGE_NEXT_SPEAK), self.next_page
        )
        controls.append(self.forward)
        self.column.append(controls)

        self.show_page(window)
        return self.column

    def show_page(self, window: ActivityWindow | None = None) -> None:
        """Draw the current page. The only thing that changes the screen."""
        window = window or self.owner.window
        if self.body is None:  # pragma: no cover - build() has always run
            return
        self.cancel_highlight()
        child = self.body.get_first_child()
        while child is not None:
            following = child.get_next_sibling()
            self.body.remove(child)
            child = following

        area = window.area
        page = self.page
        self.picture = _illustration(area, page.picture, PICTURE_MM)
        self.body.append(self.picture)

        self.line = Gtk.Label()
        self.line.add_css_class("reading-line")
        self.line.set_wrap(True)
        self.line.set_justify(Gtk.Justification.CENTER)
        self.line.set_xalign(0.5)
        self.line.set_max_width_chars(28)
        # **One label, not one widget per word.** See the module docstring: the
        # absence of a per-word widget is what makes tapping a word do nothing.
        self.lit = None
        self.render_line()
        self.body.append(self.line)

        if self.back is not None:
            self.back.set_sensitive(not page.first)
        window.keys.set_content(window.content)

        if self.narration.speaks_on_arrival:
            self.read_aloud()

    def render_line(self) -> None:
        """Set the sentence, with the lit word marked, as Pango markup."""
        if self.line is None:  # pragma: no cover
            return
        self.line.set_markup(self.markup())

    def markup(self) -> str:
        """The sentence as markup: the size, and the highlight if there is one.

        The size is in the markup rather than in CSS because a point size is
        derived from millimetres of real panel and a CSS pixel is not -- the
        same reason :func:`sounds_and_words.activity._letter_label` computes
        its own. The family stays in CSS, where a missing Andika can fall back
        through a stack.
        """
        size = int(self.points * 1024)
        parts = []
        for index, word in enumerate(self.page.words):
            escaped = GLib.markup_escape_text(word)
            if index == self.lit:
                parts.append(f'<span background="#ffd23f">{escaped}</span>')
            else:
                parts.append(escaped)
        return f'<span size="{size}">{" ".join(parts)}</span>'

    # -- narration and the highlight --

    def spans(self) -> tuple[WordSpan, ...]:
        """When each word of this page lights up. Approximate, and says so."""
        access = self.owner.access
        rate = -20 if access is None else access.effective_speech_rate
        return word_spans(self.page.sentence, rate=rate)

    def read_aloud(self) -> None:
        """Say the sentence, and run the highlight along it.

        The caption strip shows the same words that are already on the screen,
        which everywhere else in kidnix would be redundant and here is exactly
        right: the child is *reading* this sentence, so the words being written
        down is the content, not a spoiler.
        """
        if self.narration is Narration.NEVER:
            return
        self.owner.window.speak(self.page.sentence)
        self.start_highlight()

    def start_highlight(self) -> None:
        """One timeout per word, plus one to put the line back as it was.

        A timer per word rather than a tick: there are at most a dozen of them,
        cancelling is a list of source ids, and nothing has to hold a clock.
        """
        self.cancel_highlight()
        spans = self.spans()
        for span in spans:
            self._sources.append(
                self.owner.after(span.start_ms, lambda index=span.index: self.highlight(index))
            )
        if spans:
            end = spans[-1].end_ms + HIGHLIGHT_TAIL_MS
            self._sources.append(self.owner.after(end, lambda: self.highlight(None)))

    def highlight(self, index: int | None) -> None:
        """Light one word, or none. The whole of what the highlight does."""
        self.lit = index
        self.render_line()

    def cancel_highlight(self) -> None:
        """Stop the highlight. A child who has turned the page is not waiting."""
        for source in self._sources:
            GLib.source_remove(source)
        self._sources = []
        if self.lit is not None:
            self.lit = None
            self.render_line()

    # -- turning the page --

    def next_page(self) -> None:
        if self.index >= len(self.text) - 1:
            self.finish()
            return
        self.index += 1
        self.show_page()

    def previous_page(self) -> None:
        if self.index <= 0:
            return
        self.index -= 1
        self.show_page()

    def finish(self) -> None:
        """The end of the book: hand it to a person, and keep the card.

        Not a "well done", not a count of pages, not a star. The card is the
        thing the child made -- a book with its name on it -- and the card is
        kept **here**, at the end of the book, rather than at the end of the
        session: a child who stops halfway through has not read it, and a
        Journal entry saying they did would be a lie about a person.
        """
        if self.finished:
            return
        self.finished = True
        self.cancel_highlight()
        window = self.owner.window
        area = window.area
        window.clear()

        window.add(
            Prompt(self.owner.child_text("read_it"), speech=window.speech, area=area)
        )
        kept = self.owner.keep_reading(self.text)
        if kept is not None:
            card = Gtk.Picture()
            card.add_css_class("word-picture")
            card.set_can_shrink(True)
            card.set_content_fit(Gtk.ContentFit.CONTAIN)
            card.set_filename(str(kept))
            card.set_vexpand(True)
            window.add(card)

        window.add(
            GrownUpTurn(
                self.owner.grown_up_read_body(),
                title=self.owner.grown_up_title(),
                speech=window.speech,
                area=area,
            )
        )
        onwards = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=area.gap)
        onwards.set_halign(Gtk.Align.CENTER)
        onwards.append(
            _icon_button(window, "next", _(NEXT_LABEL), _(NEXT_SPEAK), self._onwards)
        )
        window.add(onwards)
        window.keys.set_content(window.content)
        window.speak(self.owner.child_text("read_it"))

    def _onwards(self) -> None:
        if self.on_done is not None:
            self.on_done()


def build_read_it(
    window: ActivityWindow,
    owner,
    text: ReadingText,
    *,
    narration: Narration = Narration.OPTIONAL,
    on_done=None,
) -> ReadIt:
    """Put one book on the screen at its first page. Returns it, for the tests."""
    screen = ReadIt(owner, text, narration=narration, on_done=on_done)
    window.clear()
    window.add(screen.build(window))
    window.keys.set_content(window.content)
    return screen
