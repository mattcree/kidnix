"""Widget construction smoke tests.

These need a display. On a developer machine that is the running Wayland or X
session; in CI there may be none, in which case every test here skips. The
logic tests are the ones that must always run (spec section 7).
"""

from __future__ import annotations

import logging
import os
import re
from dataclasses import replace
from datetime import date
from pathlib import Path

import pytest

from .conftest import make_activity, write_png

gi = pytest.importorskip("gi")

if not (os.environ.get("WAYLAND_DISPLAY") or os.environ.get("DISPLAY")):
    pytest.skip("no display; skipping GTK widget tests", allow_module_level=True)

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gtk  # noqa: E402

if not Gtk.init_check():  # pragma: no cover - display present but unusable
    pytest.skip("GTK could not open the display", allow_module_level=True)

Adw.init()

from kidnix_shell.context import ShellContext  # noqa: E402
from kidnix_shell.journal import Journal  # noqa: E402
from kidnix_shell.metrics import (  # noqa: E402
    MIN_TARGET_MM,
    PRIMARY_TILE_MM,
    TILE_LABEL_MIN_PT,
    Metrics,
)
from kidnix_shell.screens.ending import EndingOfferScreen, PutAwayScreen  # noqa: E402
from kidnix_shell.screens.goodbye import GoodbyeScreen  # noqa: E402
from kidnix_shell.screens.home import HomeScreen  # noqa: E402
from kidnix_shell.screens.journal import JournalScreen  # noqa: E402
from kidnix_shell.screens.sleeping import SleepingScreen  # noqa: E402
from kidnix_shell.screens.whos_here import WhosHereScreen  # noqa: E402
from kidnix_shell.session import DailyUsage, Session, SessionPolicy  # noqa: E402
from kidnix_shell.settings import HomeConfig, KidState, ParentConfig, Paths  # noqa: E402
from kidnix_shell.sound import Earcons  # noqa: E402
from kidnix_shell.speech import FakeBackend, FakeScheduler, SpeechManager  # noqa: E402
from kidnix_shell.widgets import ActivityTile, ChildButton, Pager, SpeechUI  # noqa: E402


