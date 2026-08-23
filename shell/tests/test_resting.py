"""Two vocabularies, and what a dysregulated child gets (panel ruling, 2026-08-23).

Everything in :mod:`kidnix_shell.resting` is pure, so all of it is here and
none of it needs a display.
"""

from __future__ import annotations

from datetime import datetime, time, timedelta

from kidnix_shell.resting import (
    ALL_DONE_HEADLINE,
    BEDTIME_REFUSAL,
    BUDGET_SPENT_REFUSAL,
    RESTING_LATER_TODAY,
    RESTING_TOMORROW,
    SILENCE_AFTER_TAPS,
    SLEEPING_LINE,
    SPEECH_INTERVAL_SECONDS,
    TapSpeechLimiter,
    back_when_words,
    goodnight_label,
    refusal_line,
    rest_line,
    rest_title,
)
from kidnix_shell.session import DailyUsage, Session, SessionPolicy

from .conftest import NOW

# --- the words -----------------------------------------------------------


def test_the_daytime_vocabulary_has_no_night_in_it() -> None:
    """forum #17: a 4pm session must not end in sleep-onset cues."""
    for line in (RESTING_LATER_TODAY, RESTING_TOMORROW, ALL_DONE_HEADLINE):
        lowered = line.lower()
        assert "sleep" not in lowered
        assert "goodnight" not in lowered
        assert "night" not in lowered


def test_nothing_the_machine_says_when_it_is_shut_asks_the_child_for_anything() -> None:
    """forum #23: no demands to a child whose executive function has gone."""
    for line in (RESTING_LATER_TODAY, RESTING_TOMORROW, SLEEPING_LINE):
        assert "ask a grown-up" not in line.lower()


def test_no_return_promise_anywhere_in_the_daytime_vocabulary() -> None:
    """D6: the system has no interest in whether the child comes back."""
    for line in (RESTING_LATER_TODAY, ALL_DONE_HEADLINE, BUDGET_SPENT_REFUSAL):
        lowered = line.lower()
        assert "see you" not in lowered
        assert "next time" not in lowered
        assert "tomorrow" not in lowered


def test_the_daytime_refusal_points_at_something_to_do() -> None:
    assert BUDGET_SPENT_REFUSAL == ("That's all the computer time for today. Ready to go and play?")
    assert refusal_line(bedtime=False) == BUDGET_SPENT_REFUSAL
    assert refusal_line(bedtime=True) == BEDTIME_REFUSAL


def test_the_titles_and_the_goodnight_button_switch_on_bedtime() -> None:
    assert rest_title(bedtime=False) == "Resting"
    assert rest_title(bedtime=True) == "Goodnight"
    assert goodnight_label(bedtime=False) == "All done"
    assert goodnight_label(bedtime=True) == "Goodnight"


# --- and it says *when* (forum #31) --------------------------------------


def test_a_window_later_today_is_after_tea() -> None:
    now = datetime(2026, 8, 18, 16, 0)
    assert back_when_words(now, now + timedelta(hours=2)) == "after tea"
    assert rest_line(now, now + timedelta(hours=2), bedtime=False) == RESTING_LATER_TODAY


def test_a_window_on_another_day_is_tomorrow() -> None:
    now = datetime(2026, 8, 18, 16, 0)
    assert back_when_words(now, datetime(2026, 8, 19, 4, 0)) == "tomorrow"
    assert rest_line(now, datetime(2026, 8, 19, 4, 0), bedtime=False) == RESTING_TOMORROW


def test_bedtime_keeps_its_own_line() -> None:
    now = datetime(2026, 8, 18, 20, 0)
    assert rest_line(now, now + timedelta(hours=11), bedtime=True) == SLEEPING_LINE


def test_a_spent_afternoon_says_tomorrow_because_the_budget_rolls_at_four() -> None:
    """The line is computed, not guessed: 04:00 is the budget's own boundary."""
    policy = SessionPolicy(bedtime_start=time(19, 0), bedtime_end=time(7, 0))
    usage = DailyUsage(day=NOW.date(), seconds=policy.daily_budget)
    session = Session(policy=policy, usage=usage)
    afternoon = datetime(2026, 8, 18, 16, 30)
    assert rest_line(afternoon, session.next_allowed(afternoon), bedtime=False) == (
        RESTING_TOMORROW
    )


# --- the rate limit ------------------------------------------------------


def test_the_first_press_is_answered() -> None:
    limiter = TapSpeechLimiter()
    assert limiter.should_speak(100.0) is True


def test_a_second_press_inside_the_floor_is_ignored_not_interrupted() -> None:
    """Ignored, so nothing is cancelled, so nothing is cut off mid-word."""
    limiter = TapSpeechLimiter()
    limiter.should_speak(100.0)
    assert limiter.should_speak(101.0) is False
    assert limiter.should_speak(100.0 + SPEECH_INTERVAL_SECONDS - 0.1) is False


def test_three_presses_in_thirty_seconds_and_it_goes_quiet() -> None:
    """forum #23: repeated demands during dysregulation escalate."""
    limiter = TapSpeechLimiter()
    for at in (100.0, 101.0, 102.0):
        limiter.should_speak(at)
    assert limiter.silent is True
    # Even once the eight-second floor has passed.
    assert limiter.should_speak(115.0) is False
    assert limiter.should_speak(120.0) is False


def test_the_silence_lifts_once_the_hammering_stops() -> None:
    limiter = TapSpeechLimiter()
    for at in (100.0, 101.0, 102.0):
        limiter.should_speak(at)
    assert limiter.silent is True
    assert limiter.should_speak(200.0) is True


def test_a_fresh_arrival_speaks_again() -> None:
    limiter = TapSpeechLimiter()
    for at in (100.0, 101.0, 102.0):
        limiter.should_speak(at)
    limiter.reset()
    assert limiter.should_speak(103.0) is True


def test_the_thresholds_are_the_clinicians_numbers() -> None:
    assert SPEECH_INTERVAL_SECONDS == 8.0
    assert SILENCE_AFTER_TAPS == 3
