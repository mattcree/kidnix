"""No child-facing label is ever cut short (SYNTHESIS B4).

v0.1.1 ellipsised, and a 1280x800 panel showed "Letters & n...", "Number ga...",
"Copy the li..." and "Jump and r..." -- four of the ten activities the image
ships, each one a word a pre-reader is supposed to be learning to recognise.
These tests are the fence: they take the *actual* names from the manifests in
``system_files`` and prove, on every panel geometry we ship for, that each one
fits its tile whole.

They need no display: :mod:`kidnix_shell.labels` measures with a deliberately
pessimistic model of the shipped face, so a pass here is a pass in Pango too.
"""

from __future__ import annotations

import tomllib
from itertools import pairwise
from pathlib import Path

import pytest

from kidnix_shell.labels import (
    LabelFit,
    em_width,
    fit_label,
    keeps_words_whole,
    line_height_px,
    step_points,
    text_width_px,
    wrap_estimate,
)
from kidnix_shell.metrics import TILE_LABEL_LINES, TILE_LABEL_MIN_PT, Metrics

#: The panels we have promised to fit: the 1280x800 of the first real boot at
#: three plausible reported densities, and the commonest cheap laptop.
PANELS = ((1280, 800, 96.0), (1280, 800, 102.0), (1280, 800, 118.0), (1366, 768, 96.0))

MANIFESTS = Path(__file__).resolve().parents[2] / "system_files/usr/share/kidnix/activities"

#: Spec 7a: Home's last tile is always this one, and it is a label like the
#: others even though no manifest produces it.
ALL_DONE_NAME = "All done"


def shipped_names() -> list[str]:
    """Every ``name`` the image's activity manifests put on a tile."""
    if not MANIFESTS.is_dir():  # pragma: no cover - running outside the repo
        pytest.skip(f"no shipped manifests at {MANIFESTS}")
    names = []
    for path in sorted(MANIFESTS.glob("*.toml")):
        names.append(str(tomllib.loads(path.read_text(encoding="utf-8"))["name"]))
    return names


def tile_fit(name: str, metrics: Metrics) -> LabelFit:
    """What a Home tile's label comes out as: ``(lines, points)`` and the rest.

    This is the whole rule in one call -- the helper the tests are about.
    """
    return fit_label(
        name,
        metrics.tile_label_width,
        base_pt=metrics.tile_label_pt,
        floor_pt=metrics.label_floor_pt,
        height=metrics.tile_label_height,
    )


# --- the shipped names on the panels we ship for --------------------------

#: How many tiles the image ships. A guard, not a target: if it moves, the
#: measurements below were taken against a different set and want re-taking.
SHIPPED_ACTIVITY_COUNT = 14


def test_the_image_still_ships_the_measured_set() -> None:
    """If this changes, the numbers below were measured against the wrong set."""
    assert len(shipped_names()) == SHIPPED_ACTIVITY_COUNT


@pytest.mark.parametrize(("width", "height", "dpi"), PANELS)
def test_every_shipped_name_fits_its_tile_whole(width: int, height: int, dpi: float) -> None:
    metrics = Metrics.for_screen(width, height, dpi=dpi)
    for name in [*shipped_names(), ALL_DONE_NAME]:
        fit = tile_fit(name, metrics)
        assert fit.fits, f"{name!r} does not fit a {width}x{height}@{dpi} tile"
        assert not fit.ellipsised
        assert "".join(fit.lines).replace(" ", "") == name.replace(" ", ""), (
            f"{name!r} lost characters: {fit.lines}"
        )
        assert fit.width <= metrics.tile_label_width


#: The one panel where ADR-0011's 20 mm floor and the caption strip together
#: leave a tile too narrow for "Letters & numbers" on two lines at the 18 pt
#: floor -- so it takes the documented third line and the tile grows. Named
#: rather than tolerated (see ``tests/test_metrics.TIGHT_PANELS``): the floors
#: are what hold, and the label is still whole and still never cut.
TIGHT = {(1280, 800, 118.0)}


