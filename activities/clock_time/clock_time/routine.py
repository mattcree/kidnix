"""This family's day: what happens when, and what the sky is doing while it does.

The link the activity is actually for. 02 #18 is the finding underneath it --
*"reflect real-world context, since context is what actually ends screen time;
39% of transitions ended because the situation changed"* -- and a clock that a
child can connect to *tea* and *bath* is a clock that means something in the
room they are in. "Half past six" is an abstraction; "half past six is when we
have tea" is a fact about their house.

Three pure things, no GTK:

* :class:`Routine` -- six to eight moments, each with a time and a picture,
  read from the grown-up's file (:mod:`clock_time.settings`);
* :func:`Routine.at` -- which moment a position of the hands is nearest to,
  which is harder than it looks because a dial has no morning or afternoon;
* :class:`Sky` -- morning, afternoon, evening, night, as a second, redundant
  channel for the same fact (SYNTHESIS B6: colour is never the sole carrier,
  so the sky is *with* the picture and the highlight, never instead of them).

**This is not a timeline.** 09 Q4 is explicit -- *"never ask the child to order
anything; no timeline graphic, no drag-to-reorder"* -- and the strip on screen
obeys it: the child is never asked what comes first, nothing is draggable, and
the left-to-right order of the pictures is convenience for the adult reading
over their shoulder. What carries "when" is the hands, the highlight and the
sky. If the strip were shuffled the activity would still work.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Iterator, Sequence
from dataclasses import dataclass
from enum import Enum

from .words import ClockTime

__all__ = [
    "DEFAULT_ROUTINE",
    "MINUTES_IN_A_DAY",
    "Routine",
    "RoutineItem",
    "Sky",
    "parse_hhmm",
]

#: A whole day, for the modular arithmetic below.
MINUTES_IN_A_DAY = 24 * 60


class Sky(Enum):
    """What the light is doing. Four, because a day has four of them to a child.

    The boundaries are the ones a family would say out loud, not astronomical
    ones: morning is until lunch, afternoon until tea-time, evening until it is
    properly dark. They are deliberately not configurable -- a parent who moves
    bedtime moves the *routine item*, and the sky follows the clock, which is
    the direction the causation actually runs.
    """

    MORNING = "morning"
    AFTERNOON = "afternoon"
    EVENING = "evening"
    NIGHT = "night"

    @property
    def words(self) -> str:
        """"in the morning". What the voice adds after the time, sometimes."""
        return f"in the {self.value}" if self is not Sky.NIGHT else "at night"

    @classmethod
    def at(cls, minutes: int) -> Sky:
        """Which sky ``minutes`` past midnight falls under. 0-1439, wrapping."""
        minutes = int(minutes) % MINUTES_IN_A_DAY
        if 5 * 60 <= minutes < 12 * 60:
            return cls.MORNING
        if 12 * 60 <= minutes < 17 * 60:
            return cls.AFTERNOON
        if 17 * 60 <= minutes < 21 * 60:
            return cls.EVENING
        return cls.NIGHT

    @property
    def is_dark(self) -> bool:
        """Is there a moon in the sky rather than a sun?"""
        return self is Sky.NIGHT


_HHMM = re.compile(r"^\s*(\d{1,2})\s*[:.]\s*(\d{2})\s*$")


def parse_hhmm(text: str) -> int | None:
    """``"07:30"`` -> 450 minutes past midnight. ``None`` if it is not a time.

    Never raises, and never guesses: a grown-up who typed ``half seven`` gets
    that item dropped with a line in the log rather than an activity that
    refuses to start. Accepts a full stop as well as a colon, because that is
    how a lot of people in the UK write it.
    """
    match = _HHMM.match(text or "")
    if match is None:
        return None
    hour, minute = int(match.group(1)), int(match.group(2))
    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        return None
    return hour * 60 + minute


@dataclass(frozen=True)
class RoutineItem:
    """One thing that happens, at one time, with one picture.

    ``at`` is minutes past **midnight**, 0-1439 -- a twenty-four hour fact,
    unlike the dial, which is why :meth:`Routine.at` has work to do.
    """

    #: The slug. Also the picture's filename, unless ``picture`` says otherwise.
    id: str
    #: What it is called, in the words the family uses. Spoken and written.
    name: str
    #: Minutes past midnight.
    at: int
    #: The picture's stem in ``clock_time/pictures``. Defaults to ``id``.
    picture: str = ""

    def __post_init__(self) -> None:
        if not self.picture:
            object.__setattr__(self, "picture", self.id)
        object.__setattr__(self, "at", int(self.at) % MINUTES_IN_A_DAY)

    @property
    def clock(self) -> ClockTime:
        """Where the hands would be. Twelve-hour, so this loses am/pm."""
        return ClockTime(self.at)

    @property
    def sky(self) -> Sky:
        return Sky.at(self.at)

    @property
    def sentence(self) -> str:
        """"Tea is at half past five." One line, for the ear and the strip."""
        return f"{self.name} is at {self.clock.words()}."


#: What a machine with nobody's config file on it uses.
#:
#: Eight moments, which is the top of the range the brief asks for, and they
#: are the ones that recur in every UK family timetable rather than an
#: idealised one. The times are ordinary and slightly early, because a default
#: that is wrong in the *late* direction puts "bed" in the middle of a child's
#: actual evening and makes the picture argue with the room.
#:
#: The pictures are plain (05 section 2c, Kaminski & Sloutsky: perceptual
#: richness makes children count the decorations) -- one object, flat colour,
#: no scene, nothing countable in it.
DEFAULT_ROUTINE: tuple[RoutineItem, ...] = (
    RoutineItem("wake", "Wake up", 7 * 60),
    RoutineItem("breakfast", "Breakfast", 7 * 60 + 30),
    RoutineItem("school", "School", 9 * 60),
    RoutineItem("lunch", "Lunch", 12 * 60),
    RoutineItem("home", "Home", 15 * 60 + 30),
    RoutineItem("tea", "Tea", 17 * 60 + 30),
    RoutineItem("bath", "Bath", 18 * 60 + 30),
    RoutineItem("bed", "Bed", 19 * 60),
)


@dataclass(frozen=True)
class Routine:
    """The whole day, in order, with the lookup that makes a dial mean something."""

    items: tuple[RoutineItem, ...] = DEFAULT_ROUTINE

    @classmethod
    def of(cls, items: Iterable[RoutineItem]) -> Routine:
        """Build one, sorted by time. Order on screen is order in the day."""
        ordered = tuple(sorted(items, key=lambda item: item.at))
        return cls(ordered or DEFAULT_ROUTINE)

    def __iter__(self) -> Iterator[RoutineItem]:
        return iter(self.items)

    def __len__(self) -> int:
        return len(self.items)

    def __getitem__(self, index: int) -> RoutineItem:
        return self.items[index]

    def by_id(self, item_id: str) -> RoutineItem | None:
        return next((item for item in self.items if item.id == item_id), None)

    # -- the lookup --

    def at_minute(self, minutes: int) -> RoutineItem:
        """The last thing that has happened by ``minutes`` past midnight.

        "What is happening now" is *the most recent thing that started*, not
        the nearest one: at four in the afternoon a child has been home from
        school for half an hour and is not yet having tea, and the honest
        picture is the one they are living in. Wraps at midnight, so three in
        the morning is still "bed" -- which is true, and is the answer a child
        who has got up in the night would recognise.
        """
        minutes = int(minutes) % MINUTES_IN_A_DAY
        best = self.items[-1]
        best_gap = MINUTES_IN_A_DAY + 1
        for item in self.items:
            gap = (minutes - item.at) % MINUTES_IN_A_DAY
            if gap < best_gap:
                best, best_gap = item, gap
        return best

    def minutes_for(self, clock: ClockTime, now: int | None = None) -> int:
        """Which of the dial's two candidate times of day the hands mean.

        A twelve-hour dial has no am and no pm: seven o'clock is either getting
        up or going to bed, and the hands say nothing at all about which. Two
        rules decide it, in this order.

        **The room, if we know what time it is there.** ``now`` is minutes past
        midnight of the *real* clock. The candidate nearer to it wins, because
        that is what an adult sitting next to the child would assume: at six in
        the evening, seven o'clock means bedtime. This matters more than it
        looks -- with a default day whose morning is crowded and whose evening
        is not, the gap rule below can make "bed" unreachable, and a routine
        strip with an item nobody can ever land on is a strip with a lie in it.

        **Otherwise, the tighter fit.** The candidate that lands *closer behind*
        a routine item: at three o'clock the afternoon one is three hours after
        lunch and the small-hours one is eight hours after bed, so the afternoon
        wins. Ties go to the earlier candidate, because a child is more often
        awake in the first half of a dial than the second.
        """
        morning, afternoon = clock.total, clock.total + 720
        if now is not None:
            now = int(now) % MINUTES_IN_A_DAY
            near_am = _circular(morning, now)
            near_pm = _circular(afternoon, now)
            return morning if near_am <= near_pm else afternoon
        gap_am = min((morning - item.at) % MINUTES_IN_A_DAY for item in self.items)
        gap_pm = min((afternoon - item.at) % MINUTES_IN_A_DAY for item in self.items)
        return morning if gap_am <= gap_pm else afternoon

    def at(self, clock: ClockTime, now: int | None = None) -> RoutineItem:
        """The moment a position of the hands is showing. See :meth:`minutes_for`."""
        return self.at_minute(self.minutes_for(clock, now))

    def sky_for(self, clock: ClockTime, now: int | None = None) -> Sky:
        """What the light is doing, for a position of the hands."""
        return Sky.at(self.minutes_for(clock, now))

    def index_of(self, item: RoutineItem) -> int:
        """Where it sits in the strip. -1 if it is not this routine's."""
        try:
            return self.items.index(item)
        except ValueError:
            return -1

    def pictures(self) -> Sequence[str]:
        return tuple(item.picture for item in self.items)


def _circular(a: int, b: int) -> int:
    """How far apart two times of day are, the short way round the clock."""
    gap = (a - b) % MINUTES_IN_A_DAY
    return min(gap, MINUTES_IN_A_DAY - gap)
