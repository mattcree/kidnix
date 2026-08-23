"""Where the drawings are, and what to do when one is missing.

Eight moments ship with a picture each. A family who renames "tea" to "dinner"
in ``/etc/kidnix/clock_time.toml`` gets a moment with no drawing, and that must
be an ordinary thing rather than a crash: :func:`picture_for` hands back
``None``, the tile shows the word on its own, and the voice still says the whole
sentence. The alternative -- refusing the entry, or substituting somebody
else's picture -- would either lose the grown-up's day or tell the child that
dinner is a bath.

The drawings themselves are deliberately plain: one object, flat colour, no
scene, nothing countable in them. 05 section 2c (Kaminski & Sloutsky) is the
finding -- perceptual richness makes children attend to the decoration rather
than to what it stands for -- and a routine tile is exactly a picture that
stands for something.

Beside :mod:`clock_time.routine` rather than inside it because ``routine`` is
about *times* and knows nothing about files; this module is the only place that
touches the disk, which is what lets the routine tests run with no package
installed at all.
"""

from __future__ import annotations

from pathlib import Path

from .routine import RoutineItem

__all__ = ["PICTURE_DIR", "SUFFIX", "known_pictures", "picture_for", "picture_path"]

#: Beside this file. Copied into the image with the rest of the package.
PICTURE_DIR = Path(__file__).parent / "pictures"
#: Flat SVG, in the shell's house style: ink outline, one flat fill.
SUFFIX = ".svg"


def picture_path(item: RoutineItem | str) -> Path:
    """Where a moment's drawing *would* be. Does not check that it is there."""
    name = item if isinstance(item, str) else item.picture
    return PICTURE_DIR / f"{name}{SUFFIX}"


def picture_for(item: RoutineItem | str) -> Path | None:
    """The drawing, or ``None`` if this family invented a moment we have not."""
    candidate = picture_path(item)
    return candidate if candidate.is_file() else None


def known_pictures() -> tuple[str, ...]:
    """Every drawing that ships, by stem. What a parent may name in the file."""
    if not PICTURE_DIR.is_dir():  # pragma: no cover - a broken install
        return ()
    return tuple(sorted(path.stem for path in PICTURE_DIR.glob(f"*{SUFFIX}")))
