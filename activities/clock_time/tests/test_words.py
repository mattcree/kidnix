"""What the hands are showing, said the way a UK child is taught to say it.

The heart of the activity and the reason `words.py` has no GTK in it: the
guarantee is *"a Year 1 child is never shown or told a time their school has
not taught"*, and a guarantee that can only be exercised by pressing a button
is a guarantee nobody can check.
"""

from __future__ import annotations

from datetime import datetime, time

import pytest

from clock_time.words import (
    HOUR_NAMES,
    MINUTES_ON_A_DIAL,
    ClockTime,
    Mode,
    grid_for,
    hour_name,
    minute_words,
    rim_targets,
    snap,
)

# --- o'clock ----------------------------------------------------------------


@pytest.mark.parametrize(
    ("hour", "expected"),
    [
        (1, "one o'clock"),
        (2, "two o'clock"),
        (3, "three o'clock"),
        (6, "six o'clock"),
        (9, "nine o'clock"),
        (11, "eleven o'clock"),
        (12, "twelve o'clock"),
    ],
)
def test_every_hour_is_o_clock(hour, expected):
    assert ClockTime.of(hour, 0).words() == expected


def test_midnight_and_midday_are_both_twelve_o_clock():
    """A dial has no zero on it, so hour 0 and hour 12 are the same words."""
    assert ClockTime.of(0, 0).words() == "twelve o'clock"
    assert ClockTime.of(12, 0).words() == "twelve o'clock"
    assert ClockTime.of(0, 0) == ClockTime.of(12, 0)


# --- half past --------------------------------------------------------------


@pytest.mark.parametrize(
    ("hour", "expected"),
    [
        (1, "half past one"),
        (3, "half past three"),
        (7, "half past seven"),
        (11, "half past eleven"),
        (12, "half past twelve"),
    ],
)
def test_half_past_names_the_hour_it_is_past(hour, expected):
    assert ClockTime.of(hour, 30).words() == expected


# --- the quarters and the five-minute marks (Year 2) ------------------------


@pytest.mark.parametrize(
    ("hour", "minute", "expected"),
    [
        (3, 5, "five past three"),
        (3, 10, "ten past three"),
        (3, 15, "quarter past three"),
        (3, 20, "twenty past three"),
        (3, 25, "twenty-five past three"),
        (3, 30, "half past three"),
        (3, 35, "twenty-five to four"),
        (3, 40, "twenty to four"),
        (3, 45, "quarter to four"),
        (3, 50, "ten to four"),
        (3, 55, "five to four"),
    ],
)
def test_the_whole_hour_of_five_minute_marks(hour, minute, expected):
    assert ClockTime.of(hour, minute).words() == expected


def test_the_hour_the_minute_hand_counts_to_wraps_at_twelve():
    """"Quarter to one", not "quarter to thirteen"."""
    assert ClockTime.of(12, 45).words() == "quarter to one"
    assert ClockTime.of(11, 55).words() == "five to twelve"


def test_quarter_past_and_quarter_to_are_the_uk_words():
    assert ClockTime.of(8, 15).words() == "quarter past eight"
    assert ClockTime.of(8, 45).words() == "quarter to nine"


def test_twenty_five_is_hyphenated_because_the_caption_is_read():
    assert "twenty-five" in ClockTime.of(2, 25).words()
    assert "twenty-five" in ClockTime.of(2, 35).words()


def test_no_string_the_child_hears_contains_a_digit():
    """01 #19 / 03 #32. The dial carries numerals; the voice never does."""
    for total in range(MINUTES_ON_A_DIAL):
        assert not any(character.isdigit() for character in ClockTime(total).words())


def test_hour_names_are_the_twelve_and_start_at_twelve():
    assert len(HOUR_NAMES) == 12
    assert hour_name(0) == hour_name(12) == "twelve"
    assert hour_name(13) == "one"


# --- the position on the rim, with no hour attached -------------------------


@pytest.mark.parametrize(
    ("minute", "expected"),
    [
        (0, "o'clock"),
        (15, "quarter past"),
        (30, "half past"),
        (45, "quarter to"),
        (5, "five past"),
        (55, "five to"),
    ],
)
def test_a_rim_target_is_named_by_its_position_not_its_time(minute, expected):
    assert minute_words(minute) == expected


def test_an_off_grid_minute_is_named_by_the_mark_it_is_nearest():
    assert minute_words(31) == "half past"
    assert minute_words(58) == "o'clock"


# --- snapping ---------------------------------------------------------------


def test_year_one_has_exactly_two_positions_in_an_hour():
    assert grid_for(Mode.Y1) == (0, 30)


