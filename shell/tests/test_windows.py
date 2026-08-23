"""Schedule windows, and the words a child gets outside one (parent-panel §7.1).

``[[windows]]`` in ``session.toml`` is the parent panel's answer to SYNTHESIS
D1 -- "match the household's boundaries" -- and FLOWS B5 recorded it as unbuilt
for a release and a half while the panel wrote the key anyway. This is the
shell learning to read it.

Three properties are load-bearing and every one of them has a test here:

1. **An empty schedule allows everything.** No windows, a malformed file, a
   window with no days -- all of them mean *no restriction*, never "no time at
   all". An empty allow-list has meant "all of them" since v0.1; a schedule
   that failed to parse must fail in the same direction, because the failure
   mode on the other side is a five-year-old locked out of a machine that
   worked yesterday and nobody able to say why.
2. **Bedtime wins.** A child outside their window at 8 pm is told it is night
   time. "It isn't your window" is not a sentence a five-year-old can act on
   and "it's night time" is.
3. **The refusal says when**, in child terms, with no digits: after tea,
   tomorrow, or on Saturday. Windows are what made the third one reachable --
   before them nothing was ever further off than tomorrow morning.

All pure, all clock-injected. ``NOW`` is midday on a **Tuesday**.
"""

from __future__ import annotations

import logging
from datetime import date, datetime, time, timedelta
from pathlib import Path

import pytest

from kidnix_shell.resting import (
    LATER_TODAY_WORDS,
    OUT_OF_HOURS_LATER_TODAY,
    OUT_OF_HOURS_ON_DAY,
    OUT_OF_HOURS_REFUSAL,
    OUT_OF_HOURS_TOMORROW,
    RESTING_LATER_TODAY,
    RESTING_ON_DAY,
    RESTING_TOMORROW,
    TOMORROW_WORDS,
    WEEKDAY_WORDS,
    back_when_words,
    out_of_hours_line,
    refusal_line,
    rest_line,
)
from kidnix_shell.session import (
    DAYS,
    DailyUsage,
    Session,
    SessionPolicy,
    StartRefusal,
    Window,
    load_policy,
    parse_days,
    parse_windows,
)

WEEKDAYS = frozenset({"mon", "tue", "wed", "thu", "fri"})
WEEKEND = frozenset({"sat", "sun"})

#: The example the panel's own docs use, and the one in the shipped file.
AFTER_SCHOOL = Window(days=WEEKDAYS, start=time(15, 30), end=time(18, 0), label="After school")
WEEKEND_MORNINGS = Window(days=WEEKEND, start=time(9, 30), end=time(12, 0))
#: A window that means "Friday evening until half past midnight".
FILM_NIGHT = Window(days=frozenset({"fri"}), start=time(20, 0), end=time(0, 30))

TUESDAY = date(2026, 8, 18)
SATURDAY = date(2026, 8, 22)


def at(day: date, hour: int, minute: int = 0) -> datetime:
    return datetime.combine(day, time(hour, minute))


def policy_with(*windows: Window, **kwargs: object) -> SessionPolicy:
    return SessionPolicy(windows=windows, **kwargs)  # type: ignore[arg-type]


def session_with(policy: SessionPolicy, spent: int = 0) -> Session:
    return Session(policy=policy, usage=DailyUsage(day=TUESDAY, seconds=spent))


# --- the days table -------------------------------------------------------


def test_the_day_names_are_weekday_indexed_so_nothing_has_to_map_them() -> None:
    """``DAYS[d.weekday()]`` is the whole of "which day is it", in both files."""
    assert DAYS == ("mon", "tue", "wed", "thu", "fri", "sat", "sun")
    assert DAYS[TUESDAY.weekday()] == "tue"
    assert DAYS[SATURDAY.weekday()] == "sat"


def test_the_weekday_words_line_up_with_the_day_names() -> None:
    """Two tuples in two modules, and the index is the only thing joining them."""
    assert len(WEEKDAY_WORDS) == len(DAYS)
    for index, name in enumerate(DAYS):
        assert name[0] == WEEKDAY_WORDS[index].removeprefix("on ")[0].lower()


# --- one window -----------------------------------------------------------


