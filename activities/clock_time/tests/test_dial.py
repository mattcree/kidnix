"""Where a tap lands, and that the drawing actually draws.

``cairo`` imports with no display, so the picture is testable rather than
merely reviewable: these render to an image surface and look at the pixels.
That is the point of keeping the drawing out of the GTK module -- a screenshot
somebody eyeballs once is not a test.
"""

from __future__ import annotations

import cairo
import pytest

from clock_time.dial import (
    CARD_SIZE,
    INK,
    PAPER,
    SKY_COLOURS,
    draw_dial,
    draw_disc,
    draw_ghost,
    draw_sky,
    hand_tip,
    render_card,
    rgb,
    total_from_point,
)
from clock_time.minute import disc_geometry
from clock_time.routine import Sky
from clock_time.words import ClockTime, Mode


def surface(size: int = 300) -> tuple[cairo.ImageSurface, cairo.Context]:
    image = cairo.ImageSurface(cairo.FORMAT_ARGB32, size, size)
    return image, cairo.Context(image)


def painted(image: cairo.ImageSurface) -> int:
    """How many pixels are not transparent. "Did anything get drawn?"."""
    data = bytes(image.get_data())
    return sum(1 for index in range(3, len(data), 4) if data[index] != 0)


# --- a tap on the rim -------------------------------------------------------


@pytest.mark.parametrize(
    ("dx", "dy", "expected_minute"),
    [
        (0.0, -100.0, 0),
        (100.0, 0.0, 15),
        (0.0, 100.0, 30),
        (-100.0, 0.0, 45),
    ],
)
def test_the_four_quarters_of_the_face_are_where_they_look(dx, dy, expected_minute):
    landed = total_from_point(dx, dy, ClockTime.of(3, 0), Mode.Y2)
    assert landed.minute == expected_minute


def test_a_tap_at_twelve_from_ten_to_four_reads_as_four_o_clock():
    """The hands take the short way round, as a hand pushed by a finger would."""
    landed = total_from_point(0.0, -100.0, ClockTime.of(3, 50), Mode.Y1)
    assert landed == ClockTime.of(4, 0)


def test_a_tap_at_twelve_from_ten_past_three_reads_as_three_o_clock():
    landed = total_from_point(0.0, -100.0, ClockTime.of(3, 10), Mode.Y1)
    assert landed == ClockTime.of(3, 0)


def test_a_tap_at_six_is_half_past_the_hour_you_were_in():
    landed = total_from_point(0.0, 100.0, ClockTime.of(3, 10), Mode.Y1)
    assert landed == ClockTime.of(3, 30)


def test_a_tap_in_year_one_never_lands_between_the_two_positions():
    for degrees in range(0, 360, 7):
        import math

        radians = math.radians(degrees)
        landed = total_from_point(
            100 * math.sin(radians), -100 * math.cos(radians), ClockTime.of(3, 0), Mode.Y1
        )
        assert landed.minute in (0, 30)


def test_a_tap_in_year_two_always_lands_on_a_five_minute_mark():
    for degrees in range(0, 360, 3):
        import math

        radians = math.radians(degrees)
        landed = total_from_point(
            100 * math.sin(radians), -100 * math.cos(radians), ClockTime.of(7, 0), Mode.Y2
        )
        assert landed.minute % 5 == 0


def test_a_tap_on_the_exact_centre_leaves_the_clock_alone():
    """There is no angle there, and guessing one would move the hands at random."""
    before = ClockTime.of(3, 30)
    assert total_from_point(0.0, 0.0, before, Mode.Y2) == before


def test_distance_from_the_centre_does_not_matter_only_the_angle():
    near = total_from_point(0.0, -5.0, ClockTime.of(3, 0), Mode.Y2)
    far = total_from_point(0.0, -500.0, ClockTime.of(3, 0), Mode.Y2)
    assert near == far


# --- the hands --------------------------------------------------------------


def test_a_hand_at_twelve_points_straight_up():
    x, y = hand_tip((100.0, 100.0), 50.0, 0.0)
    assert x == pytest.approx(100.0)
    assert y == pytest.approx(50.0)


def test_a_hand_at_three_points_right():
    x, y = hand_tip((100.0, 100.0), 50.0, 90.0)
    assert x == pytest.approx(150.0)
    assert y == pytest.approx(100.0)


# --- the drawing ------------------------------------------------------------


def test_a_colour_parses_to_three_floats():
    assert rgb(PAPER) == pytest.approx((0xFB / 255, 0xF7 / 255, 0xEF / 255))
    assert rgb(INK) == pytest.approx((0x16 / 255, 0x18 / 255, 0x1D / 255))


