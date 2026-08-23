"""hello_draw without a window.

The shape every activity should copy: what the activity *knows* and what it
*does* live here, with no GTK import anywhere, so they can be tested by an
ordinary headless test on a machine with no display and no GTK at all. The
window (:mod:`~kidnix_activity.examples.hello_draw.activity`) is then only
wiring, and wiring is the part that needs a display to test.

Sounds & Words is being built the same way round, and it is the reason: the
part of a literacy activity worth proving -- which grapheme comes next, what
the ceiling is, whether a word is decodable yet -- must not be reachable only
through a button.
"""

from __future__ import annotations

import tempfile
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, Protocol

from kidnix_shell.journal import Entry

from .picture import write_square

__all__ = ["LOST_LINE", "PROMPT", "HelloDraw", "Saver", "caption_for", "make_and_keep"]

PROMPT = "Press the big button to make a square."
BUTTON_LABEL = "Make"
BUTTON_SPEAK = "Make a square."

#: The co-use moment (SUITE section 3). Addressed to the adult, in the adult's
#: words, and it never blocks the child.
GROWNUP_BODY = (
    "Ask what colour they made, and what they would like to make next. "
    "Naming the colour out loud is the part that does the work."
)

#: What the child hears when the save failed. In their words, and it names the
#: one thing they can actually do about it (SYNTHESIS C3).
LOST_LINE = "I could not keep that one. Ask a grown-up."


class Saver(Protocol):
    """The shape of :meth:`kidnix_activity.app.ActivityApplication.save_entry`.

    A protocol rather than the method itself, so that the test can be one and
    the logic never has to import the GTK half to know what it is calling.
    """

    def __call__(
        self,
        kind: str,
        files: Sequence[Path],
        caption: str | None = None,
        voice: Path | None = None,
        meta: Mapping[str, Any] | None = None,
    ) -> Entry: ...


def caption_for(colour: str) -> str:
    """What the child's picture is called. One short line, no digits."""
    return f"A {colour} square"


class HelloDraw:
    """What the activity knows. Nothing on disk until it is saved."""

    def __init__(self, scratch: Path | None = None) -> None:
        self.made = 0
        self.last: Path | None = None
        self.last_colour = ""
        self._scratch = scratch
        self._temporary: tempfile.TemporaryDirectory[str] | None = None

    @property
    def scratch(self) -> Path:
        """Somewhere to put the PNG before it is copied into the Journal.

        A temporary directory, not a directory in the child's home: the file
        here is an implementation detail of *making* the square, and the
        Journal keeps the copy that matters. An activity that left its working
        files in ``$HOME`` would be asking a parent to work out which of two
        copies is the real one.
        """
        if self._scratch is None:
            self._temporary = tempfile.TemporaryDirectory(prefix="hello-draw-")
            self._scratch = Path(self._temporary.name)
        return self._scratch

    def make(self) -> tuple[Path, str]:
        """Draw the next square. Returns the file and the colour's name."""
        path = self.scratch / f"square-{self.made + 1:02d}.png"
        colour = write_square(path, self.made)
        self.made += 1
        self.last, self.last_colour = path, colour
        return path, colour


def make_and_keep(state: HelloDraw, save: Saver) -> tuple[Entry, str]:
    """Draw the next square and keep it. Returns the entry and its caption.

    Separated from the button so that the thing worth testing -- one press
    produces one Journal entry a child can find -- is testable without a
    display. ``save`` is the application's ``save_entry`` in the running
    activity and a scratch journal in the test.
    """
    path, colour = state.make()
    caption = caption_for(colour)
    entry = save("picture", [path], caption=caption, meta={"colour": colour})
    return entry, caption