def test_an_ordinary_window_covers_its_own_afternoon() -> None:
    assert AFTER_SCHOOL.covers(at(TUESDAY, 15, 30))
    assert AFTER_SCHOOL.covers(at(TUESDAY, 16, 45))
    assert not AFTER_SCHOOL.covers(at(TUESDAY, 15, 29))


def test_the_end_of_a_window_is_the_first_moment_outside_it() -> None:
    """Half-open, like every other interval in the shell."""
    assert AFTER_SCHOOL.covers(at(TUESDAY, 17, 59))
    assert not AFTER_SCHOOL.covers(at(TUESDAY, 18, 0))


def test_a_window_does_not_cover_a_day_it_was_not_given() -> None:
    assert not AFTER_SCHOOL.covers(at(SATURDAY, 16, 0))
    assert WEEKEND_MORNINGS.covers(at(SATURDAY, 10, 0))
    assert not WEEKEND_MORNINGS.covers(at(TUESDAY, 10, 0))


def test_a_window_that_wraps_midnight_belongs_to_the_day_it_starts_on() -> None:
    """ "Friday evening until half past midnight" is one window, not two.

    Saturday 00:15 is covered without ``sat`` being listed, and Friday 00:15 --
    which is the *previous* wrap, from a Thursday nobody scheduled -- is not.
    """
    friday = date(2026, 8, 21)
    saturday = date(2026, 8, 22)
    assert FILM_NIGHT.wraps_midnight
    assert FILM_NIGHT.covers(at(friday, 21, 0))
    assert FILM_NIGHT.covers(at(saturday, 0, 15))
    assert not FILM_NIGHT.covers(at(saturday, 0, 30))
    assert not FILM_NIGHT.covers(at(friday, 0, 15))


def test_equal_start_and_end_is_a_whole_day_and_not_an_empty_one() -> None:
    """The safer of the two readings, and the panel refuses to write it anyway."""
    all_day = Window(days=frozenset({"tue"}), start=time(9, 0), end=time(9, 0))
    assert all_day.wraps_midnight
    assert all_day.covers(at(TUESDAY, 9, 0))
    assert all_day.covers(at(TUESDAY, 23, 59))
    assert all_day.covers(at(TUESDAY + timedelta(days=1), 8, 59))
    assert not all_day.covers(at(TUESDAY + timedelta(days=1), 9, 0))


def test_a_window_with_no_days_covers_nothing_and_opens_never() -> None:
    """It cannot be built from TOML; a programmatic caller still gets a no."""
    empty = Window(days=frozenset(), start=time(9, 0), end=time(17, 0))
    assert not empty.covers(at(TUESDAY, 12, 0))
    assert empty.next_start(at(TUESDAY, 12, 0)) is None


def test_the_next_start_is_strictly_in_the_future() -> None:
    noon = at(TUESDAY, 12, 0)
    assert AFTER_SCHOOL.next_start(noon) == at(TUESDAY, 15, 30)
    # Standing exactly on the opening, the *next* one is tomorrow's.
    assert AFTER_SCHOOL.next_start(at(TUESDAY, 15, 30)) == at(TUESDAY + timedelta(days=1), 15, 30)


def test_the_next_start_skips_the_days_the_window_does_not_have() -> None:
    """Saturday tea time on a weekdays-only machine is Monday."""
    assert AFTER_SCHOOL.next_start(at(SATURDAY, 17, 0)) == at(date(2026, 8, 24), 15, 30)


def test_the_next_start_never_looks_more_than_a_week_ahead() -> None:
    """Windows repeat weekly, so the answer is always inside seven days."""
    for hour in range(24):
        opens = WEEKEND_MORNINGS.next_start(at(TUESDAY, hour))
        assert opens is not None
        assert 0 < (opens - at(TUESDAY, hour)).days < 7


# --- parsing --------------------------------------------------------------


def test_days_are_normalised_to_three_lower_case_letters() -> None:
    assert parse_days(["Mon", "TUESDAY", " wed "]) == frozenset({"mon", "tue", "wed"})


def test_a_day_nobody_recognises_is_dropped_and_the_rest_survive() -> None:
    """A typo in one of seven strings is not the difference between a schedule
    and no schedule."""
    assert parse_days(["mon", "funday", "fri"]) == frozenset({"mon", "fri"})


