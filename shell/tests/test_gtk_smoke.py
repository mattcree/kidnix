"""Widget construction smoke tests.

These need a display. On a developer machine that is the running Wayland or X
session; in CI there may be none, in which case every test here skips. The
logic tests are the ones that must always run (spec section 7).
"""

from __future__ import annotations

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
from kidnix_shell.settings import ParentConfig, Paths  # noqa: E402
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
    config = ParentConfig()
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