def test_the_dial_draws_something():
    image, ctx = surface()
    radius = draw_dial(ctx, 300, 300, ClockTime.of(3, 30), mode=Mode.Y1)
    assert radius > 0
    assert painted(image) > 300 * 300 * 0.5


def test_a_dial_with_no_room_draws_nothing_rather_than_throwing():
    image, ctx = surface(4)
    assert draw_dial(ctx, 4, 4, ClockTime.of(3, 30)) <= 2
    assert painted(image) == 0


def test_moving_the_hands_changes_the_picture():
    first, ctx = surface()
    draw_dial(ctx, 300, 300, ClockTime.of(3, 0), mode=Mode.Y1)
    second, ctx2 = surface()
    draw_dial(ctx2, 300, 300, ClockTime.of(3, 30), mode=Mode.Y1)
    assert bytes(first.get_data()) != bytes(second.get_data())


def test_year_two_draws_minute_ticks_and_year_one_does_not():
    """A Year 1 face has nowhere on it that is not o'clock or half past, so
    sixty ticks would be decoration that looks like information (05 2c)."""
    one, ctx = surface()
    draw_dial(ctx, 300, 300, ClockTime.of(3, 0), mode=Mode.Y1)
    two, ctx2 = surface()
    draw_dial(ctx2, 300, 300, ClockTime.of(3, 0), mode=Mode.Y2)
    assert bytes(one.get_data()) != bytes(two.get_data())


@pytest.mark.parametrize("sky", list(Sky))
def test_every_sky_paints_the_whole_ground(sky):
    image, ctx = surface()
    draw_sky(ctx, 300, 300, sky)
    assert painted(image) == 300 * 300


def test_the_four_skies_are_four_different_pictures():
    seen = set()
    for sky in Sky:
        image, ctx = surface(40)
        draw_sky(ctx, 40, 40, sky)
        seen.add(bytes(image.get_data()))
    assert len(seen) == len(Sky)


def test_every_sky_has_a_colour_pair():
    assert set(SKY_COLOURS) == set(Sky)
    for top, bottom in SKY_COLOURS.values():
        assert len(rgb(top)) == 3
        assert len(rgb(bottom)) == 3


def test_the_disc_draws_and_the_ghost_draws_less_of_it():
    full, ctx = surface()
    draw_disc(ctx, 300, 300, disc_geometry(0.0, 300, 300))
    ghost, ctx2 = surface()
    draw_ghost(ctx2, 300, 300, disc_geometry(0.0, 300, 300))
    assert painted(full) > painted(ghost) > 0


def test_the_dial_reads_on_the_night_sky_as_well_as_the_morning_one():
    """The rings are stroked twice, ink inside and paper outside, precisely so
    that a dark ground does not swallow the edge."""
    for sky in Sky:
        image, ctx = surface()
        draw_sky(ctx, 300, 300, sky)
        assert draw_dial(ctx, 300, 300, ClockTime.of(3, 30)) > 0
        assert painted(image) == 300 * 300


# --- the Journal card -------------------------------------------------------


def test_a_card_is_written_and_is_a_png(tmp_path):
    path = render_card(tmp_path / "clock.png", ClockTime.of(3, 30))
    assert path.is_file()
    assert path.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"


def test_the_card_is_the_size_the_journal_thumbnails_from(tmp_path):
    path = render_card(tmp_path / "clock.png", ClockTime.of(3, 30))
    image = cairo.ImageSurface.create_from_png(str(path))
    assert (image.get_width(), image.get_height()) == (CARD_SIZE, CARD_SIZE)


def test_the_card_makes_its_own_directory(tmp_path):
    path = render_card(tmp_path / "deep" / "down" / "clock.png", ClockTime.of(6, 0))
    assert path.is_file()


def test_two_different_times_make_two_different_cards(tmp_path):
    one = render_card(tmp_path / "a.png", ClockTime.of(3, 0)).read_bytes()
    two = render_card(tmp_path / "b.png", ClockTime.of(3, 30)).read_bytes()
    assert one != two


def test_the_sky_is_in_the_card_because_the_card_is_the_record(tmp_path):
    day = render_card(tmp_path / "day.png", ClockTime.of(3, 0), sky=Sky.AFTERNOON)
    night = render_card(tmp_path / "night.png", ClockTime.of(3, 0), sky=Sky.NIGHT)
    assert day.read_bytes() != night.read_bytes()