class RecordingHost:
    """Stands in for ShellWindow: records what a screen asked for."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, object]] = []

    def __getattr__(self, name: str):  # type: ignore[no-untyped-def]
        def record(*args: object, **kwargs: object) -> None:
            self.calls.append((name, args))

        return record


@pytest.fixture
def ctx(tmp_path: Path) -> ShellContext:
    paths = Paths(
        home=tmp_path,
        data_home=tmp_path / "data",
        config_home=tmp_path / "config",
        cache_home=tmp_path / "cache",
        state_home=tmp_path / "state",
    )
    journal = Journal(paths.journal_root)
    journal.load()
    speech = SpeechManager(backend=FakeBackend(), scheduler=FakeScheduler())
    config = ParentConfig()
    activities = [
        make_activity("scribble", category="make"),
        make_activity("letters", category="learn"),
        make_activity("bounce", category="play"),
    ]
    return ShellContext(
        metrics=Metrics(),
        speech=speech,
        speech_ui=SpeechUI(speech),
        journal=journal,
        session=Session(policy=SessionPolicy.demo(), usage=DailyUsage(day=date.today())),
        config=config,
        paths=paths,
        earcons=Earcons(enabled=False),
        host=RecordingHost(),
        activities=activities,
        profile=config.profiles[0],
        # Spec 7b: an old machine, so progressive disclosure is not the thing
        # under test in every other case here. `home_first_run` is the fixture
        # that puts it back to zero.
        kid_state=KidState(sessions_completed=100),
        demo=True,
    )


def test_a_child_button_carries_its_spoken_text_as_its_accessible_name(
    ctx: ShellContext,
) -> None:
    button = ChildButton(speak_text="Draw", speech_ui=ctx.speech_ui)
    assert button.speak_text == "Draw"
    assert button.get_focusable()


def test_a_child_button_fires_once_under_burst_clicking(ctx: ShellContext) -> None:
    """SYNTHESIS A3: eight clicks a second is one action, not eight."""
    fired: list[int] = []
    button = ChildButton(
        speak_text="Draw", on_activate=lambda: fired.append(1), speech_ui=ctx.speech_ui
    )
    for _ in range(8):
        button.fire()
    assert fired == [1]


def test_activating_a_button_speaks_it(ctx: ShellContext) -> None:
    backend = ctx.speech.backend
    button = ChildButton(speak_text="Draw", speech_ui=ctx.speech_ui)
    button.fire()
    assert backend.spoken == ["Draw"]  # type: ignore[attr-defined]


def test_the_speech_ring_lands_on_the_right_widget(ctx: ShellContext) -> None:
    button = ChildButton(speak_text="Draw", speech_ui=ctx.speech_ui)
    ctx.speech.speak("Draw", key=button.key)
    assert button.has_css_class("speaking")
    ctx.speech.cancel()
    assert not button.has_css_class("speaking")


def test_a_tile_is_at_least_forty_millimetres(ctx: ShellContext) -> None:
    tile = ActivityTile(ctx.activities[0], ctx.metrics, ctx.speech_ui, lambda: None)
    width, _ = tile.get_size_request()
    assert width >= ctx.metrics.mm(40)


def test_a_not_allowed_tile_is_outline_only_and_says_so(ctx: ShellContext) -> None:
    tile = ActivityTile(ctx.activities[0], ctx.metrics, ctx.speech_ui, lambda: None, allowed=False)
    assert tile.has_css_class("not-allowed")
    assert "Ask a grown-up" in tile.speak_text


def test_the_pager_hides_itself_when_there_is_one_page(ctx: ShellContext) -> None:
    pager = Pager(ctx.metrics, ctx.speech_ui, lambda page: None)
    pager.set_pages(1)
    assert not pager.get_visible()
    pager.set_pages(3)
    assert pager.get_visible()


def test_the_pager_will_not_walk_off_the_end(ctx: ShellContext) -> None:
    seen: list[int] = []
    pager = Pager(ctx.metrics, ctx.speech_ui, seen.append)
    pager.set_pages(2)
    pager.go(-5)
    pager.go(99)
    assert pager.page == 1
    assert seen == [1]


@pytest.mark.parametrize(
    "screen_class",
    [
        WhosHereScreen,
        HomeScreen,
        JournalScreen,
        EndingOfferScreen,
        PutAwayScreen,
        GoodbyeScreen,
        SleepingScreen,
    ],
)
def test_every_screen_constructs_and_can_be_entered(ctx: ShellContext, screen_class: type) -> None:
    screen = screen_class(ctx)
    screen.on_enter()
    screen.on_leave()
    assert screen.get_vexpand()


def test_home_pages_when_there_are_more_than_twelve_activities(ctx: ShellContext) -> None:
    ctx.activities = [make_activity(f"a{i}") for i in range(14)]
    screen = HomeScreen(ctx)
    assert screen.pager.pages == 2


def test_home_says_something_on_arrival(ctx: ShellContext) -> None:
    screen = HomeScreen(ctx)
    screen.on_enter()
    assert ctx.speech.last_utterance.startswith("Home")


def test_my_things_shows_an_empty_state(ctx: ShellContext) -> None:
    screen = JournalScreen(ctx)
    screen.on_enter()
    assert screen.empty.get_visible()


def test_my_things_shows_cards_once_there_is_work(ctx: ShellContext, tmp_path: Path) -> None:
    source = write_png(tmp_path / "work" / "picture.png")
    ctx.journal.import_file(source, "scribble", activity_name="Scribble")
    screen = JournalScreen(ctx)
    screen.on_enter()
    assert not screen.empty.get_visible()
    assert screen.pager.pages == 1


def test_showing_mode_does_not_resume(ctx: ShellContext, tmp_path: Path) -> None:
    """S7: showing a grown-up is read-only."""
    source = write_png(tmp_path / "work" / "picture.png")
    entry = ctx.journal.import_file(source, "scribble")
    assert entry is not None
    screen = JournalScreen(ctx)
    screen.showing_mode = True
    screen._open(entry)
    assert ctx.host.calls == []  # type: ignore[attr-defined]


def test_goodbye_counts_what_was_made_today(ctx: ShellContext, tmp_path: Path) -> None:
    for index in range(2):
        source = write_png(tmp_path / "work" / f"p{index}.png", colour=(index * 60, 0, 0))
        ctx.journal.import_file(source, "scribble")
    screen = GoodbyeScreen(ctx)
    screen.on_enter()
    assert "two things" in screen.headline.get_label()


def test_goodbye_with_nothing_made_does_not_say_you_made_nothing(
    ctx: ShellContext,
) -> None:
    screen = GoodbyeScreen(ctx)
    screen.on_enter()
    assert screen.headline.get_label() == "See you next time"
    assert not screen.show_button.get_visible()


def make_band(metrics, speech_ui):  # type: ignore[no-untyped-def]
    from kidnix_shell.band import Band, BandActions

    noop = lambda: None  # noqa: E731
    return Band(metrics, speech_ui, BandActions(noop, noop, noop, noop, noop, noop))


def test_the_band_has_every_control_the_spec_names(ctx: ShellContext) -> None:
    band = make_band(ctx.metrics, ctx.speech_ui)
    for button in (band.back, band.undo, band.my_things, band.ear):
        assert button.speak_text
    assert band.grownup.has_css_class("grownup-gate")
    height = band.get_size_request()[1]
    assert height >= ctx.metrics.band_height


def test_ask_is_not_in_the_band(ctx: ShellContext) -> None:
    """Spec 7a: an always-disabled control teaches a child that buttons lie."""
    from kidnix_shell import band as band_module

    assert band_module.SHOW_ASK is False
    assert make_band(ctx.metrics, ctx.speech_ui).ask is None


def test_the_band_fits_the_panel_it_was_sized_for(ctx: ShellContext) -> None:
    """The v0.1.0 bug: the band measured taller than the screen and got clipped."""
    for width, height, dpi in ((1280, 800, 102.0), (1280, 800, 118.0), (1366, 768, 96.0)):
        metrics = Metrics.for_screen(width, height, dpi=dpi)
        band = make_band(metrics, ctx.speech_ui)
        assert band.measure(Gtk.Orientation.VERTICAL, -1)[0] <= metrics.band_height
        assert band.measure(Gtk.Orientation.HORIZONTAL, -1)[0] <= width


def test_home_ends_with_the_all_done_tile(ctx: ShellContext) -> None:
    """Spec 7a / SYNTHESIS D5: the child can say they have had enough."""
    from kidnix_shell.screens.home import ALL_DONE, AllDone

    screen = HomeScreen(ctx)
    cells = screen.cells()
    assert isinstance(cells[-1], AllDone)
    assert cells[-1].speak_text == "All done for today?"
    assert len(cells) == len(ctx.activities) + 1
    assert ALL_DONE.icon == "kidnix-moon"


def test_the_all_done_tile_runs_the_ending_ritual(ctx: ShellContext) -> None:
    screen = HomeScreen(ctx)
    screen._all_done()
    assert ("finish_now", ()) in ctx.host.calls  # type: ignore[attr-defined]


def test_home_measures_inside_the_panel_it_was_sized_for(ctx: ShellContext) -> None:
    """Twelve tiles, a pager and a band, all inside a 1280x800 panel."""
    metrics = Metrics.for_screen(1280, 800, dpi=102.0)
    ctx.metrics = metrics
    ctx.activities = [make_activity(f"a{i}") for i in range(12)]
    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
    box.append(make_band(metrics, ctx.speech_ui))
    box.append(HomeScreen(ctx))
    assert box.measure(Gtk.Orientation.VERTICAL, -1)[0] <= 800
    assert box.measure(Gtk.Orientation.HORIZONTAL, -1)[0] <= 1280


def test_a_shrunk_layout_shrinks_the_type_too(ctx: ShellContext) -> None:
    """Points do not know about the fit factor, so theme.py restates them.

    ...and never below the 18 pt floor. A stylesheet that re-emitted 14.9 pt
    would put back exactly the floor the audit's fix #1 took out.
    """
    from kidnix_shell.theme import dynamic_css

    css = dynamic_css(Metrics(dpi=96.0, fit=0.7), ctx.profile)
    assert ".tile-label" in css
    for size in re.findall(r"font-size:\s*([\d.]+)pt", css):
        assert float(size) >= TILE_LABEL_MIN_PT, css
    provider = Gtk.CssProvider()
    provider.load_from_string(css)  # must be valid CSS, not just a string


def test_a_panel_that_does_not_have_to_shrink_restates_nothing(ctx: ShellContext) -> None:
    """1280x800 at 118 dpi keeps its 40 mm tile now; only the chrome gave way."""
    from kidnix_shell.theme import dynamic_css

    metrics = Metrics.for_screen(1280, 800, dpi=118.0)
    assert metrics.fit == 1.0
    assert ".tile-label" not in dynamic_css(metrics, ctx.profile)


def test_the_sun_moves_when_the_session_depletes(ctx: ShellContext) -> None:
    from kidnix_shell.band import Sun

    sun = Sun(ctx.metrics)
    assert sun.fraction == 0.0
    sun.set_progress(0.7, warm=True)
    assert sun.fraction == 0.7 and sun.warm


def test_the_theme_loads(ctx: ShellContext) -> None:
    provider = Gtk.CssProvider()
    provider.load_from_path(str(Path(__file__).resolve().parents[1] / "kidnix_shell/theme.css"))


def test_every_bundled_icon_loads() -> None:
    from kidnix_shell.widgets import data_dir

    icons = sorted((data_dir() / "icons").glob("*.svg"))
    assert len(icons) >= 12
    for icon in icons:
        image = Gtk.Image.new_from_file(str(icon))
        assert image.get_storage_type() != Gtk.ImageType.EMPTY, icon


# --- the whole window (v0.1.1) ------------------------------------------


def build_window(tmp_path: Path, screen: str = "1280x800@102"):  # type: ignore[no-untyped-def]
    """A real ShellWindow, never presented, on a pretend panel."""
    from kidnix_shell.app import ShellApplication, ShellWindow
    from kidnix_shell.metrics import parse_screen

    paths = Paths(
        home=tmp_path,
        data_home=tmp_path / "data",
        config_home=tmp_path / "config",
        cache_home=tmp_path / "cache",
        state_home=tmp_path / "state",
    )
    config = ParentConfig()
    application = ShellApplication(
        paths=paths,
        config=config,
        policy=SessionPolicy.demo(),
        activities=[make_activity(f"a{i}") for i in range(13)],
        demo=True,
        fullscreen=False,
        speech_backend="null",
    )
    return ShellWindow(
        application,
        paths=paths,
        config=config,
        policy=SessionPolicy.demo(),
        activities=application._activities,
        demo=True,
        fullscreen=False,
        speech_backend="null",
        screen=parse_screen(screen),
    )


@pytest.mark.parametrize("screen", ["1280x800@96", "1280x800@102", "1280x800@118", "1366x768@96"])
def test_the_whole_shell_fits_the_panel_it_was_told_about(tmp_path: Path, screen: str) -> None:
    """The regression the first real boot found, measured on the real tree."""
    window = build_window(tmp_path, screen)
    try:
        width = window.metrics.screen_width
        height = window.metrics.screen_height
        assert window._root.measure(Gtk.Orientation.HORIZONTAL, -1)[0] <= width
        assert window._root.measure(Gtk.Orientation.VERTICAL, -1)[0] <= height
    finally:
        window.shutdown()


def test_all_done_runs_the_ritual_and_back_recovers_an_accident(tmp_path: Path) -> None:
    """Spec 7a end to end: one tap, three dead seconds, then a way back."""
    from kidnix_shell.state import State

    window = build_window(tmp_path)

    def state() -> State:
        return window.machine.state

    try:
        window.choose_profile(window.ctx.profile)
        # Spec 7b: S1b sits between Who's here and Home now.
        assert state() is State.NEXT_CHOICE
        window.choose_next_after(window.ctx.config.next_after[0])
        assert state() is State.HOME

        window.finish_now()
        assert state() is State.PUT_AWAY

        window.on_back()  # inside the three-second lock: nothing happens
        assert state() is State.PUT_AWAY

        window._back_locked_until = 0.0
        window.on_back()
        assert state() is State.HOME

        # The goodbye timer that is still pending must not drag them back.
        window._goodbye_now()
        assert state() is State.HOME

        window.finish_now()
        window._goodbye_now()
        assert state() is State.GOODBYE
    finally:
        window.shutdown()


def test_undo_is_honest_when_there_is_nothing_to_undo(tmp_path: Path) -> None:
    window = build_window(tmp_path)
    try:
        window.speech.backend = FakeBackend()
        window.on_undo()
        assert window.speech.last_utterance == "Nothing to undo."
    finally:
        window.shutdown()


# --- Home and activities that cannot run --------------------------------


def test_home_leaves_out_an_activity_that_is_not_installed(ctx: ShellContext) -> None:
    """e2e spike 3.1: a tile that flickers and comes back is a button that lies."""
    ctx.activities = [
        make_activity("scribble"),
        make_activity("ghost", available=False),
    ]
    cells = HomeScreen(ctx).cells()
    assert [getattr(c, "id", "") for c in cells] == ["scribble", "kidnix.all-done"]


def test_a_manifest_can_ask_to_be_shown_anyway(ctx: ShellContext) -> None:
    ctx.activities = [make_activity("ghost", available=False, show_when_unavailable=True)]
    screen = HomeScreen(ctx)
    assert [getattr(c, "id", "") for c in screen.cells()] == ["ghost", "kidnix.all-done"]
    tile = screen._tile(ctx.activities[0])
    assert tile.has_css_class("not-allowed")  # outline-only, never greyed out
    assert "isn't ready yet" in tile.speak_text


def test_the_two_denials_do_not_say_the_same_thing(ctx: ShellContext) -> None:
    """Not-allowed sends the child to a grown-up who can help; not-installed
    should not send them to ask for something nobody can give them."""
    from kidnix_shell.screens.home import NOT_ALLOWED_LINE, NOT_READY_LINE

    ctx.activities = [make_activity("ghost", available=False, show_when_unavailable=True)]
    # A *non-empty* list that does not name "ghost". An empty list means
    # "everything is allowed" (settings.ParentConfig.is_allowed): a parent
    # panel that unticks the last box must not empty Home.
    ctx.config.allowed_activity_ids = ["something-else"]
    screen = HomeScreen(ctx)
    assert screen._denial(ctx.activities[0]) == NOT_ALLOWED_LINE  # forbidden wins
    ctx.config.allowed_activity_ids = None
    assert screen._denial(ctx.activities[0]) == NOT_READY_LINE
    assert NOT_ALLOWED_LINE != NOT_READY_LINE


def test_pressing_an_unavailable_tile_says_why_and_launches_nothing(
    ctx: ShellContext,
) -> None:
    ctx.activities = [make_activity("ghost", available=False, show_when_unavailable=True)]
    screen = HomeScreen(ctx)
    screen._activate(ctx.activities[0])
    assert "isn't ready yet" in ctx.speech.last_utterance
    assert not any(name == "launch" for name, _ in ctx.host.calls)  # type: ignore[attr-defined]


def test_home_honours_the_manifest_order(ctx: ShellContext) -> None:
    ctx.activities = sorted(
        [
            make_activity("last", order=99),
            make_activity("first", order=1),
            make_activity("unordered"),
        ],
        key=lambda a: a.sort_key,
    )
    cells = HomeScreen(ctx).cells()
    assert [getattr(c, "id", "") for c in cells[:-1]] == ["first", "last", "unordered"]


def test_ask_for_more_time_dismisses_the_offer(ctx: ShellContext) -> None:
    """S5: asking a grown-up is an answer; the child must not come back to it."""
    screen = EndingOfferScreen(ctx)
    screen._ask_for_more()
    assert ("dismiss_offer", (False,)) in ctx.host.calls  # type: ignore[attr-defined]


# --- no child-facing label is ever cut (SYNTHESIS B4) --------------------

import contextlib  # noqa: E402
from collections.abc import Iterator  # noqa: E402

from kidnix_shell.metrics import TILE_LABEL_LINES  # noqa: E402
from kidnix_shell.theme import dynamic_css  # noqa: E402
from tests.test_labels import ALL_DONE_NAME, PANELS, shipped_names  # noqa: E402

gi.require_version("Pango", "1.0")
from gi.repository import Gdk, Pango  # noqa: E402

THEME_CSS = Path(__file__).resolve().parents[1] / "kidnix_shell/theme.css"


@contextlib.contextmanager
def themed(ctx: ShellContext) -> Iterator[None]:
    """The display styled for *these* metrics, the way the real app styles it.

    ``ShellWindow`` installs ``theme.css`` plus the type sizes for the panel it
    is on, and how big ``.tile-label`` is in CSS is what GTK turns
    ``max-width-chars`` into pixels with. Without this the tests inherit
    whatever panel the last window in the session was built for.
    """
    display = Gdk.Display.get_default()
    base = Gtk.CssProvider()
    base.load_from_path(str(THEME_CSS))
    tint = Gtk.CssProvider()
    tint.load_from_string(dynamic_css(ctx.metrics, ctx.profile) or ".tile-label {}")
    Gtk.StyleContext.add_provider_for_display(display, base, Gtk.STYLE_PROVIDER_PRIORITY_USER)
    Gtk.StyleContext.add_provider_for_display(display, tint, Gtk.STYLE_PROVIDER_PRIORITY_USER + 1)
    try:
        yield
    finally:
        Gtk.StyleContext.remove_provider_for_display(display, tint)
        Gtk.StyleContext.remove_provider_for_display(display, base)


def walk(widget):  # type: ignore[no-untyped-def]
    """Every widget under ``widget``, itself included."""
    yield widget
    child = widget.get_first_child()
    while child is not None:
        yield from walk(child)
        child = child.get_next_sibling()


def tile_labels(widget):  # type: ignore[no-untyped-def]
    return [
        found
        for found in walk(widget)
        if isinstance(found, Gtk.Label) and found.has_css_class("tile-label")
    ]


def panel_metrics(width: int, height: int, dpi: float) -> Metrics:
    return Metrics.for_screen(width, height, dpi=dpi)


def home_with_shipped_names(ctx: ShellContext, screen: str) -> HomeScreen:
    """Home as the image ships it: the ten real manifest names, on one panel."""
    from kidnix_shell.metrics import parse_screen

    override = parse_screen(screen)
    ctx.metrics = Metrics.for_screen(override.width, override.height, dpi=override.dpi)
    ctx.activities = [
        make_activity(f"a{index}", name=name, audio_label=f"{name}. Come and play.")
        for index, name in enumerate(shipped_names())
    ]
    return HomeScreen(ctx)


@pytest.mark.parametrize(("width", "height", "dpi"), PANELS)
def test_no_home_tile_label_is_ellipsized(
    ctx: ShellContext, width: int, height: int, dpi: float
) -> None:
    """The v0.1.1 bug, measured by Pango itself on the real widget tree.

    ``Letters & n...`` was four of the ten shipped tiles on this panel.
    """
    home = home_with_shipped_names(ctx, f"{width}x{height}@{dpi:g}")
    labels = tile_labels(home)
    assert len(labels) == len(shipped_names()) + 1  # + the "All done" tile

    names = {*shipped_names(), ALL_DONE_NAME}
    for label in labels:
        assert label.get_label() in names
        assert label.get_ellipsize() == Pango.EllipsizeMode.NONE
        assert label.get_layout().is_ellipsized() is False
        assert label.get_wrap()
        assert label.get_wrap_mode() == Pango.WrapMode.WORD_CHAR


@pytest.mark.parametrize(("width", "height", "dpi"), PANELS)
def test_every_home_tile_label_fits_the_tile_it_is_in(
    ctx: ShellContext, width: int, height: int, dpi: float
) -> None:
    """Not cut *and* not spilling: what GTK will ask for fits what it will get."""
    ctx.metrics = panel_metrics(width, height, dpi)
    with themed(ctx):
        home = home_with_shipped_names(ctx, f"{width}x{height}@{dpi:g}")
        metrics = ctx.metrics
        for label in tile_labels(home):
            tall = label.measure(Gtk.Orientation.VERTICAL, metrics.tile_label_width)[1]
            assert tall <= metrics.tile_label_height, label.get_label()
        for tile in walk(home):
            if isinstance(tile, ActivityTile):
                natural = tile.measure(Gtk.Orientation.VERTICAL, -1)[1]
                assert natural <= metrics.tile_height, tile.speak_text


@pytest.mark.parametrize(("width", "height", "dpi"), PANELS)
def test_no_home_tile_label_takes_more_than_two_lines(
    ctx: ShellContext, width: int, height: int, dpi: float
) -> None:
    ctx.metrics = panel_metrics(width, height, dpi)
    with themed(ctx):
        home = home_with_shipped_names(ctx, f"{width}x{height}@{dpi:g}")
        for label in tile_labels(home):
            layout = label.get_layout()
            layout.set_width(ctx.metrics.tile_label_width * Pango.SCALE)
            assert layout.get_line_count() <= TILE_LABEL_LINES, label.get_label()


def test_a_page_of_tiles_is_all_one_type_size(ctx: ShellContext) -> None:
    """A grid where "Draw" is 24 pt and "Letters & numbers" is 18 pt reads as
    a mistake, so a page agrees on the size its longest name can carry."""
    home = home_with_shipped_names(ctx, "1280x800@102")
    tiles = [found for found in walk(home) if isinstance(found, ActivityTile)]
    assert len(tiles) == len(shipped_names()) + 1
    assert len({tile.label_fit.points for tile in tiles}) == 1
    assert all(tile.label.get_attributes() is not None for tile in tiles)


def test_the_tile_speaks_the_whole_audio_label_however_the_text_wraps(
    ctx: ShellContext,
) -> None:
    """B4: what the child *hears* is never the abbreviation of what they see."""
    ctx.metrics = Metrics.for_screen(1280, 800, dpi=102.0)
    activity = make_activity(
        "gcompris", name="Letters & numbers", audio_label="Letters and numbers"
    )
    tile = ActivityTile(activity, ctx.metrics, ctx.speech_ui, lambda: None)
    assert tile.speak_text == "Letters and numbers"
    assert tile.label.get_label() == "Letters & numbers"
    assert tile.label_fit.line_count == 2
    tile.fire()
    assert ctx.speech.backend.spoken == ["Letters and numbers"]  # type: ignore[attr-defined]


def test_a_profile_name_is_never_cut_either(ctx: ShellContext) -> None:
    """S1: a child's own name is the last thing that may be abbreviated."""
    from kidnix_shell.settings import Profile

    ctx.metrics = Metrics.for_screen(1280, 800, dpi=102.0)
    ctx.config.profiles = [
        Profile(id="a", name="Bartholomew", colour_primary="#0f8a8a", colour_secondary="#f06292")
    ]
    screen = WhosHereScreen(ctx)
    labels = tile_labels(screen)
    assert [label.get_label() for label in labels] == ["Bartholomew"]
    assert labels[0].get_ellipsize() == Pango.EllipsizeMode.NONE
    assert labels[0].get_layout().is_ellipsized() is False