@pytest.mark.parametrize(("width", "height", "dpi"), PANELS)
def test_no_shipped_name_needs_a_third_line(width: int, height: int, dpi: float) -> None:
    """The third line is the last resort. On the panels we ship for it is unused."""
    metrics = Metrics.for_screen(width, height, dpi=dpi)
    limit = TILE_LABEL_LINES + (1 if (width, height, dpi) in TIGHT else 0)
    for name in [*shipped_names(), ALL_DONE_NAME]:
        fit = tile_fit(name, metrics)
        assert fit.line_count <= limit, name
        # Whichever it takes, it is still whole and still broken between words.
        assert keeps_words_whole(name, fit.lines), name


@pytest.mark.parametrize(("width", "height", "dpi"), PANELS)
def test_a_wrapped_label_still_fits_the_reserved_box(width: int, height: int, dpi: float) -> None:
    """Two lines are reserved in the tile, so the grid never jumps.

    The exception is the documented last resort, on the one panel that needs
    it: there the tile is *allowed* to grow around a third line rather than
    cut a name (:data:`TIGHT`).
    """
    metrics = Metrics.for_screen(width, height, dpi=dpi)
    for name in [*shipped_names(), ALL_DONE_NAME]:
        fit = tile_fit(name, metrics)
        if (width, height, dpi) in TIGHT and fit.line_count > TILE_LABEL_LINES:
            continue
        assert fit.height <= metrics.tile_label_height, name


@pytest.mark.parametrize(("width", "height", "dpi"), PANELS)
def test_no_shipped_name_goes_under_the_floor(width: int, height: int, dpi: float) -> None:
    """18 pt (SYNTHESIS B4), or its equivalent on a layout we had to shrink."""
    metrics = Metrics.for_screen(width, height, dpi=dpi)
    for name in [*shipped_names(), ALL_DONE_NAME]:
        assert tile_fit(name, metrics).points >= metrics.label_floor_pt - 0.05, name


def test_the_floor_is_eighteen_points_where_nothing_had_to_shrink() -> None:
    metrics = Metrics.for_screen(1920, 1080, dpi=96.0)
    assert metrics.fit == 1.0
    assert metrics.label_floor_pt == TILE_LABEL_MIN_PT
    for name in [*shipped_names(), ALL_DONE_NAME]:
        assert tile_fit(name, metrics).points >= TILE_LABEL_MIN_PT


def test_the_longest_shipped_name_is_the_one_that_used_to_be_cut() -> None:
    """A canary: "Letters & numbers" is what "Letters & n..." was."""
    metrics = Metrics.for_screen(1280, 800, dpi=102.0)
    fit = tile_fit("Letters & numbers", metrics)
    assert fit.line_count == 2
    assert fit.lines == ("Letters &", "numbers")


# --- the rule itself ------------------------------------------------------


def test_a_label_that_fits_on_one_line_keeps_the_full_size() -> None:
    fit = fit_label("Draw", 400, base_pt=24.0, floor_pt=18.0)
    assert (fit.line_count, fit.points) == (1, 24.0)


def test_a_label_wraps_before_it_shrinks() -> None:
    """Two lines at a big size beat one line at a small one."""
    wide = fit_label("Copy the lights", 240, base_pt=24.0, floor_pt=18.0)
    assert wide.line_count == 2
    assert wide.points == 24.0


def test_the_size_steps_down_a_point_at_a_time() -> None:
    steps = list(step_points(24.0, 18.0))
    assert steps == [24.0, 23.0, 22.0, 21.0, 20.0, 19.0, 18.0]
    assert all(a - b >= 1.0 for a, b in pairwise(steps))


def test_the_floor_is_always_tried_exactly() -> None:
    """Whatever the arithmetic does, the last size offered is the floor."""
    assert list(step_points(19.3, 14.5))[-1] == 14.5
    assert list(step_points(18.0, 18.0)) == [18.0]
    assert list(step_points(12.0, 18.0)) == [12.0]  # a floor above the base


