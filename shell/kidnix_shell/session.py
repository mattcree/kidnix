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
    BUDGET_SPENT = "budget_spent"


# SYNTHESIS section 3: 25 min default, 10-45 range, ~60 min/day ceiling.
MIN_SESSION_MINUTES = 10
MAX_SESSION_MINUTES = 45


@dataclass(frozen=True)
class SessionPolicy:
    """Parent-set shape of the sandbox. Seconds throughout."""

    length: int = 25 * 60
    daily_budget: int = 60 * 60
    ending_offer_at: int = 6 * 60  # seconds *before* the end
    put_away_at: int = 2 * 60  # seconds before the end
    bedtime_start: time = time(19, 0)
    bedtime_end: time = time(7, 0)

    @classmethod
    def from_minutes(
        cls,
        length: float = 25,
        daily_budget: float = 60,
        ending_offer_at: float = 6,
        put_away_at: float = 2,
        bedtime_start: time = time(19, 0),
        bedtime_end: time = time(7, 0),
    ) -> SessionPolicy:
        return cls(
            length=int(length * 60),
            daily_budget=int(daily_budget * 60),
            ending_offer_at=int(ending_offer_at * 60),
            put_away_at=int(put_away_at * 60),
            bedtime_start=bedtime_start,
            bedtime_end=bedtime_end,
        )

    @classmethod
    def demo(cls) -> SessionPolicy:
        """--demo: a 3-minute session so the whole ritual fits in a CI run."""
        return cls(
            length=180,
            daily_budget=60 * 60,
            ending_offer_at=60,
            put_away_at=20,
            bedtime_start=time(23, 59),
            bedtime_end=time(0, 0),
        )

    def with_length_minutes(self, minutes: float) -> SessionPolicy:
        clamped = max(MIN_SESSION_MINUTES, min(MAX_SESSION_MINUTES, minutes))
        return replace(self, length=int(clamped * 60))

    def is_bedtime(self, when: datetime) -> bool:
        """Bedtime windows wrap midnight (19:00-07:00 is the default)."""
        if self.bedtime_start == self.bedtime_end:
            return False
        now = when.time()
        if self.bedtime_start < self.bedtime_end:
            return self.bedtime_start <= now < self.bedtime_end
        return now >= self.bedtime_start or now < self.bedtime_end

    def next_wake(self, when: datetime) -> datetime:
        """When the Sleeping screen may next let a session start."""
        if not self.is_bedtime(when):
            return when
        candidate = datetime.combine(when.date(), self.bedtime_end, tzinfo=when.tzinfo)
        if candidate <= when:
            candidate += timedelta(days=1)
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

    return SessionPolicy(
        length=minutes("length_minutes", default.length),
        daily_budget=minutes("daily_budget_minutes", default.daily_budget),
        ending_offer_at=minutes("ending_offer_minutes", default.ending_offer_at),
        put_away_at=minutes("put_away_minutes", default.put_away_at),
        bedtime_start=clock("bedtime_start", default.bedtime_start),
        bedtime_end=clock("bedtime_end", default.bedtime_end),
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


@dataclass
class DailyUsage:
    """Seconds spent today. Kid-owned state; resets at 04:00 (spec 7a)."""

    day: date
    seconds: int = 0
    path: Path | None = None

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
        return cls(day=stored_day, seconds=max(0, seconds), path=path)

    def save(self, path: Path | None = None) -> None:
        target = path or self.path
        if target is None:
            return
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            f'day = "{self.day.isoformat()}"\nseconds = {self.seconds}\n', encoding="utf-8"
        )
        self.path = target

    def roll(self, today: date) -> None:
        if self.day != today:
            self.day = today
            self.seconds = 0

    def add(self, seconds: int) -> None:
        self.seconds = max(0, self.seconds + seconds)

    def remaining(self, budget: int) -> int:
        return max(0, budget - self.seconds)


# --- the session itself --------------------------------------------------


@dataclass
class Session:
    """One bounded sitting.

    ``granted`` is the session's own length in seconds -- the policy length,
    capped by whatever is left of today's budget, plus any grants the grown-up
    added mid-session.
    """

    policy: SessionPolicy
    usage: DailyUsage
    started_at: datetime | None = None
    granted: int = 0
    _ended: bool = False

    # -- lifecycle --

    def may_start(self, now: datetime) -> StartRefusal:
        # Rolls the budget day first: a shell that has been sitting on the
        # Sleeping screen since last night must see the fresh budget at 04:00
        # without anyone having restarted it.
        self.usage.roll(budget_day(now))
        if self.policy.is_bedtime(now):
            return StartRefusal.BEDTIME
        if self.usage.remaining(self.policy.daily_budget) <= 0:
            return StartRefusal.BUDGET_SPENT
        return StartRefusal.OK

    def start(self, now: datetime, length: int | None = None) -> bool:
        """Begin. Returns False if policy refuses (bedtime / budget spent)."""
        self.usage.roll(budget_day(now))
        if self.may_start(now) is not StartRefusal.OK:
            return False
        wanted = self.policy.length if length is None else length
        self.granted = min(wanted, self.usage.remaining(self.policy.daily_budget))
        self.started_at = now
        self._ended = False
        log.info("session started for %d s (budget leaves %d s)", self.granted, wanted)
        return True

    def end(self, now: datetime) -> None:
        """Stop the clock and bank the time against today's budget."""
        if self.started_at is not None and not self._ended:
            self.usage.add(int((now - self.started_at).total_seconds()))
            self.usage.save()
        self._ended = True
        self.started_at = None
        self.granted = 0

    def add_minutes(self, minutes: int, now: datetime) -> int:
        """Grown-up grant (+5/+15/+30). Returns the seconds actually added.

        A grant is still bounded by the daily budget -- the parent raises the
        budget from the sheet if they want more than that.
        """
        if self.started_at is None:
            return 0
        spent = int((now - self.started_at).total_seconds())
        headroom = self.usage.remaining(self.policy.daily_budget) - self.granted
        added = max(0, min(minutes * 60, max(0, headroom)))
        self.granted += added
        if added and self.phase(now) is Phase.ENDED:
            # A grant during Goodbye reopens the session rather than stranding
            # the child on the ending screen.
            self._ended = False
        log.info("granted %d s (elapsed %d s, now %d s)", added, spent, self.granted)
        return added

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
        if left <= self.policy.put_away_at:
            return Phase.PUT_AWAY
        if left <= self.policy.ending_offer_at:
            return Phase.ENDING_OFFER
        return Phase.RUNNING

    def is_warm(self, now: datetime) -> bool:
        """Spec section 2: the sun warms in the last six minutes."""
        return self.running and self.remaining(now) <= self.policy.ending_offer_at
