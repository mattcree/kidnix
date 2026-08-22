"""``window-config.ini``: the arithmetic, the templates and the two phases.

The compositor half of the band (`docs/spikes/band-over-activity.md`) cannot be
tested without a compositor, but everything *we* decide can: which numbers go
in, which file is in place when, and that we never write a file with a token
left in it. No display and no GTK.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from kidnix_shell import kiosk
from kidnix_shell.kiosk import (
    ACTIVITY_PHASE,
    BAND_PHASE,
    BAND_TITLE,
    CONTENT_TITLE,
    SEED,
    GeometryError,
    WindowConfig,
    config_path,
    placed,
    render,
)

#: The panel the whole project tests on.
PANEL: dict[str, int] = {"width": 1280, "height": 800, "band_height": 96}


# --- rendering -------------------------------------------------------------


def test_the_band_phase_describes_the_strip_and_nothing_else() -> None:
    text = render(BAND_PHASE, **PANEL)
    assert "set-y=0" in text
    assert "set-width=1280" in text
    assert "set-height=96" in text
    assert "lock-on-area=0,0 1280x96" in text


def test_the_activity_phase_describes_everything_below_the_band() -> None:
    text = render(ACTIVITY_PHASE, **PANEL)
    assert "set-y=96" in text
    assert "set-height=704" in text, "content height must be H - band, not H"
    assert "lock-on-area=0,96 1280x704" in text
    assert "set-fullscreen=false" in text


@pytest.mark.parametrize(
    ("width", "height", "band"),
    [(1280, 800, 96), (1366, 768, 80), (1920, 1080, 128), (3840, 2160, 128), (1024, 600, 80)],
)
def test_the_content_area_is_always_the_rest_of_the_panel(
    width: int, height: int, band: int
) -> None:
    text = render(ACTIVITY_PHASE, width=width, height=height, band_height=band)
    assert f"lock-on-area=0,{band} {width}x{height - band}" in text
    assert f"set-height={height - band}" in text


def _keys(template: str) -> list[str]:
    """The template's actual settings -- comments and section headers dropped."""
    return [
        line.strip()
        for line in template.splitlines()
        if line.strip() and not line.lstrip().startswith(("#", "["))
    ]


def test_both_phases_raise_the_band_by_title_not_by_class() -> None:
    """Rule R3: at a window's first configure there is no app_id to match on,
    and both toplevels share one anyway. The title is the whole identity."""
    for template in (SEED, BAND_PHASE, ACTIVITY_PHASE):
        keys = _keys(template)
        assert f"match-title={BAND_TITLE}" in keys
        assert not [key for key in keys if key.startswith("match-class")]
        assert "set-above=true" in keys


def test_the_titles_have_no_glob_characters_in_them() -> None:
    """gnome-kiosk matches with g_pattern_match_simple."""
    for title in (BAND_TITLE, CONTENT_TITLE):
        assert not set(title) & set("*?[]")


def test_a_template_with_an_unknown_token_is_refused() -> None:
    """An unreplaced @TOKEN@ is a value gnome-kiosk's ini parser drops in
    silence; the failure would only show up as a window in the wrong place."""
    with pytest.raises(ValueError, match="@DEPTH@"):
        render("[all]\nset-x=@DEPTH@\n", **PANEL)


@pytest.mark.parametrize(
    ("width", "height", "band"),
    [(0, 800, 96), (1280, 0, 96), (1280, 800, 0), (1280, 800, 800), (1280, 800, 1000)],
)
def test_geometry_that_cannot_describe_a_band_is_refused(
    width: int, height: int, band: int
) -> None:
    with pytest.raises(GeometryError):
        render(BAND_PHASE, width=width, height=height, band_height=band)


# --- the seed --------------------------------------------------------------


def test_the_seed_carries_no_geometry_at_all() -> None:
    """It runs before there is a compositor to measure a monitor with, and a
    guessed strip on the wrong panel is worse than gnome-kiosk's defaults."""
    keys = _keys(SEED)
    for name in ("set-x", "set-y", "set-width", "set-height", "lock-on-area", "set-fullscreen"):
        assert not [key for key in keys if key.startswith(name)], name


def test_the_seed_needs_no_rendering() -> None:
    """It is installed by a shell script that has no numbers to substitute."""
    assert not [key for key in _keys(SEED) if "@" in key]


# --- the writer ------------------------------------------------------------


def test_the_two_phases_land_in_the_path_gnome_kiosk_searches(tmp_path: Path) -> None:
    assert config_path(tmp_path) == tmp_path / "gnome-kiosk" / "window-config.ini"
    config = WindowConfig(tmp_path)
    assert config.band_phase(**PANEL) is True
    assert config.path.is_file()
    assert config.path.read_text() == render(BAND_PHASE, **PANEL)

    assert config.activity_phase(**PANEL) is True
    assert config.path.read_text() == render(ACTIVITY_PHASE, **PANEL)


