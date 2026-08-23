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

from kidnix_shell.activities import QUIT_CONFIRM, QUIT_SIGNAL
from kidnix_shell.ritual import (
    BACK_DELAY_SECONDS,
    KEEP_LINE,
    LOST_LINE,
    OFFER_SPEECH,
    PUT_AWAY_BACK_LOCK_SECONDS,
    OfferAnswer,
    RitualAction,
    all_done_delay_seconds,
    back_delay_seconds,
    next_action,
    put_away_line,
)
from kidnix_shell.session import DailyUsage, Phase, Session, SessionPolicy
from kidnix_shell.state import Event, State, StateMachine

NOW = datetime(2026, 8, 18, 12, 0, 0)

#: A short session with the shipped ratios: 20 minutes, so the proportional
#: windows land at T-4 (20% of 20, capped at four) and T-2 (10% of 20, capped
#: at two). Long enough that the three windows are distinct.
POLICY = SessionPolicy.from_minutes(length=20)
#: Where the two beats fall in that session, in minutes from the start.
OFFER_MINUTE = 16
PUT_AWAY_MINUTE = 18


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
    assert live.phase(at(17)) is Phase.ENDING_OFFER
    assert live.add_minutes(15, at(17)) > 0
    assert live.phase(at(17)) is Phase.RUNNING
    assert live.offer_answered is False


def test_a_grant_too_small_to_clear_the_window_does_not_re_ask(live: Session) -> None:
    """+1 minute inside the offer window is not a new ending to warn about."""
    live.answer_offer()
    live.add_minutes(1, at(17))
    assert live.phase(at(17)) is Phase.ENDING_OFFER
    assert live.offer_answered is True


def test_a_refused_grant_changes_nothing(live: Session) -> None:
    live.usage.seconds = live.policy.daily_budget  # no headroom at all
    live.answer_offer()
    assert live.add_minutes(30, at(17)) == 0
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

    def dismiss_offer(self, answer: OfferAnswer = OfferAnswer.ONE_MORE) -> None:
        """What ``ShellWindow.dismiss_offer`` does, minus the window."""
        self.session.answer_offer(defer_put_away=answer.defers_put_away)
        self.machine.try_fire(Event.DISMISS_OFFER)
        if answer.returns_home and self.machine.state is State.JOURNAL:
            self.machine.try_fire(Event.BACK)

    def run(self, start: float, stop: float, step: float = 0.25) -> None:
        minute = start
        while minute < stop:
            self.tick(at(minute))
            minute += step


def test_the_offer_appears_once_and_the_child_is_left_alone(live: Session) -> None:
    """The e2e repro, at 4 Hz: answer at T-6, and nothing asks again."""
    shell = FakeShell(live)
    shell.run(0, 16.1)
    assert shell.offers_presented == 1
    assert state_of(shell) is State.ENDING_OFFER

    shell.dismiss_offer()
    assert state_of(shell) is State.HOME

    shell.run(16.2, 17.9)  # the rest of the offer window
    assert shell.offers_presented == 1
    assert state_of(shell) is State.HOME


def test_one_last_little_thing_leaves_the_child_on_home(live: Session) -> None:
    """S5: they may still open one more activity, so Home has to still work."""
    shell = FakeShell(live)
    shell.run(0, 16.1)
    shell.dismiss_offer()
    assert state_of(shell) is State.HOME
    assert shell.machine.can(Event.LAUNCH_ACTIVITY)
    assert shell.machine.fire(Event.LAUNCH_ACTIVITY) is State.IN_ACTIVITY

    shell.run(16.5, 17.9)
    assert shell.offers_presented == 1
    assert state_of(shell) is State.IN_ACTIVITY  # not yanked out of it


def test_dismissing_from_an_activity_goes_back_to_the_activity(live: Session) -> None:
    shell = FakeShell(live, State.IN_ACTIVITY)
    shell.run(0, 16.1)
    assert state_of(shell) is State.ENDING_OFFER
    shell.dismiss_offer()
    assert state_of(shell) is State.IN_ACTIVITY


def test_put_away_arrives_at_t_minus_two_whatever_was_chosen(live: Session) -> None:
    shell = FakeShell(live)
    shell.run(0, 16.1)
    shell.dismiss_offer()
    shell.run(16.2, 18.3)
    assert state_of(shell) is State.PUT_AWAY
    assert shell.offers_presented == 1


