"""The shell state machine (spec section 2 and 7b).

``CHOOSING -> NEXT_CHOICE -> HOME <-> IN_ACTIVITY``, ``HOME <-> JOURNAL``,
``{HOME, IN_ACTIVITY, JOURNAL} -> ENDING_OFFER -> PUT_AWAY -> GOODBYE ->
SLEEPING -> CHOOSING``, plus ``GROWNUP`` as a modal sheet reachable from
anywhere.

Two transitions are *dynamic*: leaving GROWNUP and dismissing the ending offer
both return to wherever the child was. Those are remembered on the machine
rather than encoded in the table, and :func:`successors` resolves them for the
"no dead ends" test.

This module is pure -- no GTK -- so the whole navigation graph is unit-testable.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from enum import Enum

log = logging.getLogger(__name__)


class State(Enum):
    CHOOSING = "choosing"  # S1 Who's here?
    NEXT_CHOICE = "next_choice"  # S1b What's next after? (spec 7b)
    HOME = "home"  # S2
    IN_ACTIVITY = "in_activity"  # S3
    JOURNAL = "journal"  # S4 My Things
    ENDING_OFFER = "ending_offer"  # S5
    PUT_AWAY = "put_away"  # S6
    GOODBYE = "goodbye"  # S7
    SHOWING = "showing"  # S7's "Show a grown-up" -- read-only Journal
    SLEEPING = "sleeping"  # S8
    GROWNUP = "grownup"  # S9


class Event(Enum):
    CHOOSE_PROFILE = "choose_profile"
    #: S1b: the child picked what happens after (spec 7b, Coco's Videos).
    CHOOSE_NEXT_AFTER = "choose_next_after"
    #: The profile asked not to be asked (``skip_next_choice``), so the shell
    #: goes straight to Home. A separate event rather than a conditional edge:
    #: the graph has to say out loud that the screen can be skipped.
    SKIP_NEXT_CHOICE = "skip_next_choice"
    LAUNCH_ACTIVITY = "launch_activity"
    ACTIVITY_EXITED = "activity_exited"
    OPEN_JOURNAL = "open_journal"
    BACK = "back"
    ENDING_OFFER_DUE = "ending_offer_due"
    DISMISS_OFFER = "dismiss_offer"  # "Finish this one" / "One last little thing"
    PUT_AWAY_DUE = "put_away_due"
    IM_FINISHED = "im_finished"  # child- or grown-up-initiated early end
    GOODBYE_DUE = "goodbye_due"
    SHOW_A_GROWNUP = "show_a_grownup"
    SHOWING_DONE = "showing_done"
    GOODNIGHT = "goodnight"
    WAKE = "wake"  # session allowed again
    OPEN_GROWNUP = "open_grownup"
    CLOSE_GROWNUP = "close_grownup"
    START_SESSION = "start_session"  # from the grown-up sheet


class InvalidTransition(Exception):
    def __init__(self, state: State, event: Event) -> None:
        super().__init__(f"{event.value} is not valid in state {state.value}")
        self.state = state
        self.event = event


#: ``None`` marks a dynamic target resolved from the machine's memory.
TRANSITIONS: dict[State, dict[Event, State | None]] = {
    State.CHOOSING: {
        Event.CHOOSE_PROFILE: State.NEXT_CHOICE,
        Event.SKIP_NEXT_CHOICE: State.HOME,
        Event.OPEN_GROWNUP: State.GROWNUP,
        Event.GOODNIGHT: State.SLEEPING,
    },
    # S1b. The clock is already running by the time the child is here (the
    # session starts when they say who they are), so the hard stop still
    # reaches them -- but the *offer* deliberately does not: an ending offer
    # on top of the opening question would be absurd, and `ritual.INTERRUPTIBLE`
    # leaves this state out for that reason.
    State.NEXT_CHOICE: {
        Event.CHOOSE_NEXT_AFTER: State.HOME,
        # Spec 7b: no exit friction. Back here is the way out of a screen the
        # child did not want, and it goes where they came from.
        Event.BACK: State.CHOOSING,
        Event.PUT_AWAY_DUE: State.PUT_AWAY,
        Event.IM_FINISHED: State.PUT_AWAY,
        Event.OPEN_GROWNUP: State.GROWNUP,
        Event.GOODNIGHT: State.SLEEPING,
    },
    State.HOME: {
        Event.LAUNCH_ACTIVITY: State.IN_ACTIVITY,
        Event.OPEN_JOURNAL: State.JOURNAL,
        Event.BACK: State.HOME,  # "You're home" -- never a dead end, never a jolt
        Event.ENDING_OFFER_DUE: State.ENDING_OFFER,
        Event.PUT_AWAY_DUE: State.PUT_AWAY,
        Event.IM_FINISHED: State.PUT_AWAY,
        Event.OPEN_GROWNUP: State.GROWNUP,
    },
    State.IN_ACTIVITY: {
        Event.ACTIVITY_EXITED: State.HOME,
        Event.BACK: State.HOME,
        Event.ENDING_OFFER_DUE: State.ENDING_OFFER,
        Event.PUT_AWAY_DUE: State.PUT_AWAY,
        Event.IM_FINISHED: State.PUT_AWAY,
        Event.OPEN_GROWNUP: State.GROWNUP,
    },
    State.JOURNAL: {
        Event.BACK: State.HOME,
        Event.LAUNCH_ACTIVITY: State.IN_ACTIVITY,  # resume from a card
        Event.OPEN_JOURNAL: State.JOURNAL,  # idempotent under burst-clicking
        Event.ENDING_OFFER_DUE: State.ENDING_OFFER,
        Event.PUT_AWAY_DUE: State.PUT_AWAY,
        Event.IM_FINISHED: State.PUT_AWAY,
        Event.OPEN_GROWNUP: State.GROWNUP,
    },
    State.ENDING_OFFER: {
        Event.DISMISS_OFFER: None,  # back to where the child was
        Event.PUT_AWAY_DUE: State.PUT_AWAY,
        Event.IM_FINISHED: State.PUT_AWAY,
        Event.OPEN_GROWNUP: State.GROWNUP,
    },
    State.PUT_AWAY: {
        Event.GOODBYE_DUE: State.GOODBYE,
        # Spec 7a: the escape hatch for an accidental "All done" tap. The band
        # ignores Back for the first three seconds (see app.PUT_AWAY_BACK_LOCK
        # _SECONDS); after that it takes the child home. If the *clock* put
        # them here, the next tick simply brings the ritual back.
        Event.BACK: State.HOME,
        Event.OPEN_GROWNUP: State.GROWNUP,
    },
    State.GOODBYE: {
        Event.SHOW_A_GROWNUP: State.SHOWING,
        Event.GOODNIGHT: State.SLEEPING,
        Event.OPEN_GROWNUP: State.GROWNUP,
    },
    State.SHOWING: {
        Event.SHOWING_DONE: State.GOODBYE,
        Event.BACK: State.GOODBYE,
        Event.GOODNIGHT: State.SLEEPING,
        Event.OPEN_GROWNUP: State.GROWNUP,
    },
    State.SLEEPING: {
        Event.WAKE: State.CHOOSING,
        Event.OPEN_GROWNUP: State.GROWNUP,
    },
    State.GROWNUP: {
        Event.CLOSE_GROWNUP: None,  # back to where the child was
        Event.START_SESSION: State.HOME,
        Event.IM_FINISHED: State.PUT_AWAY,  # "End session now"
        Event.GOODNIGHT: State.SLEEPING,
    },
}

#: States the child can be in when GROWNUP or ENDING_OFFER is pushed, i.e. the
#: possible dynamic return targets. Used by :func:`successors`.
RETURNABLE = frozenset(
    {
        State.CHOOSING,
        State.NEXT_CHOICE,
        State.HOME,
        State.IN_ACTIVITY,
        State.JOURNAL,
        State.ENDING_OFFER,
        State.PUT_AWAY,
        State.GOODBYE,
        State.SHOWING,
        State.SLEEPING,
    }
)


def successors(state: State) -> set[State]:
    """Every state reachable from ``state`` in one event.

    Dynamic transitions expand to every plausible return target so that graph
    properties (reachability, no dead ends) can be checked statically.
    """
    reachable: set[State] = set()
    for target in TRANSITIONS[state].values():
        if target is None:
            reachable |= set(RETURNABLE)
        else:
            reachable.add(target)
    return reachable


class StateMachine:
    """Holds the current state and the two return memories."""

    def __init__(
        self,
        initial: State = State.CHOOSING,
        on_change: Callable[[State, State, Event], None] | None = None,
    ) -> None:
        self.state = initial
        self.on_change = on_change
        self.history: list[tuple[State, Event, State]] = []
        self._grownup_return: State = initial
        self._offer_return: State = State.HOME

    def can(self, event: Event) -> bool:
        return event in TRANSITIONS[self.state]

    def fire(self, event: Event) -> State:
        """Apply ``event``; raise :class:`InvalidTransition` if it does not apply."""
        table = TRANSITIONS[self.state]
        if event not in table:
            raise InvalidTransition(self.state, event)

        previous = self.state
        target = table[event]

        if target is None:
            target = self._grownup_return if previous is State.GROWNUP else self._offer_return

        # Remember where to come back to *before* moving.
        if target is State.GROWNUP:
            self._grownup_return = previous
        if target is State.ENDING_OFFER and previous is not State.ENDING_OFFER:
            self._offer_return = previous

        self.state = target
        self.history.append((previous, event, target))
        log.debug("state %s --%s--> %s", previous.value, event.value, target.value)
        if self.on_change is not None and previous is not target:
            self.on_change(previous, target, event)
        return target

    def try_fire(self, event: Event) -> bool:
        """Fire if valid. Child-facing controls never raise at a five-year-old."""
        if not self.can(event):
            log.debug("ignoring %s in state %s", event.value, self.state.value)
            return False
        self.fire(event)
        return True

    @property
    def grownup_return(self) -> State:
        return self._grownup_return

    @property
    def offer_return(self) -> State:
        return self._offer_return
