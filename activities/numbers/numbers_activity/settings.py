"""What the grown-up said: how far it counts, and what it looks like.

One file, root-owned, in the same place and with the same ownership rule as the
shell's ``parent.toml``, Sounds & Words' ceiling and Clock's day
(:mod:`kidnix_shell.settings`, :mod:`sounds_and_words.settings`,
:mod:`clock_time.settings`)::

    /etc/kidnix/numbers.toml          the parent's copy
    /usr/share/kidnix/numbers.toml    the image's default

``/etc`` first because bootc's three-way merge makes ``/etc`` theirs and
``/usr/share`` ours. Root-owned because the child owns ``$XDG_CONFIG_HOME``,
and a setting a child can edit is not a parent's setting.

The range in particular is a claim about **what a school has taught**, and
nothing in this activity is entitled to infer, advance or widen it. That is not
caution, it is the evidence: adaptive tutoring in primary maths comes out at
g = 0.01-0.09 and is *smaller* for the low achievers it is sold for
(Steenbergen-Hu & Cooper, 34 samples), and 05 section 4 #8 says not to
over-engineer adaptive difficulty. So there is no difficulty ladder in this
program. There is a line in a file that a grown-up writes.

The schema, in full::

    [numbers]
    range = "five"      # "five" (default) or "ten"
    numerals = true     # print the digit on the answer tiles
    frames = "auto"     # "auto" (default), "five" or "ten"

**Nothing here ever raises.** A missing file, a malformed one, a typo in a key
-- all of them come back as the defaults with a line in the log. A five-year-old
told the computer is broken because a grown-up mistyped a TOML key has been
failed twice.
"""

from __future__ import annotations

import logging
import tomllib
from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

log = logging.getLogger(__name__)

__all__ = [
    "CONFIG_NAME",
    "CONFIG_SEARCH_PATH",
    "FIVE_FRAME",
    "TEN_FRAME",
    "Frame",
    "FrameStyle",
    "NumberRange",
    "ParentSettings",
    "config_candidates",
    "load_settings",
    "read_document",
    "settings_from_document",
]

#: The file the grown-up's answers land in.
CONFIG_NAME = "numbers.toml"

#: Root-owned config, in the order it is read. A list rather than a tuple so a
#: test can point it somewhere writable; nothing derived from the child's own
#: environment is ever appended to it.
CONFIG_SEARCH_PATH: list[Path] = [Path("/etc/kidnix"), Path("/usr/share/kidnix")]


class NumberRange(Enum):
    """How far it counts."""

    #: One to five, and the bonds to five. The ELG's floor, and the default.
    FIVE = "five"
    #: Adds six to ten as five-and-some-more, and some bonds to ten.
    TEN = "ten"

    @property
    def top(self) -> int:
        """The largest number a child is shown or asked for."""
        return 5 if self is NumberRange.FIVE else 10

    @classmethod
    def parse(cls, raw: str) -> NumberRange:
        """Lenient, because a grown-up typing "10" means ten."""
        cleaned = (raw or "").strip().lower()
        if cleaned in {"ten", "10", "to10", "to ten", "to-ten"}:
            return cls.TEN
        return cls.FIVE


@dataclass(frozen=True)
class Frame:
    """A grid of boxes to put counters in. Five wide, one or two rows deep."""

    columns: int
    rows: int

    @property
    def capacity(self) -> int:
        return self.columns * self.rows


#: One row of five. What a Reception classroom starts with.
FIVE_FRAME = Frame(columns=5, rows=1)
#: Two rows of five. The representation the ELG's "composition of each number"
#: is really about, and the one on every UK classroom wall.
TEN_FRAME = Frame(columns=5, rows=2)


class FrameStyle(Enum):
    """Which frame the bonds are drawn in, where there is a choice."""

    #: A five-frame for bonds to five, a ten-frame for bonds to ten.
    AUTO = "auto"
    #: Prefer the five-frame.
    FIVE = "five"
    #: Always the ten-frame, so that five reads as half of ten.
    TEN = "ten"

    @classmethod
    def parse(cls, raw: str) -> FrameStyle:
        cleaned = (raw or "").strip().lower()
        for style in cls:
            if cleaned == style.value:
                return style
        return cls.AUTO


