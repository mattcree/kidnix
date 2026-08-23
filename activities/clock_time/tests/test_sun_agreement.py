"""One sun, everywhere. The activity's disc must be the shell's, not a cousin.

The panel's ruling of 2026-08-23 (``kidnix_shell/band.py``): the band drew a
disc sinking behind a horizon, the S5 screen drew a bright midday sun with rays
and ``kidnix-finish.svg`` drew a third, on screens a child sees within four
minutes. There is now one drawing.

:mod:`clock_time.minute` restates the geometry rather than importing it,
because the pure half of this activity has to be importable and testable on a
machine with no shell and no GTK at all. This file is what stops the two
drifting: wherever ``kidnix_shell`` *is* importable it re-derives every number
from the original and fails on any difference. It is the same trick
``sounds_and_words`` uses against the SDK's ``Paths``.
"""

from __future__ import annotations

import pytest

from conftest import HAVE_SHELL

pytestmark = pytest.mark.skipif(
    not HAVE_SHELL, reason="kidnix_shell is not importable here"
)


def test_the_fractions_are_the_shells_own():
    from kidnix_shell import sun

    from clock_time import minute

    assert minute.HORIZON_FRACTION == sun.HORIZON_FRACTION
    assert minute.MAX_RADIUS_FRACTION == sun.MAX_RADIUS_FRACTION
    assert minute.MIN_RADIUS_FRACTION == sun.MIN_RADIUS_FRACTION
    assert minute.TOP_PAD_FRACTION == sun.TOP_PAD_FRACTION


def test_the_colours_are_the_shells_own():
    from kidnix_shell import sun

    from clock_time import minute

    assert minute.SUN_FILL == sun.SUN_FILL
    assert minute.SUN_EDGE_INNER == sun.SUN_EDGE_INNER
    assert minute.SUN_EDGE_OUTER == sun.SUN_EDGE_OUTER
    assert minute.SUN_EDGE_INNER_PX == sun.SUN_EDGE_INNER_PX
    assert minute.SUN_EDGE_OUTER_PX == sun.SUN_EDGE_OUTER_PX


@pytest.mark.parametrize("spent", [0.0, 0.1, 0.25, 0.5, 0.75, 0.9, 1.0, -1.0, 2.0])
@pytest.mark.parametrize(("width", "height"), [(400, 300), (1280, 96), (64, 64)])
def test_the_geometry_agrees_at_every_size_and_every_fraction(spent, width, height):
    from kidnix_shell.sun import sun_geometry

    from clock_time.minute import disc_geometry

    ours = disc_geometry(spent, width, height)
    theirs = sun_geometry(spent, width, height)
    assert ours.centre_x == pytest.approx(theirs.centre_x)
    assert ours.centre_y == pytest.approx(theirs.centre_y)
    assert ours.radius == pytest.approx(theirs.radius)
    assert ours.horizon_y == pytest.approx(theirs.horizon_y)
    assert ours.start_centre_y == pytest.approx(theirs.start_centre_y)
    assert ours.start_radius == pytest.approx(theirs.start_radius)


def test_the_disc_never_warms_because_nothing_here_is_ending():
    """``SUN_WARM_FILL`` is the *session's* last window -- "the light has
    changed" (08 section 4.6). Nothing in this activity ends, so the activity
    has no business borrowing that signal and does not."""
    from clock_time import minute

    assert not hasattr(minute, "SUN_WARM_FILL")
