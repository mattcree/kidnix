"""Where the dots go. Canonical first, random only where random is honest.

The EYFS Number ELG asks a child to **subitise up to 5** -- to say how many
without counting. Subitising is not one skill: *perceptual* subitising is the
immediate apprehension of one to about four, and *conceptual* subitising is
seeing six as a five and a one. The arrangements here are chosen so that both
are available and neither is faked:

* **dice patterns, 1-6.** The arrangement a five-year-old has already met on a
  dice, a domino and their own fingers, and the one the quick-images teaching
  routine uses. A canonical pattern is what makes six subitisable at all: as a
  cloud of six dots it is not, as two threes it is.
* **the ten-frame, 6-10.** Six to ten are *never* shown as ten scattered dots.
  They are shown as a full row of five and some more, which is the whole
  representation the ELG's "composition of each number" is asking about, and
  the one every UK Reception classroom already has on the wall.
* **random scatter, 1-4 only.** A child who can only recognise the dice five
  has learnt a picture, not a number, so the arrangement has to vary. But it
  varies only where a *perceptual* judgement is still possible without
  counting, which is one to four. Five random dots is a counting task wearing
  a subitising costume, and ten random dots is the "dot cloud" approximate
  number system training that 05 section 2c says in as many words not to
  build (Szucs & Myers: no conclusive evidence ANS training transfers;
  Szkudlarek et al. failed to replicate it in an n = 318 RCT).

Coordinates are in the **unit square**: (0, 0) top-left, (1, 1) bottom-right,
each point the centre of one counter. Nothing here knows about pixels, cairo or
GTK, so all of it is tested with no display -- which is the SDK's floor
(``docs/design/activity-sdk.md`` section 10).
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from enum import Enum

__all__ = [
    "DICE_PATTERNS",
    "MAX_DICE",
    "MAX_SCATTER",
    "SCATTER_MARGIN",
    "SCATTER_MIN_DISTANCE",
    "Arrangement",
    "Shape",
    "arrangement_for",
    "dice",
    "frame_cells",
    "scatter",
    "ten_frame",
]


class Shape(Enum):
    """How this many dots were laid out."""

    #: The face of a dice. 1-6, and the arrangement a child already knows.
    DICE = "dice"
    #: Five in a row, then the rest underneath. 1-10.
    TEN_FRAME = "ten-frame"
    #: Anywhere, far enough apart to be seen as separate. 1-4 only.
    SCATTER = "scatter"


#: The largest number a dice face is drawn for.
MAX_DICE = 6
#: The largest number that is ever scattered. See the module docstring: past
#: four, "random" means "count them", and counting is not what is being asked.
MAX_SCATTER = 4

#: How far from the edge a scattered dot may land, in unit coordinates. Keeps a
#: counter's own radius inside the picture rather than half off it.
SCATTER_MARGIN = 0.16
#: The closest two scattered dots may be. Below this they read as a blob, and a
#: blob is not four things.
SCATTER_MIN_DISTANCE = 0.28

#: The dice faces, in unit coordinates. Written out rather than generated:
#: these are cultural objects, not arithmetic, and a table is what a reader can
#: check against a dice in their hand.
DICE_PATTERNS: dict[int, tuple[tuple[float, float], ...]] = {
    1: ((0.50, 0.50),),
    2: ((0.25, 0.25), (0.75, 0.75)),
    3: ((0.25, 0.25), (0.50, 0.50), (0.75, 0.75)),
    4: ((0.25, 0.25), (0.75, 0.25), (0.25, 0.75), (0.75, 0.75)),
    5: ((0.25, 0.25), (0.75, 0.25), (0.50, 0.50), (0.25, 0.75), (0.75, 0.75)),
    6: ((0.25, 0.20), (0.75, 0.20), (0.25, 0.50), (0.75, 0.50), (0.25, 0.80), (0.75, 0.80)),
}


@dataclass(frozen=True)
class Arrangement:
    """``count`` counters, laid out, and enough to draw the frame behind them.

    ``columns``/``rows`` are zero for a shape that has no frame. They are here
    rather than in the drawing code because *where the boxes are* is the same
    fact as *where the counters are*, and two modules deriving it separately is
    how a counter comes to sit half in its box.
    """

    count: int
    shape: Shape
    points: tuple[tuple[float, float], ...]
    columns: int = 0
    rows: int = 0

    def __post_init__(self) -> None:
        if len(self.points) != self.count:
            raise ValueError(f"{self.count} counters but {len(self.points)} points")

    @property
    def framed(self) -> bool:
        """Is there a grid of boxes to draw behind these counters?"""
        return self.columns > 0 and self.rows > 0


def frame_cells(columns: int, rows: int) -> tuple[tuple[float, float], ...]:
    """The centre of every box in a ``columns`` x ``rows`` frame, reading order.

    Reading order is the fill order, and the fill order is what makes a
    ten-frame mean anything: the top row fills left to right and only then does
    the bottom row start, so seven is *always* a full five and two more rather
    than seven boxes somebody shaded in.
    """
    columns = max(1, columns)
    rows = max(1, rows)
    return tuple(
        ((column + 0.5) / columns, (row + 0.5) / rows)
        for row in range(rows)
        for column in range(columns)
    )


def dice(count: int) -> Arrangement:
    """The dice face for ``count``. 1 to 6."""
    if count not in DICE_PATTERNS:
        raise ValueError(f"there is no dice face for {count}")
    return Arrangement(count=count, shape=Shape.DICE, points=DICE_PATTERNS[count])


def ten_frame(count: int, *, columns: int = 5, rows: int = 2) -> Arrangement:
    """``count`` counters in the first boxes of a frame. 0 to columns x rows.

    ``rows = 1`` is the five-frame. The default is the ten-frame, and for six
    to ten the top row is full by construction -- which is the point.
    """
    cells = frame_cells(columns, rows)
    if not 0 <= count <= len(cells):
        raise ValueError(f"{count} will not fit in a {columns} by {rows} frame")
    return Arrangement(
        count=count,
        shape=Shape.TEN_FRAME,
        points=cells[:count],
        columns=columns,
        rows=rows,
    )


def scatter(
    count: int,
    rng: random.Random,
    *,
    min_distance: float = SCATTER_MIN_DISTANCE,
    margin: float = SCATTER_MARGIN,
    attempts: int = 600,
) -> Arrangement:
    """``count`` dots anywhere, no two closer than ``min_distance``. 1 to 4.

    Rejection sampling, with the dice face as the backstop. The backstop is not
    decoration: a placement loop that can fail is a screen that can be blank,
    and a blank screen in front of a five-year-old who was asked "how many?" is
    worse than a familiar-looking four.
    """
    if not 1 <= count <= MAX_SCATTER:
        raise ValueError(f"{count} is not scattered; see MAX_SCATTER")
    low, high = margin, 1.0 - margin
    points: list[tuple[float, float]] = []
    for _ in range(attempts):
        if len(points) == count:
            break
        candidate = (rng.uniform(low, high), rng.uniform(low, high))
        if all(_distance(candidate, other) >= min_distance for other in points):
            points.append(candidate)
    if len(points) != count:  # pragma: no cover - needs a pathological rng
        return dice(count)
    return Arrangement(count=count, shape=Shape.SCATTER, points=tuple(points))


def arrangement_for(
    count: int,
    *,
    shape: Shape = Shape.DICE,
    rng: random.Random | None = None,
    columns: int = 5,
    rows: int = 2,
) -> Arrangement:
    """One entry point, with the rules of the module enforced in one place.

    A shape that cannot honestly show ``count`` is **corrected, not refused**:
    seven dice pips do not exist, so seven comes back as a ten-frame; scattering
    five is a counting task, so five comes back as a dice face. The caller is
    :mod:`numbers_activity.items`, which already picks the right shape -- this
    is the guard rail under it, and a test drives every count through it.
    """
    if count < 1:
        raise ValueError("there is nothing to arrange")
    if shape is Shape.SCATTER and count <= MAX_SCATTER:
        return scatter(count, rng if rng is not None else random.Random())
    if shape is not Shape.TEN_FRAME and count <= MAX_DICE:
        # Includes a scatter that was asked for and is not allowed: five random
        # dots is a counting task, so it comes back as the dice five.
        return dice(count)
    return ten_frame(count, columns=columns, rows=rows)


def _distance(a: tuple[float, float], b: tuple[float, float]) -> float:
    return ((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2) ** 0.5
