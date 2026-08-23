"""What happens when: the lookup that makes a dial mean something in this house.

02 #18 is the finding underneath the whole strip -- *context is what actually
ends screen time; 39% of transitions ended because the situation changed* --
and it only pays if the picture beside the clock is right. A twelve-hour dial
has no morning and no afternoon, so getting it right is the one piece of real
arithmetic in this module.
"""

from __future__ import annotations

import pytest

from clock_time.routine import (
    DEFAULT_ROUTINE,
    MINUTES_IN_A_DAY,
    Routine,
    RoutineItem,
    Sky,
    parse_hhmm,
)
from clock_time.words import ClockTime, Mode


@pytest.fixture
def day() -> Routine:
    return Routine(DEFAULT_ROUTINE)


# --- reading a time out of the grown-up's file ------------------------------


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("07:00", 420),
        ("7:00", 420),
        ("07.30", 450),
        ("  17:30 ", 1050),
        ("00:00", 0),
        ("23:59", 1439),
    ],
)
def test_a_time_is_read_the_way_people_write_it(text, expected):
    assert parse_hhmm(text) == expected


@pytest.mark.parametrize(
    "text", ["", "half seven", "7", "25:00", "07:60", "seven o'clock", "7:0", None]
)
def test_anything_that_is_not_a_time_is_dropped_rather_than_guessed(text):
    assert parse_hhmm(text) is None


# --- the default day --------------------------------------------------------


def test_the_default_day_is_the_eight_the_brief_asked_for(day):
    assert len(day) == 8
    assert [item.id for item in day] == [
        "wake",
        "breakfast",
        "school",
        "lunch",
        "home",
        "tea",
        "bath",
        "bed",
    ]


def test_every_default_moment_has_a_drawing_that_exists():
    from clock_time.pictures import picture_path

    for item in DEFAULT_ROUTINE:
        assert picture_path(item).is_file(), item.id


def test_a_moment_says_itself_in_one_line_with_no_digits(day):
    for item in day:
        assert not any(character.isdigit() for character in item.sentence)
        assert item.sentence.endswith(".")


def test_tea_is_at_half_past_five(day):
    assert day.by_id("tea").sentence == "Tea is at half past five."


def test_a_moment_defaults_its_picture_to_its_id():
    assert RoutineItem("bath", "Bath", 18 * 60).picture == "bath"
    assert RoutineItem("bath", "Bath", 18 * 60, picture="tub").picture == "tub"


def test_a_routine_is_sorted_by_time_however_it_was_written():
    shuffled = Routine.of(
        [
            RoutineItem("bed", "Bed", 19 * 60),
            RoutineItem("wake", "Wake up", 7 * 60),
            RoutineItem("tea", "Tea", 17 * 60),
        ]
    )
    assert [item.id for item in shuffled] == ["wake", "tea", "bed"]


def test_an_empty_routine_falls_back_to_the_default_day():
    assert Routine.of([]).items == DEFAULT_ROUTINE


# --- the sky ----------------------------------------------------------------


@pytest.mark.parametrize(
    ("minutes", "expected"),
    [
        (0, Sky.NIGHT),
        (4 * 60 + 59, Sky.NIGHT),
        (5 * 60, Sky.MORNING),
        (7 * 60, Sky.MORNING),
        (11 * 60 + 59, Sky.MORNING),
        (12 * 60, Sky.AFTERNOON),
        (16 * 60 + 59, Sky.AFTERNOON),
        (17 * 60, Sky.EVENING),
        (20 * 60 + 59, Sky.EVENING),
        (21 * 60, Sky.NIGHT),
        (23 * 60 + 59, Sky.NIGHT),
    ],
)
def test_the_sky_changes_where_a_family_would_say_it_does(minutes, expected):
    assert Sky.at(minutes) is expected


def test_the_sky_wraps_rather_than_running_off_the_end_of_the_day():
    assert Sky.at(MINUTES_IN_A_DAY) is Sky.at(0)
    assert Sky.at(-60) is Sky.at(23 * 60)


def test_only_the_night_is_dark():
    assert Sky.NIGHT.is_dark
    assert not any(sky.is_dark for sky in Sky if sky is not Sky.NIGHT)