def test_a_third_line_is_the_last_resort_and_only_that() -> None:
    """Narrow enough that two lines cannot hold it, even at the floor."""
    two = fit_label("Copy the coloured lights", 110, base_pt=24.0, floor_pt=18.0, max_lines=2)
    assert two.line_count == 3, "two lines were tried first and could not hold it"
    assert two.points >= 18.0, "the floor is not negotiable; the third line is"
    assert two.fits and not two.ellipsised


def test_a_word_is_shrunk_to_the_floor_before_it_is_ever_broken() -> None:
    """The Goodbye-screen bug: "Goodnight" came out as "Goodnig" / "ht".

    Character wrapping is allowed (nothing may spill), but it is the last thing
    tried, after two lines and after every point size down to the floor.
    """
    fit = fit_label("Goodnight", 128, base_pt=27.4, floor_pt=14.2)
    assert fit.lines == ("Goodnight",)
    assert keeps_words_whole(fit.text, fit.lines)


def test_a_pair_of_buttons_can_share_one_size_without_breaking_a_word() -> None:
    """S7: "Show a grown-up" and "Goodnight" are set at one size, both whole."""
    texts = ("Show a grown-up", "Goodnight")
    points = min(fit_label(t, 128, base_pt=27.4, floor_pt=14.2).points for t in texts)
    for text in texts:
        lines, widest = wrap_estimate(text, points, 128)
        assert keeps_words_whole(text, lines), (text, lines)
        assert widest <= 128


def test_a_word_that_cannot_fit_at_the_floor_is_broken_rather_than_spilled() -> None:
    fit = fit_label("Antidisestablishmentarianism", 120, base_pt=24.0, floor_pt=18.0)
    assert not keeps_words_whole(fit.text, fit.lines)
    assert "".join(fit.lines) == "Antidisestablishmentarianism"


def test_every_shipped_name_breaks_only_between_words() -> None:
    for width, height, dpi in PANELS:
        metrics = Metrics.for_screen(width, height, dpi=dpi)
        for name in [*shipped_names(), ALL_DONE_NAME]:
            fit = tile_fit(name, metrics)
            assert keeps_words_whole(fit.text, fit.lines), (name, fit.lines)


def test_nothing_is_ever_ellipsised_even_when_nothing_fits() -> None:
    """One word, a tile a tenth its width: still every character, never a dot."""
    fit = fit_label("Antidisestablishmentarianism", 40, base_pt=24.0, floor_pt=18.0)
    assert not fit.ellipsised
    assert "".join(fit.lines) == "Antidisestablishmentarianism"


def test_a_word_wider_than_the_line_is_broken_not_spilled() -> None:
    lines, widest = wrap_estimate("Antidisestablishmentarianism", 18.0, 80)
    assert len(lines) > 1
    assert widest <= 80
    assert "".join(lines) == "Antidisestablishmentarianism"


def test_the_wrap_keeps_words_whole_while_they_fit() -> None:
    lines, _ = wrap_estimate("Letters & numbers", 18.0, 130)
    assert lines == ("Letters &", "numbers")


def test_empty_text_is_one_empty_line_not_a_crash() -> None:
    fit = fit_label("", 100, base_pt=24.0, floor_pt=18.0)
    assert fit.lines == ("",)
    assert fit.fits


# --- the model behind the estimate ----------------------------------------


def test_wide_letters_measure_wider_than_narrow_ones() -> None:
    assert em_width("mmm") > em_width("iii")
    assert em_width("MMM") > em_width("...")


def test_measurement_scales_with_the_point_size() -> None:
    small = text_width_px("Letters & numbers", 12.0)
    big = text_width_px("Letters & numbers", 24.0)
    assert 1.9 <= big / small <= 2.1


def test_a_line_box_is_taller_than_the_em() -> None:
    """Ascenders and descenders: two 18 pt lines are not 2 x 18 pt of pixels."""
    assert line_height_px(18.0) > 18.0 * 96.0 / 72.0


def test_the_estimate_is_pessimistic_not_optimistic() -> None:
    """It may refuse a label Pango would have fitted; never the other way round.

    Measured against the shipped face, "Letters & numbers" at 24 pt is 280 px.
    The estimate must be at least that, or a headless pass means nothing.
    """
    assert text_width_px("Letters & numbers", 24.0) >= 280
