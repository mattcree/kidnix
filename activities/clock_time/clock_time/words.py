"""What the hands are showing, in the words a UK child is taught to say.

No GTK, no cairo, no clock: this module is the part of the activity worth
proving, and it is provable with a plain ``assert`` on a machine with no
display (``docs/design/activity-sdk.md`` section 2).

Three things live here and nothing else does:

* :class:`ClockTime` -- a position of two hands, as one integer;
* :func:`snap` -- where a tap on the rim lands, which is the whole difference
  between Year 1 and Year 2;
* :meth:`ClockTime.words` -- "half past three", "quarter to eight",
  "twelve o'clock".

**Words, never digits.** Every string that leaves this module is spelled out.
The dial the child *looks* at carries the numerals 1 to 12, because reading
them is the thing being learnt; the voice never does, and neither does a
caption. That is the narrow reading of 01 #19 / 03 #32 ("no digits where a
child can see or hear them"), and the narrowness is deliberate: the rule is
about *quantities of time remaining* -- "about as long as one story", never
"twelve minutes" -- and a clock face is the one place in kidnix where a numeral
is the subject rather than a readout.

The clock is a **twelve-hour** clock, so ``total`` is 0-719 and three in the
morning and three in the afternoon are the same position. Which of the two a
family's routine means is :mod:`clock_time.routine`'s question, not this one's.
"""

from __future__ import annotations

import bisect
from dataclasses import dataclass
from datetime import datetime, time
from enum import Enum

__all__ = [
    "HOUR_NAMES",
    "MINUTES_ON_A_DIAL",
    "ClockTime",
    "Mode",
    "grid_for",
    "hour_name",
    "minute_words",
    "nearest_on_grid",
    "rim_targets",
    "snap",
]

#: A twelve-hour dial holds this many minutes. Everything here is modular
#: arithmetic on that circle, which is why "five to twelve" needs no special
#: case: it is minute 715 and the next hour is minute 720, which is 0.
MINUTES_ON_A_DIAL = 720

#: One to twelve, said. Index 0 is "twelve", because midnight and midday are
#: both twelve o'clock and a dial has no zero on it.
HOUR_NAMES: tuple[str, ...] = (
    "twelve",
    "one",
    "two",
    "three",
    "four",
    "five",
    "six",
    "seven",
    "eight",
    "nine",
    "ten",
    "eleven",
)

#: What the minute hand says, at each five-minute mark, in the half of the
#: hour that counts *past*. UK usage, and hyphenated where a UK child writes it
#: hyphenated ("twenty-five past"), because the caption is read as well as
#: heard.
_PAST: dict[int, str] = {
    5: "five past",
    10: "ten past",
    15: "quarter past",
    20: "twenty past",
    25: "twenty-five past",
    30: "half past",
}
#: And in the half that counts *to* the next hour.
_TO: dict[int, str] = {
    35: "twenty-five to",
    40: "twenty to",
    45: "quarter to",
    50: "ten to",
    55: "five to",
}


class Mode(Enum):
    """Which of the two things a school has taught this child so far.

    Year 1 Measurement asks for *"tell the time to the hour and half past the
    hour"* (National Curriculum KS1; quoted in
    ``docs/spikes/gcompris-curation.md``). Year 2 adds the quarters and the
    five-minute marks.

    It is **parent configuration and nothing else**. There is no way for a
    child to change it, no way for the activity to infer it, and no way for it
    to advance on its own -- the same rule Sounds & Words' ceiling keeps, and
    for the same reason: a child shown "twenty-five to eight" in the term they
    are learning "o'clock" has been shown something their school has not
    taught, and nothing in an activity is entitled to decide that.
    """

    #: O'clock and half past. The default, because starting low costs nothing.
    Y1 = "y1"
    #: Quarters and five-minute marks as well.
    Y2 = "y2"

    @classmethod
    def parse(cls, text: str | None) -> Mode:
        """``"y2"`` -> :data:`Mode.Y2`; anything else -> :data:`Mode.Y1`.

        Never raises. A grown-up who typed ``"year 2"`` into a TOML file gets
        the safe answer and a line in the log, not a child told the computer
        is broken.
        """
        cleaned = (text or "").strip().lower().replace(" ", "").replace("year", "y")
        for mode in cls:
            if cleaned == mode.value:
                return mode
        return cls.Y1