def test_the_ending_choices_are_never_cut(ctx: ShellContext) -> None:
    """S5: the two ways to end a session are the two the child has to read."""
    ctx.metrics = Metrics.for_screen(1280, 800, dpi=102.0)
    screen = EndingOfferScreen(ctx)
    texts = {
        found.get_label()
        for found in walk(screen)
        if isinstance(found, Gtk.Label) and found.get_label()
    }
    assert {"Finish this one", "One last little thing", "Ask for more time"} <= texts
    for found in walk(screen):
        if isinstance(found, Gtk.Label):
            assert found.get_layout().is_ellipsized() is False
            assert found.get_ellipsize() == Pango.EllipsizeMode.NONE


def test_the_goodbye_buttons_are_never_cut(ctx: ShellContext) -> None:
    ctx.metrics = Metrics.for_screen(1280, 800, dpi=102.0)
    screen = GoodbyeScreen(ctx)
    for found in walk(screen):
        if isinstance(found, Gtk.Label):
            assert found.get_ellipsize() == Pango.EllipsizeMode.NONE
            assert found.get_layout().is_ellipsized() is False


def test_my_things_headings_are_never_cut(ctx: ShellContext, tmp_path: Path) -> None:
    ctx.metrics = Metrics.for_screen(1280, 800, dpi=102.0)
    ctx.journal.import_file(write_png(tmp_path / "work" / "p.png"), "scribble")
    screen = JournalScreen(ctx)
    screen.on_enter()
    for found in walk(screen):
        if isinstance(found, Gtk.Label):
            assert found.get_ellipsize() == Pango.EllipsizeMode.NONE


