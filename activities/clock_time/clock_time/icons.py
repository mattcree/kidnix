"""The pictures on the minute screen's buttons.

The 2026-08-23 CCI audit found the "How long is a minute?" screen carrying six
controls, five of them **a word and nothing else**, on a screen built for a
child who cannot read one. SYNTHESIS B3 asks every control for a picture, a
label *and* a spoken sentence; the labels and the sentences were already there,
so what is here is the missing third.

Each drawing is the thing itself rather than a symbol for it (08 section 3.7,
"the thing, not a chevron"):

===============  ===========================================================
``start``        the whole sun, every bit of it still there
``stop``         a hand held up, palm out -- what an adult does, and what a
                 child does back
``again``        an arrow all the way round the sun: watch it go past again
``back``         the shell's own fat back arrow, restated at this size
``length-*``     three discs on the ground, one bigger than the last. 09 Q1:
                 *encode duration as area, never as horizontal travel* -- so
                 "two minutes" is a bigger disc and never a longer bar, and
                 there is no digit in any of the three
===============  ===========================================================

They live beside the package, in their own directory rather than in
``pictures/``: that one is the *routine* namespace, a grown-up may name any
moment in it from ``clock_time.toml``, and a family whose day contained a
moment called "stop" would otherwise get a picture of a hand at tea time.

Nothing here raises and nothing here is required. :func:`icon_for` hands back
``""`` for a drawing that is not on disk, which is exactly what
:class:`~kidnix_activity.widgets.BigButton` reads as "no picture" -- so a
broken install loses the pictures and keeps the words and the voice, which is
the same failure the routine strip already takes.
"""

from __future__ import annotations

from pathlib import Path

from .minute import Length

__all__ = [
    "BUTTON_ICONS",
    "ICON_DIR",
    "LENGTH_ICONS",
    "SUFFIX",
    "icon_for",
    "icon_path",
    "known_icons",
    "length_icon",
]

#: Beside this file, copied into the image with the rest of the package.
ICON_DIR = Path(__file__).parent / "icons"
#: Flat SVG in the package's house style: ink outline, two or three flat fills.
SUFFIX = ".svg"

#: The picture on each of the minute screen's own controls. ``start`` and
#: ``stop`` are the two faces of one button: the same control says "Start" with
#: the whole sun on it and "Stop" with a hand on it, because a child pressing
#: it a second time is doing a different thing and a control that looks
#: identical in both states has told them otherwise.
BUTTON_ICONS: tuple[str, ...] = ("start", "stop", "again", "back")

#: One per interval, shortest first. The order matters: :func:`length_icon` is
#: the only place that knows a longer interval gets a bigger disc, and
#: ``tests/test_icons.py`` reads the radii back out of the drawings to check it.
LENGTH_ICONS: dict[Length, str] = {
    Length.HALF_MINUTE: "length-half",
    Length.MINUTE: "length-one",
    Length.TWO_MINUTES: "length-two",
}


def icon_path(name: str) -> Path:
    """Where a drawing *would* be. Does not check that it is there."""
    return ICON_DIR / f"{name}{SUFFIX}"


def icon_for(name: str) -> str:
    """The absolute path to a drawing, or ``""`` when we have not drawn one.

    A string rather than a :class:`~pathlib.Path` because that is what
    ``BigButton(icon=...)`` takes, and empty rather than ``None`` because
    empty is what it already reads as "this control has no picture".
    """
    candidate = icon_path(name)
    return str(candidate) if candidate.is_file() else ""


def length_icon(length: Length) -> str:
    """The disc for one interval: bigger for longer, and never a digit."""
    return icon_for(LENGTH_ICONS[length])


def known_icons() -> tuple[str, ...]:
    """Every drawing that ships, by stem."""
    if not ICON_DIR.is_dir():  # pragma: no cover - a broken install
        return ()
    return tuple(sorted(path.stem for path in ICON_DIR.glob(f"*{SUFFIX}")))
