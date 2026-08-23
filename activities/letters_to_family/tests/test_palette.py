"""The colours this activity restates must be the shell's own.

A missing colour in GTK CSS is not an error, it is a black rectangle, so both
``activity.css`` and :mod:`letters_to_family.draw` restate the theme tokens
rather than relying on the shell being loaded. This test re-reads
``shell/kidnix_shell/theme.css`` on disk and fails if any of them has drifted.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from conftest import THEME_CSS
from letters_to_family import draw
from letters_to_family.scribble import COLOURS

ACTIVITY_CSS = Path(__file__).resolve().parents[1] / "letters_to_family" / "activity.css"

DEFINE = re.compile(r"@define-color\s+([a-z0-9-]+)\s+(#[0-9a-fA-F]{6})\s*;")

pytestmark = pytest.mark.skipif(
    not THEME_CSS.is_file(), reason="the shell checkout is not beside this one"
)


def theme() -> dict[str, str]:
    return {
        name: value.lower() for name, value in DEFINE.findall(THEME_CSS.read_text(encoding="utf-8"))
    }


def to_rgb(value: str) -> tuple[float, float, float]:
    raw = value.lstrip("#")
    return tuple(int(raw[i : i + 2], 16) / 255 for i in (0, 2, 4))  # type: ignore[return-value]


@pytest.mark.parametrize(
    ("token", "constant"),
    [
        ("kid-ink", "INK"),
        ("kid-paper", "PAPER"),
        ("kid-paper-dim", "PAPER_DIM"),
        ("kid-edge", "EDGE"),
        ("kid-primary", "PRIMARY"),
        ("kid-secondary", "SECONDARY"),
    ],
)
def test_the_drawing_uses_the_shell_s_own_colours(token: str, constant: str) -> None:
    tokens = theme()
    if token not in tokens:  # pragma: no cover - the shell renamed a token
        pytest.skip(f"{token} is not in theme.css any more")
    assert getattr(draw, constant) == pytest.approx(to_rgb(tokens[token]))


def test_the_crayons_are_the_shell_s_own_colours() -> None:
    tokens = theme()
    wanted = {"teal": "kid-primary", "pink": "kid-secondary", "black": "kid-ink"}
    for colour in COLOURS:
        token = wanted[colour.key]
        if token in tokens:
            assert colour.hex.lower() == tokens[token]


def test_the_stylesheet_restates_every_token_it_uses() -> None:
    """A ``@kid-*`` reference with no ``@define-color`` above it is a black
    rectangle on a machine with no shell behind it."""
    body = ACTIVITY_CSS.read_text(encoding="utf-8")
    defined = {name for name, _value in DEFINE.findall(body)}
    used = set(re.findall(r"@(kid-[a-z-]+)", body))
    assert used <= defined, sorted(used - defined)


def test_the_stylesheet_has_no_error_styling_in_it() -> None:
    """05 section 3: there is no such thing as a spelling error in a
    five-year-old's letter, so there is nothing here that could draw one.

    Comments are stripped first: the file *talks* about spelling at length,
    deliberately, and what is being pinned is that no rule in it paints a
    squiggle, a red underline or an error state.
    """
    body = re.sub(r"/\*.*?\*/", "", ACTIVITY_CSS.read_text(encoding="utf-8"), flags=re.S).lower()
    for banned in (".error", "underline", "text-decoration", "squiggl", "wavy"):
        assert banned not in body, banned
