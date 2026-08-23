"""The schedule: which of the *already-permitted* sounds get rehearsed today.

Deliberately dumb, inspectable and deterministic (research 10, section 4.3).
It lives in one file in the child's home and a parent can read it in a text
editor. There is no model here, and there will not be one: the cleanest test of
adaptivity in this literature (the Norwegian GraphoGame RCT, whose only
difference between arms was adaptivity) found no difference, and
Steenbergen-Hu & Cooper put adaptive tutoring at g = 0.01-0.09. Spacing is
Tier 1. Spend the engineering there.

The hard parent ceiling is **not** an input to this model. It is a gate applied
first, in ``ceiling.py``. ``compose_session`` takes a ``Ceiling`` and can only
ever choose from what it already allows; nothing here can widen it.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field, replace
from enum import StrEnum

from .ceiling import Ceiling, allowed_sentences, allowed_words
from .corpus import Corpus
from .reading import texts_for

#: Leitner intervals in days, indexed by box.
BOX_INTERVALS: tuple[int, ...] = (0, 1, 2, 4, 8, 16)
MAX_BOX = len(BOX_INTERVALS) - 1

#: "Mastered" = box 4 or above, and three consecutive first-attempt correct,
#: across at least two different days. The two-day rule is the point: it stops
#: same-session repetition faking mastery, which is the standard failure of
#: in-app mastery bars.
MASTERY_BOX = 4
MASTERY_STREAK = 3
MASTERY_DISTINCT_DAYS = 2

#: Session composition, fixed and boring (research 10, section 4.3).
SHARE_REVIEW = 0.6
SHARE_NEW = 0.2
SHARE_INTERLEAVE = 0.2


class Role(StrEnum):
    REVIEW = "review"
    NEW = "new"
    INTERLEAVE = "interleave"


class ItemKind(StrEnum):
    FIND_IT = "find_it"
    BLEND_IT = "blend_it"
    #: One caption or sentence out of the L&S bank. There is no module for it
    #: on its own -- it is the promise that a session lands in real language,
    #: and Read it is what keeps that promise now it exists.
    READ_IT = "read_it"
    #: One of the twelve authored books (:mod:`sounds_and_words.reading`).
    #: Payload is the slug, not the title: a title is copy and may be edited,
    #: and a plan that pointed at a title would break when it was.
    READ_TEXT = "read_text"


@dataclass(frozen=True)
class GpcState:
    """What has happened with one GPC on this computer. Not an assessment."""

    gpc_id: str
    box: int = 0
    streak: int = 0
    streak_days: tuple[int, ...] = ()
    correct_days: tuple[int, ...] = ()
    last_seen_day: int | None = None
    attempts: int = 0
    first_attempt_correct: int = 0

    @property
    def mastered(self) -> bool:
        return (
            self.box >= MASTERY_BOX
            and self.streak >= MASTERY_STREAK
            and len(set(self.streak_days)) >= MASTERY_DISTINCT_DAYS
        )

    @property
    def seen(self) -> bool:
        return self.attempts > 0

    def due_on(self, day: int) -> bool:
        if self.last_seen_day is None:
            return True
        return day - self.last_seen_day >= BOX_INTERVALS[self.box]

    def parent_state(self) -> str:
        """The only three words the parent pane may use for a grapheme."""
        if not self.seen:
            return "not tried"
        if len(set(self.correct_days)) >= 3:
            return "read correctly on 3 different days"
        return "tried"


@dataclass
class History:
    """Every GPC's state. Serialises to a flat dict; no schema migration games."""

    states: dict[str, GpcState] = field(default_factory=dict)

    def state(self, gpc_id: str) -> GpcState:
        return self.states.get(gpc_id, GpcState(gpc_id))

    def record(self, gpc_id: str, day: int, *, correct: bool) -> GpcState:
        """One first attempt at one GPC on one day.

        Correct promotes a box; any error demotes to box 1 -- never to 0. A
        demotion to zero re-teaches, and re-teaching is the school's job.
        """
        s = self.state(gpc_id)
        if correct:
            streak_days = (*s.streak_days, day)
            new = replace(
                s,
                box=min(s.box + 1, MAX_BOX),
                streak=s.streak + 1,
                streak_days=streak_days,
                correct_days=(*s.correct_days, day),
                last_seen_day=day,
                attempts=s.attempts + 1,
                first_attempt_correct=s.first_attempt_correct + 1,
            )
        else:
            new = replace(
                s,
                box=1,
                streak=0,
                streak_days=(),
                last_seen_day=day,
                attempts=s.attempts + 1,
            )
        self.states[gpc_id] = new
        return new

    def mastered_ids(self) -> list[str]:
        return [gid for gid, s in self.states.items() if s.mastered]

    def to_dict(self) -> dict:
        return {
            gid: {
                "box": s.box,
                "streak": s.streak,
                "streak_days": list(s.streak_days),
                "correct_days": list(s.correct_days),
                "last_seen_day": s.last_seen_day,
                "attempts": s.attempts,
                "first_attempt_correct": s.first_attempt_correct,
            }
            for gid, s in sorted(self.states.items())
        }

    @classmethod
    def from_dict(cls, doc: dict) -> History:
        return cls({
            gid: GpcState(
                gpc_id=gid,
                box=row.get("box", 0),
                streak=row.get("streak", 0),
                streak_days=tuple(row.get("streak_days", ())),
                correct_days=tuple(row.get("correct_days", ())),
                last_seen_day=row.get("last_seen_day"),
                attempts=row.get("attempts", 0),
                first_attempt_correct=row.get("first_attempt_correct", 0),
            )
            for gid, row in doc.items()
        })


