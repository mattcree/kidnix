"""Fifteen pictures, for fifteen words that are things.

A picture next to ``cat`` is worth having and a picture next to ``sat`` is not.
Blend it therefore illustrates **concrete nouns only**, and only where the
drawing is cheap enough to be unambiguous at 30 mm: a cat, a bus, a cup. There
is no picture for ``it``, ``and``, ``sat`` or ``big``, and there is no attempt
to invent one -- a vague scribble beside a verb teaches a child to distrust the
pictures beside the nouns.

Why kidnix's own drawings rather than an icon set
-------------------------------------------------

Two reasons, in order of importance. First, **licensing**: every asset in this
image needs a row in ``docs/LICENSES.md`` and ``data/sources.toml``, and one
mixed-licence icon pack is more paperwork than fifteen shapes. These are ours,
Apache-2.0 like the rest of kidnix, drawn as plain SVG paths that anybody can
read in a text editor. Second, **the word decides the picture, not the other
way round**: the word list comes from the L&S banks under the ceiling, so the
pictures have to follow whatever those banks contain, and a stock icon set
never contains the fifteen things you need.

They are deliberately flat, high-contrast and outline-first. SYNTHESIS B6:
colour is never the sole carrier of meaning, so every one of them reads in
greyscale, and none of them needs a child to know that a fox is orange.

The list is short on purpose. Fifteen is what week 3 needs; growing it is a
morning's work and a row in the ledger, not a design decision to be made again.
"""

from __future__ import annotations

from pathlib import Path

__all__ = ["PICTURE_DIR", "PICTURE_WORDS", "have_pictures", "picture_for"]

#: Beside this module, inside the package, so a wheel carries them.
PICTURE_DIR = Path(__file__).resolve().parent / "pictures"

#: The words that have a drawing. Every one is a concrete noun and every one is
#: in the Letters and Sounds banks at Phase 2 or 3, so they are reachable under
#: a real ceiling rather than decorative.
PICTURE_WORDS: tuple[str, ...] = (
    "bag",
    "bed",
    "bus",
    "cat",
    "cup",
    "dog",
    "fox",
    "hat",
    "jam",
    "map",
    "net",
    "pin",
    "pot",
    "sun",
    "tap",
)


def picture_for(word: str, *, directory: Path | None = None) -> Path | None:
    """The drawing for ``word``, or ``None`` -- which is the common answer.

    Checks the file is really there rather than trusting the list: a picture
    named in code and missing on disk would be an empty frame beside a word,
    and an empty frame is worse than no frame.
    """
    root = PICTURE_DIR if directory is None else directory
    key = (word or "").strip().lower()
    if key not in PICTURE_WORDS:
        return None
    path = root / f"{key}.svg"
    return path if path.is_file() else None


def have_pictures(*, directory: Path | None = None) -> list[str]:
    """Which of :data:`PICTURE_WORDS` are actually installed. What a test asserts on."""
    return [word for word in PICTURE_WORDS if picture_for(word, directory=directory) is not None]
