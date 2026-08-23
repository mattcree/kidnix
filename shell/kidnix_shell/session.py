"""The session: how long the child gets, and how it ends (spec section 6).

Principle D from SYNTHESIS: *the machine ends the session*, predictably, at a
natural boundary, with a continuous analogue depletion the child can glance at.
No digits anywhere in the child-facing UI -- this module deals in seconds so
the sun can be drawn from a single float.

Everything here is pure and clock-injectable: the caller passes ``now``. The
GTK tick lives in :mod:`kidnix_shell.app`.
"""

from __future__ import annotations

import logging
import tomllib
from dataclasses import dataclass, replace
from datetime import date, datetime, time, timedelta
from enum import Enum
from pathlib import Path
from typing import Any

from .i18n import N_, _

log = logging.getLogger(__name__)


class Phase(Enum):
    """Where a running session is in its arc."""

    IDLE = "idle"  # not started
    RUNNING = "running"
    ENDING_OFFER = "ending_offer"  # T-6 min (spec S5)
    PUT_AWAY = "put_away"  # T-2 min (spec S6)
    ENDED = "ended"  # -> Goodbye (spec S7)


class StartRefusal(Enum):
    """Why a session may not start. Spoken as a friendly line, never an error."""

    OK = "ok"
    BEDTIME = "bedtime"
    #: Outside every ``[[windows]]`` the parent set (parent-panel §7.1). It sits
    #: **between** bedtime and the budget because the stricter and more
    #: comprehensible refusal has to win: a child outside their window at 8 pm
    #: is told it is night time, not that it is Tuesday.
    OUT_OF_HOURS = "out_of_hours"
    BUDGET_SPENT = "budget_spent"
    #: **This child's sitting is over** (ADR-0014). Set when their session
    #: reaches its ending, cleared by exactly the conditions that used to wake
    #: the whole machine: a new budget day, the bedtime window that ended it
    #: being over, or the schedule window having changed
    #: (:meth:`SessionPolicy.still_resting`).
    #:
    #: **Last of the four**, deliberately. Two of them can hold at once -- a
    #: child who pressed "All done" on a day whose budget was already gone is
    #: rested *and* spent -- and "that's all the computer time for today" is
    #: both truer and more actionable than "resting", which sounds temporary.
    #: The rest of the order is unchanged, so a machine with one child on it
    #: says exactly what it said before this refusal existed.
    RESTED = "rested"


# SYNTHESIS section 3: 25 min default, 10-45 range, ~60 min/day ceiling.
MIN_SESSION_MINUTES = 10
MAX_SESSION_MINUTES = 45

# --- the session floor (panel ruling, 2026-08-23) ------------------------
#
# ``start()`` used to do ``granted = min(wanted, budget_remaining)`` with no
# floor, and ``may_start()`` refused only when the budget was *exactly* spent.
# So the third sitting of a 60-minute day was ten minutes, and a well-meant
# "+5" on a spent day produced a two-minute sitting that **began in
# Phase.PUT_AWAY** -- the child answered "What's next after?" with a plan and
# was told "Let's keep that" over nothing ninety seconds later. Two reviewers
# found it independently (forum #14, #15) and a parent named the mechanism
# from the other side (#59: "do not let me give a grant that is too short to
# be a session").
#
# So: below the floor there is no session. The refusal lands at Who's here,
# **before** the child has invested a plan, and the grown-up sheet refuses a
# sub-floor grant in words with the minimum named.

#: A sitting shorter than this is not a sitting, it is an ending.
MIN_SESSION_SECONDS = 5 * 60
#: The floor on the parent-configurable floor. A parent may go down to three
#: minutes; below that the ritual itself does not fit inside the session.
MIN_SESSION_FLOOR_SECONDS = 3 * 60

# --- the ending windows are proportional (panel ruling, 2026-08-23) ------
#
# They were absolute: T-6 and T-2 whatever the sitting was. At the fifteen
# minutes CHILD-TEST-PROTOCOL specifies that is 40% of the sitting spent in
# "the sun is going down"; at ten minutes it is 60%. Worse, the *rate* of the
# sun changed silently between sittings, so a child who had spent three weeks
# learning to read it was misled on exactly the sittings that matter most
# (forum #33). Both windows are now a fraction of what was actually granted,
# with a floor and a ceiling, and the ritual keeps its two beats.

#: Fraction of the granted sitting spent in the ending offer window.
OFFER_FRACTION = 0.20
OFFER_MIN_SECONDS = 2 * 60
OFFER_MAX_SECONDS = 4 * 60
#: Fraction of the granted sitting spent putting things away.
PUT_AWAY_FRACTION = 0.10
PUT_AWAY_MIN_SECONDS = 60
PUT_AWAY_MAX_SECONDS = 2 * 60