def test_days_that_are_not_a_list_at_all_are_no_days() -> None:
    assert parse_days("mon") == frozenset()
    assert parse_days(None) == frozenset()


def test_a_whole_window_parses_out_of_the_shape_the_panel_writes() -> None:
    windows = parse_windows(
        [
            {
                "label": "After school",
                "days": ["mon", "tue", "wed", "thu", "fri"],
                "start": "15:30",
                "end": "18:00",
            }
        ]
    )
    assert windows == (AFTER_SCHOOL,)
    assert windows[0].label == "After school"


def test_the_label_is_optional_and_never_invented() -> None:
    (window,) = parse_windows([{"days": ["sat"], "start": "09:30", "end": "12:00"}])
    assert window.label == ""


@pytest.mark.parametrize(
    "entry",
    [
        {"days": [], "start": "15:30", "end": "18:00"},  # no days
        {"days": ["mon"], "start": "half three", "end": "18:00"},  # no clock
        {"days": ["mon"], "start": "15:30"},  # no end
        {"days": ["mon"], "start": "15:30", "end": "25:00"},  # not an hour
        {"start": "15:30", "end": "18:00"},  # no days key at all
        "after school",  # not a table
    ],
)
def test_a_malformed_window_is_skipped_and_not_guessed_at(entry: object) -> None:
    assert parse_windows([entry]) == ()


def test_one_bad_window_does_not_take_the_good_ones_with_it() -> None:
    windows = parse_windows(
        [
            {"days": ["mon"], "start": "nope", "end": "18:00"},
            {"days": ["sat", "sun"], "start": "09:30", "end": "12:00"},
        ]
    )
    assert windows == (WEEKEND_MORNINGS,)


def test_windows_that_are_not_a_list_are_no_windows_which_is_no_restriction() -> None:
    assert parse_windows(None) == ()
    assert parse_windows({"days": ["mon"]}) == ()
    assert parse_windows("mon 15:30") == ()


def test_a_skipped_window_says_so_in_the_journal(caplog: pytest.LogCaptureFixture) -> None:
    """Silence here is a parent who set a schedule and never learns it was junk."""
    with caplog.at_level(logging.WARNING, logger="kidnix_shell.session"):
        parse_windows([{"days": ["mon"], "start": "quarter past", "end": "18:00"}])
    assert any("skipping window" in record.getMessage() for record in caplog.records)


def test_the_policy_reads_windows_out_of_a_real_session_toml(tmp_path: Path) -> None:
    path = tmp_path / "session.toml"
    path.write_text(
        "length_minutes = 25\n"
        "\n"
        "[[windows]]\n"
        'label = "After school"\n'
        'days = ["mon", "tue", "wed", "thu", "fri"]\n'
        'start = "15:30"\n'
        'end = "18:00"\n',
        encoding="utf-8",
    )
    policy = load_policy(path)
    assert policy.windows == (AFTER_SCHOOL,)
    assert policy.length == 25 * 60  # the rest of the file still applies


def test_a_session_toml_with_no_windows_key_has_no_restriction(tmp_path: Path) -> None:
    path = tmp_path / "session.toml"
    path.write_text("length_minutes = 25\n", encoding="utf-8")
    policy = load_policy(path)
    assert policy.windows == ()
    assert policy.in_window(at(TUESDAY, 3, 0))


def test_the_shipped_session_toml_ships_no_active_windows() -> None:
    """The examples in it are commented out, and that is the shipped promise:
    a machine nobody has scheduled is open whenever bedtime and the budget are.
    """
    shipped = Path(__file__).resolve().parents[2] / "system_files/etc/kidnix/session.toml"
    policy = load_policy(shipped)
    assert policy.windows == ()
    assert policy.in_window(at(TUESDAY, 6, 0))
    assert "[[windows]]" in shipped.read_text(encoding="utf-8")


# --- in_window, over a whole policy ---------------------------------------


def test_no_windows_means_no_restriction_at_every_hour_of_the_week() -> None:
    """**The property that must never regress.** Empty is all, never none."""
    policy = SessionPolicy()
    for offset in range(7 * 24):
        assert policy.in_window(at(TUESDAY, 0) + timedelta(hours=offset))


