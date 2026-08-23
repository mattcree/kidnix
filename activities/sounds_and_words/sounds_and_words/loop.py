"""One loop, in one order, with an end you can see coming.

Research 10 section 4.1: **A to G is one 8-12 minute loop, in that order, never
a menu of seven games.** The DfE's screen-use guidance ("slow-paced, repetitive
and predictable") and the four pillars both push the same way, and a five-year-
old who is offered a menu spends the session choosing.

What is built, and what the gaps are for::

    start
      -> Hear it    (module A -- week 6 if time; not built)
      -> Find it    (module B -- built)
      -> Blend it   (module C -- built)
      -> Read it    (module E -- week 4; planned but not shown)
      -> done

The missing modules are **skipped, not stubbed**. A grey "coming soon" tile is
a thing a child will press every session and be refused by, which is the exact
opposite of what an activity that promises predictability should ship.

Two boundaries, both hard
-------------------------

**Twelve items.** :data:`MAX_ITEMS`, counted, and it is a ceiling rather than a
target -- if the schedule has less to do, the session is shorter. kidnix does
not manufacture work (research 10 section 4.3).

**Twelve minutes.** :func:`estimated_minutes` costs the plan from measured-ish
per-item budgets and :func:`plan_session` drops the tail that does not fit. The
child is never told a number and never sees a timer (SYNTHESIS D3, and 01 #19:
no digits where a child can see or hear them). The session's *real* ending
belongs to the shell, which owns the clock and the ritual; this budget only
stops the activity handing the shell a plan it could never have finished.

Two attempts, and then it moves on
----------------------------------

Wrong is not a buzzer, a cross, a lost life or a retry screen. The correct tile
pulses, the sound plays again, and the child tries again; after
:data:`MAX_ATTEMPTS` the loop moves on without comment. Research 05 section 2f:
informational, never controlling. The Leitner box is written from the **first**
attempt only (research 10 section 4.3) -- getting it on the third go is not the
same event as getting it first time, and treating them alike is how in-app
mastery bars come to mean nothing.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from enum import StrEnum

from .ceiling import Ceiling
from .corpus import Corpus
from .schedule import History, Item, ItemKind, Session, compose_session

__all__ = [
    "MAX_ATTEMPTS",
    "MAX_ITEMS",
    "MAX_MINUTES",
    "MIN_MINUTES",
    "Outcome",
    "SessionRunner",
    "estimated_minutes",
    "plan_session",
]

#: The most steps one session may contain, whatever the schedule offers.
MAX_ITEMS = 12
#: Research 10 section 4.1's upper bound. Never shown to the child.
MAX_MINUTES = 12.0
#: The lower bound, for the log line and for the tests that keep us honest
#: about whether a session is worth opening at all.
MIN_MINUTES = 8.0
#: Tries at one Find it item before the loop moves on. Not "lives".
MAX_ATTEMPTS = 2

#: Seconds per item, by module. Rough, deliberately generous, and only ever
#: used to decide how much to *drop*: a plan that overruns costs a child the
#: end of their session, and a plan that underruns costs nothing at all.
SECONDS: dict[ItemKind, float] = {
    ItemKind.FIND_IT: 25.0,
    ItemKind.BLEND_IT: 45.0,
    ItemKind.READ_IT: 120.0,
}

#: The modules that exist. Anything else the schedule plans is dropped from the
#: runnable session and kept in :attr:`Plan.deferred`, so the log can say what
#: week 4 will add rather than the plan silently shrinking.
BUILT: frozenset[ItemKind] = frozenset({ItemKind.FIND_IT, ItemKind.BLEND_IT})


class Outcome(StrEnum):
    """What one answer did to the loop."""

    #: Right first time. The box goes up; move on.
    CORRECT = "correct"
    #: Wrong, and there is another try. Pulse the right tile, say it again.
    AGAIN = "again"
    #: Out of tries. No comment, no sound of failure; the loop moves on.
    MOVE_ON = "move_on"


@dataclass(frozen=True)
class Plan:
    """A session's runnable items, and what was left out of it."""

    items: tuple[Item, ...]
    deferred: tuple[Item, ...] = ()
    ceiling_label: str = ""
    day: int = 0

    @property
    def minutes(self) -> float:
        return estimated_minutes(self.items)

    def of_kind(self, kind: ItemKind) -> tuple[Item, ...]:
        return tuple(item for item in self.items if item.kind is kind)

    def __len__(self) -> int:
        return len(self.items)

    def describe(self) -> str:
        """One line at start-up: what the child is about to be offered, and why."""
        counts = ", ".join(
            f"{len(self.of_kind(kind))} {kind.value}" for kind in (ItemKind.FIND_IT, ItemKind.BLEND_IT)
        )
        deferred = f", {len(self.deferred)} deferred" if self.deferred else ""
        return f"{len(self.items)} items ({counts}{deferred}), ~{self.minutes:.0f} min, {self.ceiling_label}"