def test_ignoring_the_offer_still_puts_away(live: Session) -> None:
    """Not answering is an answer. S6 reaches the offer screen too."""
    shell = FakeShell(live)
    shell.run(0, 18.1)
    assert state_of(shell) is State.PUT_AWAY


def test_the_whole_session_ends_in_goodbye(live: Session) -> None:
    shell = FakeShell(live)
    shell.run(0, 16.1)
    shell.dismiss_offer()
    shell.run(16.2, 20.5)
    assert state_of(shell) is State.GOODBYE
    assert shell.offers_presented == 1


def test_a_grant_gives_the_child_one_more_warning_and_only_one(live: Session) -> None:
    """Grant re-arms: a second ending deserves a second offer, not a third."""
    shell = FakeShell(live)
    shell.run(0, 16.1)
    shell.dismiss_offer()
    assert shell.offers_presented == 1

    live.add_minutes(15, at(17))  # a grown-up at the gate
    shell.run(17, 31.1)
    assert shell.offers_presented == 2
    assert state_of(shell) is State.ENDING_OFFER

    shell.dismiss_offer()
    shell.run(31.2, 32.9)
    assert shell.offers_presented == 2


# --- the offer in the band (v0.1.5) --------------------------------------
#
# When the child is inside an activity the offer no longer covers their drawing
# with a fullscreen window (CCI audit 02 #4): it appears as two buttons in the
# band, and they stay in IN_ACTIVITY. That state is in `ritual.INTERRUPTIBLE`,
# so without `offer_shown` the shell would re-present it on every tick -- the
# very bug this file exists for, in a new place.


class BandShell(FakeShell):
    """The v0.1.5 route: the offer goes in the band and the state does not move.

    ``ShellWindow`` sets ``_offer_on_band`` when it puts the two choices in the
    band, clears it when they are answered, and -- if nobody answers within
    ``app.BAND_OFFER_SECONDS`` -- latches the offer as answered rather than
    asking again. All three are modelled here.
    """

    def __init__(self, session: Session) -> None:
        super().__init__(session, State.IN_ACTIVITY)
        self.offer_on_band = False

    def tick(self, now: datetime) -> RitualAction:
        action = next_action(
            self.session.phase(now),
            self.machine.state,
            offer_answered=self.session.offer_answered,
            offer_shown=self.offer_on_band,
        )
        if action is RitualAction.PRESENT_OFFER:
            self.offers_presented += 1
            self.offer_on_band = True
        elif action is RitualAction.PUT_AWAY:
            self.offer_on_band = False
            self.machine.try_fire(Event.PUT_AWAY_DUE)
        elif action is RitualAction.GOODBYE:
            self.session.end(now)
            self.machine.try_fire(Event.GOODBYE_DUE)
        return action

    def answer_in_the_band(self) -> None:
        self.offer_on_band = False
        self.session.answer_offer()
        self.machine.try_fire(Event.DISMISS_OFFER)  # a no-op in IN_ACTIVITY

    def band_offer_expired(self) -> None:
        self.offer_on_band = False
        self.session.answer_offer()


def test_the_band_offer_appears_once_and_never_moves_the_child(live: Session) -> None:
    shell = BandShell(live)
    shell.run(0, 16.1)
    assert shell.offers_presented == 1
    assert shell.offer_on_band is True
    assert state_of(shell) is State.IN_ACTIVITY, "the drawing is never covered"


def test_answering_in_the_band_leaves_the_child_in_the_activity(live: Session) -> None:
    """Both answers mean "carry on until the sun does" -- there is nowhere to
    navigate to, and the DISMISS_OFFER that a screen would fire is a no-op."""
    shell = BandShell(live)
    shell.run(0, 16.1)
    shell.answer_in_the_band()
    assert state_of(shell) is State.IN_ACTIVITY

    shell.run(16.2, 17.9)
    assert shell.offers_presented == 1


def test_an_unanswered_band_offer_is_not_asked_again(live: Session) -> None:
    """The timeout latches it. Ignoring a question is a legitimate answer, and
    the alternative is asking it four hundred times over four minutes."""
    shell = BandShell(live)
    shell.run(0, 16.1)
    shell.band_offer_expired()
    shell.run(16.2, 17.9)
    assert shell.offers_presented == 1
    assert live.offer_answered is True