def test_year_two_has_twelve():
    assert grid_for(Mode.Y2) == tuple(range(0, 60, 5))


@pytest.mark.parametrize(
    ("hour", "minute", "expected"),
    [
        (3, 3, "three o'clock"),
        (3, 14, "three o'clock"),
        (3, 16, "half past three"),
        (3, 29, "half past three"),
        (3, 40, "half past three"),
        (3, 46, "four o'clock"),
    ],
)
def test_year_one_snaps_to_o_clock_or_half_past_and_nothing_else(hour, minute, expected):
    assert ClockTime.of(hour, minute).snapped(Mode.Y1).words() == expected


def test_year_one_never_produces_a_quarter():
    for total in range(MINUTES_ON_A_DIAL):
        words = ClockTime(snap(total, Mode.Y1)).words()
        assert "quarter" not in words
        assert "twenty" not in words
        assert "five past" not in words


def test_snapping_wraps_over_twelve_rather_than_going_backwards():
    """Ten to twelve is nearer to twelve o'clock than to half past eleven."""
    assert ClockTime.of(11, 50).snapped(Mode.Y1).words() == "twelve o'clock"


def test_the_hour_hand_comes_with_it():
    """Snapping forwards past the hour must move the hour, not just the minute."""
    snapped = ClockTime.of(3, 50).snapped(Mode.Y1)
    assert snapped.hour == 4
    assert snapped.minute == 0


def test_a_tie_rounds_up_so_the_answer_never_depends_on_direction():
    """Quarter past, in Year 1, is exactly between o'clock and half past."""
    assert ClockTime.of(3, 15).snapped(Mode.Y1) == ClockTime.of(3, 30)


@pytest.mark.parametrize("minute", [0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55])
def test_year_two_leaves_a_five_minute_mark_where_it_is(minute):
    assert ClockTime.of(4, minute).snapped(Mode.Y2) == ClockTime.of(4, minute)


def test_year_two_snaps_a_real_minute_to_the_nearest_mark():
    assert ClockTime.of(4, 23).snapped(Mode.Y2) == ClockTime.of(4, 25)
    assert ClockTime.of(4, 58).snapped(Mode.Y2) == ClockTime.of(5, 0)


def test_snapping_accepts_a_negative_and_does_not_throw():
    assert snap(-10, Mode.Y2) == snap(710, Mode.Y2)


# --- stepping round the rim (the arrow keys) --------------------------------


def test_one_step_forward_in_year_one_is_half_an_hour():
    assert ClockTime.of(3, 0).stepped(1, Mode.Y1) == ClockTime.of(3, 30)
    assert ClockTime.of(3, 30).stepped(1, Mode.Y1) == ClockTime.of(4, 0)


def test_one_step_forward_in_year_two_is_five_minutes():
    assert ClockTime.of(3, 0).stepped(1, Mode.Y2) == ClockTime.of(3, 5)


def test_stepping_backwards_goes_backwards():
    assert ClockTime.of(3, 30).stepped(-1, Mode.Y1) == ClockTime.of(3, 0)
    assert ClockTime.of(3, 0).stepped(-1, Mode.Y2) == ClockTime.of(2, 55)


def test_stepping_wraps_round_the_dial_in_both_directions():
    assert ClockTime.of(11, 30).stepped(1, Mode.Y1) == ClockTime.of(12, 0)
    assert ClockTime.of(12, 0).stepped(-1, Mode.Y1) == ClockTime.of(11, 30)


def test_stepping_off_an_odd_minute_tidies_the_clock_up():
    """The Now button can leave the hands between marks; one arrow fixes it."""
    assert ClockTime.of(3, 26).stepped(1, Mode.Y2) == ClockTime.of(3, 30)
    assert ClockTime.of(3, 26).stepped(-1, Mode.Y2) == ClockTime.of(3, 25)


def test_stepping_by_zero_changes_nothing():
    assert ClockTime.of(3, 26).stepped(0, Mode.Y2) == ClockTime.of(3, 26)


# --- reading a real clock ---------------------------------------------------


def test_the_hands_come_from_a_real_datetime_and_drop_the_seconds():
    assert ClockTime.from_time(datetime(2026, 8, 23, 15, 30, 44)) == ClockTime.of(3, 30)


def test_a_time_works_as_well_as_a_datetime():
    assert ClockTime.from_time(time(7, 45)) == ClockTime.of(7, 45)


def test_the_voice_hedges_when_the_hands_are_between_marks():
    """Saying "half past three" at twenty-six past teaches the wrong thing."""
    assert ClockTime.of(3, 26).spoken(Mode.Y2) == "about twenty-five past three"
    assert ClockTime.of(3, 26).spoken(Mode.Y1) == "about half past three"


