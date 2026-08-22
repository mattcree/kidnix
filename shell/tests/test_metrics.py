"""Sizes are specified in millimetres (SYNTHESIS A1); check they come out that way."""

from __future__ import annotations

import pytest

from kidnix_shell.metrics import (
    BAND_CHROME_PX,
    BAND_MAX_PX,
    BAND_MIN_PX,
    DEFAULT_DPI,
    MIN_TARGET_MM,
    PRIMARY_TILE_MM,
    Metrics,
    ScreenOverride,
    detect_metrics,
    override_from_env,
    parse_screen,
)


def test_default_is_96_dpi() -> None:
    assert Metrics().dpi == DEFAULT_DPI
    assert round(Metrics().px_per_mm, 3) == 3.780


def test_millimetres_never_round_down() -> None:
    metrics = Metrics()
    # 18 mm at 96 dpi is 68.03 px; undersizing a target is the one error that
    # matters, so it rounds up.
    assert metrics.mm(MIN_TARGET_MM) == 69


def test_tile_is_at_least_forty_millimetres_on_a_dense_display() -> None:
    dense = Metrics(dpi=192)
    assert dense.tile_size >= dense.mm(PRIMARY_TILE_MM)
    assert dense.tile_size / dense.px_per_mm >= PRIMARY_TILE_MM


def test_tile_uses_the_design_pixel_floor_at_96_dpi() -> None:
    # 160 design px is 42.3 mm at 96 dpi, so the design value wins.
    assert Metrics().tile_size == 160


def test_monitor_geometry_gives_real_dpi() -> None:
    # A 1920 px wide panel that is 344 mm across is a 14" 1080p ThinkPad.
    metrics = Metrics.from_monitor(1920, 344)
    assert 140 < metrics.dpi < 145


def test_implausible_monitor_geometry_falls_back() -> None:
    for width_px, width_mm in ((1920, 0), (0, 300), (1920, 10), (100, 900)):
        assert Metrics.from_monitor(width_px, width_mm).dpi == DEFAULT_DPI


def test_scale_factor_is_divided_out_of_logical_pixels() -> None:
    # A HiDPI panel: GTK reports 1920 *logical* px across 344 mm at scale 2, so
    # the panel is really 3840 px wide (283 physical dpi). GTK lays out in
    # logical pixels, so Metrics stores the logical density -- half of that.
    metrics = Metrics.from_monitor(1920, 344, scale_factor=2)
    assert metrics.scale_factor == 2
    assert 140 < metrics.dpi < 143
    # A 40 mm tile is then about 223 logical px, twice the 96 dpi value.
    assert metrics.tile_size / metrics.px_per_mm >= PRIMARY_TILE_MM


def test_every_child_facing_size_clears_the_minimum_target() -> None:
    for dpi in (96, 120, 141, 192, 220):
        metrics = Metrics(dpi=dpi)
        for size in (metrics.tile_size, metrics.card_size, metrics.avatar_size):
            assert size >= metrics.min_target


def test_gap_is_at_least_eight_millimetres() -> None:
    metrics = Metrics()
    assert metrics.gap / metrics.px_per_mm >= 8.0


def test_detect_metrics_never_raises_without_a_display() -> None:
    assert isinstance(detect_metrics(), Metrics)


# --- fitting the screen (v0.1.1) ----------------------------------------
#
# The first real boot rendered a layout ~6% larger than the 1280x800 panel and
# clipped the band off the top of the screen
# (docs/design/screenshots/boot-home.png). These are the tests that stop that
# happening again on any panel we claim to support.

#: (width, height, dpi, scale_factor) -- the panels v0.1.1 must fit.
SCREENS = [
    (1280, 800, 96.0, 1),
    (1280, 800, 102.0, 1),  # the qcow2 VM's virtio panel: the one that clipped
    (1280, 800, 118.0, 1),  # this development host's density on a small panel
    (1366, 768, 96.0, 1),
    (1920, 1080, 96.0, 1),
    (1920, 1080, 141.0, 2),  # 3840x2160 at scale 2: GTK lays out in logical px
    (2560, 1440, 118.0, 1),
]


@pytest.mark.parametrize(("width", "height", "dpi", "scale"), SCREENS)
def test_the_layout_never_exceeds_the_monitor(
    width: int, height: int, dpi: float, scale: int
) -> None:
    metrics = Metrics.for_screen(width, height, dpi=dpi, scale_factor=scale)
    needed_width, needed_height = metrics.required_size()
    assert needed_width <= width, metrics.describe()
    assert needed_height <= height, metrics.describe()


@pytest.mark.parametrize(("width", "height", "dpi", "scale"), SCREENS)
def test_the_band_stays_inside_the_ruling_clamp(
    width: int, height: int, dpi: float, scale: int
) -> None:
    """Spec 7a: the band scales with everything else, clamped to 80-128 px."""
    metrics = Metrics.for_screen(width, height, dpi=dpi, scale_factor=scale)
    assert BAND_MIN_PX <= metrics.band_height <= BAND_MAX_PX


