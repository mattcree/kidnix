"""The routine strip's plan: eight names across a panel, none of them cut.

The bug this file is the fence round is in
``docs/design/screenshots/clock-play.png`` as it stood on 2026-08-23: the tiles
said **"Brea-kfast"** and **"Scho-ol"**. The strip had sized its tiles from the
*count* alone -- eight squares that fit across 1024 px -- and then asked each
name to fit in the ~70 px that left. "Breakfast" wants 105 px at the 18 pt
floor, there is no line inside a word to break, so Pango broke it between
characters and drew a hyphen to say so.

A cut word is a lie about the word, and it is a lie told to exactly the child
who cannot spot it: a pre-reader matching a shape to a sound
(``shell/kidnix_shell/labels.py``, and SYNTHESIS B4). So the name is measured
first and the tile is sized to hold it, and the tests here are about that
order.

Everything in this module is displayless: :func:`clock_time.activity._measurer`
falls back to :mod:`kidnix_shell.labels`' pure estimate when there is no Pango
context, and the estimate is deliberately a few percent *wide* -- it can say
"that does not fit" where Pango would have squeezed it in and must never say
the opposite, which is the direction a floor-planner has to be wrong in.
"""

from __future__ import annotations

import pytest

from conftest import HAVE_SDK

pytestmark = pytest.mark.skipif(not HAVE_SDK, reason="kidnix_activity is not importable here")


@pytest.fixture
def activity():
    """A :class:`ClockActivity` with no application and no window behind it.

    Nothing here builds a widget; the plan is arithmetic over the routine's
    names, which is exactly why it can be tested without a display.
    """
    from clock_time.activity import ClockActivity

    return ClockActivity(app=None)


def area_for(width: int, height: int = 800):
    """A :class:`ContentArea` for a panel of a stated size."""
    from kidnix_activity.metrics import ContentArea
    from kidnix_shell.metrics import ScreenOverride, detect_metrics

    return ContentArea.from_panel(detect_metrics(ScreenOverride(width, height, 96.0)))


# --- the measurement -------------------------------------------------------


def test_a_one_word_name_asks_for_the_whole_word() -> None:
    """There is nowhere in "Breakfast" for a line to break, so the box it needs
    is the width of the word. That number is the strip's constraint, and the
    old code's mistake was to treat it as negotiable."""
    from clock_time.activity import _label_box

    def measure(text: str, points: float) -> int:
        return len(text) * 10

    assert _label_box(measure, "Breakfast", 18.0) == 90


def test_a_two_word_name_asks_only_for_its_wider_half() -> None:
    """Two lines is the tile's budget, so "Wake up" needs "Wake", not
    "Wake up" -- which is why the strip has room for it at the tile floor."""
    from clock_time.activity import _label_box

    def measure(text: str, points: float) -> int:
        return len(text) * 10

    assert _label_box(measure, "Wake up", 18.0) == 40  # "Wake", not "Wake up"


def test_a_three_word_name_is_split_at_its_best_break() -> None:
    from clock_time.activity import _label_box

    def measure(text: str, points: float) -> int:
        return len(text) * 10

    # "Home from school": "Home from" | "school" is 90, "Home" | "from school"
    # is 110, the whole line is 160. The best two-line split wins.
    assert _label_box(measure, "Home from school", 18.0) == 90


def test_an_empty_name_asks_for_nothing() -> None:
    from clock_time.activity import _label_box

    assert _label_box(lambda text, points: 999, "   ", 18.0) == 0


# --- the plan ---------------------------------------------------------------


@pytest.mark.parametrize("width", [1024, 1280, 1366, 1920])
def test_every_shipped_name_gets_the_room_it_needs(activity, width: int) -> None:
    """The whole point. On every panel kidnix ships for, each tile's label box
    is at least as wide as that name needs at the size the strip settled on."""
    from clock_time.activity import _label_box, _measurer

    area = area_for(width)
    plan = activity._strip_plan(area, object())
    measure = _measurer(object())
    assert len(plan.widths) == len(activity.routine)
    for item, box in zip(activity.routine, plan.widths, strict=True):
        assert box >= _label_box(measure, item.name, plan.points), item.name


@pytest.mark.parametrize("width", [1280, 1366, 1920])
def test_the_whole_day_fits_across(activity, width: int) -> None:
    """Every tile, plus the gaps, inside the content box's margins -- proved on
    a machine with no display at all, against the pure estimate."""
    area = area_for(width)
    plan = activity._strip_plan(area, object())
    assert plan.fits
    assert plan.across(area) <= area.width - area.margin * 2