def test_the_voice_does_not_hedge_when_it_does_not_have_to():
    assert ClockTime.of(3, 30).spoken(Mode.Y2) == "half past three"
    assert ClockTime.of(3, 30).spoken(Mode.Y1) == "half past three"


def test_year_one_hedges_more_often_than_year_two_and_that_is_correct():
    assert ClockTime.of(3, 15).spoken(Mode.Y1).startswith("about")
    assert not ClockTime.of(3, 15).spoken(Mode.Y2).startswith("about")


# --- the geometry the drawing asks for --------------------------------------


def test_the_minute_hand_goes_six_degrees_a_minute():
    assert ClockTime.of(12, 0).minute_angle == 0.0
    assert ClockTime.of(12, 15).minute_angle == 90.0
    assert ClockTime.of(12, 30).minute_angle == 180.0
    assert ClockTime.of(12, 45).minute_angle == 270.0


def test_the_hour_hand_follows_the_minutes_as_a_real_one_does():
    """At half past three the hour hand is halfway between three and four."""
    assert ClockTime.of(3, 0).hour_angle == 90.0
    assert ClockTime.of(3, 30).hour_angle == 105.0
    assert ClockTime.of(4, 0).hour_angle == 120.0


def test_the_two_hands_are_only_together_when_they_should_be():
    together = [
        total
        for total in range(MINUTES_ON_A_DIAL)
        if abs(ClockTime(total).hour_angle - ClockTime(total).minute_angle) < 1e-9
    ]
    assert together == [0]


# --- the mode is the parent's, and only the parent's ------------------------


@pytest.mark.parametrize("text", ["y1", "Y1", " y1 ", "year 1", "Year1"])
def test_year_one_is_spelled_several_ways_and_all_of_them_work(text):
    assert Mode.parse(text) is Mode.Y1


@pytest.mark.parametrize("text", ["y2", "Y2", "year 2", "YEAR 2"])
def test_year_two_likewise(text):
    assert Mode.parse(text) is Mode.Y2


@pytest.mark.parametrize("text", [None, "", "reception", "3", "y3", "nonsense"])
def test_anything_unrecognised_falls_back_to_the_safe_answer(text):
    """Starting too low costs nothing; starting too high shows a child
    something their school has not taught."""
    assert Mode.parse(text) is Mode.Y1


def test_clock_time_is_orderable_so_a_routine_can_be_sorted():
    assert ClockTime.of(3, 0) < ClockTime.of(3, 30) < ClockTime.of(4, 0)


def test_the_dial_is_modular_and_never_out_of_range():
    assert ClockTime(MINUTES_ON_A_DIAL) == ClockTime(0)
    assert ClockTime(-1).total == MINUTES_ON_A_DIAL - 1


def test_describe_is_for_the_log_and_may_carry_digits():
    """A parent reads the journal; a child does not."""
    assert ClockTime.of(3, 30).describe() == "03:30 (half past three)"


# --- ADR-0013: what the rim offers, and what it may not ---------------------


def test_year_one_offers_two_targets_and_year_two_offers_twelve():
    """ADR-0013. A labelled grid whose items *are* the task is not a choice
    set, so the twelve hours of a clock face stay in Year 2 -- but the default
    year is the two positions the National Curriculum names for it."""
    assert [minute for minute, _name in rim_targets(Mode.Y1)] == [0, 30]
    assert len(rim_targets(Mode.Y2)) == 12


def test_year_one_has_nothing_on_the_five_minute_rim():
    """Not a quarter past, not twenty to, and no voice for them either. A
    target a child can hear but has not been taught is a lesson their school
    has not given."""
    said = {name for _minute, name in rim_targets(Mode.Y1)}
    assert said == {"o'clock", "half past"}
    for taught_later in ("quarter past", "quarter to", "five past", "twenty-five to"):
        assert taught_later not in said


def test_every_target_says_its_position_and_never_a_digit():
    for mode in Mode:
        for minute, name in rim_targets(mode):
            assert name == minute_words(minute)
            assert not any(character.isdigit() for character in name)


def test_the_targets_are_exactly_the_grid_the_hands_may_land_on():
    """One list, two readers. "What a child can press" and "where a hand may
    stop" drifting apart is a rim target that moves the hands somewhere the
    snap will not keep them."""
    for mode in Mode:
        assert [minute for minute, _name in rim_targets(mode)] == list(grid_for(mode))
        for minute, _name in rim_targets(mode):
            assert snap(minute, mode) == minute