@dataclass(frozen=True)
class ParentSettings:
    """The three answers, and the file they came from.

    ``source`` is ``None`` when nobody has answered. That distinction is not
    cosmetic: a parent pane must be able to say *"nobody has told us, so we are
    starting at five"* rather than presenting kidnix's guess back to a parent as
    their own statement.
    """

    range: NumberRange = NumberRange.FIVE
    numerals: bool = True
    frames: FrameStyle = FrameStyle.AUTO
    source: Path | None = None

    @property
    def is_default(self) -> bool:
        return self.source is None

    @property
    def top(self) -> int:
        """The largest number offered on a tile. Five or ten."""
        return self.range.top

    @property
    def choices(self) -> tuple[int, ...]:
        """Every number a tile is drawn for, in order, for the whole session.

        The row never changes shape between items. B1 is spatial stability, and
        a child who has found where the four is should find it there next time.
        """
        return tuple(range(1, self.top + 1))

    def frame_for(self, total: int) -> Frame:
        """Which frame a bond to ``total`` is drawn in.

        The one correction this makes without being asked: ``frames = "five"``
        with a bond to ten gets a ten-frame anyway, because ten counters do not
        fit in five boxes. Honouring the setting there would mean either a wrong
        picture or no picture, and a grown-up who wrote "five" was answering a
        question about the bonds to five.
        """
        if self.frames is FrameStyle.TEN:
            return TEN_FRAME
        if total <= FIVE_FRAME.capacity:
            return FIVE_FRAME
        if self.frames is FrameStyle.FIVE:
            log.info(
                "frames = \"five\" but this bond makes %d; drawing a ten-frame", total
            )
        return TEN_FRAME

    def describe(self) -> str:
        """One line for the log at start-up, naming the file that decided it."""
        where = str(self.source) if self.source is not None else "(no config; defaults)"
        return (
            f"range={self.range.value} numerals={self.numerals} "
            f"frames={self.frames.value} from {where}"
        )


def config_candidates(name: str = CONFIG_NAME) -> list[Path]:
    """Every place the file may be written, in the order it is read."""
    return [directory / name for directory in CONFIG_SEARCH_PATH]


def read_document(path: Path) -> Mapping[str, object] | None:
    """Parse one TOML file. ``None`` on anything at all going wrong."""
    try:
        if not path.is_file():
            return None
        with path.open("rb") as handle:
            return tomllib.load(handle)
    except (OSError, tomllib.TOMLDecodeError) as exc:
        log.warning("could not read %s: %s; using the defaults", path, exc)
        return None


def settings_from_document(
    doc: Mapping[str, object], source: Path | None = None
) -> ParentSettings:
    """Turn a parsed file into settings, dropping whatever does not make sense.

    Partial credit, deliberately: a file with a good ``range`` and a nonsense
    ``frames`` keeps the range. An all-or-nothing reader would throw away a
    grown-up's answer over somebody else's typo.
    """
    section = doc.get("numbers")
    if section is not None and not isinstance(section, dict):
        log.warning("[numbers] is not a table; using the defaults")
        section = None
    section = section or {}

    raw_range = section.get("range")
    number_range = NumberRange.parse(str(raw_range) if raw_range is not None else "")
    if (
        raw_range is not None
        and number_range is NumberRange.FIVE
        and str(raw_range).strip().lower() not in {"five", "5", "to5", "to five", "to-five"}
    ):
        log.warning("numbers.range=%r is not \"five\" or \"ten\"; using five", raw_range)

    raw_numerals = section.get("numerals", True)
    if isinstance(raw_numerals, bool):
        numerals = raw_numerals
    else:
        log.warning("numbers.numerals=%r is not true or false; showing them", raw_numerals)
        numerals = True

    raw_frames = section.get("frames")
    frames = FrameStyle.parse(str(raw_frames) if raw_frames is not None else "")
    if (
        raw_frames is not None
        and frames is FrameStyle.AUTO
        and str(raw_frames).strip().lower() != "auto"
    ):
        log.warning(
            "numbers.frames=%r is not \"auto\", \"five\" or \"ten\"; using auto", raw_frames
        )

    return ParentSettings(
        range=number_range, numerals=numerals, frames=frames, source=source
    )


def load_settings(*, search: list[Path] | None = None, name: str = CONFIG_NAME) -> ParentSettings:
    """Read the first readable root-owned file, or hand back the defaults."""
    directories = CONFIG_SEARCH_PATH if search is None else search
    for path in (directory / name for directory in directories):
        doc = read_document(path)
        if doc is None:
            continue
        return settings_from_document(doc, source=path)
    return ParentSettings()