def estimated_minutes(items: tuple[Item, ...] | list[Item]) -> float:
    """How long this plan should take. Never shown to anybody under eight."""
    return sum(SECONDS.get(item.kind, 30.0) for item in items) / 60.0


def plan_session(
    corpus: Corpus,
    ceiling: Ceiling,
    history: History,
    day: int = 0,
    *,
    size: int = 4,
    words_per_gpc: int = 2,
    max_items: int = MAX_ITEMS,
    max_minutes: float = MAX_MINUTES,
    rng: random.Random | None = None,
) -> Plan:
    """Compose today's loop, then cut it down to something a child can finish.

    ``size=4`` and ``words_per_gpc=2`` is four Find it items and eight Blend it
    words -- exactly :data:`MAX_ITEMS` before any trimming, which is how the
    two bounds were chosen rather than the other way round.

    The trim always cuts from the **end**, so what survives is Find it first and
    then as many words as fit. Cutting from the middle would break the module
    order, and the module order is the design.
    """
    session: Session = compose_session(
        corpus, ceiling, history, day, size=size, words_per_gpc=words_per_gpc, rng=rng
    )
    runnable = [item for item in session.items if item.kind in BUILT]
    deferred = tuple(item for item in session.items if item.kind not in BUILT)

    kept: list[Item] = []
    for item in runnable[: max(0, max_items)]:
        if estimated_minutes([*kept, item]) > max_minutes:
            break
        kept.append(item)

    return Plan(
        items=tuple(kept),
        deferred=deferred,
        ceiling_label=session.ceiling_label,
        day=day,
    )


@dataclass
class SessionRunner:
    """Walks one :class:`Plan`, and is the only thing that writes to history.

    Deliberately free of widgets, audio and clocks: what a test needs to prove
    about the loop -- that two wrong answers move on, that the box is written
    from the first attempt, that the words read today are the words that were
    actually reached -- must not require a display to prove.
    """

    plan: Plan
    history: History
    index: int = 0
    attempts: int = 0
    #: GPC ids whose first attempt has already been written to the Leitner box.
    recorded: set[str] = field(default_factory=set)
    #: The words the child actually blended today, in order, without repeats.
    blended: list[str] = field(default_factory=list)

    # -- where we are -----------------------------------------------------

    @property
    def done(self) -> bool:
        return self.index >= len(self.plan.items)

    @property
    def current(self) -> Item | None:
        if self.done:
            return None
        return self.plan.items[self.index]

    @property
    def remaining(self) -> int:
        return max(0, len(self.plan.items) - self.index)

    def advance(self) -> Item | None:
        """Move to the next item. Returns it, or ``None`` at the end."""
        self.index += 1
        self.attempts = 0
        return self.current

    # -- what the child did ------------------------------------------------

    def attempt(self, correct: bool) -> Outcome:
        """One answer to the current Find it item.

        The first attempt is the one that reaches the Leitner box, whichever way
        it went; later attempts on the same item change the screen and nothing
        else.
        """
        item = self.current
        if item is None:
            return Outcome.MOVE_ON
        self.attempts += 1
        first = self.attempts == 1

        if item.gpc_id and first and item.gpc_id not in self.recorded:
            self.history.record(item.gpc_id, self.plan.day, correct=correct)
            self.recorded.add(item.gpc_id)

        if correct:
            return Outcome.CORRECT
        if self.attempts >= MAX_ATTEMPTS:
            return Outcome.MOVE_ON
        return Outcome.AGAIN

    def blend(self, word: str) -> None:
        """Record that a word was put on the screen and pushed together.

        Not a score and not a claim that it was read -- kidnix has no way of
        knowing that, and would not be allowed to listen if it did (research 10
        section 4.6 #6). It is the list that becomes the card in My Things, so
        it is a list of what happened, which is all a Journal entry ever is.
        """
        cleaned = (word or "").strip().lower()
        if cleaned and cleaned not in self.blended:
            self.blended.append(cleaned)

    # -- what the session produced ----------------------------------------

    def gpcs_practised(self) -> tuple[str, ...]:
        """Every GPC that reached the screen, in the order it was offered."""
        return tuple(dict.fromkeys(item.gpc_id for item in self.plan.items[: self.index] if item.gpc_id))

    def words_read(self) -> tuple[str, ...]:
        """The words blended today. The Journal card's whole content."""
        return tuple(self.blended)
