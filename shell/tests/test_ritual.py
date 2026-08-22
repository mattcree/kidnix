"""The ending ritual as a state machine (spec S5-S7).

The bug this file exists for: ``app._advance_ritual`` re-presented the ending
offer on every 500 ms tick for the whole T-6 window, so a child who pressed
"Finish this one" was asked again one second later, and again, for four minutes
(`docs/spikes/e2e-scenario.md` section 3.2).

Everything here is headless: :mod:`kidnix_shell.ritual` is a pure function and
the latch it reads lives on :class:`~kidnix_shell.session.Session`.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta

import pytest

from kidnix_shell.ritual import RitualAction, next_action
from kidnix_shell.session import DailyUsage, Phase, Session, SessionPolicy
from kidnix_shell.state import Event, State, StateMachine

NOW = datetime(2026, 8, 18, 12, 0, 0)

#: A short session with the shipped ratios: 20 minutes, offer at T-6, put away
#: at T-2. Long enough that the three windows are distinct.
POLICY = SessionPolicy.from_minutes(length=20, ending_offer_at=6, put_away_at=2)


@pytest.fixture
def live() -> Session:
    session = Session(policy=POLICY, usage=DailyUsage(day=date(2026, 8, 18)))
    assert session.start(NOW)
    return session


def state_of(shell: FakeShell) -> State:
    """Read the state through a call, so a type checker cannot narrow it away."""
    return shell.machine.state


def at(minutes: float) -> datetime:
    """``minutes`` after the session started."""
    return NOW + timedelta(minutes=minutes)


# --- the pure decision ---------------------------------------------------


@pytest.mark.parametrize("state", [State.HOME, State.IN_ACTIVITY, State.JOURNAL])
def test_the_offer_is_presented_wherever_the_child_is(state: State) -> None:
    action = next_action(Phase.ENDING_OFFER, state, offer_answered=False)
    assert action is RitualAction.PRESENT_OFFER


def test_an_answered_offer_is_never_presented_again() -> None:
    """The whole bug, in one assertion."""
    for state in (State.HOME, State.IN_ACTIVITY, State.JOURNAL):
        assert next_action(Phase.ENDING_OFFER, state, offer_answered=True) is RitualAction.NOTHING


def test_the_offer_does_not_stack_on_top_of_itself() -> None:
    assert (
        next_action(Phase.ENDING_OFFER, State.ENDING_OFFER, offer_answered=False)
        is RitualAction.NOTHING
    )


def test_the_grown_up_sheet_is_never_interrupted() -> None:
    for phase in Phase:
        assert next_action(phase, State.GROWNUP, offer_answered=False) is RitualAction.NOTHING


@pytest.mark.parametrize(
    "state", [State.HOME, State.IN_ACTIVITY, State.JOURNAL, State.ENDING_OFFER]
)
@pytest.mark.parametrize("answered", [True, False])
def test_put_away_happens_regardless_of_the_answer(state: State, answered: bool) -> None:
    """S6 is not a question, so nothing about S5 can change it."""
    assert next_action(Phase.PUT_AWAY, state, offer_answered=answered) is RitualAction.PUT_AWAY


def test_goodbye_only_follows_put_away() -> None:
    assert next_action(Phase.ENDED, State.PUT_AWAY, offer_answered=True) is RitualAction.GOODBYE
    assert next_action(Phase.ENDED, State.HOME, offer_answered=True) is RitualAction.NOTHING


def test_a_running_session_asks_for_nothing() -> None:
    for state in State:
        assert next_action(Phase.RUNNING, state, offer_answered=False) is RitualAction.NOTHING


# --- the latch on the session -------------------------------------------


def test_a_fresh_session_has_not_answered_anything(live: Session) -> None:
    assert live.offer_answered is False


def test_answering_latches(live: Session) -> None:
    live.answer_offer()
    live.answer_offer()  # idempotent
    assert live.offer_answered is True


def test_a_new_session_re_arms_the_offer(live: Session) -> None:
    live.answer_offer()
    live.end(at(20))
    assert live.start(at(30))
    assert live.offer_answered is False


def test_a_grant_that_moves_the_hard_stop_re_arms_the_offer(live: Session) -> None:
    """A grown-up added time: there is a new T-6, so warn about it once more."""
    live.answer_offer()
    assert live.phase(at(15)) is Phase.ENDING_OFFER
    assert live.add_minutes(15, at(15)) > 0
    assert live.phase(at(15)) is Phase.RUNNING
    assert live.offer_answered is False


def test_a_grant_too_small_to_clear_the_window_does_not_re_ask(live: Session) -> None:
    """+1 minute inside the offer window is not a new ending to warn about."""
    live.answer_offer()
    live.add_minutes(1, at(15))
    assert live.phase(at(15)) is Phase.ENDING_OFFER
    assert live.offer_answered is True


def test_a_refused_grant_changes_nothing(live: Session) -> None:
    live.usage.seconds = live.policy.daily_budget  # no headroom at all
    live.answer_offer()
    assert live.add_minutes(30, at(15)) == 0
    assert live.offer_answered is True


# --- the two together, tick by tick --------------------------------------


class FakeShell:
    """The parts of ``app.ShellWindow`` the ritual actually drives.

    Deliberately tiny: it is the tick loop and the two host methods, with no
    GTK, no launcher and no speech. If this can be walked through a whole
    session, the ritual is testable without a display.
    """

    def __init__(self, session: Session, state: State = State.HOME) -> None:
        self.session = session
        self.machine = StateMachine(state)
        self.offers_presented = 0

    def tick(self, now: datetime) -> RitualAction:
        action = next_action(
            self.session.phase(now),
            self.machine.state,
            offer_answered=self.session.offer_answered,
        )
        if action is RitualAction.PRESENT_OFFER:
            self.offers_presented += 1
            self.machine.try_fire(Event.ENDING_OFFER_DUE)
        elif action is RitualAction.PUT_AWAY:
            self.machine.try_fire(Event.PUT_AWAY_DUE)
        elif action is RitualAction.GOODBYE:
            self.session.end(now)
            self.machine.try_fire(Event.GOODBYE_DUE)
        return action

    def dismiss_offer(self) -> None:
        """What ``ShellWindow.dismiss_offer`` does, minus the window."""
        self.session.answer_offer()
        self.machine.try_fire(Event.DISMISS_OFFER)

    def run(self, start: float, stop: float, step: float = 0.25) -> None:
        minute = start
        while minute < stop:
            self.tick(at(minute))
            minute += step


def test_the_offer_appears_once_and_the_child_is_left_alone(live: Session) -> None:
    """The e2e repro, at 4 Hz: answer at T-6, and nothing asks again."""
    shell = FakeShell(live)
    shell.run(0, 14.1)
    assert shell.offers_presented == 1
    assert state_of(shell) is State.ENDING_OFFER

    shell.dismiss_offer()
    assert state_of(shell) is State.HOME

    shell.run(14.2, 17.9)  # the rest of the offer window
    assert shell.offers_presented == 1
    assert state_of(shell) is State.HOME


def test_one_last_little_thing_leaves_the_child_on_home(live: Session) -> None:
    """S5: they may still open one more activity, so Home has to still work."""
    shell = FakeShell(live)
    shell.run(0, 14.1)
    shell.dismiss_offer()
    assert state_of(shell) is State.HOME
    assert shell.machine.can(Event.LAUNCH_ACTIVITY)
    assert shell.machine.fire(Event.LAUNCH_ACTIVITY) is State.IN_ACTIVITY

    shell.run(14.5, 17.9)
    assert shell.offers_presented == 1
    assert state_of(shell) is State.IN_ACTIVITY  # not yanked out of it


def test_dismissing_from_an_activity_goes_back_to_the_activity(live: Session) -> None:
    shell = FakeShell(live, State.IN_ACTIVITY)
    shell.run(0, 14.1)
    assert state_of(shell) is State.ENDING_OFFER
    shell.dismiss_offer()
    assert state_of(shell) is State.IN_ACTIVITY


def test_put_away_arrives_at_t_minus_two_whatever_was_chosen(live: Session) -> None:
    shell = FakeShell(live)
    shell.run(0, 14.1)
    shell.dismiss_offer()
    shell.run(14.2, 18.3)
    assert state_of(shell) is State.PUT_AWAY
    assert shell.offers_presented == 1


def test_ignoring_the_offer_still_puts_away(live: Session) -> None:
    """Not answering is an answer. S6 reaches the offer screen too."""
    shell = FakeShell(live)
    shell.run(0, 18.1)
    assert state_of(shell) is State.PUT_AWAY


def test_the_whole_session_ends_in_goodbye(live: Session) -> None:
    shell = FakeShell(live)
    shell.run(0, 14.1)
    shell.dismiss_offer()
    shell.run(14.2, 20.5)
    assert state_of(shell) is State.GOODBYE
    assert shell.offers_presented == 1


def test_a_grant_gives_the_child_one_more_warning_and_only_one(live: Session) -> None:
    """Grant re-arms: a second ending deserves a second offer, not a third."""
    shell = FakeShell(live)
    shell.run(0, 14.1)
    shell.dismiss_offer()
    assert shell.offers_presented == 1

    live.add_minutes(15, at(15))  # a grown-up at the gate
    shell.run(15, 29.1)
    assert shell.offers_presented == 2
    assert state_of(shell) is State.ENDING_OFFER

    shell.dismiss_offer()
    shell.run(29.2, 32.9)
    assert shell.offers_presented == 2