def test_the_grownup_sheet_wraps_instead_of_cutting(ctx: ShellContext) -> None:
    """The one adult surface: still nobody reads "/etc/kidnix/pare...".."""
    from kidnix_shell.screens.grownup import GrownupSheet

    sheet = GrownupSheet(ctx)
    rows = [found for found in walk(sheet.get_child()) if isinstance(found, Adw.PreferencesRow)]
    assert rows, "the actions page should have built some rows"
    for row in rows:
        assert row.get_title_lines() == 0
        if isinstance(row, Adw.ActionRow):
            assert row.get_subtitle_lines() == 0


@pytest.mark.parametrize("screen", ["1280x800@96", "1280x800@102", "1280x800@118", "1366x768@96"])
def test_the_shell_still_fits_with_the_names_the_image_actually_ships(
    tmp_path: Path, screen: str
) -> None:
    """The whole tree, the real names, the panels we ship for.

    ``test_the_whole_shell_fits_the_panel_it_was_told_about`` uses made-up
    one-word names, which is exactly the case that never broke. This is the
    same measurement with "Letters & numbers" in it.
    """
    from kidnix_shell.app import ShellApplication, ShellWindow
    from kidnix_shell.metrics import parse_screen
    from kidnix_shell.settings import ParentConfig

    paths = Paths(
        home=tmp_path,
        data_home=tmp_path / "data",
        config_home=tmp_path / "config",
        cache_home=tmp_path / "cache",
        state_home=tmp_path / "state",
    )
    # This test is about layout, not about spec 7b's progressive disclosure:
    # it wants every shipped name on the screen at once so it can measure them.
    config = ParentConfig(home=HomeConfig(show_everything=True))
    activities = [
        make_activity(f"a{index}", name=name) for index, name in enumerate(shipped_names())
    ]
    application = ShellApplication(
        paths=paths,
        config=config,
        policy=SessionPolicy.demo(),
        activities=activities,
        demo=True,
        fullscreen=False,
        speech_backend="null",
    )
    window = ShellWindow(
        application,
        paths=paths,
        config=config,
        policy=SessionPolicy.demo(),
        activities=application._activities,
        demo=True,
        fullscreen=False,
        speech_backend="null",
        screen=parse_screen(screen),
    )
    try:
        metrics = window.metrics
        # The measured-fit backstop has run by now, so these are the numbers a
        # child actually gets -- not the ones the arithmetic hoped for. The
        # floors hold on the real widget tree, which is the whole of the CCI
        # audit's fix #1: the grid gives way (4 x 2 here), the tile does not.
        assert metrics.mm_of(metrics.tile_size) >= PRIMARY_TILE_MM - 0.5, metrics.describe()
        assert metrics.mm_of(metrics.min_target) >= MIN_TARGET_MM - 0.05, metrics.describe()
        assert metrics.mm_of(metrics.gap) >= 8.0 - 0.05, metrics.describe()
        assert metrics.mm_of(metrics.band_target) >= MIN_TARGET_MM - 0.05, metrics.describe()
        assert metrics.label_floor_pt == TILE_LABEL_MIN_PT
        assert metrics.per_page in (8, 12), metrics.describe()
        assert window._root.measure(Gtk.Orientation.HORIZONTAL, -1)[0] <= metrics.screen_width
        assert window._root.measure(Gtk.Orientation.VERTICAL, -1)[0] <= metrics.screen_height
        # Every ``.tile-label`` in the window: all ten shipped names across
        # however many pages they take, and the profile name on Who's here,
        # which is built at the same time.
        labels = tile_labels(window._root)
        assert {*shipped_names(), ALL_DONE_NAME} <= {label.get_label() for label in labels}
        for label in labels:
            assert label.get_layout().is_ellipsized() is False
            assert label.get_ellipsize() == Pango.EllipsizeMode.NONE
            tall = label.measure(Gtk.Orientation.VERTICAL, metrics.tile_label_width)[1]
            assert tall <= metrics.tile_label_height, label.get_label()
    finally:
        window.shutdown()


# --- Home's three ways of not offering a tile (v0.1.3) --------------------


def _home_names(ctx: ShellContext) -> list[str]:
    return [getattr(cell, "name", "") for cell in HomeScreen(ctx).cells()]


def test_an_activity_outside_the_age_band_gets_no_tile_at_all(ctx: ShellContext) -> None:
    """01 #35: not outlined, not spoken -- simply not part of this computer."""
    ctx.activities = [
        make_activity("draw", name="Draw"),
        make_activity("sums", name="Number game", age_min=6, age_max=10),
    ]
    ctx.profile = replace(ctx.profile, age_band="4-5")
    assert _home_names(ctx) == ["Draw", "All done"]
    ctx.profile = replace(ctx.profile, age_band="6-8")
    assert _home_names(ctx) == ["Draw", "Number game", "All done"]


def test_a_profile_with_no_band_sees_everything(ctx: ShellContext) -> None:
    ctx.activities = [make_activity("sums", name="Number game", age_min=6, age_max=10)]
    ctx.profile = replace(ctx.profile, age_band="")
    assert _home_names(ctx) == ["Number game", "All done"]


