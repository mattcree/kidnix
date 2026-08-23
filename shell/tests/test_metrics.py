"""Sizes are specified in millimetres (SYNTHESIS A1); check they come out that way."""

from __future__ import annotations

from dataclasses import replace

import pytest

from kidnix_shell.metrics import (
    BAND_CHROME_PX,
    BAND_MAX_PX,
    BAND_MIN_PX,
    DEFAULT_DPI,
    GAP_FLOOR_MM,
    GRIDS,
    MIN_FIT,
    MIN_GRID_TILE_MM,
    MIN_TARGET_MM,
    PRIMARY_TILE_MM,
    TILE_LABEL_MIN_PT,
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
    # 20 mm at 96 dpi is 75.59 px; undersizing a target is the one error that
    # matters, so it rounds up.
    assert metrics.mm(MIN_TARGET_MM) == 76


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

#: (width, height, dpi, scale_factor) -- the panels v0.1.1 must fit, in the
#: *logical* pixels GTK lays out in.
SCREENS = [
    (1280, 800, 96.0, 1),
    (1280, 800, 102.0, 1),  # the qcow2 VM's virtio panel: the one that clipped
    (1280, 800, 118.0, 1),  # this development host's density on a small panel
    (1366, 768, 96.0, 1),
    (1920, 1080, 96.0, 1),
    (1920, 1080, 141.0, 2),  # 3840x2160 at scale 2: GTK lays out in logical px
    (2560, 1440, 118.0, 1),
    (1280, 720, 113.0, 2),  # a 2560x1440 13" panel at 2x: 1280x720 logical
]


#: The panels ADR-0011's 20 mm floor costs a 40 mm tile. Both are small or
#: dense enough that two rows of 40 mm tiles plus a 20 mm band button, a 20 mm
#: pager arrow and the caption strip do not fit in 720-800 logical pixels.
#: Named rather than tolerated: if a third one ever joins them, that is a
#: layout decision somebody has to take, not a test that quietly went green.
TIGHT_PANELS = {
    (1280, 800, 118.0, 1),
    (1280, 720, 113.0, 2),
}

#: And the one panel in :data:`SCREENS` that has no fitting layout at all.
#: A 13" 1440p at 2x is 720 logical pixels tall; every floor kidnix has --
#: 20 mm targets, an 18 pt two-line label box, the caption strip -- adds up to
#: more than that. Recorded here rather than dropped from the list, because
#: "we do not fit this panel" is a fact somebody should have to change on
#: purpose.
OUT_OF_HEIGHT = {(1280, 720, 113.0, 2)}


def test_the_smallest_panels_pay_for_the_twenty_millimetre_floor() -> None:
    """What :data:`TIGHT_PANELS` actually costs, in millimetres, on the record."""
    for width, height, dpi, scale in sorted(TIGHT_PANELS):
        metrics = Metrics.for_screen(width, height, dpi=dpi, scale_factor=scale)
        assert metrics.mm_of(metrics.tile_size) < MIN_GRID_TILE_MM, metrics.describe()
        # Still a target a five-year-old can hit, and still the whole point.
        assert metrics.mm_of(metrics.tile_size) >= MIN_TARGET_MM - 0.05, metrics.describe()
        assert metrics.mm_of(metrics.band_target) >= MIN_TARGET_MM - 0.05, metrics.describe()
        assert metrics.mm_of(metrics.min_target) >= MIN_TARGET_MM - 0.05, metrics.describe()


@pytest.mark.parametrize(("width", "height", "dpi", "scale"), SCREENS)
def test_the_layout_never_exceeds_the_monitor(
    width: int, height: int, dpi: float, scale: int
) -> None:
    metrics = Metrics.for_screen(width, height, dpi=dpi, scale_factor=scale)
    needed_width, needed_height = metrics.required_size()
    assert needed_width <= width, metrics.describe()
    if (width, height, dpi, scale) in OUT_OF_HEIGHT:
        # 720 logical pixels, minus a 158 px band window, minus a 20 mm pager
        # arrow, minus two rows of tiles that are floored at 20 mm and carry a
        # two-line 18 pt label: the arithmetic runs out. It says so rather than
        # pretending, every floor still holds, and the shell's measured
        # backstop logs an ERROR on such a panel rather than shipping a window
        # that overhangs it silently.
        assert needed_height > height, metrics.describe()
        assert metrics.fit == MIN_FIT, metrics.describe()
        assert metrics.mm_of(metrics.min_target) >= MIN_TARGET_MM - 0.05
        return
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
    """Fitting may shrink a tile below 40 mm; it may not make it unusable.

    The bar is the **target floor** since ADR-0011, not an invented 25 mm: a
    tile is an interactive thing and 20 mm is what an interactive thing gets.
    On the two smallest panels here that is what it comes out at, because a
    20 mm floor everywhere plus the caption strip is exactly the trade the ADR
    made -- see :func:`test_the_smallest_panels_pay_for_the_twenty_millimetre_floor`.
    """
    metrics = Metrics.for_screen(width, height, dpi=dpi, scale_factor=scale)
    assert metrics.mm_of(metrics.tile_size) >= MIN_TARGET_MM - 0.05, metrics.describe()
    assert metrics.tile_size >= metrics.min_target


# --- the floors are absolute (CCI audit 2026-08-22, fix #1) --------------
#
# "A floor that moves is not a floor." v0.1.2 multiplied MIN_TARGET_MM, the
# 8 mm gap and TILE_LABEL_MIN_PT by ``fit``, so the panel we actually test on
# got 14.9 mm targets and a 14.9 pt "18 pt floor". These are the fence.


@pytest.mark.parametrize(("width", "height", "dpi", "scale"), SCREENS)
def test_the_minimum_target_is_eighteen_millimetres_on_every_panel(
    width: int, height: int, dpi: float, scale: int
) -> None:
    metrics = Metrics.for_screen(width, height, dpi=dpi, scale_factor=scale)
    assert metrics.mm_of(metrics.min_target) >= MIN_TARGET_MM - 0.05, metrics.describe()


@pytest.mark.parametrize(("width", "height", "dpi", "scale"), SCREENS)
def test_the_gap_never_goes_under_eight_millimetres(
    width: int, height: int, dpi: float, scale: int
) -> None:
    """08 section 3.1c. 12 mm is the preference and may be spent; 8 mm is not."""
    metrics = Metrics.for_screen(width, height, dpi=dpi, scale_factor=scale)
    assert metrics.mm_of(metrics.gap) >= GAP_FLOOR_MM - 0.05, metrics.describe()


@pytest.mark.parametrize(("width", "height", "dpi", "scale"), SCREENS)
def test_a_band_button_is_eighteen_millimetres_inside_the_clamp(
    width: int, height: int, dpi: float, scale: int
) -> None:
    """08 3.1a asks 20 mm; SYNTHESIS A1's floor is 18. The clamp may not eat it.

    The band is still clamped to 80-128 px (spec 7a) *and* the button still
    fits inside it -- the two constraints are satisfied together, not by
    letting one win.
    """
    metrics = Metrics.for_screen(width, height, dpi=dpi, scale_factor=scale)
    assert metrics.mm_of(metrics.band_target) >= MIN_TARGET_MM - 0.05, metrics.describe()
    assert BAND_MIN_PX <= metrics.band_height <= BAND_MAX_PX
    assert metrics.band_target + BAND_CHROME_PX <= metrics.band_height


@pytest.mark.parametrize(("width", "height", "dpi", "scale"), SCREENS)
def test_the_label_floor_is_eighteen_points_on_every_panel(
    width: int, height: int, dpi: float, scale: int
) -> None:
    metrics = Metrics.for_screen(width, height, dpi=dpi, scale_factor=scale)
    assert metrics.label_floor_pt == TILE_LABEL_MIN_PT, metrics.describe()
    assert metrics.tile_label_pt >= TILE_LABEL_MIN_PT
    # And every child-facing size in theme.css comes through the same floor.
    assert metrics.child_points(22.0) >= TILE_LABEL_MIN_PT


@pytest.mark.parametrize(("width", "height", "dpi", "scale"), SCREENS)
def test_the_tile_keeps_its_forty_millimetres_on_every_panel_we_ship_for(
    width: int, height: int, dpi: float, scale: int
) -> None:
    """The grid gives way before the tile does (audit section 3.1).

    ADR-0011 moved the target floor to 20 mm and the caption strip took a
    further 49 px off the content window, and the two together cost the
    densest and smallest panels their 40 mm tile. That is the ADR's own stated
    consequence ("a few fewer pixels per tile"), so it is written down as a
    number rather than left as a failing assertion: every panel keeps 40 mm
    except the two named here, and those keep the *floor*, which is the thing
    the ADR was actually about.
    """
    metrics = Metrics.for_screen(width, height, dpi=dpi, scale_factor=scale)
    if (width, height, dpi, scale) in TIGHT_PANELS:
        assert metrics.mm_of(metrics.tile_size) >= MIN_TARGET_MM - 0.05, metrics.describe()
        return
    assert metrics.mm_of(metrics.tile_size) >= MIN_GRID_TILE_MM - 0.05, metrics.describe()


@pytest.mark.parametrize(("width", "height", "dpi", "scale"), SCREENS)
def test_the_pager_arrow_is_a_real_target_too(
    width: int, height: int, dpi: float, scale: int
) -> None:
    """Pagination is the *only* way through Home now; the arrows must be hittable."""
    metrics = Metrics.for_screen(width, height, dpi=dpi, scale_factor=scale)
    assert metrics.mm_of(metrics.pager_height) >= MIN_TARGET_MM - 0.05, metrics.describe()


@pytest.mark.parametrize(("width", "height", "dpi", "scale"), SCREENS)
def test_every_touchable_size_clears_the_floor_on_every_panel(
    width: int, height: int, dpi: float, scale: int
) -> None:
    metrics = Metrics.for_screen(width, height, dpi=dpi, scale_factor=scale)
    for size in (
        metrics.tile_size,
        metrics.card_size,
        metrics.avatar_size,
        metrics.band_target,
        metrics.pager_height,
        metrics.target_mm(30),
    ):
        assert size >= metrics.min_target, metrics.describe()


def test_chrome_is_spent_before_the_tile_is() -> None:
    """1280x800 at 102 dpi fits because the gaps gave way, not the tile.

    The reference panel, not the 118 dpi one: since ADR-0011 the dense panel
    spends its chrome *and* some of its tile (:data:`TIGHT_PANELS`). The order
    of spending is what this test is about, and it is unchanged.
    """
    metrics = Metrics.for_screen(1280, 800, dpi=102.0)
    assert metrics.fit == 1.0, "the tile did not have to shrink"
    assert metrics.chrome_fit < 1.0, "the chrome did"
    assert metrics.mm_of(metrics.gap) < 12.0
    assert metrics.mm_of(metrics.gap) >= GAP_FLOOR_MM - 0.05
    assert metrics.mm_of(metrics.tile_size) >= PRIMARY_TILE_MM


def test_a_small_panel_pages_rather_than_shrinking_twelve_tiles() -> None:
    """1280x800 and 1366x768 both drop to eight tiles a page and keep 40 mm."""
    for width, height, dpi in ((1280, 800, 96.0), (1280, 800, 102.0), (1366, 768, 96.0)):
        metrics = Metrics.for_screen(width, height, dpi=dpi)
        assert metrics.per_page == 8, metrics.describe()
        assert metrics.mm_of(metrics.tile_size) >= PRIMARY_TILE_MM, metrics.describe()


def test_a_netbook_is_the_one_panel_that_costs_a_millimetre() -> None:
    """1024x600 cannot hold 40 mm tiles; it still holds every floor.

    Documented rather than hidden: this is the residual after the audit's fix,
    and it is a panel we do not ship for.
    """
    metrics = Metrics.for_screen(1024, 600, dpi=96.0)
    assert metrics.mm_of(metrics.tile_size) < PRIMARY_TILE_MM
    # The floors hold; the tile is what gives. On 600 logical pixels a 20 mm
    # band button, a 20 mm pager arrow and two rows of tiles cannot all be had,
    # and this is the one panel where the arithmetic simply runs out -- it asks
    # for more height than there is, and says so rather than pretending.
    assert metrics.required_size()[0] <= 1024
    assert metrics.mm_of(metrics.tile_size) >= MIN_TARGET_MM - 0.05
    assert metrics.mm_of(metrics.min_target) >= MIN_TARGET_MM - 0.05
    assert metrics.mm_of(metrics.gap) >= GAP_FLOOR_MM - 0.05
    assert metrics.label_floor_pt == TILE_LABEL_MIN_PT


def test_a_big_screen_needs_no_shrinking_at_all() -> None:
    for width, height, dpi in ((1920, 1080, 96.0), (2560, 1440, 118.0)):
        metrics = Metrics.for_screen(width, height, dpi=dpi)
        assert metrics.fit == 1.0
        assert metrics.chrome_fit == 1.0
        assert metrics.tile_size == Metrics(dpi=dpi).tile_size
        assert (metrics.columns, metrics.rows) == (4, 3)


def test_the_panel_that_clipped_gives_up_a_row_not_a_millimetre() -> None:
    """1280x800 at 102 dpi: the exact geometry of the first real boot.

    v0.1.2 kept twelve tiles here by shrinking them to 35 mm and the minimum
    target to 14.9 mm. The CCI audit's fix #1 reverses that trade: the tile
    stays at its 40 mm ideal and Home drops to 4 x 2, paginating the rest.
    """
    metrics = Metrics.for_screen(1280, 800, dpi=102.0)
    assert metrics.required_size() <= (1280, 800)
    assert (metrics.columns, metrics.rows) == (4, 2)
    assert metrics.per_page == 8
    assert metrics.mm_of(metrics.tile_size) >= PRIMARY_TILE_MM
    assert metrics.mm_of(metrics.min_target) >= MIN_TARGET_MM
    assert metrics.label_floor_pt == TILE_LABEL_MIN_PT


def test_the_physical_panel_decides_the_layout_not_the_reported_dpi() -> None:
    """Same 1280x800 panel, three claimed densities, near-identical pixels.

    This is the point of fitting: mm-based sizing chooses how big things are
    *in millimetres*, and the panel chooses how many pixels that can be.

    The tolerance is in *millimetres* now, not pixels: whatever density the
    panel claims, a tile comes out the same physical size, which is the whole
    reason SYNTHESIS section 3 is written in millimetres.
    """
    sizes = {
        round(
            Metrics.for_screen(1280, 800, dpi=dpi).mm_of(
                Metrics.for_screen(1280, 800, dpi=dpi).tile_size
            ),
            1,
        )
        for dpi in (96.0, 102.0)
    }
    assert max(sizes) - min(sizes) <= 0.5


def test_a_small_screen_gets_the_biggest_tile_any_grid_can_give_it() -> None:
    """No grid clears 40 mm on a netbook, so ``for_screen`` returns the best one.

    It used to assert ``rows < 3`` -- true only while 3 x 2 happened to reach a
    bigger tile than 4 x 3. Since ADR-0011 every grid bottoms out at the same
    ``MIN_FIT`` tile on this panel, so the rule that is actually being relied
    on is the one stated here: what comes back is never smaller than what any
    other grid would have given.
    """
    metrics = Metrics.for_screen(1024, 600, dpi=96.0)
    assert metrics.per_page == metrics.columns * metrics.rows
    for columns, rows in GRIDS:
        other = replace(metrics, columns=columns, rows=rows).shrunk_to_fit()
        assert metrics.tile_size >= other.tile_size, metrics.describe()


def test_an_unknown_screen_keeps_the_design_values() -> None:
    metrics = Metrics()
    assert metrics.fit == 1.0
    assert metrics.fits()  # nothing to fit into
    assert metrics.tile_size == 160


def test_the_fit_factor_shrinks_the_preferences_but_not_the_floors() -> None:
    full = Metrics(dpi=96.0)
    half = Metrics(dpi=96.0, fit=0.5)
    # Preferences halve...
    assert half.tile_size <= full.tile_size // 2 + 1
    assert half.points(24) == 12.0
    # ...floors do not move at all.
    assert half.gap == full.mm_floor(GAP_FLOOR_MM)
    assert half.min_target == full.min_target
    assert half.label_floor_pt == full.label_floor_pt == TILE_LABEL_MIN_PT
    assert half.child_points(24) == TILE_LABEL_MIN_PT


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