def test_the_sky_says_itself_in_words():
    assert Sky.MORNING.words == "in the morning"
    assert Sky.NIGHT.words == "at night"


# --- which moment the hands are showing -------------------------------------


def test_the_current_moment_is_the_last_thing_that_started_not_the_nearest(day):
    """At four o'clock a child has been home half an hour and is not yet at tea."""
    assert day.at_minute(16 * 60).id == "home"


@pytest.mark.parametrize(
    ("hour", "minute", "expected"),
    [
        (7, 0, "wake"),
        (7, 30, "breakfast"),
        (8, 0, "breakfast"),
        (9, 0, "school"),
        (12, 0, "lunch"),
        (3, 30, "home"),
        (5, 30, "tea"),
        (6, 30, "bath"),
        (11, 45, "school"),
    ],
)
def test_a_twelve_hour_dial_still_lands_on_the_right_half_of_the_day(
    day, hour, minute, expected
):
    assert day.at(ClockTime.of(hour, minute)).id == expected


def test_three_o_clock_is_the_afternoon_and_not_the_small_hours(day):
    """Both are three o'clock on a dial. The afternoon candidate is three hours
    after lunch; the small-hours one is eight hours after bed, so the afternoon
    wins -- and the answer is "lunch", because home time is at half past three
    and at three o'clock nobody is home yet."""
    assert day.at(ClockTime.of(3, 0)).id == "lunch"
    assert day.sky_for(ClockTime.of(3, 0)) is Sky.AFTERNOON


def test_half_past_seven_is_breakfast_and_not_bath(day):
    assert day.at(ClockTime.of(7, 30)).id == "breakfast"
    assert day.sky_for(ClockTime.of(7, 30)) is Sky.MORNING


def test_the_middle_of_the_night_is_still_bed(day):
    """True, and the answer a child who has got up in the night recognises."""
    assert day.at_minute(2 * 60).id == "bed"


def test_the_lookup_never_returns_nothing(day):
    for total in range(0, 720, 5):
        assert day.at(ClockTime(total)) in day.items


def test_every_dial_position_gets_a_sky(day):
    for total in range(0, 720, 5):
        assert isinstance(day.sky_for(ClockTime(total)), Sky)


def test_a_one_moment_day_answers_for_the_whole_dial():
    single = Routine.of([RoutineItem("tea", "Tea", 17 * 60)])
    assert all(single.at(ClockTime(total)).id == "tea" for total in range(0, 720, 30))


def test_pressing_a_moment_puts_the_hands_where_that_moment_is(day):
    """The link read the other way round: bath is at half past six."""
    bath = day.by_id("bath")
    assert bath.clock.snapped(Mode.Y1).words() == "half past six"


def test_index_of_is_minus_one_for_something_that_is_not_ours(day):
    assert day.index_of(RoutineItem("nap", "Nap", 13 * 60)) == -1
    assert day.index_of(day[0]) == 0


def test_by_id_returns_nothing_for_a_name_nobody_configured(day):
    assert day.by_id("elevenses") is None


# --- the room decides which half of the dial the hands mean -----------------


def test_seven_o_clock_is_getting_up_in_the_morning(day):
    assert day.at(ClockTime.of(7, 0), now=9 * 60).id == "wake"
    assert day.sky_for(ClockTime.of(7, 0), now=9 * 60) is Sky.MORNING


def test_and_going_to_bed_in_the_evening(day):
    """With no hint, a crowded morning shadows the evening and "bed" is
    unreachable -- a strip with an item nobody can land on is a strip with a
    lie in it."""
    assert day.at(ClockTime.of(7, 0), now=18 * 60).id == "bed"
    assert day.sky_for(ClockTime.of(7, 0), now=18 * 60) is Sky.EVENING


def test_the_hint_only_chooses_between_the_two_it_is_given(day):
    """It never invents a time the hands are not showing."""
    for total in range(0, 720, 15):
        chosen = day.minutes_for(ClockTime(total), now=20 * 60)
        assert chosen % 720 == total


def test_without_a_hint_the_answer_is_deterministic(day):
    assert day.at(ClockTime.of(7, 0)).id == day.at(ClockTime.of(7, 0)).id
    assert day.at(ClockTime.of(7, 0)).id == "wake"