#: "Finish this one" holds put-away to one beat before the hard stop -- T-1.
#: The deferral may never bring the ending *forward*, which is what the
#: ``min()`` in :meth:`SessionPolicy.put_away_seconds` guarantees.
DEFERRED_PUT_AWAY_SECONDS = 60


def _clamp(value: float, low: int, high: int) -> int:
    return int(max(low, min(high, value)))


# --- schedule windows (parent-panel section 7.1) -------------------------
#
# ``[[windows]]`` in ``session.toml``, written by the parent panel:
#
#     [[windows]]
#     label = "After school"
#     days  = ["mon", "tue", "wed", "thu", "fri"]
#     start = "15:30"
#     end   = "18:00"
#
# Days are the first three letters, lower case; times are 24-hour. **No
# windows at all means no restriction**, which is the same empty-means-all
# reasoning as ``allowed_activity_ids``: a parent who deleted their last
# window, or a file that failed to parse, must never lock a child out of a
# machine that was open to them yesterday.

#: Monday first, so the index is :meth:`datetime.date.weekday`'s own.
DAYS: tuple[str, ...] = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")

#: How far ahead :meth:`Window.next_start` is willing to look. Windows repeat
#: weekly, so eight days is a full cycle plus the day we started in.
WINDOW_SEARCH_DAYS = 8


def _minutes(when: time) -> int:
    return when.hour * 60 + when.minute


@dataclass(frozen=True)
class Window:
    """One ``[[windows]]`` table: when the computer may be used at all.

    A window whose ``end`` is at or before its ``start`` runs past midnight
    into the next morning and **belongs to the day it starts on** -- which is
    what a parent means by "Friday evening until nine". So Friday 21:00-01:00
    covers Saturday 00:30 without ``sat`` being in ``days``, and does *not*
    cover Friday 00:30.
    """

    days: frozenset[str]
    start: time
    end: time
    #: The parent's own name for it ("After school"). Carried so a config
    #: round-trip does not eat it; nothing child-facing ever shows it, because
    #: it is the grown-up's words and not the child's.
    label: str = ""

    @property
    def wraps_midnight(self) -> bool:
        """True when the window runs into the next morning.

        Equal start and end is a *whole day* starting at that time, not an
        empty window: the panel refuses to write one, and the reading that
        keeps a child on the machine is the safer of the two.
        """
        return _minutes(self.end) <= _minutes(self.start)

    def covers(self, when: datetime) -> bool:
        """Is ``when`` inside this window?"""
        if not self.days:
            return False
        minute = _minutes(when.time())
        start, end = _minutes(self.start), _minutes(self.end)
        today = DAYS[when.weekday()]
        if not self.wraps_midnight:
            return today in self.days and start <= minute < end
        if today in self.days and minute >= start:
            return True
        yesterday = DAYS[(when.weekday() - 1) % 7]
        return yesterday in self.days and minute < end

    def next_start(self, when: datetime) -> datetime | None:
        """The first moment strictly after ``when`` that this window opens."""
        if not self.days:
            return None
        for offset in range(WINDOW_SEARCH_DAYS):
            day = when.date() + timedelta(days=offset)
            if DAYS[day.weekday()] not in self.days:
                continue
            candidate = datetime.combine(day, self.start, tzinfo=when.tzinfo)
            if candidate > when:
                return candidate
        return None


def parse_days(raw: Any, source: str = "session.toml") -> frozenset[str]:
    """``["Mon", "tue"]`` -> ``frozenset({"mon", "tue"})``. Junk is dropped.

    Defensive in the same way every other key in that file is: a day nobody
    recognises is skipped with a warning rather than taking the whole window
    with it, because a typo in one of seven strings should not be the
    difference between a schedule and no schedule.
    """
    if not isinstance(raw, (list, tuple)):
        log.warning('%s: [[windows]] days must be a list like ["mon"]; skipping', source)
        return frozenset()
    days: set[str] = set()
    for item in raw:
        name = str(item).strip().lower()[:3]
        if name in DAYS:
            days.add(name)
        else:
            log.warning("%s: [[windows]] has no day called %r; ignoring it", source, item)
    return frozenset(days)


def parse_clock(raw: Any, source: str = "session.toml", key: str = "start") -> time | None:
    """``"15:30"`` -> ``time(15, 30)``, or ``None`` with a warning."""
    if not isinstance(raw, str):
        log.warning('%s: [[windows]] %s must be a string like "15:30"', source, key)
        return None
    hour, _sep, minute = raw.strip().partition(":")
    try:
        return time(int(hour), int(minute or 0))
    except ValueError:
        log.warning("%s: [[windows]] %s=%r is not HH:MM", source, key, raw)
        return None