def test_windows_that_all_failed_to_parse_are_the_same_as_none(tmp_path: Path) -> None:
    path = tmp_path / "session.toml"
    path.write_text(
        '[[windows]]\ndays = ["mon"]\nstart = "oops"\nend = "18:00"\n', encoding="utf-8"
    )
    policy = load_policy(path)
    assert policy.windows == ()
    assert policy.in_window(at(TUESDAY, 12, 0))


def test_two_windows_are_a_union_and_not_an_intersection() -> None:
    policy = policy_with(AFTER_SCHOOL, WEEKEND_MORNINGS)
    assert policy.in_window(at(TUESDAY, 16, 0))
    assert policy.in_window(at(SATURDAY, 10, 0))
    assert not policy.in_window(at(TUESDAY, 10, 0))


def test_the_next_window_start_is_the_earliest_of_all_of_them() -> None:
    policy = policy_with(WEEKEND_MORNINGS, AFTER_SCHOOL)
    assert policy.next_window_start(at(TUESDAY, 12, 0)) == at(TUESDAY, 15, 30)
    assert policy.next_window_start(at(date(2026, 8, 21), 19, 0)) == at(SATURDAY, 9, 30)


def test_there_is_no_next_window_when_there_are_no_windows() -> None:
    assert SessionPolicy().next_window_start(at(TUESDAY, 12, 0)) is None


# --- may_start ------------------------------------------------------------


def test_inside_the_window_a_session_starts() -> None:
    session = session_with(policy_with(AFTER_SCHOOL))
    assert session.may_start(at(TUESDAY, 16, 0)) is StartRefusal.OK


def test_outside_every_window_the_answer_is_out_of_hours() -> None:
    session = session_with(policy_with(AFTER_SCHOOL))
    assert session.may_start(at(TUESDAY, 10, 0)) is StartRefusal.OUT_OF_HOURS


def test_bedtime_wins_over_out_of_hours_because_it_is_the_sentence_that_helps() -> None:
    """At 8 pm on a Tuesday both are true. "It's night time" is actionable."""
    session = session_with(policy_with(AFTER_SCHOOL))
    assert session.may_start(at(TUESDAY, 20, 0)) is StartRefusal.BEDTIME


def test_out_of_hours_wins_over_a_spent_budget() -> None:
    """The refusals are ranked, and the one that can say *when* comes first."""
    policy = policy_with(AFTER_SCHOOL)
    session = session_with(policy, spent=policy.daily_budget)
    assert session.may_start(at(TUESDAY, 10, 0)) is StartRefusal.OUT_OF_HOURS
    assert session.may_start(at(TUESDAY, 16, 0)) is StartRefusal.BUDGET_SPENT


def test_a_session_outside_the_window_does_not_start_at_all() -> None:
    session = session_with(policy_with(AFTER_SCHOOL))
    assert session.start(at(TUESDAY, 10, 0)) is False
    assert not session.running


def test_a_machine_with_no_windows_is_refused_for_none_of_this() -> None:
    session = session_with(SessionPolicy())
    assert session.may_start(at(TUESDAY, 10, 0)) is StartRefusal.OK


# --- next_wake and next_allowed -------------------------------------------


def test_next_wake_is_now_when_both_gates_are_open() -> None:
    policy = policy_with(AFTER_SCHOOL)
    inside = at(TUESDAY, 16, 0)
    assert policy.next_wake(inside) == inside


def test_next_wake_waits_for_the_window_on_an_ordinary_morning() -> None:
    policy = policy_with(AFTER_SCHOOL)
    assert policy.next_wake(at(TUESDAY, 10, 0)) == at(TUESDAY, 15, 30)


def test_next_wake_takes_the_later_of_the_two_gates() -> None:
    """Bedtime ends at 07:00 and the window opens at 15:30; 15:30 wins."""
    policy = policy_with(AFTER_SCHOOL)
    assert policy.next_wake(at(TUESDAY, 5, 0)) == at(TUESDAY, 15, 30)


def test_next_wake_steps_past_a_window_that_opens_inside_bedtime() -> None:
    """A window that opens at 06:00 with bedtime running to 07:00 is not an
    opening, and the shell must not promise it as one."""
    policy = policy_with(
        Window(days=frozenset(DAYS), start=time(6, 0), end=time(9, 0)),
        bedtime_start=time(19, 0),
        bedtime_end=time(7, 0),
    )
    assert policy.next_wake(at(TUESDAY, 5, 0)) == at(TUESDAY, 7, 0)


