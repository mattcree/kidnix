"""The minute screen's drawings: that they exist, and what they may contain.

Headless, and therefore part of the floor. Every one of these reads the SVG as
a file -- as XML, and as text -- because the rules an icon has to keep here are
rules about the *drawing*, and a picture somebody eyeballed once is not a test.
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ElementTree
from pathlib import Path

import pytest

from clock_time.icons import (
    BUTTON_ICONS,
    ICON_DIR,
    LENGTH_ICONS,
    icon_for,
    icon_path,
    known_icons,
    length_icon,
)
from clock_time.minute import LENGTHS

#: The activity's own palette, restated from ``activity.css`` -- which
#: ``test_activity_css.py`` already holds against the shell's ``theme.css``, so
#: an icon that keeps to this list keeps to the shell's colours as well.
PALETTE = {
    "#16181d",  # ink
    "#fbf7ef",  # paper
    "#efe8da",  # paper, dimmed
    "#7e838c",  # edge
    "#0f8a8a",  # primary
    "#f06292",  # secondary
    "#ffd23f",  # highlight -- the sun
    "none",
}

SVG = "{http://www.w3.org/2000/svg}"


def test_every_button_has_a_drawing():
    """The audit's ruling 4: five of six controls were a word and nothing
    else, on a screen for a child who cannot read one."""
    for name in BUTTON_ICONS:
        assert icon_for(name), name
    for length in LENGTHS:
        assert length_icon(length), length


def test_the_intervals_and_the_drawings_are_the_same_three():
    assert set(LENGTH_ICONS) == set(LENGTHS)
    assert len(set(LENGTH_ICONS.values())) == len(LENGTHS)


def test_a_drawing_we_have_not_made_is_an_empty_string_and_not_a_crash():
    """A broken install loses the pictures and keeps the words and the voice.
    ``""`` is what ``BigButton`` already reads as "this one has no picture"."""
    assert icon_for("no-such-drawing") == ""
    assert not icon_path("no-such-drawing").is_file()


def test_nothing_here_is_a_stray_file():
    assert set(known_icons()) == set(BUTTON_ICONS) | set(LENGTH_ICONS.values())


@pytest.mark.parametrize("name", sorted(known_icons()))
def test_each_one_is_well_formed_svg_with_a_title(name):
    """librsvg refuses a file it cannot parse and the button then draws
    nothing at all, which is the state this whole suite exists to leave. The
    parse *is* the assertion -- a double hyphen inside an XML comment is the
    way the shell's own ``kidnix-finish.svg`` came to draw nothing, and it
    raises here rather than shipping.
    """
    root = ElementTree.parse(icon_path(name)).getroot()
    assert root.tag == f"{SVG}svg"
    assert root.get("viewBox") == "0 0 120 120"
    title = root.find(f"{SVG}title")
    assert title is not None and title.text


@pytest.mark.parametrize("name", sorted(known_icons()))
def test_each_one_says_in_words_what_it_is_a_picture_of(name):
    root = ElementTree.parse(icon_path(name)).getroot()
    assert root.get("role") == "img"
    assert (root.get("aria-label") or "").strip()


@pytest.mark.parametrize("name", sorted(known_icons()))
def test_no_drawing_shows_a_word_or_a_number(name):
    """01 #19 / 03 #32. "Two minutes" is a bigger disc and never a numeral, so
    no icon here draws type at all -- and a ``<text>`` element would in any
    case be a glyph from a font the image does not promise, which is why even
    the shell's letter tiles draw letterforms as paths."""
    root = ElementTree.parse(icon_path(name)).getroot()
    assert f"{SVG}text" not in [element.tag for element in root.iter()]
    text = icon_path(name).read_text(encoding="utf-8")
    assert "font" not in text
    said = (root.get("aria-label") or "") + (root.findtext(f"{SVG}title") or "")
    assert not any(character.isdigit() for character in said)


@pytest.mark.parametrize("name", sorted(known_icons()))
def test_each_one_keeps_to_the_activitys_palette(name):
    """Flat colour from the theme, and no gradient, filter or raster."""
    text = icon_path(name).read_text(encoding="utf-8")
    for colour in re.findall(r'(?:fill|stroke)="([^"]+)"', text):
        assert colour.lower() in PALETTE, (name, colour)
    for banned in ("Gradient", "filter", "mask", "image", "opacity"):
        assert banned not in text, (name, banned)


@pytest.mark.parametrize("name", sorted(known_icons()))
def test_each_one_is_small_enough_to_be_a_drawing_and_not_a_program(name):
    assert icon_path(name).stat().st_size < 4096


def test_a_longer_interval_is_a_bigger_disc():
    """09 Q1: duration is encoded as **area**, never as horizontal travel --
    Tillman et al. (2018) found most preschoolers do not read a timeline at
    all. So the three buttons are three discs on one ground line, and the
    order of their radii is the order of the intervals."""
    radii = []
    for length in LENGTHS:
        root = ElementTree.parse(ICON_DIR / f"{LENGTH_ICONS[length]}.svg").getroot()
        circles = [float(c.get("r")) for c in root.iter(f"{SVG}circle")]
        assert len(circles) == 1, LENGTH_ICONS[length]
        radii.append(circles[0])
    assert radii == sorted(radii)
    assert len(set(radii)) == len(radii)
    assert [length.seconds for length in LENGTHS] == sorted(
        length.seconds for length in LENGTHS
    )


def test_every_disc_rests_on_the_same_ground_line():
    """Three sizes are only *three sizes* if they share a baseline: a disc
    floating higher would read as further away rather than as longer."""
    grounds = set()
    for name in LENGTH_ICONS.values():
        root = ElementTree.parse(ICON_DIR / f"{name}.svg").getroot()
        circle = next(iter(root.iter(f"{SVG}circle")))
        grounds.add(float(circle.get("cy")) + float(circle.get("r")))
    assert len(grounds) == 1


def test_the_icons_are_not_in_the_routine_namespace():
    """``pictures/`` is what a grown-up may name a moment after in
    ``clock_time.toml``. A family whose day had a moment called "stop" would
    otherwise be handed a picture of a hand at tea time."""
    from clock_time.pictures import PICTURE_DIR, known_pictures

    assert ICON_DIR != PICTURE_DIR
    assert not set(known_icons()) & set(known_pictures())
    assert Path(ICON_DIR).is_dir()