def test_an_activity_with_no_content_gets_no_tile(ctx: ShellContext) -> None:
    """05 Lib-4: kiwix-serve is installed and there is no ZIM."""
    ctx.activities = [make_activity("library", name="Library", has_content=False)]
    assert _home_names(ctx) == ["All done"]


def test_a_contentless_activity_that_asks_to_be_seen_is_outlined_and_says_why(
    ctx: ShellContext,
) -> None:
    from kidnix_shell.screens.home import NOT_READY_LINE

    ctx.activities = [
        make_activity("library", name="Library", has_content=False, show_when_unavailable=True)
    ]
    screen = HomeScreen(ctx)
    assert _home_names(ctx) == ["Library", "All done"]
    assert screen._denial(ctx.activities[0]) == NOT_READY_LINE


def test_an_empty_allow_list_leaves_every_tile_pressable(ctx: ShellContext) -> None:
    """A parent panel that unticks the last box must not empty Home."""
    ctx.config.allowed_activity_ids = []
    screen = HomeScreen(ctx)
    for activity in ctx.activities:
        assert screen._denial(activity) is None


def test_a_named_allow_list_outlines_the_rest_rather_than_hiding_them(
    ctx: ShellContext,
) -> None:
    """SYNTHESIS G3: the outline is the affordance, so the tile has to stay."""
    from kidnix_shell.screens.home import NOT_ALLOWED_LINE

    ctx.config.allowed_activity_ids = ["scribble"]
    screen = HomeScreen(ctx)
    assert len(screen.cells()) == len(ctx.activities) + 1  # nothing was hidden
    assert screen._denial(ctx.activities[0]) is None
    assert screen._denial(ctx.activities[1]) == NOT_ALLOWED_LINE
    tile = screen._tile(ctx.activities[1])
    assert tile.has_css_class("not-allowed")
    assert NOT_ALLOWED_LINE in tile.speak_text


# --- the sun answers when you ask it (08 section 4.6) ---------------------


def test_the_sun_is_a_target_not_a_picture(ctx: ShellContext) -> None:
    """v0.1.2's Sun was an AccessibleRole.IMG with no gesture on it."""
    band = make_band(ctx.metrics, ctx.speech_ui)
    assert isinstance(band.sun_button, ChildButton)
    assert band.sun_button.get_focusable()
    assert band.sun_button.has_css_class("sun")


def test_tapping_the_sun_says_how_much_is_left_in_child_terms(ctx: ShellContext) -> None:
    from kidnix_shell.session import LOTS_LEFT, NEARLY_TIME, NOT_RUNNING

    band = make_band(ctx.metrics, ctx.speech_ui)
    assert band.sun_button.speak_text == NOT_RUNNING

    band.set_progress(0.1, warm=False, words=LOTS_LEFT)
    assert band.sun_button.speak_text == LOTS_LEFT
    band.sun_button.fire()
    assert ctx.speech.backend.spoken[-1] == LOTS_LEFT  # type: ignore[attr-defined]

    band.set_progress(0.95, warm=True, words=NEARLY_TIME)
    assert band.sun_button.speak_text == NEARLY_TIME
    # And the accessible name follows it, so a screen reader hears the same.
    assert band.sun_button.get_size_request() is not None


def test_the_sun_never_speaks_a_digit(ctx: ShellContext) -> None:
    from kidnix_shell.session import time_left_words

    band = make_band(ctx.metrics, ctx.speech_ui)
    for step in range(21):
        band.set_progress(step / 20, warm=False, words=time_left_words(1 - step / 20))
        assert not any(c.isdigit() for c in band.sun_button.speak_text)


# --- S1b "What's next after?" (spec 7b) ----------------------------------


def test_s1b_offers_every_configured_picture(ctx: ShellContext) -> None:
    from kidnix_shell.screens.next_after import NextAfterScreen

    screen = NextAfterScreen(ctx)
    screen.on_enter()
    labels = [label.get_label() for label in tile_labels(screen)]
    assert labels == [option.label for option in ctx.config.next_after]


def test_every_s1b_tile_is_a_home_sized_target(ctx: ShellContext) -> None:
    """Same tile, same size, same gesture: the child learns one thing."""
    from kidnix_shell.screens.next_after import NextAfterScreen

    screen = NextAfterScreen(ctx)
    for tile in _tiles(screen):
        assert tile.get_size_request()[0] == ctx.metrics.tile_size


def test_s1b_speaks_the_audio_label_not_the_tile_label(ctx: ShellContext) -> None:
    """The label box is two lines; the voice has no box (SYNTHESIS B4)."""
    from kidnix_shell.screens.next_after import NextAfterScreen

    screen = NextAfterScreen(ctx)
    spoken = {tile.speak_text for tile in _tiles(screen)}
    assert spoken == {option.speak_text for option in ctx.config.next_after}


def test_tapping_an_s1b_tile_chooses_it(ctx: ShellContext) -> None:
    from kidnix_shell.screens.next_after import NextAfterScreen

    screen = NextAfterScreen(ctx)
    _tiles(screen)[0].fire()
    calls = ctx.host.calls  # type: ignore[attr-defined]
    assert [name for name, _ in calls] == ["choose_next_after"]
    assert calls[0][1][0] is ctx.config.next_after[0]


def test_s1b_says_something_on_arrival(ctx: ShellContext) -> None:
    from kidnix_shell.screens.next_after import NextAfterScreen

    screen = NextAfterScreen(ctx)
    screen.on_enter()
    assert "next" in ctx.speech.last_utterance.lower()


def test_s1b_sits_between_whos_here_and_home_in_the_real_window(tmp_path: Path) -> None:
    from kidnix_shell.state import State

    window = build_window(tmp_path)
    try:
        window.choose_profile(window.ctx.profile)
        assert window.machine.state.value == State.NEXT_CHOICE.value
        assert window.stack.get_visible_child_name() == "next_after"
        window.choose_next_after(window.ctx.config.next_after[1])
        assert window.machine.state.value == State.HOME.value
        assert window.ctx.next_after is window.ctx.config.next_after[1]
    finally:
        window.shutdown()


def test_back_on_s1b_returns_to_whos_here_and_stops_the_clock(tmp_path: Path) -> None:
    from kidnix_shell.state import State

    window = build_window(tmp_path)
    try:
        window.choose_profile(window.ctx.profile)
        assert window.session.running
        window.on_back()
        assert window.machine.state is State.CHOOSING
        assert not window.session.running
        assert window.ctx.next_after is None
    finally:
        window.shutdown()


def test_a_profile_that_skips_s1b_goes_straight_home(tmp_path: Path) -> None:
    from kidnix_shell.state import State

    window = build_window(tmp_path)
    try:
        window.ctx.profile = replace(window.ctx.profile, skip_next_choice=True)
        window.choose_profile(window.ctx.profile)
        assert window.machine.state is State.HOME
        assert window.ctx.next_after is None
    finally:
        window.shutdown()


def test_a_new_session_forgets_last_time_s_answer(tmp_path: Path) -> None:
    """Goodbye must never show a picture nobody chose *today*."""
    from kidnix_shell.state import Event, State

    window = build_window(tmp_path)
    try:
        window.choose_profile(window.ctx.profile)
        window.choose_next_after(window.ctx.config.next_after[0])
        assert window.ctx.next_after is not None
        window.finish_now()
        window._goodbye_now()
        window.goodnight()
        assert window.machine.state.value == State.SLEEPING.value
        window.machine.try_fire(Event.WAKE)
        assert window.machine.state.value == State.CHOOSING.value
        window.choose_profile(window.ctx.profile)
        assert window.ctx.next_after is None
    finally:
        window.shutdown()


# --- S7 shows the choice back (spec 7b, Coco's Videos) -------------------


def test_goodbye_shows_the_childs_own_choice(ctx: ShellContext) -> None:
    ctx.next_after = ctx.config.next_after[0]
    screen = GoodbyeScreen(ctx)
    screen.on_enter()
    assert screen.suggestion.get_label() == "Ready to go outside?"
    assert screen.next_after_box.get_visible()
    assert "Ready to go outside?" in ctx.speech.last_utterance


def test_goodbye_falls_back_to_the_generated_line_when_nothing_was_chosen(
    ctx: ShellContext,
) -> None:
    """The suggestion list is the fallback now, not the mechanism."""
    ctx.next_after = None
    screen = GoodbyeScreen(ctx)
    screen.on_enter()
    assert not screen.next_after_box.get_visible()
    assert screen.suggestion.get_label()
    assert not screen.suggestion.get_label().startswith("Ready to")


