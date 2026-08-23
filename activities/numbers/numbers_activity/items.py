"""What a child is asked, in what order, and what happens when they answer.

This is the whole of the activity's judgement, and none of it needs a display.

**The loop is fixed.** Eight items: four *how many?*, then four *make five*
(or, at the ten range, two make five and two make ten). Always in that order,
always that many. There is no adaptive difficulty and no branching, for two
reasons that both come out of 05:

* adaptive tutoring in primary maths measures g = 0.01-0.09 and is *smaller*
  for low achievers and for long use (Steenbergen-Hu & Cooper, 34 samples), and
  05 section 4 #8 says not to over-engineer it;
* the DfE's own early-years guidance -- the one the EYFS framework now
  references -- asks for content that is "slow-paced, repetitive and
  predictable". A four-year-old who knows what is coming next is a four-year-old
  who can spend their attention on the number instead of on the program.

**The progression inside the loop is the one thing that is evidenced.** The WWC
practice guide rates exactly one of its five recommendations at Moderate:
*teach number and operations following a developmental progression*. So: small
numbers before large, canonical arrangements before varied ones, bonds to five
before bonds to ten, and the double (five and five) always among the tens
because the ELG names double facts.

**Nothing here counts anything.** There is no score in this module, no accuracy,
no running total, and no place one could be added without a test failing. What
is recorded is *what was practised* -- which bonds, which quantities -- because
that is what goes on the Journal card for a grown-up to read.
"""

from __future__ import annotations

import random
from collections.abc import Sequence
from dataclasses import dataclass, field
from enum import Enum
from typing import ClassVar

from .arrange import MAX_SCATTER, Arrangement, Shape, arrangement_for
from .settings import Frame, NumberRange, ParentSettings
from .words import card_caption

__all__ = [
    "BOND_ITEMS",
    "HOW_MANY_ITEMS",
    "MAX_ATTEMPTS",
    "SESSION_ITEMS",
    "TEN_BOND_PARTNERS",
    "HowMany",
    "Item",
    "ItemKind",
    "MakeBond",
    "Practised",
    "Response",
    "bond_items",
    "grownup_numbers",
    "how_many_items",
    "respond",
    "session",
]

#: How many *how many?* items are in a session.
HOW_MANY_ITEMS = 4
#: How many *make five / make ten* items are in a session.
BOND_ITEMS = 4
#: The whole loop. Eight items is about eight minutes with a grown-up beside
#: you and rather less on your own -- and the session's length is the shell's
#: business, not ours (SDK section 11: *you never end the session*).
SESSION_ITEMS = HOW_MANY_ITEMS + BOND_ITEMS

#: Two goes, and then you are told. A third ask is a test; two and a grown-up's
#: answer is what sitting next to somebody looks like.
MAX_ATTEMPTS = 2

#: The bonds to ten that get used, as the amount already showing. The double
#: (five and five) is handled separately because the ELG names double facts and
#: it is therefore in every ten-range session rather than sometimes.
TEN_BOND_PARTNERS: tuple[int, ...] = (9, 8, 7, 6)


class ItemKind(Enum):
    """Which of the two questions this is."""

    HOW_MANY = "how-many"
    MAKE = "make"


@dataclass(frozen=True)
class HowMany:
    """A picture flashes; how many were there?"""

    kind: ClassVar[ItemKind] = ItemKind.HOW_MANY

    count: int
    arrangement: Arrangement

    def __post_init__(self) -> None:
        if self.arrangement.count != self.count:
            raise ValueError("the arrangement does not show this many")

    def is_answer(self, number: int) -> bool:
        return number == self.count

    @property
    def answer(self) -> int:
        return self.count


@dataclass(frozen=True)
class MakeBond:
    """Some counters are in the frame; how many more make five (or ten)?"""

    kind: ClassVar[ItemKind] = ItemKind.MAKE

    shown: int
    total: int
    frame: Frame

    def __post_init__(self) -> None:
        if not 1 <= self.shown < self.total:
            # Both parts of a bond are at least one, on purpose. "Five and zero
            # make five" is true and is not what a five-year-old is learning;
            # an empty frame with "how many more make five?" over it is a
            # counting question wearing a bond's clothes.
            raise ValueError(f"{self.shown} and something do not make {self.total}")
        if self.total > self.frame.capacity:
            raise ValueError(f"{self.total} counters do not fit this frame")

    @property
    def missing(self) -> int:
        return self.total - self.shown

    @property
    def answer(self) -> int:
        return self.missing

    @property
    def bond(self) -> tuple[int, int, int]:
        """``(shown, missing, total)`` -- what the spoken sentence is made of."""
        return (self.shown, self.missing, self.total)

    def is_answer(self, number: int) -> bool:
        return number == self.missing


#: Either question.
Item = HowMany | MakeBond


class Response(Enum):
    """What to do about the answer that just arrived."""

    #: It was the number. Say it back and move on.
    RIGHT = "right"
    #: Show the picture again, count it out loud, and let them have another go.
    TRY_AGAIN = "try-again"
    #: Second go used. Count it, say what it was, and move on. Nobody is stuck.
    TOLD = "told"


def respond(item: Item, number: int, attempts: int) -> Response:
    """The whole of the marking, and it marks nothing.

    ``attempts`` is how many answers have already been wrong on *this* item. The
    function is total and has no memory, so the caller cannot accumulate a score
    in it by accident -- and the only thing that ever leaves it is which of
    three *actions* to take next.
    """
    if item.is_answer(number):
        return Response.RIGHT
    return Response.TRY_AGAIN if attempts + 1 < MAX_ATTEMPTS else Response.TOLD