def test_a_schedule_entirely_inside_bedtime_still_answers_rather_than_hanging() -> None:
    """A parent has asked for two contradictory things. The walk is bounded."""
    policy = policy_with(
        Window(days=frozenset(DAYS), start=time(21, 0), end=time(23, 0)),
        bedtime_start=time(19, 0),
        bedtime_end=time(7, 0),
    )
    assert isinstance(policy.next_wake(at(TUESDAY, 12, 0)), datetime)


def test_next_wake_is_unchanged_on_a_machine_with_no_windows() -> None:
    policy = SessionPolicy()
    morning = at(TUESDAY, 10, 0)
    assert policy.next_wake(morning) == morning
    assert policy.next_wake(at(TUESDAY, 20, 0)) == at(TUESDAY + timedelta(days=1), 7, 0)


def test_a_spent_budget_waits_for_the_window_after_the_reset() -> None:
    """04:00 is outside every schedule a household actually sets, so the two
    gates are asked again about the moment the budget comes back."""
    policy = policy_with(AFTER_SCHOOL)
    session = session_with(policy, spent=policy.daily_budget)
    assert session.next_allowed(at(TUESDAY, 16, 30)) == at(TUESDAY + timedelta(days=1), 15, 30)


def test_a_spent_budget_on_a_machine_with_no_windows_still_says_four_am() -> None:
    policy = SessionPolicy()
    session = session_with(policy, spent=policy.daily_budget)
    assert session.next_allowed(at(TUESDAY, 16, 30)) == at(TUESDAY + timedelta(days=1), 4, 0)


def test_a_weekends_only_machine_on_a_monday_waits_five_days() -> None:
    policy = policy_with(WEEKEND_MORNINGS)
    session = session_with(policy)
    monday = at(date(2026, 8, 17), 16, 0)
    assert session.next_allowed(monday) == at(date(2026, 8, 22), 9, 30)


# --- the words ------------------------------------------------------------


def test_later_the_same_day_is_after_tea() -> None:
    now = at(TUESDAY, 12, 0)
    assert back_when_words(now, at(TUESDAY, 15, 30)) == LATER_TODAY_WORDS


def test_the_next_day_is_tomorrow() -> None:
    now = at(TUESDAY, 16, 0)
    assert back_when_words(now, at(TUESDAY + timedelta(days=1), 15, 30)) == TOMORROW_WORDS


def test_anything_further_off_is_a_named_day() -> None:
    """The third answer, and windows are what made it reachable."""
    monday = at(date(2026, 8, 17), 16, 0)
    assert back_when_words(monday, at(SATURDAY, 9, 30)) == "on Saturday"


def test_a_whole_week_away_is_still_the_day_it_lands_on() -> None:
    now = at(TUESDAY, 16, 0)
    assert back_when_words(now, at(TUESDAY + timedelta(days=7), 15, 30)) == "on Tuesday"


def test_a_next_open_in_the_past_promises_the_least() -> None:
    """A clock that jumped, or a window list that ran out. Never "after tea"."""
    now = at(TUESDAY, 16, 0)
    assert back_when_words(now, at(TUESDAY, 9, 0)) == TOMORROW_WORDS


def test_no_when_word_anywhere_has_a_digit_in_it() -> None:
    words = [LATER_TODAY_WORDS, TOMORROW_WORDS, *WEEKDAY_WORDS]
    for word in words:
        assert not any(character.isdigit() for character in word), word


def test_the_resting_line_gains_a_named_day_and_keeps_the_other_two() -> None:
    monday = at(date(2026, 8, 17), 16, 0)
    assert rest_line(monday, at(SATURDAY, 9, 30), bedtime=False) == RESTING_ON_DAY.format(
        day="on Saturday"
    )
    assert rest_line(monday, at(date(2026, 8, 17), 18, 0), bedtime=False) == RESTING_LATER_TODAY
    assert rest_line(monday, at(TUESDAY, 9, 0), bedtime=False) == RESTING_TOMORROW