def test_writing_the_same_phase_twice_does_not_touch_the_file(tmp_path: Path) -> None:
    """gnome-kiosk reloads on every G_FILE_MONITOR_EVENT_CHANGED. A reload that
    changes nothing can only cost us a race, so idempotence is a feature."""
    config = WindowConfig(tmp_path)
    assert config.band_phase(**PANEL) is True
    stamp = config.path.stat().st_mtime_ns
    assert config.band_phase(**PANEL) is False
    assert config.path.stat().st_mtime_ns == stamp


def test_an_unmeasurable_monitor_leaves_the_seed_alone(tmp_path: Path) -> None:
    """Headless, or a display we could not measure. No geometry beats wrong
    geometry: the session then behaves as it did before the band existed."""
    config = WindowConfig(tmp_path)
    config.seed()
    before = config.path.read_text()
    assert config.band_phase(0, 0, 96) is False
    assert config.path.read_text() == before


def test_the_writer_creates_the_directory_it_needs(tmp_path: Path) -> None:
    config = WindowConfig(tmp_path / "fresh" / "config")
    assert config.band_phase(**PANEL) is True
    assert config.path.is_file()


def test_describe_names_both_rectangles(tmp_path: Path) -> None:
    config = WindowConfig(tmp_path)
    config.activity_phase(**PANEL)
    assert "0,0 1280x96" in config.describe()
    assert "0,96 1280x704" in config.describe()


# --- the shipped copies ----------------------------------------------------

SHIPPED = Path(__file__).resolve().parents[2] / "system_files/usr/share/kidnix/kiosk"


@pytest.mark.parametrize(
    ("name", "template"),
    [
        ("window-config.seed.ini", SEED),
        ("window-config.band.ini", BAND_PHASE),
        ("window-config.activity.ini", ACTIVITY_PHASE),
    ],
)
def test_the_files_the_image_ships_are_the_ones_the_shell_writes(name: str, template: str) -> None:
    """The seed is installed by ``/usr/bin/kidnix-shell`` from the image copy and
    the other two are written by the shell from these constants. If the two ever
    disagreed, the band would be placed by one set of rules and raised by
    another. Skipped when the shell is installed on its own (in the image, this
    test's repo-relative path does not exist)."""
    path = SHIPPED / name
    if not path.is_file():  # pragma: no cover - running from an installed copy
        pytest.skip(f"{path} is not here; the shipped copies are a repo-only check")
    assert path.read_text(encoding="utf-8") == template


def test_the_module_and_the_image_agree_on_where_the_templates_live() -> None:
    assert str(kiosk.SHIPPED_DIR) == "/usr/share/kidnix/kiosk"


# --- placement, confirmed rather than assumed ------------------------------
#
# v0.1.5.0 trusted GTK's `map` signal as "the band has its strip". It is not:
# `map` fires before the compositor answers with the toplevel's initial
# configure, so the shell wrote phase B into the gap, gnome-kiosk's file
# monitor coalesced the burst, and the band was placed by phase B -- 1280x708
# in the content rectangle, above the content window, measured in the VM.


def test_a_window_with_no_configure_yet_is_not_placed() -> None:
    """0x0 is "the compositor has not answered", not "it answered wrongly"."""
    assert placed(0, 0, 1280, 96) is False
    assert placed(1280, 0, 1280, 96) is False


def test_the_band_landing_in_the_content_rectangle_is_not_placed() -> None:
    """The exact regression: asked for 1280x92, got 1280x708."""
    assert placed(1280, 708, 1280, 92) is False


def test_a_fullscreen_band_is_not_placed_either() -> None:
    """What a seed with no geometry gets: gnome-kiosk's own default."""
    assert placed(1280, 800, 1280, 96) is False


def test_the_strip_we_asked_for_is_placed() -> None:
    assert placed(1280, 96, 1280, 96) is True


@pytest.mark.parametrize("slack", [-2, -1, 0, 1, 2])
def test_a_pixel_or_two_of_slack_still_counts(slack: int) -> None:
    """A fractional scale or a shadow may cost a pixel; the failure this
    catches is off by hundreds."""
    assert placed(1280 + slack, 96 + slack, 1280, 96) is True


@pytest.mark.parametrize("slack", [-4, 3, 20])
def test_more_than_a_pixel_or_two_does_not(slack: int) -> None:
    assert placed(1280, 96 + slack, 1280, 96) is False


def test_an_unknown_screen_width_only_checks_the_height() -> None:
    """Headless metrics report 0x0, and the height is the load-bearing half."""
    assert placed(1280, 96, 0, 96) is True
    assert placed(1280, 700, 0, 96) is False


def test_nothing_is_placed_against_a_zero_height_budget() -> None:
    assert placed(1280, 800, 1280, 0) is False