def parse_windows(raw: Any, source: str = "session.toml") -> tuple[Window, ...]:
    """``[[windows]]`` out of TOML. A malformed window is skipped, loudly.

    Returning ``()`` -- which is what a missing key, a wrong type and a file
    full of unparseable windows all produce -- means *no restriction*. That is
    deliberate and it is the only safe direction to fail in.
    """
    if raw is None:
        return ()
    if not isinstance(raw, (list, tuple)):
        log.warning("%s: [[windows]] must be a list of tables; ignoring it", source)
        return ()
    windows: list[Window] = []
    for entry in raw:
        if not isinstance(entry, dict):
            log.warning("%s: skipping malformed window %r", source, entry)
            continue
        days = parse_days(entry.get("days"), source)
        start = parse_clock(entry.get("start"), source, "start")
        end = parse_clock(entry.get("end"), source, "end")
        if not days or start is None or end is None:
            log.warning("%s: skipping window %r; it has no days or no times", source, entry)
            continue
        label = entry.get("label", "")
        windows.append(Window(days=days, start=start, end=end, label=str(label) if label else ""))
    return tuple(windows)


@dataclass(frozen=True)
class SessionPolicy:
    """Parent-set shape of the sandbox. Seconds throughout."""

    length: int = 25 * 60
    daily_budget: int = 60 * 60
    #: **Historical, and only a ceiling now.** The ending offer's window is
    #: computed from what was actually granted
    #: (:meth:`offer_seconds`); this is the largest it may ever be, so a parent
    #: who writes ``ending_offer_minutes = 3`` still gets three.
    ending_offer_at: int = OFFER_MAX_SECONDS  # seconds *before* the end
    put_away_at: int = PUT_AWAY_MAX_SECONDS  # seconds before the end
    bedtime_start: time = time(19, 0)
    bedtime_end: time = time(7, 0)
    #: No session is granted below this (panel ruling, 2026-08-23).
    min_session: int = MIN_SESSION_SECONDS
    offer_min: int = OFFER_MIN_SECONDS
    put_away_min: int = PUT_AWAY_MIN_SECONDS
    #: ``[[windows]]`` (parent-panel section 7.1). **Empty means no
    #: restriction**, never "no time at all".
    windows: tuple[Window, ...] = ()

    @classmethod
    def from_minutes(
        cls,
        length: float = 25,
        daily_budget: float = 60,
        ending_offer_at: float = OFFER_MAX_SECONDS / 60,
        put_away_at: float = PUT_AWAY_MAX_SECONDS / 60,
        bedtime_start: time = time(19, 0),
        bedtime_end: time = time(7, 0),
        min_session: float = MIN_SESSION_SECONDS / 60,
    ) -> SessionPolicy:
        return cls(
            length=int(length * 60),
            daily_budget=int(daily_budget * 60),
            ending_offer_at=int(ending_offer_at * 60),
            put_away_at=int(put_away_at * 60),
            bedtime_start=bedtime_start,
            bedtime_end=bedtime_end,
            min_session=int(min_session * 60),
        )

    @classmethod
    def demo(cls) -> SessionPolicy:
        """--demo: a 3-minute session so the whole ritual fits in a CI run.

        The floor and the window caps scale with it, because the demo is the
        one place where a three-minute sitting is a legitimate session rather
        than the stub the floor exists to refuse.
        """
        return cls(
            length=180,
            daily_budget=60 * 60,
            ending_offer_at=60,
            put_away_at=20,
            bedtime_start=time(23, 59),
            bedtime_end=time(0, 0),
            min_session=60,
            offer_min=60,
            put_away_min=15,
        )

    def with_length_minutes(self, minutes: float) -> SessionPolicy:
        clamped = max(MIN_SESSION_MINUTES, min(MAX_SESSION_MINUTES, minutes))
        return replace(self, length=int(clamped * 60))

    # -- the two ending windows, as a proportion of what was granted --

    def offer_seconds(self, granted: int) -> int:
        """How long before the hard stop the ending offer arrives.

        Proportional, clamped both ways, and then held strictly under half the
        sitting: a session must never open into its own ending, whatever a
        hand-edited ``session.toml`` says. ``tests/test_session.py`` asserts
        ``offer < granted / 2`` across every reachable grant.
        """
        if granted <= 0:
            return 0
        window = _clamp(granted * OFFER_FRACTION, self.offer_min, self.ending_offer_at)
        return min(window, max(0, (granted - 1) // 2))

    def put_away_seconds(self, granted: int, *, deferred: bool = False) -> int:
        """How long before the hard stop the shell asks for things to be put away.

        ``deferred`` is "Finish this one" (spec S5, re-ruled 2026-08-23): the
        child keeps the activity until one beat before the hard stop. The
        ``min()`` is what makes the promise safe -- a deferral can only ever
        move put-away *later*, never earlier.
        """
        if granted <= 0:
            return 0
        window = _clamp(granted * PUT_AWAY_FRACTION, self.put_away_min, self.put_away_at)
        offer = self.offer_seconds(granted)
        window = min(window, max(0, offer - 1))  # two beats, never one
        if deferred:
            window = min(window, max(1, min(DEFERRED_PUT_AWAY_SECONDS, self.put_away_min)))
        return window

    def is_bedtime(self, when: datetime) -> bool:
        """Bedtime windows wrap midnight (19:00-07:00 is the default)."""
        if self.bedtime_start == self.bedtime_end:
            return False
        now = when.time()
        if self.bedtime_start < self.bedtime_end:
            return self.bedtime_start <= now < self.bedtime_end
        return now >= self.bedtime_start or now < self.bedtime_end

    def in_window(self, when: datetime) -> bool:
        """Is ``when`` inside one of the parent's schedule windows?

        **True when there are none.** An empty list is "no restriction" and
        never "nothing is allowed" -- see :func:`parse_windows`.
        """
        if not self.windows:
            return True
        return any(window.covers(when) for window in self.windows)

    def still_resting(self, rested_at: datetime, now: datetime) -> bool:
        """Is a sitting that ended at ``rested_at`` still over at ``now``? (ADR-0014)

        The rule this asks used to live in ``app.ShellWindow._maybe_wake`` and
        it was asked about the **machine**: the screen rested until the next
        window or the next day, so a sibling could not start without a grown-up
        at the gate. The argument for the rule -- "re-waking thirty seconds
        later would teach a child that the ending is negotiable" -- is about
        the *same* child and says nothing about a different one, so the
        question moved to the profile and the conditions came with it,
        unchanged:

        * the **budget day has rolled** (04:00, :func:`budget_day`) -- which is
          what ends an ordinary afternoon's rest;
        * the **bedtime window that ended it is over**;
        * the **schedule window has changed** -- the sitting ended outside
          every ``[[windows]]``, so whatever window is open now is not the one
          it ended in.

        Pure, and it is the *only* statement of the rule: ``may_start`` and the
        shell's wake-up both ask it, so the two cannot drift apart.
        """
        if budget_day(now) != budget_day(rested_at):
            return False
        if self.is_bedtime(rested_at):
            return False
        return self.in_window(rested_at)

    def next_window_start(self, when: datetime) -> datetime | None:
        """The earliest window opening strictly after ``when``, or ``None``.

        ``None`` when no windows are configured -- there is nothing to wait
        for, so the Resting screen's "when" falls back to the two gates it
        already had.
        """
        if not self.windows:
            return None
        starts = [start for start in (window.next_start(when) for window in self.windows) if start]
        return min(starts) if starts else None

    def _after_bedtime(self, when: datetime) -> datetime:
        """The end of the bedtime window ``when`` is inside."""
        candidate = datetime.combine(when.date(), self.bedtime_end, tzinfo=when.tzinfo)
        if candidate <= when:
            candidate += timedelta(days=1)
        return candidate

    def next_wake(self, when: datetime) -> datetime:
        """When the Sleeping screen may next let a session start.

        Two gates now, and both have to be open: bedtime has to be over
        **and** ``when`` has to be inside a schedule window. They interact --
        the next window may open inside bedtime, and the end of bedtime may
        land outside every window -- so this walks the pair until they agree
        rather than taking a single ``max()`` of two independent answers.

        The walk is bounded. A household whose windows lie entirely inside
        bedtime has asked for two contradictory things, and the honest answer
        to a contradiction is the best moment found, not a hang.
        """
        candidate = when
        for _round in range(WINDOW_SEARCH_DAYS):
            moved = False
            if self.is_bedtime(candidate):
                candidate = self._after_bedtime(candidate)
                moved = True
            if not self.in_window(candidate):
                opens = self.next_window_start(candidate)
                if opens is None:  # unreachable: no windows means in_window()
                    return candidate
                candidate = max(candidate, opens)
                moved = True
            if not moved:
                return candidate
        log.warning("the bedtime window and the schedule windows never agree; using %s", candidate)
        return candidate


def load_policy(path: Path | None) -> SessionPolicy:
    """Read ``session.toml``. Any problem falls back to the defaults, loudly."""
    if path is None:
        log.info("no root-owned session config; using the SYNTHESIS defaults")
        return SessionPolicy()
    if not path.is_file():
        log.info("no session config at %s; using defaults", path)
        return SessionPolicy()
    try:
        with path.open("rb") as handle:
            data = tomllib.load(handle)
    except (OSError, tomllib.TOMLDecodeError) as exc:
        log.warning("session config %s unreadable (%s); using defaults", path, exc)
        return SessionPolicy()

    default = SessionPolicy()

    def minutes(key: str, fallback: int) -> int:
        value = data.get(key)
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return fallback
        if value < 0:
            return fallback
        return int(value * 60)

    def clock(key: str, fallback: time) -> time:
        value = data.get(key)
        if not isinstance(value, str):
            return fallback
        try:
            hour, _, minute = value.partition(":")
            return time(int(hour), int(minute or 0))
        except ValueError:
            log.warning("session config %s: %s=%r is not HH:MM", path, key, value)
            return fallback

    # The floor is parent-configurable *downwards to three minutes only*: below
    # that the two-beat ritual does not fit inside the session it is ending.
    floor = max(MIN_SESSION_FLOOR_SECONDS, minutes("min_session_minutes", default.min_session))
    if floor != minutes("min_session_minutes", default.min_session):
        log.warning(
            "session config %s: min_session_minutes is below the %d-minute floor; using %d",
            path,
            MIN_SESSION_FLOOR_SECONDS // 60,
            floor // 60,
        )

    return SessionPolicy(
        length=minutes("length_minutes", default.length),
        daily_budget=minutes("daily_budget_minutes", default.daily_budget),
        ending_offer_at=minutes("ending_offer_minutes", default.ending_offer_at),
        put_away_at=minutes("put_away_minutes", default.put_away_at),
        bedtime_start=clock("bedtime_start", default.bedtime_start),
        bedtime_end=clock("bedtime_end", default.bedtime_end),
        min_session=floor,
        windows=parse_windows(data.get("windows"), str(path)),
    )


# --- daily usage ---------------------------------------------------------

#: Spec 7a: "the daily budget resets at 04:00 local". Midnight is the wrong
#: boundary -- a child awake at 00:30 is still having last night's evening, and
#: handing them a fresh hour at midnight is exactly backwards.
BUDGET_RESET_HOUR = 4


def budget_day(now: datetime) -> date:
    """Which day's budget ``now`` spends. Rolls at 04:00, not at midnight."""
    return (now - timedelta(hours=BUDGET_RESET_HOUR)).date()


def next_budget_reset(now: datetime) -> datetime:
    """When the budget next refills."""
    today = datetime.combine(now.date(), time(BUDGET_RESET_HOUR, 0), tzinfo=now.tzinfo)
    return today if now < today else today + timedelta(days=1)


def _parse_rested_at(raw: Any, path: Path) -> datetime | None:
    """``rested_at`` out of a usage file. Anything odd is "not rested".

    The failure direction matters: a mark nobody can read must not lock a
    child out of a machine that worked ten minutes ago, and the cost of
    getting it wrong the other way is one extra sitting.
    """
    if raw is None:
        return None
    if isinstance(raw, datetime):  # TOML's own datetime, if somebody hand-edits one
        return raw
    try:
        return datetime.fromisoformat(str(raw))
    except (TypeError, ValueError):
        log.warning("usage state %s: rested_at=%r is not a datetime; ignoring", path, raw)
        return None


@dataclass
class DailyUsage:
    """Seconds spent today. Kid-owned state; resets at 04:00 (spec 7a).

    **One of these per child** since profiles landed: it is loaded from
    ``paths.for_profile(id).usage_state``, so the budget, and now the "this
    child's sitting is over" mark, belong to whoever is sitting down rather
    than to the machine (ADR-0014).
    """

    day: date
    seconds: int = 0
    path: Path | None = None
    #: When this child's sitting ended, or ``None`` if they have not had one
    #: today (ADR-0014). Persisted beside the seconds because it answers the
    #: same question the seconds answer -- "may this child start now?" -- and
    #: because a shell that is restarted mid-afternoon must not hand back a
    #: sitting the ritual has already ended.
    rested_at: datetime | None = None

    @classmethod
    def for_now(cls, path: Path, now: datetime) -> DailyUsage:
        """Load the usage file against the 04:00 budget day."""
        return cls.load(path, budget_day(now))

    @classmethod
    def load(cls, path: Path, today: date) -> DailyUsage:
        if not path.is_file():
            return cls(day=today, path=path)
        try:
            with path.open("rb") as handle:
                data = tomllib.load(handle)
            stored_day = date.fromisoformat(str(data.get("day", "")))
            seconds = int(data.get("seconds", 0))
        except (OSError, ValueError, tomllib.TOMLDecodeError) as exc:
            log.warning("usage state %s unreadable (%s); starting fresh", path, exc)
            return cls(day=today, path=path)
        if stored_day != today:
            return cls(day=today, path=path)
        return cls(
            day=stored_day,
            seconds=max(0, seconds),
            path=path,
            rested_at=_parse_rested_at(data.get("rested_at"), path),
        )

    def save(self, path: Path | None = None) -> None:
        target = path or self.path
        if target is None:
            return
        target.parent.mkdir(parents=True, exist_ok=True)
        lines = [f'day = "{self.day.isoformat()}"', f"seconds = {self.seconds}"]
        if self.rested_at is not None:
            # A quoted string rather than TOML's own datetime type: this file
            # is read with ``tomllib`` and written by hand, and a naive local
            # datetime round-trips through ISO-8601 without either half having
            # to have an opinion about time zones.
            lines.append(f'rested_at = "{self.rested_at.isoformat(timespec="seconds")}"')
        target.write_text("\n".join(lines) + "\n", encoding="utf-8")
        self.path = target

    def roll(self, today: date) -> None:
        if self.day != today:
            self.day = today
            self.seconds = 0
            # A new budget day is one of the three things that ends a rest
            # (:meth:`SessionPolicy.still_resting`), so the mark goes with the
            # seconds rather than being left for the predicate to ignore.
            self.rested_at = None

    def rest(self, now: datetime) -> None:
        """This child's sitting is over (ADR-0014). Idempotent within a day.

        The *first* ending of the day is the one remembered: a second call --
        a grown-up ending an already-ended session from the sheet, a Goodbye
        re-entered -- must not push the mark forward, because
        ``still_resting`` measures from it.
        """
        if self.rested_at is None:
            self.rested_at = now
            self.save()

    def wake(self) -> None:
        """Forget the rest. What "the grown-up said so" does (ADR-0014)."""
        if self.rested_at is not None:
            self.rested_at = None
            self.save()

    def add(self, seconds: int) -> None:
        self.seconds = max(0, self.seconds + seconds)

    def remaining(self, budget: int) -> int:
        return max(0, budget - self.seconds)


# --- may this child start? (ADR-0014) ------------------------------------
#
# Two free functions, because "may *that* child start?" is a question the
# shell has to answer about a profile that is **not** the live one -- the
# faces on Who's here, and "is anybody able to start, or is the whole machine
# resting?". Answering it used to mean swapping the live profile in and out to
# borrow its ``Session``, which would drag the Journal, the progress counter,
# the band tint and the language along with it.
#
# So the policy plus a ``DailyUsage`` loaded from that child's own
# ``usage_state`` is all either of these takes, and :class:`Session` is a thin
# wrapper over them. Nothing here mutates anything.


def refusal_for(policy: SessionPolicy, usage: DailyUsage, now: datetime) -> StartRefusal:
    """Why this child may not start right now, or :attr:`StartRefusal.OK`.

    The order is :class:`StartRefusal`'s own and the reasoning is written
    there: bedtime, then out of hours, then the spent budget, then rested.

    ``usage`` is read against the 04:00 budget day rather than rolled, because
    this is asked about children who are not sitting at the machine: a stale
    file is a fresh day, exactly as :meth:`DailyUsage.roll` would make it, and
    nobody else's state file is written as a side effect of drawing a face.
    """
    today = budget_day(now)
    stale = usage.day != today
    spent = 0 if stale else usage.seconds
    rested_at = None if stale else usage.rested_at

    if policy.is_bedtime(now):
        return StartRefusal.BEDTIME
    if not policy.in_window(now):
        return StartRefusal.OUT_OF_HOURS
    # The floor, not zero (panel ruling, 2026-08-23). Four minutes left of the
    # day is not a short session, it is a session that opens into its own
    # ending -- so the answer is a warm no at the door.
    if max(0, policy.daily_budget - spent) < policy.min_session:
        return StartRefusal.BUDGET_SPENT
    if rested_at is not None and policy.still_resting(rested_at, now):
        return StartRefusal.RESTED
    return StartRefusal.OK


def next_allowed_for(policy: SessionPolicy, usage: DailyUsage, now: datetime) -> datetime:
    """The next moment this child could start. Drives the Resting line.

    Four gates now, and the latest of them wins: the bedtime window has to be
    over, ``now`` has to be inside one of the parent's schedule windows
    (:meth:`SessionPolicy.next_wake` settles those two between themselves),
    there has to be a budget again, **and** this child's sitting has to be
    over with (ADR-0014). A child who is told the computer is resting and
    cannot tell whether it comes back after tea, tomorrow or on Saturday is
    the condition D2 exists to stop (forum #31).

    The last two gates stay here rather than in ``next_wake`` because they are
    the ones about *this child* -- ``policy`` is the machine's and ``usage`` is
    theirs.
    """
    when = policy.next_wake(now)
    spent = usage.remaining(policy.daily_budget) < policy.min_session
    resting = usage.rested_at is not None and policy.still_resting(usage.rested_at, now)
    if spent or resting:
        when = max(when, next_budget_reset(now))
        if policy.windows:
            # 04:00 is outside every schedule a household actually sets, so on
            # a machine that has one the gates are asked again about the moment
            # the budget returns. Guarded on ``windows`` so a machine without a
            # schedule keeps exactly the answer it gave before this key existed
            # -- "tomorrow, when the budget rolls" -- rather than quietly
            # gaining the bedtime gate on top.
            when = policy.next_wake(when)
    return when


# --- the session itself --------------------------------------------------


@dataclass
class Session:
    """One bounded sitting.

    ``granted`` is the session's own length in seconds -- the policy length,
    capped by whatever is left of today's budget, plus any grants the grown-up
    added mid-session.

    ``offer_answered`` is the ending offer's one-shot latch (spec S5). The
    offer is a *question*, and a question asked twice is not a ritual, it is
    nagging: once the child has answered it, the shell must leave them alone
    until Put away. A grown-up grant that pushes the hard stop back past a new
    T-6 re-arms it, because that genuinely is a new ending to warn about.
    """

    policy: SessionPolicy
    usage: DailyUsage
    started_at: datetime | None = None
    granted: int = 0
    _ended: bool = False
    _offer_answered: bool = False
    #: "Finish this one" was chosen: put-away is held to one beat before the
    #: hard stop, which is what makes the sentence the shell said true.
    _put_away_deferred: bool = False

    # -- lifecycle --

    def may_start(self, now: datetime) -> StartRefusal:
        """This child's own answer. The rule is :func:`refusal_for`.

        Rolls the budget day first: a shell that has been sitting on the
        Sleeping screen since last night must see the fresh budget at 04:00
        without anyone having restarted it. That is the only difference from
        the free function -- which is asked about children who are *not*
        sitting at the machine and therefore writes nothing.
        """
        self.usage.roll(budget_day(now))
        return refusal_for(self.policy, self.usage, now)

    def start(self, now: datetime, length: int | None = None) -> bool:
        """Begin. Returns False if policy refuses (bedtime / budget spent).

        The grant is never below :attr:`SessionPolicy.min_session`: ``may_start``
        has already established that the budget can afford the floor, so a
        ``length`` shorter than it is raised rather than honoured. A grown-up
        who wants a three-minute sitting is refused in the sheet, in words.
        """
        self.usage.roll(budget_day(now))
        if self.may_start(now) is not StartRefusal.OK:
            return False
        wanted = self.policy.length if length is None else length
        remaining = self.usage.remaining(self.policy.daily_budget)
        granted = min(wanted, remaining)
        if granted < self.policy.min_session:
            granted = min(self.policy.min_session, remaining)
            log.info(
                "asked for %d s; the floor is %d s, so that is what was granted",
                wanted,
                granted,
            )
        self.granted = granted
        self.started_at = now
        self._ended = False
        self._offer_answered = False
        self._put_away_deferred = False
        log.info(
            "session started for %d s (offer at T-%d s, put away at T-%d s)",
            self.granted,
            self.offer_at,
            self.put_away_at,
        )
        return True

    def end(self, now: datetime) -> None:
        """Stop the clock and bank the time against today's budget."""
        if self.started_at is not None and not self._ended:
            self.usage.add(int((now - self.started_at).total_seconds()))
            self.usage.save()
        self._ended = True
        self.started_at = None
        self.granted = 0
        self._offer_answered = False
        self._put_away_deferred = False

    def may_add(self, minutes: int, now: datetime) -> int:
        """Seconds a ``+N`` grant would actually add, or 0 if it is refused.

        Pure: the sheet asks this *before* granting so it can say no in words
        with the minimum named (forum #59, #60). A grant the daily budget
        truncates below the session floor is refused whole rather than
        half-given -- "+5" that buys two minutes is the arithmetic that broke
        Priya's Tuesday afternoon.
        """
        if self.started_at is None:
            return 0
        wanted = max(0, minutes) * 60
        headroom = self.usage.remaining(self.policy.daily_budget) - self.granted
        added = max(0, min(wanted, max(0, headroom)))
        if added < wanted and added < self.policy.min_session:
            return 0
        return added

    def add_minutes(self, minutes: int, now: datetime) -> int:
        """Grown-up grant (+5/+15/+30). Returns the seconds actually added.

        A grant is still bounded by the daily budget -- the parent raises the
        budget from the sheet if they want more than that -- and a grant the
        budget would cut below the floor is refused rather than truncated
        (:meth:`may_add`).
        """
        if self.started_at is None:
            return 0
        spent = int((now - self.started_at).total_seconds())
        added = self.may_add(minutes, now)
        self.granted += added
        if added and self.phase(now) is Phase.ENDED:
            # A grant during Goodbye reopens the session rather than stranding
            # the child on the ending screen.
            self._ended = False
        if added and self.remaining(now) > self.offer_at:
            # The hard stop moved: there is a *new* T-6 coming, so the offer is
            # armed again. A grant too small to clear the offer window leaves
            # the latch alone -- re-asking inside the same warning would be the
            # nagging this latch exists to prevent.
            self._offer_answered = False
        log.info("granted %d s (elapsed %d s, now %d s)", added, spent, self.granted)
        return added

    # -- the ending offer's one-shot latch (spec S5) --

    @property
    def offer_answered(self) -> bool:
        """Has the child already answered this session's ending offer?"""
        return self._offer_answered

    def answer_offer(self, *, defer_put_away: bool = False) -> None:
        """Record that the offer was answered. Idempotent.

        ``defer_put_away`` is "Finish this one" (panel ruling, 2026-08-23).
        Until it existed both answers did the same thing to the machine, so
        the choice was theatre and the sentence "finish this one" was a promise
        the clock did not keep (forum #20, #29). Now the answer moves put-away
        to one beat before the hard stop, and the words say so.
        """
        if not self._offer_answered:
            log.info("the ending offer was answered; not asking again this session")
        self._offer_answered = True
        if defer_put_away and not self._put_away_deferred:
            self._put_away_deferred = True
            log.info(
                "put-away deferred to T-%d s: the child said they would finish this one",
                self.put_away_at,
            )

    @property
    def put_away_deferred(self) -> bool:
        return self._put_away_deferred

    # -- the two windows, for this sitting --

    @property
    def offer_at(self) -> int:
        """Seconds before the hard stop that the ending offer arrives."""
        return self.policy.offer_seconds(self.granted)

    @property
    def put_away_at(self) -> int:
        """Seconds before the hard stop that put-away arrives, this sitting."""
        return self.policy.put_away_seconds(self.granted, deferred=self._put_away_deferred)

    # -- state --

    @property
    def running(self) -> bool:
        return self.started_at is not None and not self._ended

    def elapsed(self, now: datetime) -> int:
        if self.started_at is None:
            return 0
        return max(0, int((now - self.started_at).total_seconds()))

    def remaining(self, now: datetime) -> int:
        if self.started_at is None:
            return 0
        return max(0, self.granted - self.elapsed(now))

    def fraction_spent(self, now: datetime) -> float:
        """0.0 at the start, 1.0 at the hard stop. This is the sun's position."""
        if self.started_at is None or self.granted <= 0:
            return 0.0
        return min(1.0, self.elapsed(now) / self.granted)

    def phase(self, now: datetime) -> Phase:
        if self.started_at is None:
            return Phase.ENDED if self._ended else Phase.IDLE
        left = self.remaining(now)
        if left <= 0:
            return Phase.ENDED
        if left <= self.put_away_at:
            return Phase.PUT_AWAY
        if left <= self.offer_at:
            return Phase.ENDING_OFFER
        return Phase.RUNNING

    def is_warm(self, now: datetime) -> bool:
        """Spec section 2: the sun warms over the ending window."""
        return self.running and self.remaining(now) <= self.offer_at

    # -- when the machine is next allowed to open (spec 7a) --

    def next_allowed(self, now: datetime) -> datetime:
        """The next moment this child could start. See :func:`next_allowed_for`."""
        return next_allowed_for(self.policy, self.usage, now)

    def fraction_left(self, now: datetime) -> float:
        """1.0 at the start, 0.0 at the hard stop. What the sun *says*."""
        return 1.0 - self.fraction_spent(now)

    def time_left_words(self, now: datetime) -> str:
        """What tapping the sun says (08 section 4.6)."""
        return time_left_words(self.fraction_left(now), running=self.running)


# --- what the sun says when a child taps it (08 section 4.6) --------------
#
# "Tapping speaks the remaining time in child terms." The sun is the most
# distinctive thing in the build and until v0.1.3 it was an `AccessibleRole.IMG`
# with no gesture: a five-year-old could look at it and not ask it anything.
#
# Every one of these is a *comparison*, never a quantity. A four-year-old has
# no idea what "twelve minutes" is and every idea what "one story" is; a number
# would also put a digit into the one part of the product that has never had
# one (01 #19, 01 #30 -- a countdown is an anxiety animation).

#: More than two thirds of the sitting still ahead.
LOTS_LEFT = N_("Lots of time left.")
#: A third to two thirds -- about ten minutes of a twenty-five minute session,
#: which is a bedtime story. The unit a child already owns.
ONE_STORY_LEFT = N_("About as long as one story.")
#: Inside the last third, but before the ending offer.
A_LITTLE_LEFT = N_("A little bit of time left.")
#: The last tenth. The same words the ritual is about to use, said early.
NEARLY_TIME = N_("Nearly time to put things away.")
#: No session running: Goodbye, or the shell sitting idle. Honest, not sad.
NOT_RUNNING = N_("The sun has gone down for today.")

LOTS_ABOVE = 2.0 / 3.0
ONE_STORY_ABOVE = 1.0 / 3.0
A_LITTLE_ABOVE = 0.1


def time_left_words(fraction_left: float, *, running: bool = True) -> str:
    """Map "how much of the sitting is left" onto words with no digits in them.

    Pure and total: any float, including nonsense from a clock that jumped,
    lands on one of five sentences, each of them two sentences or fewer and
    twelve words or fewer (01 #16).
    """
    if not running:
        return _(NOT_RUNNING)
    fraction = max(0.0, min(1.0, fraction_left))
    if fraction > LOTS_ABOVE:
        return _(LOTS_LEFT)
    if fraction > ONE_STORY_ABOVE:
        return _(ONE_STORY_LEFT)
    if fraction > A_LITTLE_ABOVE:
        return _(A_LITTLE_LEFT)
    return _(NEARLY_TIME)