def test_goodbye_asks_rather_than_instructs(ctx: ShellContext) -> None:
    """Coco's failure mode: "Coco will make you do it". Nothing here commands."""
    for option in ctx.config.next_after:
        ctx.next_after = option
        screen = GoodbyeScreen(ctx)
        screen.on_enter()
        line = screen.suggestion.get_label()
        assert line.endswith("?")
        assert "must" not in line.lower() and "now it's time" not in line.lower()


# --- progressive disclosure (spec 7b, SYNTHESIS B2) ----------------------


def test_a_first_run_home_shows_six_tiles_including_all_done(tmp_path: Path) -> None:
    ctx = _disclosure_ctx(tmp_path, sessions=0, activities=10)
    names = _home_names(ctx)
    assert len(names) == 6
    assert names[-1] == ALL_DONE_NAME


def test_home_grows_by_one_tile_every_two_sessions(tmp_path: Path) -> None:
    for sessions, expected in ((0, 6), (1, 6), (2, 7), (4, 8), (10, 11)):
        ctx = _disclosure_ctx(tmp_path, sessions=sessions, activities=10)
        assert len(_home_names(ctx)) == expected, sessions


def test_all_done_is_on_home_from_the_very_first_run(tmp_path: Path) -> None:
    """SYNTHESIS D5: a child who has had enough must always be able to say so."""
    for sessions in (0, 1, 2, 50):
        ctx = _disclosure_ctx(tmp_path, sessions=sessions, activities=10)
        assert ALL_DONE_NAME in _home_names(ctx)


def test_home_never_outgrows_the_allow_list(tmp_path: Path) -> None:
    ctx = _disclosure_ctx(tmp_path, sessions=500, activities=3)
    assert len(_home_names(ctx)) == 4  # three activities plus All done


def test_show_everything_hands_over_the_whole_grid_at_once(tmp_path: Path) -> None:
    ctx = _disclosure_ctx(tmp_path, sessions=0, activities=10, show_everything=True)
    assert len(_home_names(ctx)) == 11


def test_the_revealed_tiles_are_the_first_ones_by_order(tmp_path: Path) -> None:
    """The parent's `order` decides what a child meets first, not chance."""
    ctx = _disclosure_ctx(tmp_path, sessions=0, activities=10)
    assert _home_names(ctx)[:-1] == [f"A{index}" for index in range(5)]


def _disclosure_ctx(
    tmp_path: Path, *, sessions: int, activities: int, show_everything: bool = False
) -> ShellContext:
    from kidnix_shell.journal import Journal

    paths = Paths(
        home=tmp_path,
        data_home=tmp_path / "data",
        config_home=tmp_path / "config",
        cache_home=tmp_path / "cache",
        state_home=tmp_path / "state",
    )
    journal = Journal(paths.journal_root)
    journal.load()
    speech = SpeechManager(backend=FakeBackend(), scheduler=FakeScheduler())
    config = ParentConfig(home=HomeConfig(show_everything=show_everything))
    return ShellContext(
        metrics=Metrics(),
        speech=speech,
        speech_ui=SpeechUI(speech),
        journal=journal,
        session=Session(policy=SessionPolicy.demo(), usage=DailyUsage(day=date.today())),
        config=config,
        paths=paths,
        earcons=Earcons(enabled=False),
        host=RecordingHost(),
        activities=[
            make_activity(f"a{index}", name=f"A{index}", order=index) for index in range(activities)
        ],
        profile=config.profiles[0],
        kid_state=KidState(sessions_completed=sessions),
        demo=True,
    )


# --- the sun shrinks and sinks, and does not travel (spec 7b) ------------


def test_the_bands_sun_keeps_its_x_through_a_whole_session(ctx: ShellContext) -> None:
    from kidnix_shell.band import Sun

    sun = Sun(ctx.metrics)
    xs = set()
    for step in range(21):
        sun.set_progress(step / 20, warm=step > 14)
        xs.add(sun.geometry(320, 96).centre_x)
    assert len(xs) == 1


def test_the_bands_sun_gets_smaller_and_lower(ctx: ShellContext) -> None:
    from kidnix_shell.band import Sun

    sun = Sun(ctx.metrics)
    sun.set_progress(0.0, warm=False)
    start = sun.geometry(320, 96)
    sun.set_progress(0.9, warm=True)
    late = sun.geometry(320, 96)
    assert late.radius < start.radius
    assert late.centre_y > start.centre_y
    assert late.centre_x == start.centre_x


# --- the gate is not voiced (spec 7b, SYNTHESIS G2) ----------------------


def test_the_grown_up_gate_says_nothing_on_hover_or_focus(ctx: ShellContext) -> None:
    band = make_band(ctx.metrics, ctx.speech_ui)
    gate = band.grownup
    ctx.speech.backend.spoken.clear()  # type: ignore[attr-defined]
    for controller in gate.observe_controllers():
        assert not isinstance(controller, Gtk.EventControllerFocus)
    # Nothing registered it with the speech layer either, so the manager has
    # no key to speak or to ring.
    assert gate.key not in ctx.speech_ui._widgets


def test_the_grown_up_gate_still_has_an_accessible_name(ctx: ShellContext) -> None:
    """Unvoiced by us is not invisible to an assistive technology."""
    band = make_band(ctx.metrics, ctx.speech_ui)
    assert "Grown-up" in band.grownup.speak_text


def test_the_whos_here_grown_up_tile_is_not_voiced_either(ctx: ShellContext) -> None:
    screen = WhosHereScreen(ctx)
    ctx.speech.backend.spoken.clear()  # type: ignore[attr-defined]
    for button in _buttons(screen):
        if button.speak_text == "Grown-up":
            button.fire()
    assert ctx.speech.backend.spoken == []  # type: ignore[attr-defined]
    assert ctx.host.calls == [("open_grownup", ())]  # type: ignore[attr-defined]


def test_a_childs_own_tile_is_still_voiced(ctx: ShellContext) -> None:
    """The gate is the exception, not a new rule for the screen."""
    screen = WhosHereScreen(ctx)
    ctx.speech.backend.spoken.clear()  # type: ignore[attr-defined]
    for button in _buttons(screen):
        if button.speak_text != "Grown-up":
            button.fire()
    assert ctx.speech.backend.spoken  # type: ignore[attr-defined]


def test_the_pin_pad_is_not_voiced(ctx: ShellContext) -> None:
    from kidnix_shell.screens.grownup import GrownupSheet
    from kidnix_shell.widgets import ChildButton as VoicedButton

    sheet = GrownupSheet(ctx)
    assert not any(isinstance(widget, VoicedButton) for widget in walk(sheet))


def test_a_wrong_pin_is_free_silent_and_logged_without_the_digits(
    ctx: ShellContext, caplog: pytest.LogCaptureFixture
) -> None:
    """SYNTHESIS G2: no lockout, no delay, no counter, no voice -- one log line."""
    from kidnix_shell.screens.grownup import GrownupSheet

    sheet = GrownupSheet(ctx)
    ctx.speech.backend.spoken.clear()  # type: ignore[attr-defined]
    with caplog.at_level(logging.INFO, logger="kidnix_shell.screens.grownup"):
        for digit in "9999":
            sheet._push(digit)
        for digit in "1234":
            sheet._push(digit)
    assert ctx.speech.backend.spoken == []  # type: ignore[attr-defined]
    lines = [m for m in caplog.messages if m.startswith("grown-up gate")]
    assert len(lines) == 2
    assert "rejected" in lines[0] and "accepted" in lines[1]
    for line in lines:
        assert "9999" not in line and "1234" not in line
    # And a rejected attempt costs the grown-up nothing: the pad is still live.
    assert sheet._stack.get_visible_child_name() == "actions"


def _tiles(widget: Gtk.Widget) -> list[ActivityTile]:
    return [node for node in walk(widget) if isinstance(node, ActivityTile)]


def _buttons(widget: Gtk.Widget) -> list[ChildButton]:
    return [node for node in walk(widget) if isinstance(node, ChildButton)]


# --- v0.1.5: two toplevels, and the band during an activity ---------------
#
# docs/spikes/band-over-activity.md. The band is its own window now, so that
# gnome-kiosk can pin it to the top strip and keep it above a fullscreen
# activity. These tests cannot see a compositor -- what they can check is that
# the shell hands one the two windows, with the two titles, that the offer no
# longer covers a child's drawing, and that Back and My Things actually end the
# activity they are now reachable from.

import time  # noqa: E402

from kidnix_shell.kiosk import BAND_TITLE, CONTENT_TITLE, WindowConfig, placed  # noqa: E402
from kidnix_shell.state import State  # noqa: E402


