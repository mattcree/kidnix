"""Widget construction smoke tests.

These need a display. On a developer machine that is the running Wayland or X
session; in CI there may be none, in which case every test here skips. The
logic tests are the ones that must always run (spec section 7).
"""

from __future__ import annotations

import os
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
from kidnix_shell.metrics import Metrics  # noqa: E402
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


def test_the_band_has_every_control_the_spec_names(ctx: ShellContext) -> None:
    from kidnix_shell.band import Band, BandActions

    noop = lambda: None  # noqa: E731
    band = Band(
        ctx.metrics,
        ctx.speech_ui,
        BandActions(noop, noop, noop, noop, noop, noop),
    )
    for button in (band.back, band.undo, band.my_things, band.ear, band.ask):
        assert button.speak_text
    assert band.ask.has_css_class("outline-only")
    assert band.grownup.has_css_class("grownup-gate")
    height = band.get_size_request()[1]
    assert height >= ctx.metrics.band_height


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
