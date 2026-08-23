"""How long is a minute -- the bands, the shape, and what is never said.

The sharpest constraint in the activity is SYNTHESIS **D6**: *"no fabricated
time pressure; countdown timers with no real stake are a named manipulative
pattern -- the session timer is real and nothing else should imitate it."* Most
of what keeps this the right side of that line is design rather than code, but
three things are assertable and are asserted here: no number ever reaches the
child, no band is praise or blame, and the shape is the shell's sun rather than
a second picture of one.
"""

from __future__ import annotations

import pytest

from clock_time.minute import (
    EARLY_BAND,
    LATE_BAND,
    LENGTHS,
    MAX_RADIUS_FRACTION,
    MIN_RADIUS_FRACTION,
    Length,
    Phase,
    Verdict,
    disc_geometry,
    verdict_for,
)

# --- the intervals ----------------------------------------------------------


def test_the_three_intervals_are_named_and_never_numbered():
    assert [length.words for length in LENGTHS] == [
        "half a minute",
        "a minute",
        "two minutes",
    ]


def test_no_interval_says_a_digit_out_loud():
    for length in LENGTHS:
        assert not any(character.isdigit() for character in length.words)
        assert not any(character.isdigit() for character in length.prompt)


def test_the_prompt_is_an_imperative_and_short(*_):
    """SYNTHESIS B5: audio-first instructions, at most two sentences."""
    for length in LENGTHS:
        assert length.prompt.startswith("Press stop")
        assert len(length.prompt.split()) <= 12


def test_the_intervals_are_in_order_shortest_first():
    assert [length.seconds for length in LENGTHS] == [30.0, 60.0, 120.0]


# --- the bands --------------------------------------------------------------


@pytest.mark.parametrize(
    ("elapsed", "expected"),
    [
        (0.0, Verdict.EARLY),
        (1.0, Verdict.EARLY),
        (30.0, Verdict.EARLY),
        (44.0, Verdict.EARLY),
        (45.0, Verdict.JUST_RIGHT),
        (60.0, Verdict.JUST_RIGHT),
        (75.0, Verdict.JUST_RIGHT),
        (75.1, Verdict.LATE),
        (120.0, Verdict.LATE),
        (600.0, Verdict.LATE),
    ],
)
def test_the_bands_for_a_minute(elapsed, expected):
    assert verdict_for(elapsed, Length.MINUTE) is expected


def test_the_boundaries_are_inclusive_at_the_generous_end_on_both_sides():
    """Exactly three-quarters is right; exactly a quarter over is too."""
    assert verdict_for(EARLY_BAND * 60.0, Length.MINUTE) is Verdict.JUST_RIGHT
    assert verdict_for(LATE_BAND * 60.0, Length.MINUTE) is Verdict.JUST_RIGHT


def test_the_bands_scale_with_the_interval():
    assert verdict_for(22.5, Length.HALF_MINUTE) is Verdict.JUST_RIGHT
    assert verdict_for(22.5, Length.MINUTE) is Verdict.EARLY
    assert verdict_for(150.0, Length.TWO_MINUTES) is Verdict.JUST_RIGHT


def test_a_negative_or_zero_interval_is_early_rather_than_an_exception():
    """A monotonic clock that went backwards must not throw at a five-year-old."""
    assert verdict_for(-5.0, Length.MINUTE) is Verdict.EARLY
    assert verdict_for(0.0, Length.TWO_MINUTES) is Verdict.EARLY


def test_the_bands_are_wide_because_duration_judgement_at_this_age_is_not():
    """02 section 2.8. A band a five-year-old lands in only by luck would be
    measuring luck."""
    assert EARLY_BAND <= 0.75
    assert LATE_BAND >= 1.25


# --- what is said about them ------------------------------------------------


def test_there_are_exactly_three_and_none_of_them_is_a_number():
    assert len(list(Verdict)) == 3
    for verdict in Verdict:
        assert not any(character.isdigit() for character in verdict.words)


def test_the_words_are_the_ones_the_brief_asked_for():
    assert Verdict.EARLY.words == "a bit early"
    assert Verdict.JUST_RIGHT.words == "just right!"
    assert Verdict.LATE.words == "a bit late"


def test_a_sentence_names_what_was_being_judged_and_carries_no_digit():
    for verdict in Verdict:
        for length in LENGTHS:
            sentence = verdict.sentence(length)
            assert length.words in sentence
            assert not any(character.isdigit() for character in sentence)


@pytest.mark.parametrize(
    "banned",
    ["score", "point", "star", "badge", "level", "streak", "well done", "wrong", "fail"],
)
def test_no_verdict_carries_a_reward_or_a_judgement(banned):
    """SUITE section 5 / SYNTHESIS E1. "A bit early" describes the interval,
    not the child."""
    for verdict in Verdict:
        for length in LENGTHS:
            assert banned not in verdict.sentence(length).lower()


# --- the phases -------------------------------------------------------------


def test_the_disc_is_not_drawn_while_the_child_is_judging():
    """The whole point. A disc that depleted over exactly the interval being
    guessed would be showing them the answer."""
    assert not Phase.GUESSING.draws_disc


def test_the_disc_is_drawn_when_it_is_explaining_or_demonstrating():
    assert Phase.SHOWING.draws_disc
    assert Phase.RESULT.draws_disc


def test_there_are_four_phases_and_no_dialogue_between_them():
    assert {phase.value for phase in Phase} == {"ready", "showing", "guessing", "result"}


# --- the shape --------------------------------------------------------------


def test_the_disc_never_travels_sideways():
    """09 Q1, Tillman et al. 2018: most preschoolers do not represent time as a
    directional spatial line. Depletion is size and height, never travel."""
    xs = {disc_geometry(spent / 10.0, 400, 300).centre_x for spent in range(11)}
    assert xs == {200.0}


def test_the_disc_shrinks_as_the_interval_goes():
    radii = [disc_geometry(spent / 10.0, 400, 300).radius for spent in range(11)]
    assert radii == sorted(radii, reverse=True)


def test_the_disc_sinks_as_the_interval_goes():
    heights = [disc_geometry(spent / 10.0, 400, 300).centre_y for spent in range(11)]
    assert heights == sorted(heights)


def test_the_disc_never_vanishes():
    """"A sun that vanishes is a sun that broke" (kidnix_shell.sun)."""
    assert disc_geometry(1.0, 400, 300).radius == pytest.approx(300 * MIN_RADIUS_FRACTION)
    assert disc_geometry(1.0, 400, 300).radius > 0


def test_a_full_disc_is_the_biggest_it_gets():
    assert disc_geometry(0.0, 400, 300).radius == pytest.approx(300 * MAX_RADIUS_FRACTION)


def test_the_disc_ends_on_the_horizon_it_sank_to():
    geometry = disc_geometry(1.0, 400, 300)
    assert geometry.centre_y == pytest.approx(geometry.horizon_y)


def test_the_ghost_is_where_it_started_so_the_loss_is_visible():
    start = disc_geometry(0.0, 400, 300)
    end = disc_geometry(1.0, 400, 300)
    assert end.start_radius == pytest.approx(start.radius)
    assert end.start_centre_y == pytest.approx(start.centre_y)


@pytest.mark.parametrize("spent", [-5.0, -0.001, 1.001, 99.0, float("inf")])
def test_a_clock_that_jumped_is_clamped_rather_than_thrown_at_a_child(spent):
    geometry = disc_geometry(spent, 400, 300)
    assert 300 * MIN_RADIUS_FRACTION <= geometry.radius <= 300 * MAX_RADIUS_FRACTION
