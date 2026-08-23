"""The keyboard as a display of graphemes that never moves.

Research 10 section 6, and it is the framing that makes this legitimate at
five: *"press the key that makes /s/" is not typing practice, it is
find-the-grapheme-from-a-sound* -- a stated Letters and Sounds Phase 2 success
criterion. The keyboard is a fixed spatial index of twenty-six graphemes, which
is exactly the kind of stable layout a five-year-old can build a map of, and
none of the things that make typing tutors inappropriate at this age (home row,
finger assignment, WPM, a timer) appear anywhere in this module.

Three rules, all of them enforced here rather than remembered:

**Lowercase, always, and Shift is never required.** UK phonics teaches
lowercase first. A child with Caps Lock on -- or a keyboard whose caps say
``S`` -- must not be told they are wrong, so input is folded to lowercase and
uppercase is never a distinct answer.

**A digraph is two keys that become one tile.** ``ai`` is *one sound* and two
keys, and research 10 section 6 says getting this right "is the difference
between the keyboard reinforcing the alphabetic principle and confusing it".
:class:`BoardKeys` holds the first letter as a pending tile and fuses it with
the second; the widget half animates the two travelling together. What it must
never do is score ``a`` as a wrong answer on the way to ``ai``.

**A key that is not on the board is not a mistake.** A five-year-old exploring
a keyboard presses things. Only the graphemes actually on the screen can be
*chosen*; anything else comes back :attr:`Press.UNKNOWN`, the activity replays
the prompt, and nobody's two attempts are spent on a key that was never an
option.

The prefix problem, and why there is no timer
---------------------------------------------

If ``a`` and ``ai`` are both on the board, pressing ``a`` is simultaneously a
complete answer and half of another one. The usual fix is a timeout, which
makes the fastest child wrong and needs a clock in a pure module. Instead the
exact match is **held**: it is committed the moment the next key arrives and
does not extend it (and that key is then re-read from scratch), or by
:meth:`BoardKeys.settle` when the activity decides the child has stopped --
which is a decision about a person, and belongs in the widget layer where there
is one to watch.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from enum import StrEnum

__all__ = [
    "KEYCAPS",
    "BoardKeys",
    "Press",
    "PressResult",
    "key_hint",
    "keys_for",
    "printable",
]

#: The twenty-six keycaps a phonics module will accept, in keyboard-agnostic
#: order. Everything else on the keyboard -- digits, punctuation, modifiers --
#: is not a grapheme and is not an answer.
KEYCAPS = "abcdefghijklmnopqrstuvwxyz"


class Press(StrEnum):
    """What one key press meant."""

    #: A grapheme on the board was chosen. ``chosen`` says which.
    CHOSE = "chose"
    #: The start of a multi-key grapheme on the board. Show the pending tile.
    PENDING = "pending"
    #: A letter that begins nothing on this board. Not a wrong answer.
    UNKNOWN = "unknown"
    #: Not a letter at all: a modifier, an arrow, Escape. Never ours.
    IGNORED = "ignored"


@dataclass(frozen=True)
class PressResult:
    """The answer to one key, and everything the screen needs to redraw."""

    press: Press
    #: The grapheme chosen, when :attr:`press` is :attr:`Press.CHOSE`.
    chosen: str | None = None
    #: What is showing in the half-built tile, ``""`` when there is none.
    pending: str = ""
    #: The key as it was read, folded to lowercase. For the log, and for tests.
    key: str = ""


def printable(key: str) -> str:
    """One key as a lowercase letter, or ``""`` if it is not one.

    Takes a character rather than a GDK keyval on purpose: the pure half must
    be testable without GTK, and the widget layer already has to call
    ``Gdk.keyval_to_unicode`` to know what was pressed.
    """
    if len(key) != 1:
        return ""
    folded = key.lower()
    return folded if folded in KEYCAPS else ""


def keys_for(grapheme: str) -> tuple[str, ...]:
    """The keys that make this grapheme, in order. ``("s", "h")`` for ``sh``.

    Split digraphs (``a-e``) are not typeable as a sequence -- the letters are
    discontinuous and the word sits between them -- so they come back empty and
    the caller falls back to the tiles. That is a real limit of the keyboard
    route, not a bug in it, and it is one reason the tiles exist at all.
    """
    cleaned = (grapheme or "").strip().lower()
    if not cleaned or any(character not in KEYCAPS for character in cleaned):
        return ()
    return tuple(cleaned)


def key_hint(grapheme: str) -> str:
    """A grown-up-readable description of the key sequence. Never shown to the child."""
    keys = keys_for(grapheme)
    if not keys:
        return f"{grapheme} has no key sequence"
    if len(keys) == 1:
        return f"press {keys[0]}"
    return "press " + " then ".join(keys)


@dataclass(init=False)
class BoardKeys:
    """The keyboard half of one Find it board.

    Constructed with the graphemes that are on the screen. It answers one
    question -- *what did that key mean?* -- and holds exactly one piece of
    state, the letters typed so far towards a multi-key grapheme.
    """

    graphemes: tuple[str, ...]
    typed: str = ""
    #: The set of graphemes that are also a prefix of a longer one on this
    #: board. Computed once; the ambiguity it names is the reason for
    #: :meth:`settle`.
    ambiguous: frozenset[str] = field(default_factory=frozenset)

    def __init__(self, graphemes: Sequence[str]) -> None:
        cleaned: list[str] = []
        for grapheme in graphemes:
            keys = keys_for(grapheme)
            if keys:
                cleaned.append("".join(keys))
        self.graphemes = tuple(dict.fromkeys(cleaned))
        self.typed = ""
        self.ambiguous = frozenset(
            short
            for short in self.graphemes
            if any(other != short and other.startswith(short) for other in self.graphemes)
        )

    # -- queries ----------------------------------------------------------

    def _extends(self, candidate: str) -> bool:
        """Is ``candidate`` the beginning of something longer on this board?"""
        return any(len(g) > len(candidate) and g.startswith(candidate) for g in self.graphemes)

    def reset(self) -> None:
        """Forget the half-typed grapheme. A new round, or a wrong answer."""
        self.typed = ""

    # -- the one operation ------------------------------------------------

    def press(self, key: str) -> PressResult:
        """Read one key. Never raises, never blocks, never needs a clock."""
        letter = printable(key)
        if not letter:
            return PressResult(Press.IGNORED, pending=self.typed)

        candidate = self.typed + letter

        if candidate in self.graphemes:
            if self._extends(candidate):
                # Both a complete answer and half of a longer one. Hold it:
                # the next key decides, and so does settle().
                self.typed = candidate
                return PressResult(Press.PENDING, pending=candidate, key=letter)
            self.typed = ""
            return PressResult(Press.CHOSE, chosen=candidate, key=letter)

        if self._extends(candidate):
            self.typed = candidate
            return PressResult(Press.PENDING, pending=candidate, key=letter)

        # ``candidate`` is nothing on this board. If we were holding a complete
        # answer, that answer stands and this key starts again -- pressing "a"
        # then "t" on a board of {a, ai, t} chooses "a", not nothing.
        if self.typed in self.graphemes:
            chosen, self.typed = self.typed, ""
            return PressResult(Press.CHOSE, chosen=chosen, key=letter)

        self.typed = ""
        # A single letter that starts nothing is simply not on the board. Two
        # letters that start nothing means the first one led nowhere either,
        # and the child is exploring; both are UNKNOWN, and neither is wrong.
        return PressResult(Press.UNKNOWN, key=letter)

    def settle(self) -> PressResult:
        """The child has stopped typing. Commit a held answer, if there is one.

        Called by the widget layer, which is the only place that can know a
        person has paused. Idempotent: settling twice does not choose twice.
        """
        if self.typed and self.typed in self.graphemes:
            chosen, self.typed = self.typed, ""
            return PressResult(Press.CHOSE, chosen=chosen)
        return PressResult(Press.IGNORED, pending=self.typed)