def test_the_band_offer_does_not_delay_put_away(live: Session) -> None:
    shell = BandShell(live)
    shell.run(0, 18.1)
    assert state_of(shell) is State.PUT_AWAY
    assert shell.offers_presented == 1


def test_offer_shown_is_the_only_thing_the_flag_changes() -> None:
    """It suppresses PRESENT_OFFER and nothing else in the ritual."""
    for phase in Phase:
        for state in State:
            shown = next_action(phase, state, offer_answered=False, offer_shown=True)
            hidden = next_action(phase, state, offer_answered=False, offer_shown=False)
            if hidden is RitualAction.PRESENT_OFFER:
                assert shown is RitualAction.NOTHING
            else:
                assert shown is hidden, (phase, state)


# --- exit friction: there is none (spec 7b, SYNTHESIS D6) ----------------
#
# Kuo, Zhao & Scott (IDC 2026) name the harm and argue for "an easy way out".
# kidnix's answer is that the delay table has exactly one row in it. These
# tests are the mechanism that keeps it that way: adding a second row means
# arguing with them, in a diff, in public.


def test_only_put_away_ever_delays_back() -> None:
    assert set(BACK_DELAY_SECONDS) == {State.PUT_AWAY}


def test_back_is_immediate_in_every_other_state() -> None:
    for state in State:
        if state is State.PUT_AWAY:
            continue
        assert back_delay_seconds(state) == 0.0, f"{state.value} delays Back"


def test_the_one_delay_is_the_accidental_tap_guard_and_nothing_longer() -> None:
    """Spec 7a's three seconds. Long enough to survive a drumming hand, short
    enough that a child who meant it is not being kept."""
    assert back_delay_seconds(State.PUT_AWAY) == PUT_AWAY_BACK_LOCK_SECONDS
    assert PUT_AWAY_BACK_LOCK_SECONDS == 3.0


def test_all_done_is_never_delayed_anywhere() -> None:
    """No confirmation, no hold, no countdown, in any state, ever."""
    for state in State:
        assert all_done_delay_seconds(state) == 0.0, f"{state.value} delays All done"


def test_all_done_reaches_put_away_in_one_event_from_every_child_surface() -> None:
    """ "Friction" is also an extra tap. One press, one transition, no screen
    in between."""
    for start in (State.HOME, State.IN_ACTIVITY, State.JOURNAL, State.NEXT_CHOICE):
        machine = StateMachine(start)
        assert machine.fire(Event.IM_FINISHED) is State.PUT_AWAY


# --- put away never destroys work (spec 7c, v0.1.6) ----------------------
#
# §19.3, as a policy: at T-2 the shell *asks* a running activity to finish and
# then waits inside IN_ACTIVITY, because covering a child's drawing is what
# stopped them answering Tux Paint's tick and is therefore what destroyed it.
# The latch below is what stops the tick asking again -- and every repeat of
# that question would be another SIGTERM, so it is more load-bearing than the
# offer's.


class PutAwayShell(FakeShell):
    """The v0.1.6 route: S6 asks, and the state does not move until it is answered.

    Models the three things ``ShellWindow`` does: set ``put_away_asked`` when it
    has asked, clear it (and navigate) when the activity has actually gone, and
    SIGKILL at the hard stop -- which is the only kill in the ritual.
    """

    def __init__(self, session: Session, *, grace: float = 30.0) -> None:
        super().__init__(session, State.IN_ACTIVITY)
        self.asked = 0
        self.reasks = 0
        self.killed = 0
        self.put_away_asked = False
        self.activity_running = True
        self.grace = grace
        self.asked_at: datetime | None = None
        self.work_lost = False

    def tick(self, now: datetime) -> RitualAction:
        action = next_action(
            self.session.phase(now),
            self.machine.state,
            offer_answered=self.session.offer_answered,
            offer_shown=False,
            put_away_asked=self.put_away_asked,
        )
        if action is RitualAction.PUT_AWAY:
            self.ask(now)
        elif action is RitualAction.HARD_STOP:
            self.hard_stop()
        elif action is RitualAction.GOODBYE:
            self.session.end(now)
            self.machine.try_fire(Event.GOODBYE_DUE)
        # The re-ask is a timer on the ask, not on the clock -- but a tick is
        # where a fake shell notices that the timer would have fired.
        if (
            self.put_away_asked
            and self.activity_running
            and self.reasks == 0
            and self.asked_at is not None
            and (now - self.asked_at).total_seconds() >= self.grace
        ):
            self.reasks += 1
            self.asked += 1
        return action

    def ask(self, now: datetime) -> None:
        self.asked += 1
        self.asked_at = now
        self.put_away_asked = True

    def activity_exits(self) -> None:
        """The child answered the tick (or the program just went)."""
        self.activity_running = False
        self.put_away_asked = False
        self.machine.try_fire(Event.PUT_AWAY_DUE)

    def hard_stop(self) -> None:
        if self.activity_running:
            self.killed += 1
            self.work_lost = True
            self.activity_running = False
        self.put_away_asked = False
        self.machine.try_fire(Event.PUT_AWAY_DUE)