@pytest.mark.parametrize(("width", "height", "dpi", "scale"), SCREENS)
def test_a_band_button_fits_inside_the_band(
    width: int, height: int, dpi: float, scale: int
) -> None:
    """The v0.1.0 bug in one assertion: the buttons were taller than the band."""
    metrics = Metrics.for_screen(width, height, dpi=dpi, scale_factor=scale)
    assert metrics.band_target + BAND_CHROME_PX <= metrics.band_height
    assert metrics.band_small_target <= metrics.band_target


@pytest.mark.parametrize(("width", "height", "dpi", "scale"), SCREENS)
def test_every_screen_still_gets_a_touchable_tile(
    width: int, height: int, dpi: float, scale: int
) -> None:
    """Fitting may shrink a tile below 40 mm; it may not make it unusable."""
    metrics = Metrics.for_screen(width, height, dpi=dpi, scale_factor=scale)
    assert metrics.mm_of(metrics.tile_size) >= 25.0, metrics.describe()
    assert metrics.tile_size >= 120


def test_a_big_screen_needs_no_shrinking_at_all() -> None:
    for width, height, dpi in ((1920, 1080, 96.0), (2560, 1440, 118.0)):
        metrics = Metrics.for_screen(width, height, dpi=dpi)
        assert metrics.fit == 1.0
        assert metrics.tile_size == Metrics(dpi=dpi).tile_size
        assert (metrics.columns, metrics.rows) == (4, 3)


def test_the_panel_that_clipped_is_now_shrunk() -> None:
    """1280x800 at 102 dpi: the exact geometry of the first real boot."""
    metrics = Metrics.for_screen(1280, 800, dpi=102.0)
    assert metrics.fit < 1.0
    assert metrics.required_size() <= (1280, 800)
    # Still a 4 x 3 grid of twelve: the spec's Home is intact, just smaller.
    assert (metrics.columns, metrics.rows) == (4, 3)
    assert metrics.per_page == 12


def test_the_physical_panel_decides_the_layout_not_the_reported_dpi() -> None:
    """Same 1280x800 panel, three claimed densities, near-identical pixels.

    This is the point of fitting: mm-based sizing chooses how big things are
    *in millimetres*, and the panel chooses how many pixels that can be.
    """
    sizes = {Metrics.for_screen(1280, 800, dpi=dpi).tile_size for dpi in (96.0, 102.0, 118.0)}
    assert max(sizes) - min(sizes) <= 4


def test_a_small_screen_gets_fewer_bigger_tiles() -> None:
    metrics = Metrics.for_screen(1024, 600, dpi=96.0)
    assert metrics.required_size() <= (1024, 600)
    assert metrics.rows < 3
    assert metrics.per_page == metrics.columns * metrics.rows


def test_an_unknown_screen_keeps_the_design_values() -> None:
    metrics = Metrics()
    assert metrics.fit == 1.0
    assert metrics.fits()  # nothing to fit into
    assert metrics.tile_size == 160


def test_the_fit_factor_shrinks_everything_together() -> None:
    full = Metrics(dpi=96.0)
    half = Metrics(dpi=96.0, fit=0.5)
    assert half.tile_size <= full.tile_size // 2 + 1
    assert half.gap <= full.gap // 2 + 1
    assert half.points(24) == 12.0


def test_points_scale_with_the_layout() -> None:
    """theme.css states points; a shrunk layout has to restate them (theme.py)."""
    assert Metrics().points(24) == 24.0
    assert Metrics(fit=0.8).points(24) == 19.2


# --- the debug override --------------------------------------------------


def test_parsing_a_screen_override() -> None:
    assert parse_screen("1280x800@102") == ScreenOverride(1280, 800, 102.0)
    assert parse_screen("1920x1080") == ScreenOverride(1920, 1080, None)
    assert parse_screen(" 1366 x 768 @ 96 ") == ScreenOverride(1366, 768, 96.0)


@pytest.mark.parametrize("text", ["", "1280", "1280*800", "0x800", "1280x800@", "wide"])
def test_a_nonsense_screen_override_is_rejected(text: str) -> None:
    with pytest.raises(ValueError):
        parse_screen(text)


def test_the_environment_can_force_a_screen_or_a_density() -> None:
    assert override_from_env({"KIDNIX_SCREEN": "1280x800@102"}) == ScreenOverride(1280, 800, 102.0)
    assert override_from_env({"KIDNIX_FORCE_DPI": "118"}) == ScreenOverride(0, 0, 118.0)
    assert override_from_env({"KIDNIX_SCREEN": "1280x800", "KIDNIX_FORCE_DPI": "102"}) == (
        ScreenOverride(1280, 800, 102.0)
    )
    assert override_from_env({}) is None


def test_a_broken_environment_override_is_ignored_not_fatal() -> None:
    assert override_from_env({"KIDNIX_SCREEN": "nonsense"}) is None
    assert override_from_env({"KIDNIX_FORCE_DPI": "very-high"}) is None


def test_describe_says_enough_to_debug_a_clipped_screen() -> None:
    text = Metrics.for_screen(1280, 800, dpi=102.0).describe()
    for fragment in ("1280x800", "dpi", "fit", "tile", "band", "needs"):
        assert fragment in text
