"""The navigation graph (spec section 2): every transition, and no dead ends."""

from __future__ import annotations

import pytest

from kidnix_shell.state import (
    TRANSITIONS,
    Event,
    InvalidTransition,
    State,
    StateMachine,
    successors,
)


def test_the_shell_starts_by_asking_who_is_here() -> None:
    assert StateMachine().state is State.CHOOSING


def test_the_happy_path_through_a_session() -> None:
    machine = StateMachine()
    for event, expected in (
        (Event.CHOOSE_PROFILE, State.HOME),
        (Event.LAUNCH_ACTIVITY, State.IN_ACTIVITY),
        (Event.ACTIVITY_EXITED, State.HOME),
        (Event.OPEN_JOURNAL, State.JOURNAL),
        (Event.BACK, State.HOME),
        (Event.ENDING_OFFER_DUE, State.ENDING_OFFER),
        (Event.DISMISS_OFFER, State.HOME),
        (Event.PUT_AWAY_DUE, State.PUT_AWAY),
        (Event.GOODBYE_DUE, State.GOODBYE),
        (Event.SHOW_A_GROWNUP, State.SHOWING),
        (Event.SHOWING_DONE, State.GOODBYE),
        (Event.GOODNIGHT, State.SLEEPING),
        (Event.WAKE, State.CHOOSING),
    ):
        assert machine.fire(event) is expected


def test_the_ending_offer_returns_the_child_where_they_were() -> None:
    machine = StateMachine(State.HOME)
    machine.fire(Event.LAUNCH_ACTIVITY)
    machine.fire(Event.ENDING_OFFER_DUE)
    assert machine.offer_return is State.IN_ACTIVITY
    assert machine.fire(Event.DISMISS_OFFER) is State.IN_ACTIVITY


def test_the_ending_offer_can_arrive_from_the_journal() -> None:
    machine = StateMachine(State.HOME)
    machine.fire(Event.OPEN_JOURNAL)
    machine.fire(Event.ENDING_OFFER_DUE)
    assert machine.fire(Event.DISMISS_OFFER) is State.JOURNAL


@pytest.mark.parametrize(
    "state",
    [
        State.CHOOSING,
        State.HOME,
        State.IN_ACTIVITY,
        State.JOURNAL,
        State.ENDING_OFFER,
        State.PUT_AWAY,
        State.GOODBYE,
        State.SHOWING,
        State.SLEEPING,
    ],
)
def test_the_grown_up_gate_is_reachable_from_everywhere_and_returns(state: State) -> None:
    machine = StateMachine(state)
    assert machine.fire(Event.OPEN_GROWNUP) is State.GROWNUP
    assert machine.grownup_return is state
    assert machine.fire(Event.CLOSE_GROWNUP) is state


def test_the_gate_cannot_open_on_top_of_itself() -> None:
    machine = StateMachine(State.HOME)
    machine.fire(Event.OPEN_GROWNUP)
    assert not machine.can(Event.OPEN_GROWNUP)


def test_back_on_home_is_a_no_op_not_a_dead_end() -> None:
    machine = StateMachine(State.HOME)
    assert machine.fire(Event.BACK) is State.HOME


def test_the_journal_button_is_idempotent_under_burst_clicking() -> None:
    machine = StateMachine(State.HOME)
    machine.fire(Event.OPEN_JOURNAL)
    for _ in range(8):
        machine.try_fire(Event.OPEN_JOURNAL)
    assert machine.state is State.JOURNAL


def test_an_invalid_event_raises_but_try_fire_does_not() -> None:
    machine = StateMachine(State.SLEEPING)
    with pytest.raises(InvalidTransition):
        machine.fire(Event.LAUNCH_ACTIVITY)
    assert machine.try_fire(Event.LAUNCH_ACTIVITY) is False
    assert machine.state is State.SLEEPING