def grid_for(mode: Mode) -> tuple[int, ...]:
    """Every minute a hand is allowed to land on, in one hour.

    Year 1's grid is two positions, which is what makes the activity playable
    by a five-year-old with a mouse: there is nowhere on the rim that is a
    near-miss.

    It is also the *whole* of what Year 1 offers. **ADR-0013** ruled on the
    audit's finding that the Year 2 dial carries twelve spoken rim targets: a
    labelled grid whose items are the task itself is not a choice set, so
    twelve stays in Year 2 -- it is a clock, and the twelve hours are the
    domain -- but the default year gets the twelve hour marks and nothing else.
    :func:`rim_targets` is where that is spent.
    """
    if mode is Mode.Y1:
        return (0, 30)
    return tuple(range(0, 60, 5))


def rim_targets(mode: Mode) -> tuple[tuple[int, str], ...]:
    """Every target on the rim, as (minute, what it says). Pure, and the truth.

    The face draws these and the Tab ring walks them, and both take the list
    from here rather than working one out, so "what a child can press" and
    "what a child is taught" cannot drift apart. Two in Year 1, twelve in
    Year 2 (**ADR-0013**).

    The Year 1 pair is o'clock and half past -- the two positions the National
    Curriculum names for that year -- and *nothing on the five-minute rim*:
    no quarter past, no twenty to, and no voice for them either. A target a
    child can hear but has not been taught is a lesson their school has not
    given, which is the same rule :class:`Mode` keeps for the same reason.
    """
    return tuple((minute, minute_words(minute)) for minute in grid_for(mode))


def nearest_on_grid(total: int, mode: Mode) -> int:
    """Snap ``total`` minutes to the nearest allowed position, on the circle.

    Wraps: in Year 1, fifty minutes past three is nearer to four o'clock than
    to half past three, and the hour hand has to come with it. Ties round
    **up**, so the answer is stable and never depends on which way a hand was
    last moving.
    """
    total = int(total) % MINUTES_ON_A_DIAL
    best, best_gap, best_forward = 0, MINUTES_ON_A_DIAL + 1, False
    for step in _grid(mode):
        forward_gap = (step - total) % MINUTES_ON_A_DIAL
        backward_gap = (total - step) % MINUTES_ON_A_DIAL
        gap = min(forward_gap, backward_gap)
        forward = forward_gap <= backward_gap
        if gap < best_gap or (gap == best_gap and forward and not best_forward):
            best, best_gap, best_forward = step, gap, forward
    return best % MINUTES_ON_A_DIAL


def _grid(mode: Mode) -> list[int]:
    """Every allowed position on the whole dial, ascending. 24 of them, or 144."""
    return sorted({m for hour in range(12) for m in _positions(hour, mode)})


def _positions(hour: int, mode: Mode) -> tuple[int, ...]:
    return tuple(hour * 60 + minute for minute in grid_for(mode))


def snap(total: int, mode: Mode) -> int:
    """:func:`nearest_on_grid`, for any integer, including a negative one."""
    return nearest_on_grid(int(total) % MINUTES_ON_A_DIAL, mode)


def hour_name(hour: int) -> str:
    """``3`` -> ``"three"``; ``0`` and ``12`` -> ``"twelve"``."""
    return HOUR_NAMES[hour % 12]


def minute_words(minute: int) -> str:
    """What a *position on the rim* is called, with no hour attached.

    ``0`` -> ``"o'clock"``, ``30`` -> ``"half past"``, ``45`` ->
    ``"quarter to"``. This is what a rim target is named, and it deliberately
    does not carry the hour: a target whose spoken name changed every time the
    child moved the hands would be a different control on every press.
    """
    minute = int(minute) % 60
    if minute == 0:
        return "o'clock"
    if minute in _PAST:
        return _PAST[minute]
    if minute in _TO:
        return _TO[minute]
    return minute_words(round(minute / 5.0) * 5)


