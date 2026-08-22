"""Session timing and policy (spec section 6, SYNTHESIS D)."""

from __future__ import annotations

from datetime import date, datetime, time, timedelta
from pathlib import Path

import pytest

from kidnix_shell.session import (
    A_LITTLE_LEFT,
    LOTS_LEFT,
    NEARLY_TIME,
    NOT_RUNNING,
    ONE_STORY_LEFT,
    DailyUsage,
    Phase,
    Session,
    SessionPolicy,
    StartRefusal,
    budget_day,
    load_policy,
    next_budget_reset,
    time_left_words,
)

from .conftest import NOW


def test_defaults_match_the_synthesis_numbers() -> None:
    policy = SessionPolicy()
    assert policy.length == 25 * 60
    assert policy.daily_budget == 60 * 60
    assert policy.ending_offer_at == 6 * 60
    assert policy.put_away_at == 2 * 60


def test_demo_policy_fits_a_three_minute_run() -> None:
    policy = SessionPolicy.demo()
    assert policy.length == 180
    assert policy.ending_offer_at == 60
    assert policy.put_away_at == 20


def test_phases_step_through_the_ritual(session: Session) -> None:
    assert session.phase(NOW) is Phase.IDLE
    assert session.start(NOW)
    assert session.phase(NOW) is Phase.RUNNING
    assert session.phase(NOW + timedelta(minutes=18)) is Phase.RUNNING
    # T-6 exactly is the offer.
    assert session.phase(NOW + timedelta(minutes=19)) is Phase.ENDING_OFFER
    assert session.phase(NOW + timedelta(minutes=22)) is Phase.ENDING_OFFER
    assert session.phase(NOW + timedelta(minutes=23)) is Phase.PUT_AWAY
    assert session.phase(NOW + timedelta(minutes=25)) is Phase.ENDED
    assert session.phase(NOW + timedelta(minutes=99)) is Phase.ENDED


def test_the_sun_crosses_the_sky_linearly(session: Session) -> None:
    session.start(NOW)
    assert session.fraction_spent(NOW) == 0.0
    assert abs(session.fraction_spent(NOW + timedelta(minutes=12.5)) - 0.5) < 0.001
    assert session.fraction_spent(NOW + timedelta(minutes=40)) == 1.0


def test_the_sun_warms_in_the_last_six_minutes(session: Session) -> None:
    session.start(NOW)
    assert not session.is_warm(NOW + timedelta(minutes=18))
    assert session.is_warm(NOW + timedelta(minutes=20))


def test_remaining_never_goes_negative(session: Session) -> None:
    session.start(NOW)
    assert session.remaining(NOW + timedelta(hours=3)) == 0


def test_bedtime_wraps_around_midnight() -> None:
    policy = SessionPolicy()
    assert policy.is_bedtime(datetime(2026, 8, 18, 20, 0))
    assert policy.is_bedtime(datetime(2026, 8, 18, 3, 0))
    assert not policy.is_bedtime(datetime(2026, 8, 18, 12, 0))
    assert policy.is_bedtime(datetime(2026, 8, 18, 19, 0))
    assert not policy.is_bedtime(datetime(2026, 8, 18, 7, 0))


def test_a_daytime_bedtime_window_does_not_wrap() -> None:
    policy = SessionPolicy(bedtime_start=time(13, 0), bedtime_end=time(15, 0))
    assert policy.is_bedtime(datetime(2026, 8, 18, 14, 0))
    assert not policy.is_bedtime(datetime(2026, 8, 18, 20, 0))


def test_an_empty_bedtime_window_never_triggers() -> None:
    policy = SessionPolicy(bedtime_start=time(0, 0), bedtime_end=time(0, 0))
    assert not policy.is_bedtime(datetime(2026, 8, 18, 3, 0))


def test_next_wake_is_the_end_of_bedtime() -> None:
    policy = SessionPolicy()
    assert policy.next_wake(datetime(2026, 8, 18, 20, 0)) == datetime(2026, 8, 19, 7, 0)
    assert policy.next_wake(datetime(2026, 8, 19, 3, 0)) == datetime(2026, 8, 19, 7, 0)
    midday = datetime(2026, 8, 18, 12, 0)
    assert policy.next_wake(midday) == midday


def test_a_session_will_not_start_at_bedtime(session: Session) -> None:
    night = datetime(2026, 8, 18, 20, 30)
    assert session.may_start(night) is StartRefusal.BEDTIME
    assert not session.start(night)
    assert not session.running


def test_a_session_will_not_start_with_the_budget_spent(policy: SessionPolicy) -> None:
    usage = DailyUsage(day=NOW.date(), seconds=policy.daily_budget)
    session = Session(policy=policy, usage=usage)
    assert session.may_start(NOW) is StartRefusal.BUDGET_SPENT
    assert not session.start(NOW)