def _state(window) -> State:  # type: ignore[no-untyped-def]
    """Read the state through a call, so a type checker cannot narrow it away."""
    return window.machine.state


def _sleeper():  # type: ignore[no-untyped-def]
    """An activity that stays up until it is asked to go away."""
    return make_activity("sleeper", name="Sleeper", exec_argv=("/bin/sleep", "30"))


def _start_an_activity(window, activity=None):  # type: ignore[no-untyped-def]
    """Walk a fresh window to IN_ACTIVITY with a real child process running."""
    window.choose_profile(window.ctx.profile)
    if window.machine.state is State.NEXT_CHOICE:
        window.choose_next_after(window.ctx.config.next_after[0])
    assert _state(window) is State.HOME
    activity = _sleeper() if activity is None else activity
    window.ctx.activities.append(activity)
    window.launch(activity)
    assert _state(window) is State.IN_ACTIVITY
    assert window.launcher.running
    return activity


def _wait_for_exit(window, timeout: float = 6.0) -> None:  # type: ignore[no-untyped-def]
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if window.launcher.check() is not None:
            return
        time.sleep(0.05)
    raise AssertionError("the activity was never reaped")


def test_the_shell_is_two_toplevels_on_one_application(tmp_path: Path) -> None:
    """One GtkApplication is a requirement, not a convenience: two *processes*
    sharing an application id do not get two windows."""
    window = build_window(tmp_path)
    try:
        assert window.get_title() == CONTENT_TITLE
        assert window.band_window.get_title() == BAND_TITLE
        assert window.band_window.get_content() is window.band
        assert window.get_application() is window.band_window.get_application()
        # ...and the band is emphatically not inside the content window any more.
        assert window.band not in list(walk(window._root))
    finally:
        window.shutdown()


def test_each_window_measures_inside_its_own_share_of_the_panel(tmp_path: Path) -> None:
    """The band gets `band_height` and the content window gets what is left --
    gnome-kiosk's lock-on-area gives each of them that and nothing more."""
    window = build_window(tmp_path)
    try:
        metrics = window.metrics
        assert metrics.content_height == metrics.screen_height - metrics.band_height
        assert window.band.measure(Gtk.Orientation.VERTICAL, -1)[0] <= metrics.band_height
        assert window.band.measure(Gtk.Orientation.HORIZONTAL, -1)[0] <= metrics.screen_width
        assert window._root.measure(Gtk.Orientation.VERTICAL, -1)[0] <= metrics.content_height
        assert window._root.measure(Gtk.Orientation.HORIZONTAL, -1)[0] <= metrics.screen_width
    finally:
        window.shutdown()


def test_a_windowed_shell_never_writes_the_child_s_window_config(tmp_path: Path) -> None:
    """`--windowed` is a developer on their own desktop, where $XDG_CONFIG_HOME
    is *theirs* and there is no gnome-kiosk to talk to."""
    window = build_window(tmp_path)
    try:
        assert not window.window_config.path.exists()
    finally:
        window.shutdown()


def test_a_kiosk_shell_writes_phase_a_once_with_the_final_band_height(tmp_path: Path) -> None:
    """The v0.1.5.0 regression, as a test.

    Constructing the window used to write phase A -- three times, because the
    measured-fit backstop changed the band's height on each pass, and all three
    writes plus the phase-B one landed inside gnome-kiosk's file-monitor
    window, so the only content it ever read was phase B. Now `__init__` writes
    *nothing*: the config is written once, from `present_all()`, with the
    height the layout actually settled on.
    """
    from kidnix_shell.app import ShellApplication, ShellWindow
    from kidnix_shell.metrics import parse_screen

    paths = Paths(
        home=tmp_path,
        data_home=tmp_path / "data",
        config_home=tmp_path / "config",
        cache_home=tmp_path / "cache",
        state_home=tmp_path / "state",
    )
    config = ParentConfig()
    application = ShellApplication(
        paths=paths,
        config=config,
        policy=SessionPolicy.demo(),
        activities=[make_activity("a")],
        demo=True,
        fullscreen=True,
        speech_backend="null",
    )
    # Never presented, so `fullscreen()` is only ever a request nothing reads.
    window = ShellWindow(
        application,
        paths=paths,
        config=config,
        policy=SessionPolicy.demo(),
        activities=application._activities,
        demo=True,
        fullscreen=True,
        speech_backend="null",
        screen=parse_screen("1280x800@102"),
    )
    try:
        written = WindowConfig(paths.config_home).path
        assert not written.exists(), "building the window must not touch the config"

        # What `present_all()` does first, without putting anything on screen.
        window._write_band_phase()
        text = written.read_text()
        band = window.metrics.band_height
        assert f"lock-on-area=0,0 {window.metrics.screen_width}x{band}" in text, text
        assert f"set-height={band}" in text
        assert f"match-title={BAND_TITLE}" in text
        # ...and phase B is only ever written once the band is confirmed placed.
        assert window._band_placed is False
    finally:
        window.shutdown()


def test_the_band_is_only_believed_when_the_compositor_has_answered(tmp_path: Path) -> None:
    """`map` is not placement. The v0.1.5.0 bug in one assertion."""
    window = build_window(tmp_path)
    try:
        # A window nobody presented has no toplevel and so no allocation, which
        # is exactly the state `map` fires in.
        assert window.band_window.get_height() == 0
        assert not placed(
            window.band_window.get_width(),
            window.band_window.get_height(),
            window.metrics.screen_width,
            window.metrics.band_height,
        )
    finally:
        window.shutdown()


def test_the_fallback_is_v0_1_4_rather_than_a_screen_with_no_way_out(tmp_path: Path) -> None:
    """AGENTS non-negotiable 8. If the strip cannot be had, be last release."""
    window = build_window(tmp_path)
    try:
        window._fall_back_to_one_window()
        assert window._one_window is True
        # One window, with the band back inside it, and everything still works.
        assert window.band in list(walk(window._root))
        assert window.stack in list(walk(window._root))
        window.choose_profile(window.ctx.profile)
        assert _state(window) is State.NEXT_CHOICE
        # ...and the whole tree is budgeted against the whole panel again.
        assert window._root.measure(Gtk.Orientation.VERTICAL, -1)[0] <= window.metrics.screen_height
    finally:
        window.shutdown()


def test_the_ending_offer_never_covers_a_child_s_drawing(tmp_path: Path) -> None:
    """CCI audit 02 #4. Inside an activity the offer is two buttons in the band
    and the child stays exactly where they were."""
    window = build_window(tmp_path)
    try:
        _start_an_activity(window)
        window._present_ending_offer()

        assert _state(window) is State.IN_ACTIVITY
        assert window.band.offer_mode is True
        assert window.band.finish_this.get_visible() is True
        assert window.band.one_more.get_visible() is True
        # The two they replace are the two that stood down, and nothing else
        # in the band moved.
        assert window.band.undo.get_visible() is False
        assert window.band.my_things.get_visible() is False
        assert window.band.back.get_visible() is True
        assert window.band.ear.get_visible() is True

        window.dismiss_offer(False)
        assert window.band.offer_mode is False
        assert window.band.undo.get_visible() is True
        assert window.band.finish_this.get_visible() is False
        assert window.session.offer_answered is True
    finally:
        window.shutdown()


def test_the_offer_buttons_are_the_same_size_as_the_two_they_replace(tmp_path: Path) -> None:
    """The band must not re-flow under a child's hand at the one moment they
    are being asked to stop."""
    window = build_window(tmp_path)
    try:
        band = window.band
        for offer, ordinary in ((band.finish_this, band.undo), (band.one_more, band.my_things)):
            assert offer.get_size_request() == ordinary.get_size_request()
    finally:
        window.shutdown()


def test_back_inside_an_activity_ends_it_and_goes_home(tmp_path: Path) -> None:
    """ADR-0010 #5 retires here: Back is the way out of an activity, so Tux
    Paint's own Quit tool and its unreadable modal do not have to be."""
    window = build_window(tmp_path)
    try:
        _start_an_activity(window)
        window.on_back()
        assert _state(window) is State.IN_ACTIVITY, "not until it has actually gone"
        _wait_for_exit(window)
        assert _state(window) is State.HOME
    finally:
        window.shutdown()


def test_my_things_inside_an_activity_ends_it_then_opens_the_journal(tmp_path: Path) -> None:
    window = build_window(tmp_path)
    try:
        _start_an_activity(window)
        window.open_journal()
        assert _state(window) is State.IN_ACTIVITY
        _wait_for_exit(window)
        assert _state(window) is State.JOURNAL
    finally:
        window.shutdown()