def test_put_away_asks_once_and_then_waits(live: Session) -> None:
    """The whole ruling: no second SIGTERM twice a second, and no screen
    raised over the child's drawing while they answer it."""
    shell = PutAwayShell(live)
    shell.run(0, 18.4)  # T-2 is at minute 18
    assert shell.asked == 1
    assert shell.killed == 0
    assert state_of(shell) is State.IN_ACTIVITY, "S6 covered the activity"


def test_the_grace_buys_one_more_ask_and_only_one(live: Session) -> None:
    shell = PutAwayShell(live, grace=30.0)
    shell.run(0, 19.6)  # a minute and a half past T-2
    assert shell.reasks == 1
    assert shell.asked == 2
    assert shell.killed == 0, "the grace is not a countdown to a kill"


def test_a_short_grace_still_only_re_asks_once(live: Session) -> None:
    shell = PutAwayShell(live, grace=5.0)
    shell.run(0, 19.9)
    assert shell.asked == 2


def test_answering_takes_the_child_to_s6_and_nothing_is_lost(live: Session) -> None:
    shell = PutAwayShell(live)
    shell.run(0, 18.4)
    shell.activity_exits()
    assert state_of(shell) is State.PUT_AWAY
    assert shell.work_lost is False
    shell.run(18.5, 20.5)
    assert state_of(shell) is State.GOODBYE
    assert shell.killed == 0


def test_the_hard_stop_kills_once_and_the_ritual_still_finishes(live: Session) -> None:
    """T-0 with the activity still asking. The hard stop is the hard stop --
    and it is the only SIGKILL left in the ritual."""
    shell = PutAwayShell(live)
    shell.run(0, 19.9)  # still inside the activity, still asking
    assert shell.killed == 0
    assert state_of(shell) is State.IN_ACTIVITY

    assert shell.tick(at(20.0)) is RitualAction.HARD_STOP
    assert shell.killed == 1
    assert shell.work_lost is True
    assert state_of(shell) is State.PUT_AWAY

    shell.run(20.1, 21.0)  # and the ending finishes as it always did
    assert state_of(shell) is State.GOODBYE
    assert shell.killed == 1, "it is killed once, not once per tick"


def test_hard_stop_is_only_reachable_from_inside_an_activity() -> None:
    """Nowhere else can there be a process to kill, and a HARD_STOP anywhere
    else would be a SIGKILL aimed at nothing."""
    for state in State:
        action = next_action(Phase.ENDED, state, offer_answered=True, put_away_asked=True)
        if state is State.IN_ACTIVITY:
            assert action is RitualAction.HARD_STOP
        elif state is State.PUT_AWAY:
            assert action is RitualAction.GOODBYE
        else:
            assert action is RitualAction.NOTHING, state


def test_put_away_asked_suppresses_put_away_and_nothing_else() -> None:
    """The same discipline as ``offer_shown``: one flag, one effect."""
    for phase in Phase:
        for state in State:
            asked = next_action(phase, state, offer_answered=True, put_away_asked=True)
            fresh = next_action(phase, state, offer_answered=True, put_away_asked=False)
            if fresh is RitualAction.PUT_AWAY:
                assert asked in (RitualAction.NOTHING, RitualAction.HARD_STOP), (phase, state)
            elif fresh is RitualAction.HARD_STOP:
                assert asked is RitualAction.HARD_STOP
            else:
                assert asked is fresh, (phase, state)


# --- the words have to be true -------------------------------------------


