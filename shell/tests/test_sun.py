"""The sun's geometry (spec 7b): it shrinks and sinks, and it does not travel.

09 section 1: the directional mental timeline is not reliably available at
five (Tillman et al. 2018), so left-to-right position is a weak carrier and a
visibly shrinking quantity is a strong one. These tests pin exactly that --
that ``x`` never moves, that size and height fall monotonically with the time
left, and that a clock which jumped cannot throw at a child.
"""

from __future__ import annotations

from itertools import pairwise

import pytest

from kidnix_shell.sun import (
    HORIZON_FRACTION,
    MAX_RADIUS_FRACTION,
    MIN_RADIUS_FRACTION,
    sun_geometry,
)

WIDTH = 320
HEIGHT = 96

STEPS = [step / 20 for step in range(21)]


def test_the_sun_never_moves_sideways() -> None:
    """The whole point of the redesign. One x, for every fraction, forever."""
    xs = {sun_geometry(spent, WIDTH, HEIGHT).centre_x for spent in STEPS}
    assert xs == {WIDTH / 2.0}


def test_it_is_still_centred_on_a_different_sized_band() -> None:
    for width in (120, 320, 640, 1280):
        assert sun_geometry(0.5, width, HEIGHT).centre_x == width / 2.0


def test_the_sun_shrinks_as_the_session_goes() -> None:
    radii = [sun_geometry(spent, WIDTH, HEIGHT).radius for spent in STEPS]
    assert radii == sorted(radii, reverse=True)
    assert radii[0] > radii[-1]
    # Strictly, not just non-increasing: every minute has to show.
    assert all(later < earlier for earlier, later in pairwise(radii))


def test_the_sun_sinks_as_the_session_goes() -> None:
    """Bigger y is further down the widget."""
    heights = [sun_geometry(spent, WIDTH, HEIGHT).centre_y for spent in STEPS]
    assert heights == sorted(heights)
    assert all(later > earlier for earlier, later in pairwise(heights))


def test_a_full_session_starts_big_and_high() -> None:
    start = sun_geometry(0.0, WIDTH, HEIGHT)
    assert start.radius == pytest.approx(HEIGHT * MAX_RADIUS_FRACTION)
    assert start.centre_y == start.start_centre_y
    assert start.centre_y < start.horizon_y


def test_the_hard_stop_puts_the_sun_on_the_horizon() -> None:
    end = sun_geometry(1.0, WIDTH, HEIGHT)
    assert end.centre_y == pytest.approx(end.horizon_y)
    assert end.radius == pytest.approx(HEIGHT * MIN_RADIUS_FRACTION)


def test_the_sun_never_vanishes() -> None:
    """A sun that disappears is a sun that broke -- and it is still a target."""
    for spent in STEPS:
        assert sun_geometry(spent, WIDTH, HEIGHT).radius > 0


def test_the_horizon_leaves_ground_under_it() -> None:
    geometry = sun_geometry(0.5, WIDTH, HEIGHT)
    assert geometry.horizon_y == pytest.approx(HEIGHT * HORIZON_FRACTION)
    assert geometry.horizon_y < HEIGHT


def test_the_start_outline_is_where_the_sun_began() -> None:
    """It is the "how much has gone" mark, so it must not move either."""
    outlines = {
        (
            sun_geometry(spent, WIDTH, HEIGHT).start_centre_y,
            sun_geometry(spent, WIDTH, HEIGHT).start_radius,
        )
        for spent in STEPS
    }
    assert len(outlines) == 1


def test_a_clock_that_jumped_lands_on_a_sun_rather_than_an_exception() -> None:
    for nonsense in (-5.0, -0.001, 1.0001, 42.0, float("inf")):
        geometry = sun_geometry(nonsense, WIDTH, HEIGHT)
        assert 0 < geometry.radius <= HEIGHT * MAX_RADIUS_FRACTION
        assert geometry.centre_y <= geometry.horizon_y


def test_a_squashed_band_still_fits_its_sun() -> None:
    """The band is clamped to 80-128 px; the sun has to live inside whatever
    is left after the CSS chrome, on every panel we ship for."""
    for height in (24, 40, 60, 76, 108):
        geometry = sun_geometry(0.0, WIDTH, height)
        assert geometry.centre_y - geometry.radius >= 0
        assert geometry.horizon_y <= height
