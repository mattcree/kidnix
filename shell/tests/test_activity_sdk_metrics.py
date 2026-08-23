"""The content area: millimetres for the rectangle an activity is given.

Every panel in ``docs/plan/HARDWARE.md`` is walked, because the floors are the
contract and a floor that holds on one monitor is not a floor.
"""

from __future__ import annotations

from dataclasses import replace

import pytest

from kidnix_activity.metrics import BIG_BUTTON_MM, ContentArea
from kidnix_shell.metrics import GAP_FLOOR_MM, MIN_TARGET_MM, Metrics

#: (width, height, dpi) -- the same rows ``tests/test_metrics.py`` walks.
PANELS = [
    (1280, 800, 96.0),
    (1280, 800, 102.0),
    (1280, 800, 118.0),
    (1366, 768, 96.0),
    (1920, 1080, 96.0),
    (2560, 1440, 118.0),
    (1024, 600, 96.0),
]


def panel(width: int, height: int, dpi: float) -> Metrics:
    return Metrics.for_screen(width, height, dpi=dpi)


# --- the rectangle ---------------------------------------------------------


@pytest.mark.parametrize(("width", "height", "dpi"), PANELS)
def test_the_content_area_is_the_panel_minus_the_band(width: int, height: int, dpi: float) -> None:
    metrics = panel(width, height, dpi)
    area = ContentArea.from_panel(metrics)
    assert area.width == width
    assert area.height == height - metrics.band_window_height
    assert area.height > 0


def test_the_band_is_not_subtracted_twice() -> None:
    """The trap the wrapper exists to make impossible.

    ``Metrics.content_height`` already takes the band off ``screen_height``, so
    a ``Metrics`` built with ``screen_height = content_height`` answers the
    second question differently from the first. ``ContentArea`` cannot: it
    holds the panel's metrics and the rectangle separately.
    """
    metrics = panel(1280, 800, 102.0)
    area = ContentArea.from_panel(metrics)
    naive = replace(metrics, screen_height=metrics.content_height)
    assert naive.content_height < area.height
    assert area.height == 800 - metrics.band_window_height


def test_an_unknown_screen_constrains_nothing() -> None:
    area = ContentArea.from_panel(Metrics())
    assert area.known is False
    assert area.fits(10_000, 10_000) is True
    assert area.columns_for(cell=100, count=7) == 7


def test_a_known_screen_says_what_does_not_fit() -> None:
    area = ContentArea.from_panel(panel(1280, 800, 96.0))
    assert area.fits(1280, area.height) is True
    assert area.fits(1281, area.height) is False
    assert area.fits(1280, area.height + 1) is False


# --- the floors ------------------------------------------------------------


@pytest.mark.parametrize(("width", "height", "dpi"), PANELS)
def test_every_target_clears_twenty_millimetres(width: int, height: int, dpi: float) -> None:
    area = ContentArea.from_panel(panel(width, height, dpi))
    assert area.mm_of(area.min_target) >= MIN_TARGET_MM - 0.05
    assert area.mm_of(area.big_button) >= MIN_TARGET_MM - 0.05
    assert area.mm_of(area.picture_tile) >= MIN_TARGET_MM - 0.05


@pytest.mark.parametrize(("width", "height", "dpi"), PANELS)
def test_the_gap_never_falls_under_eight_millimetres(width: int, height: int, dpi: float) -> None:
    area = ContentArea.from_panel(panel(width, height, dpi))
    assert area.mm_of(area.gap) >= GAP_FLOOR_MM - 0.05


@pytest.mark.parametrize(("width", "height", "dpi"), PANELS)
def test_child_text_never_falls_under_eighteen_points(width: int, height: int, dpi: float) -> None:
    area = ContentArea.from_panel(panel(width, height, dpi))
    assert area.points(12.0) >= 18.0
    assert area.prompt_points >= 18.0


def test_a_big_button_prefers_forty_millimetres_where_there_is_room() -> None:
    area = ContentArea.from_panel(panel(1920, 1080, 96.0))
    assert area.mm_of(area.big_button) >= BIG_BUTTON_MM - 0.5


def test_the_margin_is_the_gap() -> None:
    area = ContentArea.from_panel(panel(1280, 800, 96.0))
    assert area.margin == area.gap


# --- laying a row out ------------------------------------------------------


def test_columns_for_counts_the_gaps_between_cells() -> None:
    area = ContentArea(
        metrics=Metrics(dpi=96.0, screen_width=1000, screen_height=800), width=1000, height=700
    )
    # Four 100 px cells with three 100 px gaps is 700; five would be 900; six
    # would be 1100 and does not fit.
    assert area.columns_for(cell=100, count=10, gap=100) == 5


def test_columns_for_never_returns_zero() -> None:
    area = ContentArea(
        metrics=Metrics(dpi=96.0, screen_width=10, screen_height=10), width=10, height=10
    )
    assert area.columns_for(cell=400, count=3) == 1


def test_columns_for_is_capped_by_what_was_asked_for() -> None:
    area = ContentArea.from_panel(panel(1920, 1080, 96.0))
    assert area.columns_for(cell=50, count=3) == 3


def test_nothing_to_lay_out_is_no_columns() -> None:
    area = ContentArea.from_panel(panel(1280, 800, 96.0))
    assert area.columns_for(cell=50, count=0) == 0


# --- the log line ----------------------------------------------------------


def test_describe_carries_the_millimetres_not_just_the_pixels() -> None:
    line = ContentArea.from_panel(panel(1280, 800, 102.0)).describe()
    assert "mm" in line
    assert "band" in line
    assert "1280x" in line


def test_detect_works_with_no_display_at_all() -> None:
    """A build container. The design values are the answer, and nothing raises."""
    area = ContentArea.detect()
    assert area.min_target > 0
    assert area.prompt_points >= 18.0
