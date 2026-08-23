"""The three pictures this activity draws: a face, a scribble, and the letter.

cairo and nothing else -- no GTK, no window, no display -- so every picture in
the activity, including the one that ends up in the Journal and in the outbox,
is exercised by the headless tests.

**1. The placeholder face.** A ``[[family]]`` entry with no photo (or a photo
that has been unplugged) is normal, and it must not show a broken-image icon to
a pre-reader. A head and shoulders in the shell's own colours is enough for a
child to tell "the tile with a person on it" from "the tile with a picture on
it", and the name is spoken beside it either way. There is deliberately **no
initial letter on it**: a tile whose only distinguishing mark is a grapheme is a
tile a four-year-old cannot use.

**2. The scribble.** :class:`letters_to_family.scribble.Scribble` rendered at
whatever size is asked for, with round caps and joins so a single press is a
round dot rather than an invisible zero-length line.

**3. The letter card.** The artefact. One PNG with the drawing, the child's own
words underneath **exactly as they were typed**, and who it is for at the top.
It is what a grown-up attaches to an email or prints and puts in an envelope,
and it is the thing in the Journal that makes the card in My Things mean
"a letter" rather than "a picture".

The card's typography carries one distinction and no judgements: the child's own
words are set large in Andika (the child-facing face, SYNTHESIS B6), and words a
grown-up wrote down for them are set smaller and lighter, because a reader must
be able to tell whose spelling they are looking at without being told which is
better. **Nothing here alters the text.** There is no capitalisation, no
sentence-casing, no ellipsis and no spell-check anywhere in this file; long text
wraps and, past what the card can hold, keeps going onto more lines and the card
grows. A child's letter is never truncated.
"""

from __future__ import annotations

import logging
from pathlib import Path

import cairo

from .i18n import N_, _
from .scribble import Scribble

log = logging.getLogger(__name__)

__all__ = [
    "CARD_HEIGHT",
    "CARD_WIDTH",
    "EDGE",
    "FOR_NAME",
    "INK",
    "PAPER",
    "PRIMARY",
    "SECONDARY",
    "draw_placeholder",
    "render_card",
    "render_scribble",
]

#: ``kidnix_shell/theme.css``, restated. ``tests/test_palette.py`` re-reads that
#: file and fails if these ever drift.
INK = (0x16 / 255, 0x18 / 255, 0x1D / 255)
PAPER = (0xFB / 255, 0xF7 / 255, 0xEF / 255)
PAPER_DIM = (0xEF / 255, 0xE8 / 255, 0xDA / 255)
EDGE = (0x7E / 255, 0x83 / 255, 0x8C / 255)
#: TRANSLATORS: the small label at the top of the letter card. {name} is a
#: person -- "for Grandad". Written on the card, not spoken.
FOR_NAME = N_("for {name}")

PRIMARY = (0x0F / 255, 0x8A / 255, 0x8A / 255)
SECONDARY = (0xF0 / 255, 0x62 / 255, 0x92 / 255)

#: One whole turn, in radians. Spelled once rather than at each `arc` call.
TAU = 2 * 3.141592653589793

#: The letter card. Portrait, because a letter is portrait, and because the
#: picture wants to be square with the words under it rather than beside it.
CARD_WIDTH = 720
CARD_HEIGHT = 960

#: The child-facing face (B6). Falls back through cairo's toy font selection to
#: whatever the machine has; the *shape* of the letters matters to a Reception
#: child and the fallback matters to a build container with no fonts at all.
CHILD_FONT = "Andika"
#: An adult's hand: what a grown-up wrote down, and the "for Grandad" line.
ADULT_FONT = "Atkinson Hyperlegible Next"


def _paper(ctx: cairo.Context, width: float, height: float) -> None:
    ctx.set_source_rgb(*PAPER)
    ctx.rectangle(0, 0, width, height)
    ctx.fill()


# -- 1. a face for a recipient with no photo ---------------------------------


def draw_placeholder(path: Path, size: int = 320) -> Path:
    """A head and shoulders, in the shell's colours. Returns ``path``.

    One drawing for everybody, on purpose. Generating a different colour per
    recipient would make the tile's identity a hue, and roughly 8% of boys are
    colour-blind (B6): the thing that tells Grandad from Nanna on this screen is
    the *name under the tile and the name in the child's ear*, which works for
    every child, and the picture says only "this is a person".

    Everything is clipped to the disc, including the shoulders. Clipping them to
    a rectangle instead is the obvious shortcut and it lets the shoulders spill
    out of the ring, which reads as a shape with a bite out of it rather than as
    somebody in a frame.
    """
    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, size, size)
    ctx = cairo.Context(surface)
    _paper(ctx, size, size)

    radius = size * 0.46
    line = max(2.0, size * 0.012)

    ctx.save()
    ctx.arc(size / 2, size / 2, radius - line / 2, 0, TAU)
    ctx.clip()

    ctx.set_source_rgb(*PAPER_DIM)
    ctx.paint()

    ctx.set_source_rgb(*PRIMARY)
    ctx.arc(size / 2, size * 0.40, size * 0.17, 0, TAU)
    ctx.fill()
    ctx.arc(size / 2, size * 0.95, size * 0.30, 0, TAU)
    ctx.fill()
    ctx.restore()

    ctx.set_source_rgb(*EDGE)
    ctx.set_line_width(line)
    ctx.arc(size / 2, size / 2, radius - line / 2, 0, TAU)
    ctx.stroke()

    path.parent.mkdir(parents=True, exist_ok=True)
    surface.write_to_png(str(path))
    return path