@dataclass(frozen=True, order=True)
class ClockTime:
    """Two hands, as one number: minutes since twelve, on a twelve-hour dial.

    One integer rather than an (hour, minute) pair because every operation the
    activity performs -- snapping, stepping by five, following the hour hand
    round, working out what "five to" means -- is addition on a circle, and a
    pair makes each one carry its own borrow.
    """

    total: int = 0

    def __post_init__(self) -> None:
        object.__setattr__(self, "total", int(self.total) % MINUTES_ON_A_DIAL)

    # -- reading it --

    @property
    def hour(self) -> int:
        """1 to 12. Never zero -- there is no zero on a dial."""
        return (self.total // 60) or 12

    @property
    def minute(self) -> int:
        return self.total % 60

    @property
    def next_hour(self) -> int:
        """The hour the minute hand is counting *to*. 1 to 12."""
        return ((self.total // 60) + 1) % 12 or 12

    # -- moving it --

    @classmethod
    def of(cls, hour: int, minute: int = 0) -> ClockTime:
        """``ClockTime.of(3, 30)`` -- how a test says half past three."""
        return cls((int(hour) % 12) * 60 + int(minute))

    @classmethod
    def from_time(cls, when: datetime | time) -> ClockTime:
        """What the hands would show at ``when``. Seconds are dropped."""
        return cls(when.hour * 60 + when.minute)

    def snapped(self, mode: Mode) -> ClockTime:
        """The nearest position the rim actually offers in this mode."""
        return ClockTime(snap(self.total, mode))

    def stepped(self, steps: int, mode: Mode) -> ClockTime:
        """``steps`` positions round the rim, forwards or backwards.

        What an arrow key does. It steps from wherever the hands are to the
        next *grid* position, so a clock left at an odd minute by the Now
        button tidies itself up on the first press rather than staying odd
        forever.
        """
        if steps == 0:
            return self
        grid = _grid(mode)
        if steps > 0:
            # The first position strictly after us, then the rest of the steps.
            index = bisect.bisect_right(grid, self.total) + steps - 1
        else:
            # The last position strictly before us, then the rest.
            index = bisect.bisect_left(grid, self.total) - 1 + steps + 1
        return ClockTime(grid[index % len(grid)])

    @property
    def is_on_the_hour(self) -> bool:
        return self.minute == 0

    # -- saying it --

    def words(self) -> str:
        """"half past three". The one string the voice and the caption share.

        Any minute is accepted, because :meth:`from_time` will hand this a real
        clock's twenty-three minutes past. A minute that is not on the
        five-minute grid is described by the mark it is nearest to, with
        ``about`` in front of it -- see :meth:`spoken`.
        """
        minute = self.minute
        if minute == 0:
            return f"{hour_name(self.hour)} o'clock"
        if minute in _PAST:
            return f"{_PAST[minute]} {hour_name(self.hour)}"
        if minute in _TO:
            return f"{_TO[minute]} {hour_name(self.next_hour)}"
        return ClockTime(nearest_on_grid(self.total, Mode.Y2)).words()

    def spoken(self, mode: Mode = Mode.Y2) -> str:
        """What the voice says, hedged when the hands are between marks.

        The Now button is the only thing that puts the hands somewhere the rim
        does not offer, and when it does, saying "half past three" at
        twenty-six minutes past would be teaching a child that the words mean
        something looser than they do. "About half past three" is true, is what
        an adult says, and costs one word.
        """
        landed = snap(self.total, mode)
        words = ClockTime(landed).words()
        return words if landed == self.total else f"about {words}"

    # -- drawing it --

    @property
    def minute_angle(self) -> float:
        """Degrees clockwise from twelve, for the minute hand."""
        return (self.minute % 60) * 6.0

    @property
    def hour_angle(self) -> float:
        """Degrees clockwise from twelve. Follows the minutes, as a real one does."""
        return (self.total % MINUTES_ON_A_DIAL) * 0.5

    def describe(self) -> str:
        """One line for the log. Digits are allowed in a log; a parent reads it."""
        return f"{self.hour:02d}:{self.minute:02d} ({self.words()})"
