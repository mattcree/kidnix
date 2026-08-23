"""The one thing the child takes away: the words they read today, on a card.

Research 10 section 4.4, and it is the whole of the "showing progress" design:
**to the child, nothing numeric, ever.** No score, no star, no percentage, no
streak, no level. *"What he sees at the end is the thing he made."* For a
literacy session the thing he made is a short list of words he got through, set
in the same letterforms he read them in, and kept in My Things beside his
drawings -- where a grown-up will see it and, with luck, ask him to read it out.

So the card carries the words and nothing else. Not a count of them, not a date
(01 #19 / 03 #32: **no digits where a child can see or hear them** -- the shell
draws the day heading itself, in My Things, for the adult), not a tick, and not
a "well done". The numbers that exist -- which GPCs, which words, what day --
go into ``meta.json``, which is for the parent pane in week 5 and for whoever
is debugging this, and which no child ever opens.

Two halves, on purpose
----------------------

:func:`caption_for`, :func:`meta_for` and :func:`layout` are pure: they decide
what the card *says* and can be tested with no display, no GTK and no fonts.
:func:`render_card` is the drawing, and it needs Pango and cairo -- both of
which are on the image already and neither of which needs a display, so its
test is an ordinary headless one that skips only where PyGObject is absent.

**Andika**, because that is what the child read the words in (SYNTHESIS B6, and
``build_files/36-fonts.sh`` installs it): single-storey ``a`` and ``g``, wide
apertures, and letterforms drawn for beginning readers rather than for print.
The family falls back through the stack if it is somehow not installed, and
:func:`font_is_andika` reports which one actually got used, so a card set in
DejaVu is a visible fact rather than a silent one.
"""

from __future__ import annotations

import logging
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from .i18n import _

__all__ = [
    "CARD_HEIGHT",
    "CARD_WIDTH",
    "ReadingSummary",
    "SummaryCard",
    "caption_for",
    "font_is_andika",
    "layout",
    "meta_for",
    "read_caption_for",
    "read_meta_for",
    "render_card",
    "render_read_card",
]

log = logging.getLogger(__name__)

#: A card, in pixels. Landscape, because the words run across; big enough that
#: the shell's 256 px thumbnailer has something to work from and small enough
#: that generating one is instant.
CARD_WIDTH = 960
CARD_HEIGHT = 600

#: Ink on cream, from the shell's own palette, so a Sounds & Words card sits in
#: My Things next to a hello_draw square without either looking like a visitor.
INK = (0x16 / 255, 0x18 / 255, 0x1D / 255)
CREAM = (0xFA / 255, 0xF6 / 255, 0xEE / 255)
RULE = (0x0F / 255, 0x8A / 255, 0x8A / 255)

#: The child-facing family, with the fallbacks that keep a missing font from
#: becoming a missing card.
FONT_FAMILY = "Andika, Atkinson Hyperlegible Next, sans-serif"

#: Three words to a line reads as a list; five reads as a paragraph.
WORDS_PER_LINE = 3


@dataclass(frozen=True)
class SummaryCard:
    """What was practised today, as data. The PNG is a rendering of this."""

    words: tuple[str, ...] = ()
    gpcs: tuple[str, ...] = ()
    day: date | None = None
    #: Which ceiling this session ran under. For the parent pane, never shown.
    ceiling_label: str = ""

    @property
    def empty(self) -> bool:
        """A session where nothing was blended. It still gets a card, saying so."""
        return not self.words


def caption_for(words: Sequence[str]) -> str:
    """``"Read today: cat, sat, pin"``.

    One line, the child's own words in the order they met them, and no count --
    "3 words" would be a score with a friendly face on it.
    """
    kept = [word.strip().lower() for word in words if word and word.strip()]
    if not kept:
        # TRANSLATORS: the caption of a session where nothing was blended. It
        # must not sound like a failure -- the child did work, it just was not
        # whole words.
        return _("Some sounds today")
    # TRANSLATORS: the Journal caption. `{words}` is the child's own word list,
    # comma-separated and never counted. Keep the placeholder last if your
    # language allows it; the words are the point of the sentence.
    return _("Read today: {words}").format(words=", ".join(kept))


