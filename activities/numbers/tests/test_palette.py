"""The colours here are the shell's colours, and this is what says so.

Both :mod:`numbers_activity.draw` (in cairo, as floats) and ``activity.css`` (in
GTK CSS, as hex) restate the shell's tokens rather than inheriting them: an
activity is a separate process that may be run with no shell behind it, and a
missing colour in GTK CSS is not an error, it is a black rectangle. Restating
means they can drift, so this test re-reads ``kidnix_shell/theme.css`` and fails
when they do.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from conftest import REPO_ROOT
from numbers_activity import draw

THEME_CSS = REPO_ROOT / "shell" / "kidnix_shell" / "theme.css"
ACTIVITY_CSS = REPO_ROOT / "activities" / "numbers" / "numbers_activity" / "activity.css"

#: Our name for each token, and the shell's.
TOKENS = {
    "INK": "kid-ink",
    "PAPER": "kid-paper",
    "PAPER_DIM": "kid-paper-dim",
    "EDGE": "kid-edge",
    "GIVEN": "kid-primary",
    "MINE": "kid-secondary",
}


def _defined(path: Path) -> dict[str, str]:
    found = {}
    for name, value in re.findall(r"@define-color\s+([\w-]+)\s+#([0-9a-fA-F]{6})", path.read_text()):
        found[name] = value.lower()
    return found


@pytest.mark.skipif(not THEME_CSS.is_file(), reason="the shell is not in this checkout")
@pytest.mark.parametrize("ours,theirs", list(TOKENS.items()))
def test_the_cairo_palette_matches_the_shells(ours: str, theirs: str) -> None:
    shell = _defined(THEME_CSS)
    assert theirs in shell, f"{theirs} has gone from theme.css"
    expected = tuple(int(shell[theirs][i : i + 2], 16) / 255 for i in (0, 2, 4))
    assert getattr(draw, ours) == pytest.approx(expected, abs=1e-9)


@pytest.mark.skipif(not THEME_CSS.is_file(), reason="the shell is not in this checkout")
def test_the_stylesheet_restates_the_shells_tokens_exactly() -> None:
    shell = _defined(THEME_CSS)
    ours = _defined(ACTIVITY_CSS)
    assert ours, "activity.css defines no colours"
    for name, value in ours.items():
        assert name in shell, f"{name} is not a shell token"
        assert value == shell[name], f"{name} has drifted from theme.css"


def test_the_given_counters_and_the_childs_differ_in_more_than_colour() -> None:
    # SYNTHESIS B6: colour is never the sole carrier. The counters that were
    # already in the frame are solid discs; the ones the child put in are rings.
    # The drawing code is what enforces it and this is the note that says why.
    source = Path(draw.__file__).read_text()
    assert "hollow=True" in source
    assert "fill_preserve" in source
