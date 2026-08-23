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
* Since v0.1.5 the offer has **two shapes**: a screen in the content window
  when the child is on a shell surface, and two buttons in the band when they
  are inside an activity. The second one does not change the state, so
  ``offer_shown`` is what stops it repeating (see :func:`next_action`), and a
  band offer nobody answers within
  :data:`kidnix_shell.app.BAND_OFFER_SECONDS` counts as answered -- ignoring a
  question is a legitimate answer and the alternative is asking it again.
* Only a grown-up grant that pushes the hard stop past a new T-6 re-arms it
  (see :meth:`kidnix_shell.session.Session.add_minutes`).

Spec S6, as re-ruled in 7c (v0.1.6) -- **put away never destroys work**:

* At T-2 the shell **asks** the activity to finish and, if the child is inside
  one, does not cover it. The content window stays where it is; the band
  speaks. See :func:`put_away_line` for what it says.
* ``put_away_asked`` is the latch that stops the tick asking again -- the same
  shape as ``offer_shown``, and for the same reason, except that here a repeat
  would be another SIGTERM every half second.
* If the activity is still there when the grace runs out the shell asks
  **once** more (that is the app's timer, not this module's: it is measured
  from the ask, not from the clock).
* :attr:`RitualAction.HARD_STOP` is the only SIGKILL, at T-0, and it is a
  logged loss. The words change with it: see :data:`LOST_LINE`.