def meta_for(card: SummaryCard) -> dict:
    """What goes in ``meta.json``. For the grown-up, and for us.

    JSON-serialisable throughout, because ``save_entry`` checks that before it
    copies anything and a card that failed there would be a card the child lost.
    """
    return {
        "gpcs_practised": list(card.gpcs),
        "words": list(card.words),
        "date": (card.day or date.today()).isoformat(),
        "ceiling": card.ceiling_label,
    }


def layout(words: Sequence[str], *, per_line: int = WORDS_PER_LINE) -> tuple[tuple[str, ...], ...]:
    """Break the words into lines. The only arithmetic on the card."""
    kept = [word.strip().lower() for word in words if word and word.strip()]
    per_line = max(1, per_line)
    return tuple(tuple(kept[start : start + per_line]) for start in range(0, len(kept), per_line))


# -- the drawing ------------------------------------------------------------


def font_is_andika(size_pt: float = 48.0) -> bool:
    """Did the requested family actually resolve to Andika on this machine?

    A card set in a fallback font is not a failure -- it is still the words --
    but it is a thing a reviewer should be told rather than have to notice.
    """
    try:
        import gi

        gi.require_version("Pango", "1.0")
        gi.require_version("PangoCairo", "1.0")
        from gi.repository import Pango, PangoCairo

        context = PangoCairo.font_map_get_default().create_context()
        description = Pango.FontDescription(f"{FONT_FAMILY} {size_pt:.0f}")
        font = PangoCairo.font_map_get_default().load_font(context, description)
        if font is None:  # pragma: no cover - no fonts at all
            return False
        described = font.describe()
        return (described.get_family() or "").lower().startswith("andika")
    except Exception as exc:  # pragma: no cover - no PyGObject, no Pango
        log.debug("could not ask Pango which font it used: %s", exc)
        return False


def render_card(
    card: SummaryCard,
    path: Path,
    *,
    width: int = CARD_WIDTH,
    height: int = CARD_HEIGHT,
) -> Path:
    """Draw the words card to ``path`` as a PNG. Returns the path.

    Raises :class:`RuntimeError` when the drawing stack is missing, and the
    caller's job is then to keep the session's *history* and skip the card --
    losing the picture is bad, refusing to end the session is worse.
    """
    lines = layout(card.words)
    # TRANSLATORS: the small heading on the card the child keeps, set in
    # lowercase because every child-facing letterform in this activity is.
    # The words under it are the child's own and are never translated.
    heading = _("read today")
    empty = _("some sounds today")
    body = [heading, *(" ".join(line) for line in lines)] if lines else [empty]
    return _draw_card(path, body, width=width, height=height)


