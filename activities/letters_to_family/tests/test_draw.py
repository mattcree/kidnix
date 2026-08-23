"""The three pictures, drawn without a display.

cairo only -- so the letter card, the placeholder face and the scribble are all
exercised on a build container with no window system at all.
"""

from __future__ import annotations

import ast
import struct
from pathlib import Path

import cairo

from letters_to_family import draw
from letters_to_family.scribble import Scribble

INVENTED = "i sor a dinosor  at the parc wiv nanna"


def code_only(module) -> str:
    """The module's source with every docstring and comment gone.

    The module *talks* about spelling, ellipsis and tidying at length, on
    purpose. What the two tests below pin is that no line of code does any of
    it, so the prose has to come out before looking.
    """
    tree = ast.parse(Path(module.__file__).read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        body = getattr(node, "body", None)
        if isinstance(body, list) and body:
            first = body[0]
            if (
                isinstance(first, ast.Expr)
                and isinstance(first.value, ast.Constant)
                and isinstance(first.value.value, str)
            ):
                body.pop(0)
    return ast.unparse(tree)


def png_size(path) -> tuple[int, int]:
    """Width and height straight out of the IHDR chunk."""
    header = path.read_bytes()[:24]
    assert header[:8] == b"\x89PNG\r\n\x1a\n"
    return struct.unpack(">II", header[16:24])


def test_the_placeholder_face_is_a_png_of_the_size_asked_for(tmp_path):
    path = draw.draw_placeholder(tmp_path / "face.png", size=200)
    assert path.is_file()
    assert png_size(path) == (200, 200)


def test_the_placeholder_makes_its_own_directory(tmp_path):
    path = draw.draw_placeholder(tmp_path / "deep" / "down" / "face.png")
    assert path.is_file()


def test_a_scribble_renders_at_the_size_asked_for(tmp_path):
    scribble = Scribble()
    scribble.start(0.1, 0.1)
    scribble.extend(0.9, 0.8)
    scribble.end()
    path = draw.render_scribble(tmp_path / "s.png", scribble, width=320, height=240)
    assert png_size(path) == (320, 240)


def test_an_empty_scribble_is_still_a_picture(tmp_path):
    """A child who pressed "That's it" without drawing meant to. Plain paper is
    a picture, and being sent back to draw more would be the program marking
    their work."""
    path = draw.render_scribble(tmp_path / "blank.png", Scribble())
    assert path.is_file()


def test_a_single_press_draws_a_visible_dot(tmp_path):
    """A zero-length path strokes to nothing in some cairo builds, so a dot is
    drawn as a filled disc. This checks something is actually there."""
    scribble = Scribble()
    scribble.start(0.5, 0.5)
    scribble.end()
    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, 100, 100)
    ctx = cairo.Context(surface)
    ctx.set_source_rgb(*draw.PAPER)
    ctx.rectangle(0, 0, 100, 100)
    ctx.fill()
    blank = bytes(surface.get_data())
    draw.draw_scribble(ctx, scribble, 100, 100)
    surface.flush()
    assert bytes(surface.get_data()) != blank


def test_the_letter_card_is_a_portrait_png(tmp_path):
    picture = draw.render_scribble(tmp_path / "p.png", Scribble())
    path = draw.render_card(tmp_path / "letter.png", picture, INVENTED, "Grandad")
    width, height = png_size(path)
    assert (width, height) == (draw.CARD_WIDTH, draw.CARD_HEIGHT)
    assert height > width


def test_the_card_renders_with_no_picture_at_all(tmp_path):
    assert draw.render_card(tmp_path / "letter.png", None, INVENTED, "Grandad").is_file()


def test_the_card_renders_when_the_picture_file_is_missing(tmp_path):
    path = draw.render_card(tmp_path / "letter.png", tmp_path / "gone.png", "hi", "Grandad")
    assert path.is_file()


def test_the_card_renders_when_the_picture_is_not_a_png(tmp_path):
    """A JPEG photo from the Journal: cairo cannot load it, and the letter is
    still a letter with the words on it rather than a traceback."""
    broken = tmp_path / "photo.jpg"
    broken.write_bytes(b"not a png at all")
    assert draw.render_card(tmp_path / "letter.png", broken, "hi", "Grandad").is_file()


def test_the_card_renders_with_no_words(tmp_path):
    picture = draw.render_scribble(tmp_path / "p.png", Scribble())
    assert draw.render_card(tmp_path / "letter.png", picture, "", "Grandad").is_file()


def test_the_card_renders_a_very_long_letter_without_cutting_it(tmp_path):
    """Nothing a child wrote is ever truncated: the wrapper breaks lines, and
    it has no ellipsis in it at all."""
    long_letter = "i luv u " * 60
    assert draw.render_card(tmp_path / "letter.png", None, long_letter, "Grandad").is_file()
    # And there is no ellipsis machinery anywhere in the module to reach for.
    body = code_only(draw)
    assert "\u2026" not in body
    assert "ellipsi" not in body.lower()
    assert "set_ellipsize" not in body


def test_the_wrapper_breaks_a_word_too_long_for_the_line_rather_than_dropping_it():
    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, 10, 10)
    ctx = cairo.Context(surface)
    ctx.set_font_size(40)
    word = "ilovyougranddadverymuchindeed"
    lines = draw._wrap(ctx, word, 120)
    assert len(lines) > 1
    assert "".join(lines) == word


def test_the_wrapper_keeps_every_character_of_an_ordinary_sentence():
    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, 10, 10)
    ctx = cairo.Context(surface)
    ctx.set_font_size(20)
    lines = draw._wrap(ctx, INVENTED, 200)
    assert " ".join(" ".join(lines).split()) == " ".join(INVENTED.split())


def test_the_card_takes_the_child_s_hand_or_the_grown_up_s(tmp_path):
    child = draw.render_card(tmp_path / "a.png", None, "hi", "Grandad", child_hand=True)
    grown = draw.render_card(tmp_path / "b.png", None, "hi", "Grandad", child_hand=False)
    assert child.read_bytes() != grown.read_bytes()


def test_nothing_in_the_drawing_module_touches_the_text(tmp_path):
    """The one rule. `render_card` may measure the caption and break it into
    lines; it may not change a character of it.

    The docstrings are stripped before looking, because they *say* all of this
    in prose; what is being pinned is that no line of code does it.
    """
    body = code_only(draw)
    for banned in (".capitalize()", ".title()", ".upper()", ".lower()", "spell"):
        assert banned not in body, banned
