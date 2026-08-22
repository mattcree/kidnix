"""The ending ritual, as a pure decision (spec S5-S7).

The clock says which :class:`~kidnix_shell.session.Phase` the session is in and
the navigation graph says which :class:`~kidnix_shell.state.State` the child is
looking at. This module is the single place that turns those two -- plus the
ending offer's one-shot latch -- into "and therefore the shell should do X".

It exists because that decision used to live inside ``app._advance_ritual``,
where it fired on every 500 ms tick and could not be tested without a display.
The bug that followed (`docs/spikes/e2e-scenario.md` section 3.2) was exactly
the kind a pure function makes impossible to reintroduce quietly: the shell
re-presented the ending offer one second after the child answered it, and kept
doing so for the whole four-minute window.

Spec S5, restated as rules:

* At T-6 the offer appears **once**.
* Any of the three answers -- "Finish this one", "One last little thing",
  "Ask for more time" -- dismisses it, and the child carries on wherever they
  were (Home stays Home, so they may still open one more activity).
* Nothing asks again before Put away at T-2, which happens regardless.
* Only a grown-up grant that pushes the hard stop past a new T-6 re-arms it
  (see :meth:`kidnix_shell.session.Session.add_minutes`).

No GTK, no clock, no I/O: everything here is an argument.
"""

from __future__ import annotations

from enum import Enum

from .session import Phase
from .state import State


class RitualAction(Enum):
    """What the shell should do on this tick."""

    NOTHING = "nothing"
    PRESENT_OFFER = "present_offer"  # S5, once per session
    PUT_AWAY = "put_away"  # S6, T-2, unconditional
    GOODBYE = "goodbye"  # S7, the hard stop


#: Where the child can be when the clock decides to interrupt them. The ritual
#: screens themselves are not in here: an interruption on top of an
#: interruption is how the offer loop happened.
INTERRUPTIBLE = frozenset({State.HOME, State.IN_ACTIVITY, State.JOURNAL})

#: Put away also reaches the child who is still looking at the offer, because
#: not answering it is a legitimate answer -- and the child still sitting on
#: S1b, because the hard stop is the hard stop wherever they are.
PUT_AWAY_FROM = INTERRUPTIBLE | {State.ENDING_OFFER, State.NEXT_CHOICE}


# --- exit friction: there is none (spec 7b, SYNTHESIS D6) ----------------
#
# Kuo, Zhao & Scott (IDC 2026) name the harm: exit friction stabilises
# engagement while the educational meaning drains out of it, and the fix they
# argue for is "an easy way out". kidnix's rule is therefore absolute -- **no
# surface anywhere delays Back or "All done"** -- with exactly one exception,
# and the exception exists to protect the child from their own hand rather
# than to keep them on the machine.
#
# Stating it as data rather than as an `if` inside `app.on_back` is what makes
# it testable: `tests/test_ritual.py` asserts that this table has one row in
# it, and that "All done" has none at all. Adding a second row should mean
# arguing with that test, in public, in a diff.

#: The one delay in the shell. Spec 7a: Back is inert for three seconds on the
#: Put-away screen so a child drumming on the band cannot undo the ritual --
#: and then it works, so an accidental "All done" is recoverable.
PUT_AWAY_BACK_LOCK_SECONDS = 3.0

#: State -> seconds Back is ignored for on arrival. One row, forever.
BACK_DELAY_SECONDS: dict[State, float] = {State.PUT_AWAY: PUT_AWAY_BACK_LOCK_SECONDS}


def back_delay_seconds(state: State) -> float:
    """How long Back is inert for on arriving at ``state``. Almost always 0."""
    return BACK_DELAY_SECONDS.get(state, 0.0)


def all_done_delay_seconds(state: State) -> float:
    """How long "All done" is inert for in ``state``. Always 0, everywhere.

    A child who has had enough says so and it happens: no confirmation, no
    hold, no countdown, no "are you sure?". There is no state in which the
    answer is different, which is why this function takes an argument it does
    not use -- so that adding one has to be a deliberate edit here.
    """
    return 0.0


def next_action(phase: Phase, state: State, *, offer_answered: bool) -> RitualAction:
    """The ritual's whole policy, in one pure function.

    ``offer_answered`` is :attr:`kidnix_shell.session.Session.offer_answered`.
    """
    if state is State.GROWNUP:
        # Never yank the sheet out from under a parent mid-task; the tick after
        # they close it picks the ritual up again.
        return RitualAction.NOTHING
    if phase is Phase.ENDING_OFFER:
        if offer_answered or state not in INTERRUPTIBLE:
            return RitualAction.NOTHING
        return RitualAction.PRESENT_OFFER
    if phase is Phase.PUT_AWAY and state in PUT_AWAY_FROM:
        return RitualAction.PUT_AWAY
    if phase is Phase.ENDED and state is State.PUT_AWAY:
        return RitualAction.GOODBYE
    return RitualAction.NOTHING