def test_the_daily_budget_caps_the_session_length(policy: SessionPolicy) -> None:
    # 50 of 60 minutes spent: today's last session is ten minutes, not 25.
    usage = DailyUsage(day=NOW.date(), seconds=50 * 60)
    session = Session(policy=policy, usage=usage)
    assert session.start(NOW)
    assert session.granted == 10 * 60


def test_ending_a_session_banks_the_time(session: Session) -> None:
    session.start(NOW)
    session.end(NOW + timedelta(minutes=12))
    assert session.usage.seconds == 12 * 60
    assert not session.running


def test_ending_twice_does_not_double_count(session: Session) -> None:
    session.start(NOW)
    session.end(NOW + timedelta(minutes=12))
    session.end(NOW + timedelta(minutes=15))
    assert session.usage.seconds == 12 * 60


def test_a_grant_extends_the_session(session: Session) -> None:
    session.start(NOW)
    assert session.add_minutes(15, NOW + timedelta(minutes=20)) == 15 * 60
    assert session.granted == 40 * 60
    assert session.phase(NOW + timedelta(minutes=20)) is Phase.RUNNING


def test_a_grant_is_still_bounded_by_the_daily_budget(policy: SessionPolicy) -> None:
    usage = DailyUsage(day=NOW.date(), seconds=20 * 60)  # 40 minutes left
    session = Session(policy=policy, usage=usage)
    session.start(NOW)  # granted 25
    assert session.add_minutes(30, NOW + timedelta(minutes=20)) == 15 * 60
    assert session.granted == 40 * 60


def test_a_grant_does_nothing_when_nothing_is_running(session: Session) -> None:
    assert session.add_minutes(15, NOW) == 0


def test_usage_resets_when_the_day_rolls_over(tmp_path: Path) -> None:
    path = tmp_path / "usage.toml"
    DailyUsage(day=date(2026, 8, 17), seconds=1800, path=path).save()
    reloaded = DailyUsage.load(path, date(2026, 8, 18))
    assert reloaded.seconds == 0
    assert reloaded.day == date(2026, 8, 18)


def test_usage_survives_within_the_same_day(tmp_path: Path) -> None:
    path = tmp_path / "usage.toml"
    DailyUsage(day=date(2026, 8, 18), seconds=1800, path=path).save()
    assert DailyUsage.load(path, date(2026, 8, 18)).seconds == 1800


def test_corrupt_usage_state_starts_fresh(tmp_path: Path) -> None:
    path = tmp_path / "usage.toml"
    path.write_text("this is not toml [[[", encoding="utf-8")
    assert DailyUsage.load(path, date(2026, 8, 18)).seconds == 0


def test_session_length_is_clamped_to_the_allowed_range() -> None:
    policy = SessionPolicy()
    assert policy.with_length_minutes(2).length == 10 * 60
    assert policy.with_length_minutes(90).length == 45 * 60
    assert policy.with_length_minutes(30).length == 30 * 60


def test_policy_loads_from_toml(tmp_path: Path) -> None:
    path = tmp_path / "session.toml"
    path.write_text(
        "\n".join(
            [
                "length_minutes = 20",
                "daily_budget_minutes = 45",
                "ending_offer_minutes = 5",
                "put_away_minutes = 1",
                'bedtime_start = "18:30"',
                'bedtime_end = "06:45"',
            ]
        ),
        encoding="utf-8",
    )
    policy = load_policy(path)
    assert policy.length == 20 * 60
    assert policy.daily_budget == 45 * 60
    assert policy.bedtime_start == time(18, 30)
    assert policy.bedtime_end == time(6, 45)


def test_a_missing_or_broken_policy_file_falls_back_to_defaults(tmp_path: Path) -> None:
    assert load_policy(tmp_path / "nope.toml") == SessionPolicy()
    bad = tmp_path / "bad.toml"
    bad.write_text("nonsense [[[", encoding="utf-8")
    assert load_policy(bad) == SessionPolicy()


def test_nonsense_values_in_the_policy_file_are_ignored(tmp_path: Path) -> None:
    path = tmp_path / "session.toml"
    path.write_text('length_minutes = "twenty"\nbedtime_start = "nope"\n', encoding="utf-8")
    policy = load_policy(path)
    assert policy.length == SessionPolicy().length
    assert policy.bedtime_start == SessionPolicy().bedtime_start


# --- the 04:00 budget day (spec 7a) --------------------------------------


def test_the_budget_day_rolls_at_four_in_the_morning() -> None:
    """Midnight is the wrong boundary: 00:30 is still last night."""
    assert budget_day(datetime(2026, 8, 18, 23, 59)) == date(2026, 8, 18)
    assert budget_day(datetime(2026, 8, 19, 0, 30)) == date(2026, 8, 18)
    assert budget_day(datetime(2026, 8, 19, 3, 59)) == date(2026, 8, 18)
    assert budget_day(datetime(2026, 8, 19, 4, 0)) == date(2026, 8, 19)
    assert budget_day(datetime(2026, 8, 19, 12, 0)) == date(2026, 8, 19)


