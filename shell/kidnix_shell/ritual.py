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
#: not answering it is a legitimate answer.
PUT_AWAY_FROM = INTERRUPTIBLE | {State.ENDING_OFFER}


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
