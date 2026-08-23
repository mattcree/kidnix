"""The stylesheet: the same colours as the shell, and no second theme.

An activity looks like the shell because it *is* the shell's stylesheet plus a
handful of selectors. The tokens are restated in ``clock_time/activity.css``
for the reason the SDK restates them -- a missing colour in GTK CSS is not an
error, it is a black rectangle, and this activity can be run on a developer's
desktop with no shell behind it -- so something has to check they still agree.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from conftest import HAVE_SHELL, SHELL_SRC

CSS = Path(__file__).resolve().parent.parent / "clock_time" / "activity.css"
DEFINE = re.compile(r"@define-color\s+([\w-]+)\s+(#[0-9a-fA-F]{3,8})\s*;")


COMMENT = re.compile(r"/\*.*?\*/", re.DOTALL)


def rules(path: Path = CSS) -> str:
    """The stylesheet with its comments taken out.

    Every prose rule below is about what the *declarations* say. The comments
    quote the things they are refusing to do -- "deliberately NOT opacity: 0"
    -- so a test that greps the raw file is testing the commentary.
    """
    return COMMENT.sub("", path.read_text(encoding="utf-8"))


def colours(path: Path) -> dict[str, str]:
    return {
        name: value.lower() for name, value in DEFINE.findall(path.read_text(encoding="utf-8"))
    }


def test_the_stylesheet_is_there_and_is_not_empty():
    assert CSS.is_file()
    assert CSS.read_text(encoding="utf-8").strip()


def test_it_defines_every_token_it_uses():
    text = rules()
    defined = set(colours(CSS))
    used = set(re.findall(r"@(kid-[\w-]+)", text))
    assert used <= defined, sorted(used - defined)


@pytest.mark.skipif(not HAVE_SHELL, reason="kidnix_shell is not importable here")
def test_every_colour_is_byte_identical_to_the_shells():
    theme = SHELL_SRC / "kidnix_shell" / "theme.css"
    if not theme.is_file():  # pragma: no cover - an installed wheel without sources
        pytest.skip("theme.css is not in this checkout")
    shell = colours(theme)
    for name, value in colours(CSS).items():
        assert name in shell, name
        assert value == shell[name], name


def test_the_dials_palette_is_the_same_palette():
    """`clock_time.dial` states the colours as literals because a value you
    cannot compute is a value nobody checked. They must still be the theme's."""
    from clock_time import dial

    tokens = colours(CSS)
    assert tokens["kid-ink"] == dial.INK
    assert tokens["kid-paper"] == dial.PAPER
    assert tokens["kid-edge"] == dial.EDGE
    assert tokens["kid-primary"] == dial.MINUTE_HAND
    assert tokens["kid-secondary"] == dial.HOUR_HAND


def test_a_rim_target_paints_nothing_until_it_is_touched():
    """The child should see a clock, not a clock with twelve buttons on it --
    but an affordance that gives nothing back under a five-year-old's hand has
    not answered them, so hover and press must still paint."""
    text = rules()
    assert "button.rim {" in text
    assert "background-color: transparent;" in text
    assert "button.rim:hover" in text
    assert "button.rim:active" in text


def test_the_rim_target_is_not_merely_transparent():
    """`opacity: 0` would take the focus ring with it."""
    assert "opacity: 0" not in rules()


def test_the_current_routine_tile_is_marked_by_more_than_colour():
    """SYNTHESIS B6: colour is never the sole carrier. The current tile has
    grown an edge and come forward, which reads with the colour removed."""
    text = rules()
    block = text.split("button.picture-tile.routine.current {", 1)[1].split("}", 1)[0]
    assert "border" in block
    assert "box-shadow" in block


def test_nothing_here_is_red_or_pulses():
    """08 section 4.6: no colour change to red, no pulse, no acceleration."""
    text = rules().lower()
    assert "animation" not in text
    assert "@keyframes" not in text
    for red in ("#f00", "#ff0000", "red;"):
        assert red not in text