No GTK, no clock, no I/O: everything here is an argument.
"""

from __future__ import annotations

from enum import Enum

from .activities import QUIT_CONFIRM
from .session import Phase
from .state import State


class OfferAnswer(Enum):
    """The three answers to S5, and they are no longer the same answer.

    Until 2026-08-23 "Finish this one" and "One last little thing" did exactly
    the same thing to the machine -- both latched the offer and neither moved
    the clock -- so a child who chose "finish this one" at T-4 and was still
    drawing at put-away had her program asked to quit anyway. Two reviewers
    called that a fake choice (forum #20, #29): "01 #38 forbids nudges" and
    "a five-year-old who picks one and is stopped at the same second as if they
    hadn't is being taught the choice was theatre."

    So each answer now does something different, and each sentence describes
    what it does:

    * :attr:`FINISH_THIS` **defers put-away to one beat before the hard stop**
      (:meth:`kidnix_shell.session.Session.answer_offer`). The child keeps the
      activity until T-1 unless they finish sooner.
    * :attr:`ONE_MORE` returns the child **to Home**, where opening one more
      activity is simply Home continuing to work, and put-away stays where it
      was -- which is what makes room for the "one last little thing" to fit.
    * :attr:`ASK` dismisses, and hands nothing to the parent in the child's
      hearing: the shell does not tell a five-year-old to go and fetch an
      adult, it says what is true about who can add time.
    """

    FINISH_THIS = "finish_this"
    ONE_MORE = "one_more"
    ASK = "ask"

    @property
    def defers_put_away(self) -> bool:
        return self is OfferAnswer.FINISH_THIS

    @property
    def returns_home(self) -> bool:
        return self is OfferAnswer.ONE_MORE

    @property
    def speech(self) -> str:
        return OFFER_SPEECH[self]


#: What each answer says out loud. Every one of them is *true of the machine*
#: after the answer, which is the whole point of the ruling.
OFFER_SPEECH: dict[OfferAnswer, str] = {
    OfferAnswer.FINISH_THIS: "Finish this one. When the sun is down, we'll keep it.",
    OfferAnswer.ONE_MORE: "One last little thing, then we'll keep it.",
    OfferAnswer.ASK: "A grown-up can add time.",
}

#: The question itself, asked once, on the screen and in the band.
OFFER_QUESTION = "The sun is going down. Finish this one, or one last little thing?"


class RitualAction(Enum):
    """What the shell should do on this tick."""

    NOTHING = "nothing"
    PRESENT_OFFER = "present_offer"  # S5, once per session
    PUT_AWAY = "put_away"  # S6, T-2, unconditional
    HARD_STOP = "hard_stop"  # S6's SIGKILL: T-0 with the activity still there
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


def next_action(
    phase: Phase,
    state: State,
    *,
    offer_answered: bool,
    offer_shown: bool = False,
    put_away_asked: bool = False,
) -> RitualAction:
    """The ritual's whole policy, in one pure function.

    ``offer_answered`` is :attr:`kidnix_shell.session.Session.offer_answered`.

    ``offer_shown`` is v0.1.5's addition and it exists because the offer no
    longer always changes the state. When the child is **in an activity** the
    offer appears *in the band* and they stay in :attr:`State.IN_ACTIVITY` --
    which is in :data:`INTERRUPTIBLE`, so without this flag the shell would
    re-present it on every 500 ms tick, which is precisely the bug the offer
    latch was written to kill (`docs/spikes/e2e-scenario.md` section 3.2). On
    every other surface the offer is a screen in the content window and the
    state change is still what stops the repeat; passing ``True`` there as well
    is harmless and says the same thing.

    ``put_away_asked`` is v0.1.6's equivalent for S6. The shell sets it when it
    has asked a running activity to finish and is waiting for it to go; the
    state does not change while it waits (the child is still looking at their
    own program, which is the entire point of spec 7c), so this is what stops
    the tick asking -- and re-signalling -- twice a second.
    """
    if state is State.GROWNUP:
        # Never yank the sheet out from under a parent mid-task; the tick after
        # they close it picks the ritual up again.
        return RitualAction.NOTHING
    if phase is Phase.ENDING_OFFER:
        if offer_answered or offer_shown or state not in INTERRUPTIBLE:
            return RitualAction.NOTHING
        return RitualAction.PRESENT_OFFER
    if phase is Phase.PUT_AWAY and state in PUT_AWAY_FROM:
        # v0.1.6: inside an activity, PUT_AWAY is a *question* and the shell
        # then waits in IN_ACTIVITY for the answer. IN_ACTIVITY is in
        # PUT_AWAY_FROM, so without this latch the shell would ask again on
        # every 500 ms tick -- the offer-loop bug, in a new place, and this
        # time each repeat is another SIGTERM.
        if put_away_asked:
            return RitualAction.NOTHING
        return RitualAction.PUT_AWAY
    if phase is Phase.ENDED:
        if state is State.PUT_AWAY:
            return RitualAction.GOODBYE
        if state is State.IN_ACTIVITY:
            # The clock ran out with the activity still on screen: it either
            # never answered the signal or the child never answered *it*. This
            # is the only SIGKILL in the ritual and it is a loss, logged as
            # one (:meth:`kidnix_shell.launcher.Launcher.hard_stop`).
            return RitualAction.HARD_STOP
    return RitualAction.NOTHING


# --- what Put away says, and why it is not always the same sentence ------


#: The line the whole ritual is named after. True whenever the activity has
#: gone quietly, or has been given the chance to save and taken it.
KEEP_LINE = "Let's keep that."

#: The ``confirm`` version. Tux Paint is now showing its own tick and cross and
#: nothing on that screen tells a pre-reader that the question is theirs, so
#: the band says so. Two sentences rather than spec 7c's dash: an em dash is a
#: comma to espeak and the pause is what makes "press the tick" an instruction.
CONFIRM_LINE = "Let's keep that. Press the tick."

#: And the honest one. If the hard stop had to SIGKILL, whatever was on that
#: canvas is gone, and "Let's keep that" would be the worst sentence in the
#: shell (§19.3's option 3, which is exactly why the ruling rejected it). The
#: shell says something true instead and does not pretend the loss away.
LOST_LINE = "Time to stop now."


def put_away_line(quit_mode: str, *, lost: bool = False) -> str:
    """What Put away says out loud, given who it is talking about.

    Pure, and separate from the screen and the band, because "the words must be
    true" is a rule about the *policy*, not about a widget: both surfaces say
    the same sentence and one test can hold both of them to it.
    """
    if lost:
        return LOST_LINE
    if quit_mode == QUIT_CONFIRM:
        return CONFIRM_LINE
    return KEEP_LINE
