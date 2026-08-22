"""Sizes are specified in millimetres (SYNTHESIS A1); check they come out that way."""

from __future__ import annotations

from kidnix_shell.metrics import (
    DEFAULT_DPI,
    MIN_TARGET_MM,
    PRIMARY_TILE_MM,
    Metrics,
    detect_metrics,
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