# -- building a session ------------------------------------------------------


def how_many_items(settings: ParentSettings, rng: random.Random) -> tuple[HowMany, ...]:
    """Four quantities to recognise, in a deliberate order.

    * The **smallest goes first.** The first thing a child meets in a session
      must be one they cannot get wrong; a program that opens with its hardest
      question has told a four-year-old something about themselves in the first
      ten seconds.
    * The first two are **canonical** -- a dice face, or the ten-frame's full
      row and some more. The last two may be **scattered**, and only if they are
      four or fewer (:data:`~numbers_activity.arrange.MAX_SCATTER`), because
      that is the boundary of what can be seen rather than counted.
    * At the ten range the quantities **alternate** small, large, small, large,
      so that six-to-ten's "a full five and some more" is never all bunched at
      one end of the session.
    """
    if settings.range is NumberRange.TEN:
        small = sorted(rng.sample(range(1, 6), 2))
        large = rng.sample(range(6, 11), 2)
        counts = [small[0], large[0], small[1], large[1]]
    else:
        counts = rng.sample(range(1, 6), HOW_MANY_ITEMS)
        smallest = min(counts)
        counts.remove(smallest)
        counts.insert(0, smallest)

    items: list[HowMany] = []
    for index, count in enumerate(counts):
        shape = _shape_for(count, index)
        items.append(
            HowMany(count=count, arrangement=arrangement_for(count, shape=shape, rng=rng))
        )
    return tuple(items)


def _shape_for(count: int, index: int) -> Shape:
    """Canonical for the first half; varied afterwards, where varying is honest.

    Six and above are **always** a ten-frame, never a dice six. A dice six is a
    real canonical arrangement and :func:`~numbers_activity.arrange.dice` can
    draw one, but the thing the ELG asks about above five is *composition* --
    six is a five and a one -- and a picture that says so is worth more here
    than a picture of a dice.
    """
    if index >= HOW_MANY_ITEMS // 2 and count <= MAX_SCATTER:
        return Shape.SCATTER
    return Shape.DICE if count <= 5 else Shape.TEN_FRAME


def bond_items(settings: ParentSettings, rng: random.Random) -> tuple[MakeBond, ...]:
    """Four bonds, fives before tens, and never the same one twice.

    At the five range that is **all four** bonds to five -- one and four, two and
    three, three and two, four and one -- which is the entire ELG requirement,
    met once a session, in a shuffled order so it is not a recitation.

    At the ten range it is two of the bonds to five and then two to ten, of
    which the first is always **five and five**: the ELG asks for "some number
    bonds to 10, **including double facts**", and a double that turns up only
    sometimes is not included.
    """
    if settings.range is NumberRange.TEN:
        fives = rng.sample(range(1, 5), 2)
        partners = [5, rng.choice(TEN_BOND_PARTNERS)]
        pairs = [(shown, 5) for shown in fives] + [(shown, 10) for shown in partners]
    else:
        shown_values = list(range(1, 5))
        rng.shuffle(shown_values)
        pairs = [(shown, 5) for shown in shown_values[:BOND_ITEMS]]

    return tuple(
        MakeBond(shown=shown, total=total, frame=settings.frame_for(total))
        for shown, total in pairs
    )


def session(
    settings: ParentSettings | None = None, rng: random.Random | None = None
) -> tuple[Item, ...]:
    """The eight items, in the order they are asked. The same shape every time."""
    settings = settings if settings is not None else ParentSettings()
    rng = rng if rng is not None else random.Random()
    return (*how_many_items(settings, rng), *bond_items(settings, rng))


def grownup_numbers(items: Sequence[Item]) -> tuple[int, int]:
    """``(a number to show on fingers, a number to make)`` for the co-use card.

    Taken from what the child has just done rather than invented, so that the
    grown-up's question is the same question the machine was asking a minute
    ago. Falls back to four and five, which are the ELG's own two numbers.
    """
    counts = [item.count for item in items if isinstance(item, HowMany)]
    totals = [item.total for item in items if isinstance(item, MakeBond)]
    number = counts[-1] if counts else 4
    total = totals[-1] if totals else 5
    if number >= total:
        number = max(1, total - 1)
    return number, total


# -- what to put on the card -------------------------------------------------


@dataclass
class Practised:
    """What was done, for the Journal card. **Not** how it went.

    The distinction is the whole of SYNTHESIS E1 and F4 in one object. This
    records that three-and-two-make-five was practised today; it does not record
    whether the child said two straight away, said four first, or was told. A
    parent opening My Things sees what their child worked on, which is a
    conversation starter. A parent seeing "4/8" sees a mark, which is a
    different object with different effects on a household, and kidnix does not
    produce one.
    """

    bonds: list[tuple[int, int, int]] = field(default_factory=list)
    counts: list[int] = field(default_factory=list)

    def add_bond(self, bond: tuple[int, int, int]) -> None:
        """Record a bond, once. The same bond twice in a session is one line."""
        if bond not in self.bonds:
            self.bonds.append(bond)

    def add_count(self, count: int) -> None:
        if count not in self.counts:
            self.counts.append(count)

    @property
    def empty(self) -> bool:
        """Nothing was done, so there is nothing to keep."""
        return not self.bonds and not self.counts

    def caption(self) -> str:
        """The one line on the card."""
        return card_caption(tuple(self.bonds))

    def clear(self) -> None:
        """After a save. What has been kept is not kept again next round."""
        self.bonds.clear()
        self.counts.clear()