def test_the_resting_screen_and_who_s_here_agree_about_when() -> None:
    """One computation, said twice: the child is told the same thing, not two."""
    policy = policy_with(WEEKEND_MORNINGS)
    session = session_with(policy)
    monday = at(date(2026, 8, 17), 16, 0)
    opens = session.next_allowed(monday)
    assert "Saturday" in rest_line(monday, opens, bedtime=False)
    assert "Saturday" in out_of_hours_line(monday, opens)


# --- the refusal ----------------------------------------------------------


def test_the_out_of_hours_refusal_says_when_in_each_of_the_three_shapes() -> None:
    monday = at(date(2026, 8, 17), 12, 0)
    assert out_of_hours_line(monday, at(date(2026, 8, 17), 15, 30)) == OUT_OF_HOURS_LATER_TODAY
    assert out_of_hours_line(monday, at(TUESDAY, 15, 30)) == OUT_OF_HOURS_TOMORROW
    assert out_of_hours_line(monday, at(SATURDAY, 9, 30)) == OUT_OF_HOURS_ON_DAY.format(
        day="on Saturday"
    )


def test_a_refusal_with_nothing_to_say_when_about_still_says_something() -> None:
    assert out_of_hours_line(at(TUESDAY, 12, 0), None) == OUT_OF_HOURS_REFUSAL


def test_refusal_line_ranks_the_three_refusals_the_way_may_start_does() -> None:
    now = at(TUESDAY, 12, 0)
    opens = at(TUESDAY, 15, 30)
    assert refusal_line(bedtime=True, out_of_hours=True, now=now, next_open=opens) != (
        OUT_OF_HOURS_LATER_TODAY
    )
    assert (
        refusal_line(bedtime=False, out_of_hours=True, now=now, next_open=opens)
        == OUT_OF_HOURS_LATER_TODAY
    )
    assert refusal_line(bedtime=False) not in {OUT_OF_HOURS_LATER_TODAY, OUT_OF_HOURS_REFUSAL}


def test_the_out_of_hours_words_are_daytime_words() -> None:
    """forum #17: this fires at half past three as readily as at half past
    eight, so a moon, a yawn or "goodnight" here would be a sleep-onset cue
    conditioned to the moment the nice thing stopped."""
    for line in (
        OUT_OF_HOURS_REFUSAL,
        OUT_OF_HOURS_LATER_TODAY,
        OUT_OF_HOURS_TOMORROW,
        OUT_OF_HOURS_ON_DAY,
        RESTING_ON_DAY,
    ):
        lowered = line.lower()
        assert "sleep" not in lowered
        assert "night" not in lowered
        assert "goodnight" not in lowered


def test_the_out_of_hours_words_ask_the_child_for_nothing() -> None:
    """forum #23: no demand issued to a child whose executive function is gone."""
    for line in (
        OUT_OF_HOURS_REFUSAL,
        OUT_OF_HOURS_LATER_TODAY,
        OUT_OF_HOURS_TOMORROW,
        OUT_OF_HOURS_ON_DAY,
    ):
        lowered = line.lower()
        assert "ask a grown-up" not in lowered
        assert "?" not in lowered


def test_no_out_of_hours_sentence_has_a_digit_or_a_clock_in_it() -> None:
    for line in (
        OUT_OF_HOURS_REFUSAL,
        OUT_OF_HOURS_LATER_TODAY,
        OUT_OF_HOURS_TOMORROW,
        OUT_OF_HOURS_ON_DAY.format(day="on Saturday"),
        RESTING_ON_DAY.format(day="on Saturday"),
        *WEEKDAY_WORDS,
    ):
        assert not any(character.isdigit() for character in line), line
        assert ":" not in line, line


def test_every_out_of_hours_sentence_stays_inside_the_shell_s_own_limits() -> None:
    """01 #16: two sentences or fewer, twelve words or fewer -- and short
    enough for the one-line caption strip the band reserves."""
    for line in (
        OUT_OF_HOURS_REFUSAL,
        OUT_OF_HOURS_LATER_TODAY,
        OUT_OF_HOURS_TOMORROW,
        OUT_OF_HOURS_ON_DAY.format(day="on Wednesday"),
        RESTING_ON_DAY.format(day="on Wednesday"),
    ):
        assert len(line.split()) <= 12, line
        assert line.count(".") <= 2, line
        assert len(line) <= 50, line