def test_ending_early_runs_the_same_ritual() -> None:
    """SYNTHESIS D5: a child- or grown-up-initiated end is not a different path."""
    for start in (State.HOME, State.IN_ACTIVITY, State.JOURNAL, State.ENDING_OFFER):
        machine = StateMachine(start)
        assert machine.fire(Event.IM_FINISHED) is State.PUT_AWAY
        assert machine.fire(Event.GOODBYE_DUE) is State.GOODBYE


def test_the_gate_can_end_a_session_and_start_one() -> None:
    machine = StateMachine(State.IN_ACTIVITY)
    machine.fire(Event.OPEN_GROWNUP)
    assert machine.fire(Event.IM_FINISHED) is State.PUT_AWAY

    machine = StateMachine(State.SLEEPING)
    machine.fire(Event.OPEN_GROWNUP)
    assert machine.fire(Event.START_SESSION) is State.HOME


def test_on_change_fires_only_on_a_real_move() -> None:
    seen: list[tuple[State, State, Event]] = []
    machine = StateMachine(State.HOME, on_change=lambda a, b, e: seen.append((a, b, e)))
    machine.fire(Event.BACK)  # HOME -> HOME
    assert seen == []
    machine.fire(Event.OPEN_JOURNAL)
    assert seen == [(State.HOME, State.JOURNAL, Event.OPEN_JOURNAL)]


def test_history_records_every_transition() -> None:
    machine = StateMachine()
    machine.fire(Event.CHOOSE_PROFILE)
    machine.fire(Event.OPEN_JOURNAL)
    assert [event for _, event, _ in machine.history] == [
        Event.CHOOSE_PROFILE,
        Event.OPEN_JOURNAL,
    ]


def test_every_state_has_a_way_out() -> None:
    for state in State:
        assert TRANSITIONS[state], f"{state} is a dead end"


def test_every_state_can_reach_home() -> None:
    """Spec section 2: no state without a visible way back to HOME."""
    for start in State:
        seen = {start}
        frontier = [start]
        while frontier:
            current = frontier.pop()
            if current is State.HOME:
                break
            for nxt in successors(current):
                if nxt not in seen:
                    seen.add(nxt)
                    frontier.append(nxt)
        assert State.HOME in seen, f"{start} cannot reach HOME"


def test_every_state_is_reachable_from_the_start() -> None:
    seen = {State.CHOOSING}
    frontier = [State.CHOOSING]
    while frontier:
        for nxt in successors(frontier.pop()):
            if nxt not in seen:
                seen.add(nxt)
                frontier.append(nxt)
    assert seen == set(State)


def test_sleeping_is_the_only_state_without_a_child_route_to_home() -> None:
    """The one deliberate exception (spec section 2)."""
    child_events = {
        Event.BACK,
        Event.ACTIVITY_EXITED,
        Event.DISMISS_OFFER,
        Event.CHOOSE_PROFILE,
        Event.GOODNIGHT,
        Event.SHOW_A_GROWNUP,
        Event.SHOWING_DONE,
        Event.OPEN_JOURNAL,
        Event.LAUNCH_ACTIVITY,
    }
    assert not (set(TRANSITIONS[State.SLEEPING]) & child_events)


def test_back_on_put_away_recovers_an_accidental_all_done() -> None:
    """Spec 7a: one tap, no confirmation -- so Back has to be the undo.

    The band ignores Back for the first three seconds
    (``app.PUT_AWAY_BACK_LOCK_SECONDS``); after that this is the way home. If
    the *clock* put the child here, the next tick simply brings the ritual
    back, which is why this is safe to allow unconditionally in the graph.
    """
    machine = StateMachine(State.HOME)
    assert machine.fire(Event.IM_FINISHED) is State.PUT_AWAY
    assert machine.fire(Event.BACK) is State.HOME


def test_put_away_still_leads_to_goodbye() -> None:
    machine = StateMachine(State.PUT_AWAY)
    assert machine.fire(Event.GOODBYE_DUE) is State.GOODBYE
