"""Our stylesheet, and the two things it must not do.

A missing colour in GTK CSS is not an error, it is a black rectangle, which is
why the SDK restates its tokens rather than inheriting them and why we restate
theirs. That is only safe if something notices when they drift, and this is the
something.

The second half is the design constitution in a grep: there is no red, no
cross, no buzzer and no reward anywhere in a child-facing stylesheet. Wrong is
the *correct* tile pulsing while the sound plays again (research 05 section 2f
-- informational, never controlling), and the tile the child actually pressed
is left completely alone.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from conftest import SHELL_SRC

OURS = Path(__file__).resolve().parent.parent / "sounds_and_words" / "activity.css"
SDK = SHELL_SRC / "kidnix_activity" / "activity.css"

TOKEN = re.compile(r"@define-color\s+([a-z-]+)\s+(#[0-9a-fA-F]+);")


def tokens(path: Path) -> dict[str, str]:
    return {name: value.lower() for name, value in TOKEN.findall(path.read_text(encoding="utf-8"))}


@pytest.fixture(scope="module")
def ours() -> str:
    return OURS.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def rules(ours: str) -> str:
    """The stylesheet with its comments taken out.

    The comments *name* the things this activity refuses -- no buzzer, no
    score, no shake -- so grepping the whole file for them would find the
    refusal and call it the offence.
    """
    return re.sub(r"/\*.*?\*/", " ", ours, flags=re.S)


def test_our_stylesheet_is_installed_beside_the_module():
    assert OURS.is_file()


@pytest.mark.skipif(not SDK.is_file(), reason="the SDK stylesheet is not in this checkout")
def test_every_colour_token_matches_the_sdks_byte_for_byte():
    mine, theirs = tokens(OURS), tokens(SDK)
    shared = set(mine) & set(theirs)
    assert shared, "no tokens in common -- one of the two files was restructured"
    for name in sorted(shared):
        assert mine[name] == theirs[name], name


def test_we_add_selectors_rather_than_changing_the_sdks(ours):
    """`button.big` is the SDK's, and an activity that redefined it would be a
    lookalike of the shell rather than the same object."""
    assert "button.big {" not in ours
    assert "button.picture-tile {" not in ours
    assert ".grownup-turn {" not in ours


def test_a_grapheme_is_set_in_andika(ours):
    assert "Andika" in ours


def test_there_is_no_red_anywhere(rules):
    """Not a colour this activity owns. Wrong is not an emergency."""
    for red in ("#f00", "#ff0000", "red;", "#d32f2f", "#c62828"):
        assert red not in rules.lower()


@pytest.mark.parametrize(
    "word", ["star", "badge", "score", "streak", "reward", "trophy", "coin", "buzz", "shake"]
)
def test_no_reward_economy_can_be_styled_because_none_is_named(rules, word):
    assert word not in rules.lower()


def test_the_pulse_is_on_the_correct_tile_and_is_documented_as_such(ours):
    assert "button.grapheme.pulse" in ours
    assert "informational, never controlling" in ours


def test_calm_mode_keeps_the_meaning_and_drops_the_movement(ours):
    """SYNTHESIS H6. The border still changes; nothing animates."""
    calm = ours[ours.index("window.calm") :]
    assert "animation: none" in calm
    assert "border-color" in calm


def test_the_dot_and_the_bar_are_both_defined(ours):
    assert ".sound-mark.dot" in ours
    assert ".sound-mark.bar" in ours


def test_the_bar_is_not_a_row_of_dots(ours):
    """L&S p.70's whole claim is that `sh` is one sound. Two dots would say
    the opposite of what the child's teacher said."""
    bar = ours[ours.index(".sound-mark.bar") : ours.index(".sound-mark.bar") + 220]
    assert "border-radius: 7px" in bar
    assert "min-width" not in bar