def test_a_confirming_activity_is_told_to_the_child_as_an_instruction() -> None:
    """Tux Paint's tick is on screen and nothing on it says, to a pre-reader,
    that the question is theirs."""
    assert put_away_line(QUIT_CONFIRM) == "Let's keep that. Press the tick."
    assert "tick" in put_away_line(QUIT_CONFIRM)


def test_an_ordinary_activity_gets_the_ritual_line_it_always_had() -> None:
    assert put_away_line(QUIT_SIGNAL) == KEEP_LINE == "Let's keep that."


def test_nothing_claims_to_have_kept_what_the_hard_stop_destroyed() -> None:
    """§19.3's option 3 -- "accept the loss and change the words" -- is the one
    the ruling refused for the *ordinary* case, and the one it requires here:
    "Let's keep that" over a deleted drawing is the worst sentence in the shell.
    """
    for mode in (QUIT_SIGNAL, QUIT_CONFIRM):
        line = put_away_line(mode, lost=True)
        assert line == LOST_LINE
        assert "keep" not in line.lower()
        assert line.endswith(".")


# --- the offer is consequential (panel ruling, 2026-08-23) ---------------


def test_each_answer_does_something_different_to_the_machine() -> None:
    assert OfferAnswer.FINISH_THIS.defers_put_away is True
    assert OfferAnswer.ONE_MORE.defers_put_away is False
    assert OfferAnswer.ASK.defers_put_away is False
    assert OfferAnswer.ONE_MORE.returns_home is True
    assert OfferAnswer.FINISH_THIS.returns_home is False


def test_the_two_answers_land_put_away_at_different_times(live: Session) -> None:
    """forum #29: "a five-year-old who picks 'one last little thing' and is
    stopped at the same second as if they hadn't is being taught the choice was
    theatre." They are not stopped at the same second any more."""
    one_more = FakeShell(live)
    one_more.run(0, 16.1)
    one_more.dismiss_offer(OfferAnswer.ONE_MORE)
    ordinary = live.put_away_at

    live.end(at(17))
    assert live.start(at(17))
    finish = FakeShell(live)
    finish.run(17, 33.1)
    finish.dismiss_offer(OfferAnswer.FINISH_THIS)
    assert live.put_away_at < ordinary


def test_finish_this_one_keeps_the_activity_until_one_beat_before_the_end(
    live: Session,
) -> None:
    shell = FakeShell(live, State.IN_ACTIVITY)
    shell.run(0, 16.1)
    shell.dismiss_offer(OfferAnswer.FINISH_THIS)
    # T-2 would have been minute 18; it is minute 19 now.
    assert live.phase(at(18.5)) is Phase.ENDING_OFFER
    assert live.phase(at(19.5)) is Phase.PUT_AWAY


def test_one_last_little_thing_still_puts_away_on_time(live: Session) -> None:
    shell = FakeShell(live)
    shell.run(0, 16.1)
    shell.dismiss_offer(OfferAnswer.ONE_MORE)
    assert live.phase(at(18.5)) is Phase.PUT_AWAY


def test_one_last_little_thing_from_my_things_goes_home(live: Session) -> None:
    """Home is where the last little thing is opened; My Things is not."""
    shell = FakeShell(live, State.JOURNAL)
    shell.run(0, 16.1)
    assert state_of(shell) is State.ENDING_OFFER
    shell.dismiss_offer(OfferAnswer.ONE_MORE)
    assert state_of(shell) is State.HOME


def test_every_answer_says_something_that_is_true_of_the_machine() -> None:
    """The rule the ruling rests on: the words describe what happens."""
    assert OFFER_SPEECH[OfferAnswer.FINISH_THIS] == (
        "Finish this one. When the sun is down, we'll keep it."
    )
    assert OFFER_SPEECH[OfferAnswer.ONE_MORE] == "One last little thing, then we'll keep it."
    assert OFFER_SPEECH[OfferAnswer.ASK] == "A grown-up can add time."


def test_asking_for_more_time_does_not_send_the_child_anywhere() -> None:
    """forum: the shell must not hand a five-year-old a negotiation."""
    line = OFFER_SPEECH[OfferAnswer.ASK].lower()
    assert "go and ask" not in line
    assert "find" not in line


def test_no_offer_sentence_promises_a_return() -> None:
    for line in OFFER_SPEECH.values():
        lowered = line.lower()
        assert "tomorrow" not in lowered
        assert "next time" not in lowered