@dataclass(frozen=True)
class Item:
    """One step of the plan. Data only -- no widgets, no audio, no timing."""

    kind: ItemKind
    role: Role
    gpc_id: str | None
    payload: str
    graphemes: tuple[str, ...] = ()
    source: str = ""


@dataclass(frozen=True)
class Session:
    ceiling_label: str
    day: int
    items: tuple[Item, ...]

    def of_kind(self, kind: ItemKind) -> tuple[Item, ...]:
        return tuple(i for i in self.items if i.kind is kind)

    def gpc_ids(self) -> tuple[str, ...]:
        return tuple(dict.fromkeys(i.gpc_id for i in self.items if i.gpc_id))

    def __len__(self) -> int:
        return len(self.items)


def _split(n: int) -> tuple[int, int, int]:
    review = round(n * SHARE_REVIEW)
    new = round(n * SHARE_NEW)
    interleave = max(n - review - new, 0)
    return review, new, interleave


def select_gpcs(
    corpus: Corpus, ceiling: Ceiling, history: History, day: int, *, size: int = 5
) -> list[tuple[str, Role]]:
    """60% due-for-review, 20% newest permitted, 20% oldest mastered.

    If nothing is due, the session is shorter. kidnix does not manufacture work.
    """
    permitted = [g for g in corpus.gpcs if g.id in ceiling.gpc_ids]
    permitted.sort(key=lambda g: g.order)
    if not permitted:
        return []

    n_review, n_new, n_inter = _split(size)

    due = [
        g.id for g in permitted
        if history.state(g.id).seen and history.state(g.id).due_on(day)
    ]
    due.sort(key=lambda gid: (history.state(gid).last_seen_day or 0, gid))

    unseen = [g.id for g in permitted if not history.state(g.id).seen]
    mastered = [g.id for g in permitted if history.state(g.id).mastered]
    mastered.sort(key=lambda gid: (history.state(gid).last_seen_day or 0, gid))

    chosen: list[tuple[str, Role]] = []
    taken: set[str] = set()

    def take(ids: list[str], role: Role, limit: int) -> None:
        for gid in ids:
            if len(chosen) >= size or limit <= 0:
                return
            if gid in taken:
                continue
            chosen.append((gid, role))
            taken.add(gid)
            limit -= 1

    take(due, Role.REVIEW, n_review)
    # newest permitted GPC first: the one the school taught most recently
    take(list(reversed(unseen)), Role.NEW, n_new)
    take(mastered, Role.INTERLEAVE, n_inter)
    # only backfill from what is genuinely due or new -- never invent revision
    take(due, Role.REVIEW, size - len(chosen))
    take(list(reversed(unseen)), Role.NEW, size - len(chosen))
    return chosen


def compose_session(
    corpus: Corpus,
    ceiling: Ceiling,
    history: History,
    day: int = 0,
    *,
    size: int = 5,
    words_per_gpc: int = 2,
    rng: random.Random | None = None,
) -> Session:
    """A short Find it / Blend it / Read it plan, in that order.

    A to G is one loop, never a menu of seven games (research 10, section 4.1).
    Nothing in the returned plan can be outside ``ceiling``; ``test_schedule``
    asserts that on every session it can build.
    """
    rng = rng or random.Random(day)
    picks = select_gpcs(corpus, ceiling, history, day, size=size)
    items: list[Item] = []

    for gpc_id, role in picks:
        gpc = corpus.gpc_by_id[gpc_id]
        items.append(Item(ItemKind.FIND_IT, role, gpc_id, gpc.grapheme,
                          (gpc_id,), gpc.source))

    pool = allowed_words(corpus, ceiling)
    for gpc_id, role in picks:
        candidates = [w for w in pool if gpc_id in w.graphemes]
        if not candidates:
            continue
        candidates.sort(key=lambda w: (len(w.graphemes), w.text))
        head = candidates[: max(words_per_gpc * 4, words_per_gpc)]
        for w in rng.sample(head, min(words_per_gpc, len(head))):
            items.append(Item(ItemKind.BLEND_IT, role, gpc_id, w.text,
                              w.graphemes, w.source))

    # Always land in real language: one caption or sentence, then one book if the
    # ceiling reaches one. Never a pure isolated-grapheme drill loop (research 05
    # section 2a: phonics *and* meaning, from the start).
    sentences = allowed_sentences(corpus, ceiling)
    if sentences:
        s = rng.choice(sentences)
        items.append(Item(ItemKind.READ_IT, Role.REVIEW, None, s.text, (), s.source))

    # **One book, and only one.** Not a shelf-full and not a book per GPC: the
    # session is eight to twelve minutes and a text is two of them. The child
    # still chooses which book on the shelf (ADR-0013); what the schedule picks
    # is the one the shelf opens on, so that a child who takes the first thing
    # offered gets a different one from yesterday.
    books = texts_for(corpus, ceiling)
    if books:
        book = rng.choice(books)
        items.append(Item(ItemKind.READ_TEXT, Role.REVIEW, None, book.slug,
                          tuple(book.lines), "kidnix"))

    return Session(ceiling.label, day, tuple(items))