# -- 2. the scribble ---------------------------------------------------------


def draw_scribble(
    ctx: cairo.Context, scribble: Scribble, width: float, height: float
) -> None:
    """Paint a scribble into an existing context, at ``width`` x ``height``."""
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    ctx.set_line_join(cairo.LINE_JOIN_ROUND)
    line = max(3.0, min(width, height) * 0.018)
    ctx.set_line_width(line)
    for stroke in scribble.strokes:
        if not stroke.points:
            continue
        ctx.set_source_rgb(*stroke.colour.rgb)
        first_x, first_y = stroke.points[0]
        if len(stroke.points) == 1:
            # A press with no drag is a dot, and a dot is a mark the child
            # meant to make. A zero-length path strokes to nothing even with
            # round caps in some cairo builds, so it is drawn as a filled disc.
            ctx.arc(first_x * width, first_y * height, line / 2, 0, TAU)
            ctx.fill()
            continue
        ctx.move_to(first_x * width, first_y * height)
        for x, y in stroke.points[1:]:
            ctx.line_to(x * width, y * height)
        ctx.stroke()


def render_scribble(
    path: Path, scribble: Scribble, width: int = 720, height: int = 540
) -> Path:
    """Write a scribble to ``path`` as a PNG on plain paper. Returns ``path``."""
    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, width, height)
    ctx = cairo.Context(surface)
    _paper(ctx, width, height)
    draw_scribble(ctx, scribble, width, height)
    path.parent.mkdir(parents=True, exist_ok=True)
    surface.write_to_png(str(path))
    return path


# -- 3. the letter card ------------------------------------------------------


def _wrap(ctx: cairo.Context, text: str, width: float) -> list[str]:
    """Break ``text`` into lines that fit ``width``. **Cuts nothing.**

    Words longer than the line (which a five-year-old's spelling produces --
    ``ilovyougranddadverymuch`` -- and which a URL never will, because there are
    none here) are broken by character rather than ellipsised, because the
    letter has to carry every letter the child wrote.
    """
    lines: list[str] = []
    for paragraph in text.splitlines() or [""]:
        current = ""
        for word in paragraph.split(" "):
            candidate = f"{current} {word}" if current else word
            if not candidate or ctx.text_extents(candidate).x_advance <= width:
                current = candidate
                continue
            if current:
                lines.append(current)
                current = ""
            # The word alone is too wide: break it, character by character.
            piece = ""
            for character in word:
                trial = piece + character
                if piece and ctx.text_extents(trial).x_advance > width:
                    lines.append(piece)
                    piece = character
                else:
                    piece = trial
            current = piece
        lines.append(current)
    return lines


def render_card(
    path: Path,
    picture: Path | None,
    caption: str,
    recipient_name: str,
    *,
    child_hand: bool = True,
    width: int = CARD_WIDTH,
    height: int = CARD_HEIGHT,
) -> Path:
    """The whole letter as one picture. Returns ``path``.

    ``caption`` is drawn **exactly as it was given**: this function does not
    strip it, case it, correct it or shorten it, and the only thing it does to
    it is decide where the lines break. ``child_hand`` picks the face -- the
    child's own words in Andika, a grown-up's transcription smaller and lighter
    -- and changes nothing else.
    """
    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, width, height)
    ctx = cairo.Context(surface)
    _paper(ctx, width, height)

    margin = width * 0.07
    inner = width - margin * 2

    # "for Grandad", small, at the top. An adult's hand, because it is a label
    # on the letter rather than part of what the child said.
    ctx.select_font_face(ADULT_FONT, cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
    ctx.set_font_size(width * 0.045)
    ctx.set_source_rgb(*EDGE)
    heading = _(FOR_NAME).format(name=recipient_name)
    ctx.move_to(margin, margin)
    ctx.show_text(heading)

    top = margin * 1.6
    picture_height = height * 0.52
    ctx.set_source_rgb(*PAPER_DIM)
    ctx.rectangle(margin, top, inner, picture_height)
    ctx.fill()

    if picture is not None and picture.is_file():
        try:
            image = cairo.ImageSurface.create_from_png(str(picture))
        except (OSError, cairo.Error) as exc:
            log.warning("could not put %s on the letter card (%s)", picture, exc)
        else:
            source_width = image.get_width() or 1
            source_height = image.get_height() or 1
            scale = min(inner / source_width, picture_height / source_height)
            offset_x = margin + (inner - source_width * scale) / 2
            offset_y = top + (picture_height - source_height * scale) / 2
            ctx.save()
            ctx.translate(offset_x, offset_y)
            ctx.scale(scale, scale)
            ctx.set_source_surface(image, 0, 0)
            ctx.paint()
            ctx.restore()

    ctx.set_source_rgb(*EDGE)
    ctx.set_line_width(max(2.0, width * 0.004))
    ctx.rectangle(margin, top, inner, picture_height)
    ctx.stroke()

    if caption:
        if child_hand:
            ctx.select_font_face(CHILD_FONT, cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
            ctx.set_font_size(width * 0.070)
            ctx.set_source_rgb(*INK)
        else:
            ctx.select_font_face(ADULT_FONT, cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
            ctx.set_font_size(width * 0.048)
            ctx.set_source_rgb(*EDGE)
        extents = ctx.font_extents()
        line_height = extents[2] * 1.18
        y = top + picture_height + margin * 0.9 + extents[0]
        for line in _wrap(ctx, caption, inner):
            ctx.move_to(margin, y)
            ctx.show_text(line)
            y += line_height

    path.parent.mkdir(parents=True, exist_ok=True)
    surface.write_to_png(str(path))
    return path