def _draw_card(
    path: Path,
    body: list[str],
    *,
    width: int = CARD_WIDTH,
    height: int = CARD_HEIGHT,
) -> Path:
    """Cream, a teal rule down the leading edge, and these lines on it.

    Both cards this activity keeps go through here, which is why they look like
    each other in My Things: one heading set small so an adult can tell what
    they are looking at from across the room, and the child's own words set
    large underneath, because the words are the artefact.
    """
    try:
        import cairo
        import gi

        gi.require_version("Pango", "1.0")
        gi.require_version("PangoCairo", "1.0")
        from gi.repository import Pango, PangoCairo
    except Exception as exc:  # pragma: no cover - exercised only off-image
        raise RuntimeError(f"cannot draw the summary card: {exc}") from exc

    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, width, height)
    context = cairo.Context(surface)

    context.set_source_rgb(*CREAM)
    context.paint()

    # A rule down the leading edge, the same device the grown-up card uses, so
    # the two obviously come from the same activity.
    context.set_source_rgb(*RULE)
    context.rectangle(0, 0, max(6, width // 90), height)
    context.fill()

    margin = width // 12
    usable = width - margin * 2
    sizes = (
        [width // 34, *(width // 12 for _ in body[1:])] if len(body) > 1 else [width // 20]
    )

    total = 0.0
    layouts = []
    for text, size in zip(body, sizes, strict=False):
        pango_layout = PangoCairo.create_layout(context)
        pango_layout.set_font_description(Pango.FontDescription(f"{FONT_FAMILY} {size}"))
        pango_layout.set_text(text, -1)
        pango_layout.set_width(usable * Pango.SCALE)
        pango_layout.set_alignment(Pango.Alignment.LEFT)
        # Not `_`: that name belongs to gettext everywhere in this package.
        _ink, logical = pango_layout.get_pixel_extents()
        layouts.append((pango_layout, logical.height))
        total += logical.height

    spacing = max(8, height // 40)
    total += spacing * max(0, len(layouts) - 1)
    y = max(margin / 2, (height - total) / 2)

    context.set_source_rgb(*INK)
    for pango_layout, line_height in layouts:
        context.move_to(margin, y)
        PangoCairo.show_layout(context, pango_layout)
        y += line_height + spacing

    path.parent.mkdir(parents=True, exist_ok=True)
    surface.write_to_png(str(path))
    log.info("summary card: %s (%s)", path, "Andika" if font_is_andika() else "fallback font")
    return path


# -- the other card: the book that was read ---------------------------------


def read_caption_for(title: str) -> str:
    """``"I read: a trip to nan"``.

    First person, because the child is the one who did it and the card is
    theirs; the title in their own lowercase letterforms, because that is what
    was on the screen. No date and no count -- the shell draws the day heading
    itself, for the adult (01 #19: no digits where a child can see them).
    """
    # TRANSLATORS: the Journal caption for a book the child read. `{title}` is
    # the book's own name and is never translated -- these are en-GB phonics
    # texts, and a French kidnix would need its own, not these ones rendered.
    return _("I read: {title}").format(title=(title or "").strip())


def read_meta_for(
    title: str,
    *,
    slug: str = "",
    phase: int = 0,
    words: Sequence[str] = (),
    day: date | None = None,
    ceiling_label: str = "",
) -> dict:
    """``meta.json`` for a book. For the parent pane, and for whoever debugs this.

    ``words`` is every distinct word in the book. It is the thing a grown-up
    can actually read off the card and recognise -- "he read *farmyard*" is
    information; "82% fluency" would be a claim nobody here is entitled to
    make.
    """
    return {
        "title": (title or "").strip(),
        "slug": slug,
        "phase": phase,
        "words": [word for word in words],
        "date": (day or date.today()).isoformat(),
        "ceiling": ceiling_label,
    }


def render_read_card(
    title: str,
    path: Path,
    *,
    width: int = CARD_WIDTH,
    height: int = CARD_HEIGHT,
) -> Path:
    """Draw the "I read this" card: a small heading and the book's title.

    Same cream, same rule, same letterforms as the words card, because the two
    sit next to each other in My Things and a child should be able to see at a
    glance that they came from the same place.
    """
    # TRANSLATORS: the small heading on the card a child keeps after reading a
    # book, set in lowercase like every child-facing letterform here. The title
    # under it is the book's own name and is not translated.
    return _draw_card(path, [_("i read"), (title or "").strip()], width=width, height=height)


@dataclass
class ReadingSummary:
    """Convenience: the caption, the meta and the card for one book."""

    title: str
    slug: str = ""
    phase: int = 0
    words: tuple[str, ...] = ()
    day: date | None = None
    ceiling_label: str = ""
    path: Path | None = field(default=None)

    @property
    def caption(self) -> str:
        return read_caption_for(self.title)

    @property
    def meta(self) -> dict:
        return read_meta_for(
            self.title,
            slug=self.slug,
            phase=self.phase,
            words=self.words,
            day=self.day,
            ceiling_label=self.ceiling_label,
        )

    def write(self, path: Path) -> Path:
        self.path = render_read_card(self.title, path)
        return self.path


@dataclass
class Summary:
    """Convenience: build the card, the caption and the meta from one session."""

    words: tuple[str, ...] = ()
    gpcs: tuple[str, ...] = ()
    day: date | None = None
    ceiling_label: str = ""
    #: Set by :meth:`write` once the PNG exists.
    path: Path | None = field(default=None)

    @property
    def card(self) -> SummaryCard:
        return SummaryCard(self.words, self.gpcs, self.day, self.ceiling_label)

    @property
    def caption(self) -> str:
        return caption_for(self.words)

    @property
    def meta(self) -> dict:
        return meta_for(self.card)

    def write(self, path: Path) -> Path:
        self.path = render_card(self.card, path)
        return self.path