def test_the_narrowest_panel_is_the_one_the_estimate_cannot_settle(activity) -> None:
    """1024 px is the edge, and the estimate is wrong in the safe direction.

    :mod:`kidnix_shell.labels`' pure model is deliberately a few percent *wide*:
    "it may say 'that does not fit' when Pango would have squeezed it in, and
    must never say the opposite". Here it does exactly that -- it asks for about
    6% more than the row has, where Pango (``test_gtk_smoke.py``, which measures
    with the engine that will draw the text) fits the same eight names inside
    it. What matters is that the answer on both sides is the same *shape*: both
    floors reached, and not one word broken to get there.
    """
    area = area_for(1024)
    plan = activity._strip_plan(area, object())
    assert not plan.fits  # the estimate's answer, not the screen's
    assert plan.tile_mm == 20.0
    assert plan.points == pytest.approx(area.points(18.0))
    assert plan.across(area) < (area.width - area.margin * 2) * 1.10


@pytest.mark.parametrize("width", [1024, 1280, 1366, 1920])
def test_no_tile_is_under_the_twenty_millimetre_floor(activity, width: int) -> None:
    """ADR-0011. Widening a tile for a long word must never be paid for by
    taking another one below the floor -- the label box is a *minimum* over the
    tile size, never a replacement for it."""
    from clock_time.activity import STRIP_MM, TILE_CHROME_X

    area = area_for(width)
    plan = activity._strip_plan(area, object())
    assert plan.tile_mm >= STRIP_MM[-1] == 20.0
    for box in plan.widths:
        assert box + TILE_CHROME_X >= area.target(plan.tile_mm)
        assert area.mm_of(box + TILE_CHROME_X) >= 20.0 - 1e-9


@pytest.mark.parametrize("width", [1024, 1280, 1366, 1920])
def test_no_label_is_under_the_eighteen_point_floor(activity, width: int) -> None:
    """SYNTHESIS B4, and it is a floor the plan is not allowed to buy room
    with: type gives ground down to 18 pt and then stops."""
    area = area_for(width)
    plan = activity._strip_plan(area, object())
    assert area.points(18.0) <= plan.points <= area.points(20.0)


def test_the_strip_is_typographically_even(activity) -> None:
    """One point size for the row, not one per label. A strip where "Tea" is
    20 pt and "Breakfast" is 18 makes the two look like different kinds of
    thing, and they are not."""
    plan = activity._strip_plan(area_for(1280), object())
    assert isinstance(plan.points, float)  # one number, for all of them


def test_an_unknown_panel_constrains_nothing(activity) -> None:
    """A headless run or a compositor that reports no monitor. Zero means "do
    not constrain", exactly as it does everywhere else in ContentArea."""
    from kidnix_activity.metrics import ContentArea
    from kidnix_shell.metrics import Metrics

    plan = activity._strip_plan(ContentArea(metrics=Metrics(), width=0, height=0), object())
    assert plan.widths == (0,) * len(activity.routine)
    assert plan.fits


def test_a_long_name_widens_its_own_tile_and_not_the_others(activity) -> None:
    """The shape of the answer: the tile that has to carry a long word is the
    tile that grows. "Tea" does not pay for "Breakfast"."""
    from clock_time.routine import Routine, RoutineItem

    activity.routine = Routine.of(
        (
            RoutineItem("wake", "Wake up", 7 * 60),
            RoutineItem("breakfast", "Breakfast", 7 * 60 + 30),
            RoutineItem("tea", "Tea", 17 * 60 + 30),
        )
    )
    area = area_for(1280)
    plan = activity._strip_plan(area, object())
    _wake, breakfast, tea = plan.widths
    assert breakfast > tea
    assert plan.fits


def test_a_name_too_long_for_any_panel_is_reported_not_cut(activity) -> None:
    """The one case the geometry cannot solve. A grown-up may name a moment
    anything at all, and when the row will not hold it the plan says so --
    ``fits`` is False, the strip logs it, and the word is still whole. Nothing
    in this code path is allowed to reach for a hyphen."""
    from clock_time.routine import Routine, RoutineItem

    activity.routine = Routine.of(
        RoutineItem(f"m{n}", "Antidisestablishmentarianism", 7 * 60 + n) for n in range(8)
    )
    plan = activity._strip_plan(area_for(1024), object())
    assert not plan.fits
    assert plan.tile_mm == 20.0  # both floors reached
    assert plan.points == pytest.approx(18.0)