def test_the_next_reset_is_the_next_four_am() -> None:
    assert next_budget_reset(datetime(2026, 8, 18, 12, 0)) == datetime(2026, 8, 19, 4, 0)
    assert next_budget_reset(datetime(2026, 8, 19, 1, 0)) == datetime(2026, 8, 19, 4, 0)


def test_a_midnight_snack_does_not_refill_the_budget(tmp_path: Path) -> None:
    """The v0.1.0 behaviour handed a child a fresh hour at 00:00."""
    # Bedtime off, so the only thing being tested is the budget boundary.
    policy = SessionPolicy.from_minutes(
        daily_budget=60, bedtime_start=time(0, 0), bedtime_end=time(0, 0)
    )
    usage = DailyUsage(day=budget_day(datetime(2026, 8, 18, 20, 0)), seconds=60 * 60)
    session = Session(policy=policy, usage=usage)
    assert session.may_start(datetime(2026, 8, 19, 0, 30)) is StartRefusal.BUDGET_SPENT
    assert session.may_start(datetime(2026, 8, 19, 3, 59)) is StartRefusal.BUDGET_SPENT
    # ...and at 04:00 tomorrow starts.
    assert session.may_start(datetime(2026, 8, 19, 12, 0)) is StartRefusal.OK
    assert usage.seconds == 0


def test_usage_loaded_after_midnight_still_belongs_to_last_night(tmp_path: Path) -> None:
    path = tmp_path / "usage.toml"
    DailyUsage(day=date(2026, 8, 18), seconds=900, path=path).save()
    late = DailyUsage.for_now(path, datetime(2026, 8, 19, 1, 0))
    assert late.seconds == 900
    fresh = DailyUsage.for_now(path, datetime(2026, 8, 19, 9, 0))
    assert fresh.seconds == 0


# --- what the sun says when a child taps it (08 section 4.6) --------------
#
# The audit: the sun is "not tappable -- Sun is an AccessibleRole.IMG with no
# gesture, so 08 section 4.6's 'tapping speaks the remaining time in child
# terms' is absent." These are the terms.


@pytest.mark.parametrize(
    ("fraction_left", "expected"),
    [
        (1.0, LOTS_LEFT),
        (0.9, LOTS_LEFT),
        (0.67, LOTS_LEFT),
        (0.66, ONE_STORY_LEFT),
        (0.5, ONE_STORY_LEFT),
        (0.34, ONE_STORY_LEFT),
        (0.33, A_LITTLE_LEFT),
        (0.2, A_LITTLE_LEFT),
        (0.11, A_LITTLE_LEFT),
        (0.1, NEARLY_TIME),
        (0.02, NEARLY_TIME),
        (0.0, NEARLY_TIME),
    ],
)
def test_the_sun_maps_a_fraction_onto_words(fraction_left: float, expected: str) -> None:
    assert time_left_words(fraction_left) == expected


def test_the_sun_never_says_a_number() -> None:
    """01 #19 and 01 #30: no digits anywhere the child can see *or hear*."""
    for fraction in [i / 100 for i in range(101)]:
        for running in (True, False):
            words = time_left_words(fraction, running=running)
            assert not any(c.isdigit() for c in words), words


def test_every_sun_sentence_is_short_enough_to_hear(session: Session) -> None:
    """01 #16: at most two sentences and twelve words."""
    for words in (LOTS_LEFT, ONE_STORY_LEFT, A_LITTLE_LEFT, NEARLY_TIME, NOT_RUNNING):
        assert len([s for s in words.split(".") if s.strip()]) <= 2, words
        assert len(words.split()) <= 12, words


def test_a_nonsense_fraction_still_lands_on_a_sentence() -> None:
    """A clock that jumped must not make the sun speechless."""
    assert time_left_words(-5.0) == NEARLY_TIME
    assert time_left_words(17.0) == LOTS_LEFT
    assert time_left_words(float("nan")) in {LOTS_LEFT, NEARLY_TIME}


def test_an_idle_sun_says_so_rather_than_lying(session: Session) -> None:
    assert session.running is False
    assert session.time_left_words(NOW) == NOT_RUNNING
    assert time_left_words(1.0, running=False) == NOT_RUNNING


def test_the_sun_walks_down_the_sentences_across_a_real_session(session: Session) -> None:
    """Twenty-five minutes, minute by minute: the words only ever go one way."""
    assert session.start(NOW)
    order = [LOTS_LEFT, ONE_STORY_LEFT, A_LITTLE_LEFT, NEARLY_TIME]
    seen = [session.time_left_words(NOW + timedelta(minutes=m)) for m in range(26)]
    assert seen[0] == LOTS_LEFT
    assert seen[-1] == NEARLY_TIME
    indices = [order.index(w) for w in seen]
    assert indices == sorted(indices), seen


def test_fraction_left_is_the_complement_of_fraction_spent(session: Session) -> None:
    assert session.start(NOW)
    for minutes in (0, 5, 12, 25, 40):
        when = NOW + timedelta(minutes=minutes)
        assert round(session.fraction_left(when) + session.fraction_spent(when), 6) == 1.0