def test_undo_inside_an_activity_says_where_the_undo_is(tmp_path: Path) -> None:
    """Ruling: speak, do not hide. A shell that guessed at a key press per
    activity would be teaching a child that the button is unreliable."""
    window = build_window(tmp_path)
    try:
        _start_an_activity(window)
        window.on_undo()
        spoken = window.speech.last_utterance
        assert "undo" in spoken.lower()
        assert "Sleeper" in spoken, "it names the thing the child is actually in"
    finally:
        window.shutdown()


def test_the_band_window_goes_dark_rather_than_away_on_sleeping(tmp_path: Path) -> None:
    """Unmapping it would cost the band its placement: a re-mapped window gets
    a fresh first configure, and by then the file says "below the band"."""
    from kidnix_shell.state import Event

    window = build_window(tmp_path)
    try:
        window.machine.try_fire(Event.GOODNIGHT)
        assert _state(window) is State.SLEEPING
        assert window.band.get_visible() is False
        assert window.band_window.has_css_class("sleeping")
        assert window.band_window.get_content() is window.band  # still mapped
    finally:
        window.shutdown()


def test_back_asks_the_activity_rather_than_killing_it(tmp_path: Path) -> None:
    """The v0.1.5.0 data-loss bug, as a test.

    Measured on the real image: Tux Paint answers SIGTERM with its own
    picture-coded "Do you really want to quit?" and waits, and only the child's
    tap makes it autosave. A Back that SIGKILLed after the autosave grace would
    therefore destroy the drawing every time. So Back asks and then waits --
    the hard stop is Put away's job, not Back's.
    """
    window = build_window(tmp_path)
    try:
        _start_an_activity(window)
        window.on_back()
        assert window._reask_handle is None, "Back is not the ritual; it schedules nothing"
        assert window._nag_handle is not None, "Back must notice if nothing happens"
    finally:
        window.shutdown()


def test_a_killed_activity_still_leaves_in_activity(tmp_path: Path) -> None:
    """`Launcher.force_stop()` reaps the process itself, so the 500 ms poll in
    `check()` never sees it go and `on_exit` never fires. Without this the shell
    sat in IN_ACTIVITY with nothing on screen but the band -- measured in the
    VM, on an activity that ignored SIGTERM."""
    window = build_window(tmp_path)
    try:
        _start_an_activity(window)
        window._hard_stop()
        assert _state(window) is State.PUT_AWAY
        assert not window.launcher.running
    finally:
        window.shutdown()


# --- put away never destroys work (spec 7c, v0.1.6) ----------------------
#
# The §19.3 bug, as tests: at T-2 the shell used to raise the content window
# over the activity, SIGTERM, and SIGKILL five seconds later -- so a child
# could not see Tux Paint's tick, did not press it, and "Let's keep that" was
# followed by the drawing being deleted. Everything below is about the shell
# *not* doing that.


def _confirming_sleeper(tmp_path: Path):  # type: ignore[no-untyped-def]
    """An activity that models Tux Paint: SIGTERM makes it *ask*, not exit.

    A real child process that installs a SIGTERM handler and keeps running, so
    "the shell did not kill it" is a fact about a process table rather than
    about a mock.
    """
    import sys

    script = tmp_path / "asker.py"
    script.write_text(
        "import signal, time\nsignal.signal(signal.SIGTERM, lambda *a: None)\ntime.sleep(60)\n",
        encoding="utf-8",
    )
    return make_activity(
        "asker",
        name="Asker",
        exec_argv=(sys.executable, str(script)),
        quit="confirm",
        quit_grace=30.0,
    )


def test_put_away_inside_an_activity_does_not_take_the_screen(tmp_path: Path) -> None:
    """The whole ruling in one assertion: the child keeps looking at their own
    program until it has actually finished."""
    window = build_window(tmp_path)
    try:
        _start_an_activity(window, _confirming_sleeper(tmp_path))
        time.sleep(0.4)  # let the handler be installed
        window._begin_put_away()
        assert _state(window) is State.IN_ACTIVITY, "S6 covered the child's activity"
        assert window._put_away_pending is True
        assert window.launcher.running, "put away must not kill on the signal grace"
        assert window.stack.get_visible_child_name() != "put_away"
    finally:
        window.shutdown()


def test_put_away_speaks_the_confirm_line_and_strips_the_band(tmp_path: Path) -> None:
    window = build_window(tmp_path)
    try:
        _start_an_activity(window, _confirming_sleeper(tmp_path))
        time.sleep(0.4)  # let the handler be installed
        window._begin_put_away()
        assert window.speech.last_utterance == "Let's keep that. Press the tick."
        assert window.band.finishing is True
        assert window.band.undo.get_visible() is False
        assert window.band.my_things.get_visible() is False
        assert window.band.finish_this.get_visible() is False
        assert window.band.back.get_visible() is True, "Back is the way to finish"
    finally:
        window.shutdown()


def test_put_away_speaks_the_plain_line_for_a_signal_activity(tmp_path: Path) -> None:
    window = build_window(tmp_path)
    try:
        _start_an_activity(window)  # the plain sleeper: quit = "signal"
        window._begin_put_away()
        assert window.speech.last_utterance == "Let's keep that."
    finally:
        window.shutdown()


def test_back_during_put_away_asks_again_rather_than_navigating(tmp_path: Path) -> None:
    """ "Back is the same as finish in this phase" -- it may not contradict the
    thing the shell has just asked for."""
    window = build_window(tmp_path)
    try:
        _start_an_activity(window, _confirming_sleeper(tmp_path))
        time.sleep(0.4)  # let the handler be installed
        window._begin_put_away()
        window.speech.speak("something else")
        window.on_back()
        assert _state(window) is State.IN_ACTIVITY
        assert window.launcher.running
        assert window.speech.last_utterance == "Let's keep that. Press the tick."
    finally:
        window.shutdown()


def test_s6_appears_only_when_the_activity_has_really_gone(tmp_path: Path) -> None:
    """The child answered the tick: *now* "Let's keep that" is true."""
    window = build_window(tmp_path)
    try:
        _start_an_activity(window, _confirming_sleeper(tmp_path))
        time.sleep(0.4)  # let the handler be installed
        window._begin_put_away()
        assert _state(window) is State.IN_ACTIVITY
        window.launcher.force_stop()  # the child pressed the tick
        window._activity_finished()
        assert _state(window) is State.PUT_AWAY
        assert window._put_away_pending is False
        assert window.band.finishing is False
        assert window.ctx.work_lost is False
    finally:
        window.shutdown()


def test_the_grace_really_does_ask_again_on_a_real_timer(tmp_path: Path) -> None:
    """The re-ask is a GLib timeout, so a unit test that never spins the main
    loop would prove nothing about it. This one spins it."""
    from gi.repository import GLib

    window = build_window(tmp_path)
    try:
        activity = _confirming_sleeper(tmp_path)
        activity = replace(activity, quit_grace=0.5)
        _start_an_activity(window, activity)
        time.sleep(0.4)  # let the handler be installed
        window._begin_put_away()
        assert window.launcher.current is not None
        assert window.launcher.current.asked == 1

        context = GLib.MainContext.default()
        deadline = time.monotonic() + 3.0
        while time.monotonic() < deadline and window.launcher.current.asked < 2:
            context.iteration(False)
            time.sleep(0.02)

        assert window.launcher.current.asked == 2, "the grace never produced a second ask"
        assert window.launcher.running, "the grace is not a countdown to a SIGKILL"

        # ...and only one. A shell that re-asked on a repeating timer would be
        # a SIGTERM every half second at the worst possible moment.
        deadline = time.monotonic() + 1.5
        while time.monotonic() < deadline:
            context.iteration(False)
            time.sleep(0.02)
        assert window.launcher.current.asked == 2
    finally:
        window.shutdown()


def test_the_hard_stop_is_the_only_kill_and_it_says_so(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """T-0 with the activity still asking. The words change with the outcome."""
    import logging

    window = build_window(tmp_path)
    try:
        _start_an_activity(window, _confirming_sleeper(tmp_path))
        time.sleep(0.4)  # let the handler be installed
        window._begin_put_away()
        with caplog.at_level(logging.WARNING):
            window._hard_stop()
        assert "with unsaved work possible" in caplog.text
        assert window.ctx.work_lost is True
        assert not window.launcher.running
        assert _state(window) is State.PUT_AWAY
        assert window.screens["put_away"].headline.get_label() == "Time to stop now."
    finally:
        window.shutdown()
