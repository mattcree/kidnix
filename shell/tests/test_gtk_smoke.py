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
from datetime import date, datetime
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

from kidnix_shell.activities import Activity  # noqa: E402
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
from kidnix_shell.settings import (  # noqa: E402
    DEFAULT_PIN,
    HomeConfig,
    KidState,
    ParentConfig,
    Paths,
)
from kidnix_shell.sound import Earcons  # noqa: E402
from kidnix_shell.speech import FakeBackend, FakeScheduler, SpeechManager  # noqa: E402
from kidnix_shell.widgets import (  # noqa: E402
    DEBOUNCE_MS,
    ActivityTile,
    ChildButton,
    MicButton,
    Pager,
    SpeechUI,
)


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
    # A machine a grown-up has already set up. Without this every sheet in
    # every test would open on the mandatory "choose a PIN" flow (spec 7d #11),
    # which is its own test below. The PIN is the documented one so the
    # existing gate tests still type four digits they know.
    config.set_pin(DEFAULT_PIN)
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


def test_goodbye_describes_what_was_made_rather_than_counting_it(
    ctx: ShellContext, tmp_path: Path
) -> None:
    """SYNTHESIS E1: descriptive feedback, not a score (forum #30, #52)."""
    for index in range(2):
        source = write_png(tmp_path / "work" / f"p{index}.png", colour=(index * 60, 0, 0))
        ctx.journal.import_file(source, "scribble")
    screen = GoodbyeScreen(ctx)
    screen.on_enter()
    assert screen.made_line.get_label().startswith("You ")
    assert "two" in screen.made_line.get_label()


def test_goodbye_never_hides_show_a_grown_up(ctx: ShellContext) -> None:
    """forum #28: the same bool that emptied the headline also withdrew the
    co-use invitation, on the child's flattest day."""
    screen = GoodbyeScreen(ctx)
    screen.on_enter()
    assert screen.show_button.get_visible()


def test_goodbye_with_nothing_made_says_something_warm_and_true(
    ctx: ShellContext,
) -> None:
    from kidnix_shell.resting import ALL_DONE_HEADLINE

    ctx.next_after = None
    screen = GoodbyeScreen(ctx)
    screen.on_enter()
    assert screen.headline.get_label() == ALL_DONE_HEADLINE
    assert "see you" not in screen.headline.get_label().lower()


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


def test_home_keeps_all_done_in_one_cell_forever(ctx: ShellContext) -> None:
    """Spec 7a / SYNTHESIS D5, and the panel ruling of 2026-08-23: the child can
    say they have had enough, and the button is where it was last time.

    It used to be *last in the list*, so it moved one cell along every time
    progressive disclosure revealed a tile -- redrawing the escape hatch on a
    schedule the child cannot perceive (forum #5, #41, #57)."""
    from kidnix_shell.screens.home import ALL_DONE, AllDone, all_done_index

    screen = HomeScreen(ctx)
    cells = screen.cells()
    index = all_done_index(ctx.metrics.per_page)
    pinned = cells[index]
    assert isinstance(pinned, AllDone)
    assert pinned.speak_text == "All done for today?"
    assert ALL_DONE.icon == "kidnix-moon"


def test_the_all_done_cell_does_not_move_as_home_fills_up(ctx: ShellContext) -> None:
    from kidnix_shell.screens.home import ALL_DONE, all_done_index

    index = all_done_index(ctx.metrics.per_page)
    everything = list(ctx.activities)
    for count in range(len(everything) + 1):
        ctx.activities = everything[:count]
        assert HomeScreen(ctx).cells()[index] is ALL_DONE, count
    ctx.activities = everything


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
    """1280x800 at 102 dpi keeps its 40 mm tile; only the chrome gave way.

    The reference panel rather than the 118 dpi one: since ADR-0011 raised the
    target floor to 20 mm and the caption strip took 49 px off the content
    window, the dense panel is one of the two that spends a little tile as
    well (``test_metrics.TIGHT_PANELS``).
    """
    from kidnix_shell.theme import dynamic_css

    metrics = Metrics.for_screen(1280, 800, dpi=102.0)
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


def build_window(  # type: ignore[no-untyped-def]
    tmp_path: Path,
    screen: str = "1280x800@102",
    config: ParentConfig | None = None,
    shelves: dict[str, list[Activity]] | None = None,
    voice: object | None = None,
):
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
    config = config or ParentConfig()
    # A shell whose gate is already set: `must_set_pin` opens the grown-up
    # sheet on the PIN flow, which is its own test.
    config.pin_configured = True
    application = ShellApplication(
        paths=paths,
        config=config,
        policy=SessionPolicy.demo(),
        activities=[make_activity(f"a{i}") for i in range(13)],
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
        shelves=shelves or {},
    )
    if voice is not None:
        window.ctx.voice = voice  # type: ignore[assignment]
    return window


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
    cells = [c for c in HomeScreen(ctx).cells() if c is not None]
    assert [getattr(c, "id", "") for c in cells] == ["scribble", "kidnix.all-done"]


def test_a_manifest_can_ask_to_be_shown_anyway(ctx: ShellContext) -> None:
    ctx.activities = [make_activity("ghost", available=False, show_when_unavailable=True)]
    screen = HomeScreen(ctx)
    assert [getattr(c, "id", "") for c in screen.cells() if c is not None] == [
        "ghost",
        "kidnix.all-done",
    ]
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
    cells = [c for c in HomeScreen(ctx).cells() if c is not None]
    assert [getattr(c, "id", "") for c in cells if c.id != "kidnix.all-done"] == [
        "first",
        "last",
        "unordered",
    ]


def test_ask_for_more_time_dismisses_the_offer(ctx: ShellContext) -> None:
    """S5: asking a grown-up is an answer; the child must not come back to it."""
    from kidnix_shell.ritual import OfferAnswer

    screen = EndingOfferScreen(ctx)
    screen._ask_for_more()
    assert ("dismiss_offer", (OfferAnswer.ASK,)) in ctx.host.calls  # type: ignore[attr-defined]


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


def label_text(label) -> str:  # type: ignore[no-untyped-def]
    """A tile label's text with the wrap taken back out.

    Inside a reserved box the shell does its own wrapping and hands GTK the
    line breaks (``widgets.fit_gtk_label``), because GTK wraps at a width
    computed from the *style* font rather than the size the text is set at.
    So the label really does contain newlines; what it says is this.
    """
    return " ".join((label.get_label() or "").split())


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
        assert label_text(label) in names
        assert label.get_ellipsize() == Pango.EllipsizeMode.NONE
        assert label.get_layout().is_ellipsized() is False
        # The wrap is the shell's own now (widgets.fit_gtk_label): what
        # matters is that nothing is cut, and that what is drawn is the name.
        assert label.get_ellipsize() == Pango.EllipsizeMode.NONE
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
            assert tall <= metrics.tile_label_height, label_text(label)
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
            # The label's own layout, at the wrap the shell chose for it. Not
            # a hypothetical re-wrap at `tile_label_width`: since the shell
            # does the wrapping itself (widgets.fit_gtk_label) the layout is
            # what will be drawn, and a re-wrap here would be measuring a
            # different label in whatever font this host happens to have.
            assert label.get_layout().get_line_count() <= TILE_LABEL_LINES, label_text(label)


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
    assert label_text(tile.label) == "Letters & numbers"
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
    assert [label_text(label) for label in labels] == ["Bartholomew"]
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


#: See ``tests/test_metrics.TIGHT_PANELS``.
TIGHT_SCREENS = {"1280x800@118"}


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
        if screen in TIGHT_SCREENS:
            # ADR-0011's stated cost, named rather than tolerated: a 20 mm
            # floor everywhere plus the caption strip does not leave two rows
            # of 40 mm tiles on the densest panel we ship for. It keeps the
            # floor, which is what the ADR was about.
            assert metrics.mm_of(metrics.tile_size) >= MIN_TARGET_MM - 0.05, metrics.describe()
        else:
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
        assert {*shipped_names(), ALL_DONE_NAME} <= {label_text(label) for label in labels}
        for label in labels:
            assert label.get_layout().is_ellipsized() is False
            assert label.get_ellipsize() == Pango.EllipsizeMode.NONE
            tall = label.measure(Gtk.Orientation.VERTICAL, metrics.tile_label_width)[1]
            assert tall <= metrics.tile_label_height, label_text(label)
    finally:
        window.shutdown()


# --- Home's three ways of not offering a tile (v0.1.3) --------------------


def _home_names(ctx: ShellContext) -> list[str]:
    """The tiles on Home, in order, skipping the cells "All done" reserves.

    Since 2026-08-23 the grid has holes in it on purpose: "All done" owns one
    cell forever and the activities grow around it, so the list is no longer
    "everything, then All done".
    """
    return [getattr(cell, "name", "") for cell in HomeScreen(ctx).cells() if cell is not None]


def test_an_activity_outside_the_age_band_gets_no_tile_at_all(ctx: ShellContext) -> None:
    """01 #35: not outlined, not spoken -- simply not part of this computer."""
    ctx.activities = [
        make_activity("draw", name="Draw"),
        make_activity("sums", name="Number game", age_min=6, age_max=10),
    ]
    ctx.profile = replace(ctx.profile, age_band="4-5")
    assert sorted(_home_names(ctx)) == ["All done", "Draw"]
    ctx.profile = replace(ctx.profile, age_band="6-8")
    assert sorted(_home_names(ctx)) == ["All done", "Draw", "Number game"]


def test_a_profile_with_no_band_sees_everything(ctx: ShellContext) -> None:
    ctx.activities = [make_activity("sums", name="Number game", age_min=6, age_max=10)]
    ctx.profile = replace(ctx.profile, age_band="")
    assert sorted(_home_names(ctx)) == ["All done", "Number game"]


def test_an_activity_with_no_content_gets_no_tile(ctx: ShellContext) -> None:
    """05 Lib-4: kiwix-serve is installed and there is no ZIM."""
    ctx.activities = [make_activity("library", name="Library", has_content=False)]
    assert _home_names(ctx) == ["All done"]  # nothing else earned a cell


def test_a_contentless_activity_that_asks_to_be_seen_is_outlined_and_says_why(
    ctx: ShellContext,
) -> None:
    from kidnix_shell.screens.home import NOT_READY_LINE

    ctx.activities = [
        make_activity("library", name="Library", has_content=False, show_when_unavailable=True)
    ]
    screen = HomeScreen(ctx)
    assert sorted(_home_names(ctx)) == ["All done", "Library"]
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
    kept = [c for c in screen.cells() if c is not None]
    assert len(kept) == len(ctx.activities) + 1  # nothing was hidden
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
    labels = [label_text(label) for label in tile_labels(screen)]
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


def test_goodbye_leads_with_the_childs_own_choice(ctx: ShellContext) -> None:
    """The ruling: the destination is the headline and the biggest picture on
    the screen, not a 24 mm icon on the bottom edge (forum #24, #30, #51)."""
    from kidnix_shell.metrics import GOODBYE_DESTINATION_MM

    ctx.next_after = ctx.config.next_after[0]
    screen = GoodbyeScreen(ctx)
    screen.on_enter()
    assert screen.headline.get_label() == "Ready to go outside?"
    assert screen.next_after_icon.get_visible()
    assert GOODBYE_DESTINATION_MM >= 40.0
    # The hierarchy, as *drawn*: the destination is bigger than a thumbnail on
    # whatever panel this is, including one the layout has had to shrink.
    assert ctx.metrics.goodbye_destination > ctx.metrics.goodbye_thumbnail
    assert "Ready to go outside?" in ctx.speech.last_utterance


def test_goodbye_falls_back_to_the_generated_line_when_nothing_was_chosen(
    ctx: ShellContext,
) -> None:
    """The suggestion list is the fallback now, not the mechanism."""
    ctx.next_after = None
    screen = GoodbyeScreen(ctx)
    screen.on_enter()
    assert not screen.next_after_icon.get_visible()
    assert screen.made_line.get_label()
    assert not screen.made_line.get_label().startswith("Ready to")


def test_goodbye_asks_rather_than_instructs(ctx: ShellContext) -> None:
    """Coco's failure mode: "Coco will make you do it". Nothing here commands."""
    for option in ctx.config.next_after:
        if option.skips:
            continue  # it is a way out of the question, not an answer to it
        ctx.next_after = option
        screen = GoodbyeScreen(ctx)
        screen.on_enter()
        line = screen.headline.get_label()
        assert line.endswith("?")
        assert "must" not in line.lower() and "now it's time" not in line.lower()


# --- progressive disclosure (spec 7b, SYNTHESIS B2) ----------------------


def test_a_first_run_home_shows_six_tiles_including_all_done(tmp_path: Path) -> None:
    """Only when a parent has asked for it: ``show_everything`` defaults to
    true since 2026-08-23 (forum #9, #26, #40)."""
    ctx = _disclosure_ctx(tmp_path, sessions=0, activities=10, show_everything=False)
    names = _home_names(ctx)
    assert len(names) == 6
    assert ALL_DONE_NAME in names


def test_home_grows_by_one_tile_every_two_sessions(tmp_path: Path) -> None:
    for sessions, expected in ((0, 6), (1, 6), (2, 7), (4, 8), (10, 11)):
        ctx = _disclosure_ctx(tmp_path, sessions=sessions, activities=10, show_everything=False)
        assert len(_home_names(ctx)) == expected, sessions


def test_all_done_is_on_home_from_the_very_first_run(tmp_path: Path) -> None:
    """SYNTHESIS D5: a child who has had enough must always be able to say so."""
    for sessions in (0, 1, 2, 50):
        ctx = _disclosure_ctx(tmp_path, sessions=sessions, activities=10)
        assert ALL_DONE_NAME in _home_names(ctx)


def test_home_never_outgrows_the_allow_list(tmp_path: Path) -> None:
    ctx = _disclosure_ctx(tmp_path, sessions=500, activities=3, show_everything=False)
    assert len(_home_names(ctx)) == 4  # three activities plus All done


def test_show_everything_hands_over_the_whole_grid_at_once(tmp_path: Path) -> None:
    ctx = _disclosure_ctx(tmp_path, sessions=0, activities=10, show_everything=True)
    assert len(_home_names(ctx)) == 11


def test_the_revealed_tiles_are_the_first_ones_by_order(tmp_path: Path) -> None:
    """The parent's `order` decides what a child meets first, not chance."""
    ctx = _disclosure_ctx(tmp_path, sessions=0, activities=10, show_everything=False)
    assert [name for name in _home_names(ctx) if name != ALL_DONE_NAME] == [
        f"A{index}" for index in range(5)
    ]


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
    """SYNTHESIS G2: no lockout, no delay, no counter, no voice.

    And **no log either, on a shipped machine** (spec 7d #10): "a log of every
    time a child tried to get past a grown-up" is research, not product, so it
    is behind ``research.toml`` and that file ships false. What is asserted
    here is both halves -- silence by default, and no digits when a study has
    deliberately turned it on.
    """
    from kidnix_shell.research import ResearchConfig
    from kidnix_shell.screens.grownup import GrownupSheet

    sheet = GrownupSheet(ctx)
    ctx.speech.backend.spoken.clear()  # type: ignore[attr-defined]
    with caplog.at_level(logging.INFO, logger="kidnix_shell.screens.grownup"):
        for digit in "9999":
            sheet._push(digit)
    assert not [m for m in caplog.messages if m.startswith("grown-up gate")]

    ctx.research = ResearchConfig(enabled=True, pin_attempt_logging=True)
    caplog.clear()
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
        # The band window holds the band *and* the caption strip under it
        # (accessibility review B2): the lines that matter most are said while
        # an activity is covering the content window.
        band_box = window.band_window.get_content()
        assert window.band.get_parent() is band_box
        assert window.captions.get_parent() is band_box
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
        # The band *window* is the row of controls plus the caption strip:
        # gnome-kiosk gives it one rectangle and both live inside it.
        assert metrics.band_window_height == metrics.band_height + metrics.caption_height
        assert metrics.content_height == metrics.screen_height - metrics.band_window_height
        band_box = window.band_window.get_content()
        assert band_box.measure(Gtk.Orientation.VERTICAL, -1)[0] <= metrics.band_window_height
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
        # The strip the compositor is asked for is the band window's, which is
        # the row of controls *and* the caption strip under it.
        band = window.metrics.band_window_height
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
    from kidnix_shell.ritual import OfferAnswer

    window = build_window(tmp_path)
    try:
        _start_an_activity(window)
        window._present_ending_offer()

        assert _state(window) is State.IN_ACTIVITY
        assert window.band.offer_mode is True
        assert window.band.finish_this.get_visible() is True
        assert window.band.one_more.get_visible() is True
        # **They are added, not swapped in** (panel ruling, 2026-08-23; forum
        # #55, #57, #61): the visual timetable adds the "tidy up" card, it
        # never takes a card away to make room, and the band must not change
        # furniture at the one moment a child is being asked to stop.
        assert window.band.undo.get_visible() is True
        assert window.band.my_things.get_visible() is True
        assert window.band.back.get_visible() is True
        assert window.band.ear.get_visible() is True
        # And there is an event to notice: the reserved highlight, for 3 s.
        assert window.band.finish_this.has_css_class("kid-new")

        window.dismiss_offer(OfferAnswer.FINISH_THIS)
        assert window.band.offer_mode is False
        assert window.band.undo.get_visible() is True
        assert window.band.finish_this.get_visible() is False
        assert window.session.offer_answered is True
        # And the answer was consequential: put-away moved.
        assert window.session.put_away_deferred is True
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
        # Daytime is "resting"; the demo policy's bedtime is 23:59-00:00, so
        # this is the warm vocabulary rather than the night one (forum #17).
        dim = "sleeping" if window.session.policy.is_bedtime(datetime.now()) else "resting"
        assert window.band_window.has_css_class(dim)
        # And the *content* window takes it too: a class on a centred box paints
        # a small dark rectangle on full-brightness cream (forum #36, #38).
        assert window.has_css_class(dim)
        assert window.band_window.get_content() is not None  # still mapped
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


# --- accessibility: keyboard, captions, calm, targets (2026-08-23) --------
#
# The review's B1 in one sentence: "there is no keyboard route to Back, Undo,
# My Things, the Ear, the sun or the gate, ever." Tab does not cross toplevels
# and the band is a toplevel of its own, so the shell keeps the focus ring
# itself (kidnix_shell.keyboard) and `Keyboard.key` is an ordinary method --
# which is what makes a keyboard-only session testable without synthetic input.


#: What the "All done" tile *says*, which is what the ring carries. The tile's
#: written name is ``ALL_DONE_NAME``; a child hears the question.
ALL_DONE_SPEAK = "All done for today?"


def ring_names(window) -> list[str]:  # type: ignore[no-untyped-def]
    from kidnix_shell.keyboard import names

    return names(window.keys.refresh())


def test_the_focus_ring_crosses_both_toplevels_band_first(tmp_path: Path) -> None:
    from kidnix_shell.state import Event

    window = build_window(tmp_path)
    try:
        # On Home, where every band control is reachable. (On Who's here My
        # Things is insensitive -- the ring skips it, which is its own test.)
        window.machine.try_fire(Event.CHOOSE_PROFILE)
        window.machine.try_fire(Event.CHOOSE_NEXT_AFTER)
        names = ring_names(window)
        # Every band control, in the order they are drawn...
        assert names[:3] == ["Back", "Undo", "My Things"]
        assert "Say it again" in names
        assert "Grown-up. Hold this for three seconds." in names
        # ...and then the screen's, in the same one ring.
        band = window.band.controls()
        assert len(names) > len([c for c in band if c.get_visible()])
        assert names.index("Back") < names.index(window.keys.ring.first().speak_text)
    finally:
        window.shutdown()


def test_every_screen_puts_focus_on_one_of_its_own_controls(tmp_path: Path) -> None:
    """B1: nothing called ``grab_focus`` anywhere, so a fresh Home had **zero**
    FOCUSED nodes in the AT-SPI tree. Now every arrival lands somewhere."""
    from kidnix_shell.keyboard import FOCUS_CLASS
    from kidnix_shell.state import Event

    window = build_window(tmp_path)
    try:
        for event in (Event.CHOOSE_PROFILE, Event.CHOOSE_NEXT_AFTER):
            focused = window.keys.focused
            assert focused is not None, _state(window)
            assert focused.has_css_class(FOCUS_CLASS)
            assert focused.speak_text
            window.machine.try_fire(event)
        assert _state(window) is State.HOME
        assert window.keys.focused is not None
    finally:
        window.shutdown()


def test_tab_goes_round_the_ring_and_shift_tab_comes_back(tmp_path: Path) -> None:
    from gi.repository import Gdk

    window = build_window(tmp_path)
    try:
        window.keys.focus(window.band.back)
        window.keys.key(Gdk.KEY_Tab)
        assert window.keys.focused is window.band.undo
        window.keys.key(Gdk.KEY_Tab, shift=True)
        assert window.keys.focused is window.band.back
        # An arrow is the same model, not a second one: a child who finds the
        # arrows must not discover subtly different behaviour.
        window.keys.key(Gdk.KEY_Right)
        assert window.keys.focused is window.band.undo
    finally:
        window.shutdown()


def test_escape_is_back_and_means_what_back_means(tmp_path: Path) -> None:
    from gi.repository import Gdk

    window = build_window(tmp_path)
    try:
        window.choose_profile(window.ctx.config.profiles[0])
        assert _state(window) is State.NEXT_CHOICE
        window.keys.key(Gdk.KEY_Escape)
        assert _state(window) is State.CHOOSING
    finally:
        window.shutdown()


def test_a_whole_session_without_touching_the_mouse(tmp_path: Path) -> None:
    """**The B1 acceptance test.** Who's here -> What's next -> Home ->
    an activity -> Back -> All done -> Goodbye, on the keyboard alone.

    Every step is a real key going into the shell's real controller, and every
    activation is dispatched to whatever the ring is on -- which is the point:
    it works whether the compositor thinks the band or the content window has
    focus, because a child on a switch has no way to change that.
    """
    from gi.repository import Gdk

    window = build_window(tmp_path)

    def press_named(name: str) -> None:
        """Tab until the ring is on ``name``, then Enter. As a child would."""
        for _ in range(40):
            focused = window.keys.focused
            if focused is not None and getattr(focused, "speak_text", "") == name:
                window.keys.key(Gdk.KEY_Return)
                return
            window.keys.key(Gdk.KEY_Tab)
        raise AssertionError(f"{name!r} was never reachable: {ring_names(window)}")

    try:
        # S1 Who's here? -- the child's own face.
        assert _state(window) is State.CHOOSING
        press_named(window.ctx.config.profiles[0].name)
        assert _state(window) is State.NEXT_CHOICE

        # S1b What's next after? -- any of the pictures.
        press_named(window.ctx.config.next_after[0].speak_text)
        assert _state(window) is State.HOME

        # S2 Home -- launch the first activity, then leave it with Back.
        activity = window.ctx.activities[0]
        press_named(activity.speak_text)
        assert _state(window) is State.IN_ACTIVITY
        window.keys.key(Gdk.KEY_Escape)
        _wait_for_exit(window)
        assert _state(window) is State.HOME

        # ...and "All done" ends the session the way the child chose to.
        press_named(ALL_DONE_SPEAK)
        assert _state(window) in (State.PUT_AWAY, State.GOODBYE)
    finally:
        window.shutdown()


def test_the_grown_up_gate_has_a_real_key_hold(tmp_path: Path) -> None:
    """It was ``self.connect("clicked", lambda _b: None)`` -- a literal no-op.

    A parent with a tremor, a switch or one hand could not open the sheet at
    all. The keyboard route is the pointer route's full three seconds, so it
    is no easier than the gate it is a route to.
    """
    from kidnix_shell.access import HOLD_SECONDS

    window = build_window(tmp_path)
    try:
        gate = window.band.grownup
        assert gate.key_pressed() is True
        assert gate.has_css_class("holding")
        # Letting go early is not a hold.
        assert gate.key_released() is False
        assert not gate.has_css_class("holding")
        assert window._sheet is None
        assert gate._hold_seconds == HOLD_SECONDS
    finally:
        window.shutdown()


def test_five_presses_open_the_gate_for_a_switch_user(tmp_path: Path) -> None:
    """A switch is a button; it cannot say "and keep it down"."""
    from kidnix_shell.access import SWITCH_PRESSES

    window = build_window(tmp_path)
    try:
        gate = window.band.grownup
        for _ in range(SWITCH_PRESSES - 1):
            gate.key_pressed()
            assert gate.key_released() is False
        gate.key_pressed()
        assert gate.key_released() is True
    finally:
        window.shutdown()


def test_a_band_button_really_is_twenty_millimetres_wide(tmp_path: Path) -> None:
    """ADR-0011, measured rather than requested.

    The review measured 69 x 77 px against a 72 px request, because
    ``theme.css`` took ``margin: 0 4px`` off each side afterwards. What is
    asserted here is what GTK will actually give the widget.
    """
    from kidnix_shell.access import HOLD_SECONDS  # noqa: F401  (documents the gate)

    window = build_window(tmp_path)
    try:
        metrics = window.metrics
        with themed(window.ctx):
            for control in (
                window.band.back,
                window.band.undo,
                window.band.my_things,
                window.band.ear,
            ):
                width = control.measure(Gtk.Orientation.HORIZONTAL, -1)[0]
                height = control.measure(Gtk.Orientation.VERTICAL, -1)[0]
                assert metrics.mm_of(width) >= MIN_TARGET_MM - 0.05, control.speak_text
                assert metrics.mm_of(height) >= MIN_TARGET_MM - 0.05, control.speak_text
    finally:
        window.shutdown()


def test_the_caption_strip_mirrors_whatever_the_shell_says(tmp_path: Path) -> None:
    """B2, end to end: the hook is on ``speak`` itself, so this cannot be
    bypassed by a call site that forgot."""
    window = build_window(tmp_path)
    try:
        window.speech.speak("Draw is asking if you're done.")
        assert window.captions.text == "Draw is asking if you're done."
        # The 13 spoken-only lines the review listed, one of each shape.
        for line in (
            "You're home.",
            "Nothing to undo.",
            "That one didn't open. Let's try something else.",
            "That one isn't here any more.",
        ):
            window.speech.speak(line)
            assert window.captions.text == line
    finally:
        window.shutdown()


def test_a_muted_shell_still_captions_every_line(tmp_path: Path) -> None:
    """Silence is not a broken machine. It is also the deaf child's default."""
    from kidnix_shell.access import AccessConfig

    window = build_window(tmp_path)
    try:
        window.set_access(AccessConfig(mute=True))
        window.speech.speak("Let's keep that.")
        assert window.captions.text == "Let's keep that."
    finally:
        window.shutdown()


def test_the_caption_strip_never_covers_the_content_window(tmp_path: Path) -> None:
    """It is in the band window, and the content window gets what is left."""
    window = build_window(tmp_path)
    try:
        metrics = window.metrics
        assert window.captions.get_parent() is window.band_window.get_content()
        assert metrics.content_height + metrics.band_window_height == metrics.screen_height
    finally:
        window.shutdown()


def test_calm_mode_cuts_the_motion_and_most_of_the_sound(tmp_path: Path) -> None:
    from kidnix_shell.access import AccessConfig

    config = ParentConfig(access=AccessConfig(calm=True))
    window = build_window(tmp_path, config=config)
    try:
        assert window.stack.get_transition_duration() == 0
        assert window.band.reduced_motion is True
        assert window.ctx.reduced_motion is True
        assert window.has_css_class("calm")
        assert window.band_window.has_css_class("calm")
        # The offer still *arrives* -- the ring is not motion, it is the one
        # reserved colour saying "this, now" -- it simply does not scale in.
        window.band.set_offer_mode(True)
        assert window.band.finish_this.get_opacity() == 1.0
        assert window.band.finish_this.has_css_class("kid-new")
    finally:
        window.shutdown()


def test_the_dim_surfaces_are_painted_on_the_windows_not_on_a_box(tmp_path: Path) -> None:
    """M4/forum #36, #38: a class on a `halign: CENTER` box is a rectangle."""
    from kidnix_shell.state import Event

    window = build_window(tmp_path)
    try:
        window.machine.try_fire(Event.GOODNIGHT)
        assert _state(window) is State.SLEEPING
        dim = "sleeping" if window.session.policy.is_bedtime(datetime.now()) else "resting"
        assert window.has_css_class(dim)
        assert window.band_window.has_css_class(dim)
        assert window.screens["sleeping"].has_css_class(dim)
    finally:
        window.shutdown()


@pytest.mark.parametrize("screen", ["1280x800@102", "1366x768@96"])
def test_every_ritual_screen_fits_the_window_it_is_given(tmp_path: Path, screen: str) -> None:
    """S5/S8's fit budget: the UX designer reproduced "Ask for more time"
    clipped by the bottom edge and Sleeping as a box floating on cream.

    Home has been measured since v0.1.1; nothing else was. Every surface in the
    stack is measured here, at the two panels we ship for, against the *content
    window's* budget rather than the monitor's -- which since v0.1.5 is what
    gnome-kiosk actually gives it.
    """
    window = build_window(tmp_path, screen=screen)
    try:
        metrics = window.metrics
        for name, surface in window.screens.items():
            wide = surface.measure(Gtk.Orientation.HORIZONTAL, -1)[0]
            tall = surface.measure(Gtk.Orientation.VERTICAL, -1)[0]
            assert wide <= metrics.screen_width, (name, wide, metrics.describe())
            assert tall <= metrics.content_height, (name, tall, metrics.describe())
            # ...and nothing inside one overhangs it either.
            for child in walk(surface):
                assert child.measure(Gtk.Orientation.VERTICAL, -1)[0] <= metrics.content_height, (
                    name,
                    type(child).__name__,
                )
    finally:
        window.shutdown()


# --- S2b, the shelf (spec 7d #12) ---------------------------------------


def shelf_world(tmp_path: Path):  # type: ignore[no-untyped-def]
    """A shelf manifest and six children in two groups, on disk."""
    from kidnix_shell.activities import load_directory, resolve_shelves

    root = tmp_path / "manifests"
    children = root / "games"
    children.mkdir(parents=True)
    (root / "shelfy.toml").write_text(
        'schema = 1\nid = "shelfy"\nname = "Letters & numbers"\n'
        'audio_label = "Choose a game."\nkind = "shelf"\nchildren_dir = "games"\n'
        'exec = ["/bin/true"]\ncategory = "learn"\norder = 5\nage_band = "4-8"\n',
        encoding="utf-8",
    )
    rows = [
        ("aa", 10, "letters", "Letters"),
        ("bb", 20, "letters", "Letters"),
        ("cc", 30, "letters", "Letters"),
        ("dd", 40, "counting", "Counting"),
        ("ee", 50, "counting", "Counting"),
        ("ff", 60, "counting", "Counting"),
    ]
    for child_id, order, group, group_name in rows:
        (children / f"{child_id}.toml").write_text(
            f'schema = 1\nid = "shelfy.{child_id}"\nname = "Game {child_id.upper()}"\n'
            f'audio_label = "Game {child_id}."\nexec = ["/bin/true"]\ncategory = "learn"\n'
            f'order = {order}\nage_band = "4-8"\nshelf_group = "{group}"\n'
            f'shelf_group_name = "{group_name}"\nshelf_group_audio_label = "{group_name}"\n',
            encoding="utf-8",
        )
    activities = load_directory(root).activities
    return activities, resolve_shelves(activities)


def test_a_shelf_tile_opens_a_screen_rather_than_launching_its_exec(tmp_path: Path) -> None:
    """The shelf's ``exec`` is the fallback for a shell with no shelf screen.

    On this one it must never run: for GCompris that argv is a single curated
    activity and the bare command is the 198-activity menu the curation exists
    to close.
    """
    from kidnix_shell.state import State

    activities, shelves = shelf_world(tmp_path)
    window = build_window(tmp_path, shelves=shelves)
    try:
        window.ctx.activities = activities
        window.machine.state = State.HOME
        shelf = next(a for a in activities if a.is_shelf)
        window.open_shelf(shelf)
        assert _state(window) is State.SHELF
        assert not window.launcher.running
        assert window.screens["shelf"].shelf is shelf
    finally:
        window.shutdown()


def test_the_shelf_draws_one_group_a_page_and_speaks_the_heading(tmp_path: Path) -> None:
    from kidnix_shell.screens.shelf import ShelfScreen
    from kidnix_shell.state import State

    activities, shelves = shelf_world(tmp_path)
    window = build_window(tmp_path, shelves=shelves)
    try:
        window.ctx.activities = activities
        window.machine.state = State.HOME
        window.open_shelf(next(a for a in activities if a.is_shelf))
        screen = window.screens["shelf"]
        assert isinstance(screen, ShelfScreen)
        # Two groups of three, and each group is its own page.
        assert screen.pager.pages == 2
        assert screen.title.get_label() == "Letters"
        names = [b.speak_text for b in walk(screen) if isinstance(b, ActivityTile)]
        assert len(names) == 6  # every child has a tile, one page apart
        screen._on_page(1)
        assert screen.title.get_label() == "Counting"
        assert window.ctx.speech.last_utterance == "Counting"
    finally:
        window.shutdown()


def test_back_from_a_shelf_goes_home_and_not_out_of_the_session(tmp_path: Path) -> None:
    from kidnix_shell.state import State

    activities, shelves = shelf_world(tmp_path)
    window = build_window(tmp_path, shelves=shelves)
    try:
        window.ctx.activities = activities
        window.machine.state = State.HOME
        window.open_shelf(next(a for a in activities if a.is_shelf))
        window.on_back()
        assert _state(window) is State.HOME
    finally:
        window.shutdown()


def test_a_shelf_has_no_all_done_of_its_own(tmp_path: Path) -> None:
    """ "All done" has one cell, on Home (spec 7d #5). Two places to reach for
    the escape hatch is one place too many for a child who navigates by
    position."""
    from kidnix_shell.screens.home import ALL_DONE_ID
    from kidnix_shell.state import State

    activities, shelves = shelf_world(tmp_path)
    window = build_window(tmp_path, shelves=shelves)
    try:
        window.ctx.activities = activities
        window.machine.state = State.HOME
        window.open_shelf(next(a for a in activities if a.is_shelf))
        tiles = [t for t in walk(window.screens["shelf"]) if isinstance(t, ActivityTile)]
        assert tiles
        assert not any(ALL_DONE_ID in t.key for t in tiles)
    finally:
        window.shutdown()


def test_home_hides_a_shelf_with_nothing_on_it(tmp_path: Path) -> None:
    """The same rule as an activity that is not installed, one level up."""
    from kidnix_shell.screens.home import HomeScreen

    activities, _ = shelf_world(tmp_path)
    window = build_window(tmp_path, shelves={})  # no children resolved at all
    try:
        window.ctx.activities = activities
        home = window.screens["home"]
        assert isinstance(home, HomeScreen)
        assert not any(getattr(c, "is_shelf", False) for c in home.cells() if c is not None)
    finally:
        window.shutdown()


def test_an_activity_launched_from_a_shelf_comes_back_to_the_shelf(tmp_path: Path) -> None:
    from kidnix_shell.state import Event, State

    activities, shelves = shelf_world(tmp_path)
    window = build_window(tmp_path, shelves=shelves)
    try:
        window.ctx.activities = activities
        window.machine.state = State.HOME
        window.open_shelf(next(a for a in activities if a.is_shelf))
        window.machine.try_fire(Event.LAUNCH_ACTIVITY)
        assert _state(window) is State.IN_ACTIVITY
        window._activity_finished()
        assert _state(window) is State.SHELF
    finally:
        window.shutdown()


def test_leaving_a_shelf_for_home_forgets_it(tmp_path: Path) -> None:
    from kidnix_shell.state import State

    activities, shelves = shelf_world(tmp_path)
    window = build_window(tmp_path, shelves=shelves)
    try:
        window.ctx.activities = activities
        window.machine.state = State.HOME
        window.open_shelf(next(a for a in activities if a.is_shelf))
        window.on_back()
        assert window._shelf is None
    finally:
        window.shutdown()


# --- "tell me about it" (spec 7d #9) ------------------------------------


def voice_note():  # type: ignore[no-untyped-def]
    from kidnix_shell.speech import FakeScheduler
    from kidnix_shell.voice import FakeRecorder, VoiceNote

    class Player:
        def __init__(self) -> None:
            self.played: list[Path] = []

        def play(self, path: Path) -> bool:
            self.played.append(path)
            return True

        def close(self) -> None:
            pass

    scheduler = FakeScheduler()
    player = Player()
    note = VoiceNote(recorder=FakeRecorder(), scheduler=scheduler, player=player)
    return note, scheduler, player


def kept_entry(ctx: ShellContext, tmp_path: Path):  # type: ignore[no-untyped-def]
    """One thing in the Journal, with a thumbnail, as if just made."""
    source = write_png(tmp_path / "work" / "drawing.png")
    entry = ctx.journal.import_file(source, "scribble", activity_name="Scribble")
    assert entry is not None
    return entry


def test_the_mic_is_not_drawn_at_all_without_a_microphone(
    ctx: ShellContext, tmp_path: Path
) -> None:
    """**Degrade silently.** A mic that does nothing teaches a child that
    buttons lie -- the rule that took Ask out of the band (spec 7a)."""
    ctx.voice = None
    kept_entry(ctx, tmp_path)
    screen = PutAwayScreen(ctx)
    screen.on_enter()
    assert screen.mic is None
    assert not any(isinstance(w, MicButton) for w in walk(screen))


def test_the_mic_records_a_note_beside_the_drawing(ctx: ShellContext, tmp_path: Path) -> None:
    from kidnix_shell.voice import has_note

    note, _scheduler, player = voice_note()
    ctx.voice = note
    entry = kept_entry(ctx, tmp_path)

    screen = PutAwayScreen(ctx)
    screen.on_enter()
    assert screen.mic is not None
    assert screen.mic.get_visible()

    screen.mic.button.fire()
    assert note.recording
    assert screen.mic.meter.get_visible()

    # A *second* press, not the same one twice: `ChildButton` swallows a burst
    # inside DEBOUNCE_MS, which is the rule that stops eight clicks a second
    # becoming eight actions (SYNTHESIS A3).
    time.sleep(DEBOUNCE_MS / 1000.0 + 0.02)
    screen.mic.button.fire()
    assert not note.recording
    assert has_note(entry.directory)
    # ...and it plays back once, immediately.
    assert player.played == [entry.directory / "note.ogg"]
    assert not screen.mic.meter.get_visible()


def test_the_mic_stops_itself_after_twenty_seconds(ctx: ShellContext, tmp_path: Path) -> None:
    from kidnix_shell.voice import MAX_SECONDS, has_note

    note, scheduler, _player = voice_note()
    ctx.voice = note
    entry = kept_entry(ctx, tmp_path)
    screen = PutAwayScreen(ctx)
    screen.on_enter()
    assert screen.mic is not None

    screen.mic.button.fire()
    scheduler.advance(int(MAX_SECONDS * 1000) + 10)
    assert not note.recording
    assert has_note(entry.directory)


def test_put_away_invites_the_child_to_talk_and_captions_it(
    ctx: ShellContext, tmp_path: Path
) -> None:
    from kidnix_shell.widgets import MIC_SPEAK

    note, _scheduler, _player = voice_note()
    ctx.voice = note
    kept_entry(ctx, tmp_path)
    said: list[str] = []
    ctx.speech.on_caption = said.append
    screen = PutAwayScreen(ctx)
    screen.on_enter()
    # "Let's keep that." first, then the invitation as its own sentence, after
    # a beat -- `speak_then` runs on the speech manager's own scheduler.
    ctx.speech.scheduler.advance(20_000)  # type: ignore[attr-defined]
    assert said[0] == "Let's keep that."
    assert MIC_SPEAK in said


def test_there_is_no_mic_when_nothing_was_made(ctx: ShellContext, tmp_path: Path) -> None:
    """Nothing to attach a note to, and nothing to be told about."""
    note, _scheduler, _player = voice_note()
    ctx.voice = note
    screen = PutAwayScreen(ctx)
    screen.on_enter()
    assert screen.mic is not None
    assert not screen.mic.get_visible()


def test_a_journal_card_with_a_note_wears_an_ear(ctx: ShellContext, tmp_path: Path) -> None:
    from kidnix_shell.voice import NOTE_NAME

    entry = kept_entry(ctx, tmp_path)
    screen = JournalScreen(ctx)
    screen.refresh()
    images = [w for w in walk(screen) if isinstance(w, Gtk.Image)]
    assert not any(w.has_css_class("note-badge") for w in images)

    (entry.directory / NOTE_NAME).write_bytes(b"OggS...")
    screen.refresh()
    images = [w for w in walk(screen) if isinstance(w, Gtk.Image)]
    assert any(w.has_css_class("note-badge") for w in images)


def test_showing_a_grownup_plays_the_note_on_tap(ctx: ShellContext, tmp_path: Path) -> None:
    """ "Show a grown-up" is the moment the child says what a thing is, and
    their own voice saying it *is* the showing."""
    from kidnix_shell.voice import NOTE_NAME

    note, _scheduler, player = voice_note()
    ctx.voice = note
    entry = kept_entry(ctx, tmp_path)
    (entry.directory / NOTE_NAME).write_bytes(b"OggS...")

    screen = JournalScreen(ctx)
    screen.showing_mode = True
    screen.on_enter()
    screen._open(entry)
    assert player.played == [entry.directory / NOTE_NAME]
    # And the mic is now about that card, so a grown-up can ask for another.
    assert screen.mic is not None and screen.mic.get_visible()


def test_an_ordinary_journal_tap_still_resumes(ctx: ShellContext, tmp_path: Path) -> None:
    """Sugar's resume-not-open is untouched by any of this (08 section 2.1)."""
    note, _scheduler, player = voice_note()
    ctx.voice = note
    entry = kept_entry(ctx, tmp_path)
    screen = JournalScreen(ctx)
    screen.on_enter()
    screen._open(entry)
    assert player.played == []
    assert any(call == "resume_entry" for call, _ in ctx.host.calls)  # type: ignore[attr-defined]


# --- Undo, inside somebody else's program (spec 7d, and its limits) -----


def test_undo_inside_an_activity_says_where_the_childs_undo_is(tmp_path: Path) -> None:
    """The shell cannot inject a keystroke into another Wayland client, so the
    press is answered with a true sentence rather than a guess."""
    from kidnix_shell.state import State

    window = build_window(tmp_path)
    try:
        window.ctx.activities = [make_activity("draw", name="Draw")]
        window.machine.state = State.IN_ACTIVITY

        class Running:
            activity_id = "draw"

        window.launcher.current = Running()
        window.on_undo()
        assert window.ctx.speech.last_utterance == "Undo for Draw is in Draw's own buttons."
    finally:
        window.launcher.current = None
        window.shutdown()


def test_a_manifest_that_names_its_undo_key_gets_it_spoken(tmp_path: Path) -> None:
    from kidnix_shell.state import State

    window = build_window(tmp_path)
    try:
        window.ctx.activities = [make_activity("draw", name="Draw", undo_key="ctrl+z")]
        window.machine.state = State.IN_ACTIVITY

        class Running:
            activity_id = "draw"

        window.launcher.current = Running()
        window.on_undo()
        assert window.ctx.speech.last_utterance == "Undo in Draw is Control and Z."
    finally:
        window.launcher.current = None
        window.shutdown()


# --- S7's fit budget (the e2e's clipped Goodbye) ------------------------


@pytest.mark.parametrize("screen", ["1280x800@102", "1366x768@96", "1280x800@118"])
def test_goodbye_fits_with_everything_on_it(tmp_path: Path, screen: str) -> None:
    """**The regression the real-VM e2e photographed**
    (``docs/design/screenshots/e2e-goodbye-v2-clipped.png``): the "Show a
    grown-up" / "Goodnight" row cut off by the bottom edge of a 1280x800 panel.

    ``required_size()`` modelled Home, a titled grid and the chooser; S7 is a
    fourth shape and was not budgeted, so ``fit`` never shrank for it and the
    measured backstop met a tree taller than the content window. Measured here
    with the screen *full*: a destination, three thumbnails and a line of
    feedback, which is the state the e2e caught.
    """
    window = build_window(tmp_path, screen=screen)
    try:
        metrics = window.metrics
        window.ctx.next_after = window.ctx.config.next_after[0]
        for index in range(3):
            source = write_png(tmp_path / "work" / f"drawing{index}.png", colour=(index * 60, 0, 0))
            window.journal.import_file(source, "a0", activity_name="Scribble")

        goodbye = window.screens["goodbye"]
        goodbye.on_enter()

        tall = goodbye.measure(Gtk.Orientation.VERTICAL, -1)[0]
        wide = goodbye.measure(Gtk.Orientation.HORIZONTAL, -1)[0]
        assert tall <= metrics.content_height, (tall, metrics.describe())
        assert wide <= metrics.screen_width, (wide, metrics.describe())

        # The two controls that end the session are fully inside the window,
        # and each is still a 20 mm target (ADR-0011).
        for button in (goodbye.show_button, goodbye.goodnight_button):
            height = button.measure(Gtk.Orientation.VERTICAL, -1)[0]
            assert metrics.mm_of(height) >= 20.0, metrics.mm_of(height)
            assert height <= metrics.content_height

        # And the arithmetic agrees with the tree, which is the point of
        # budgeting it: a backstop that has to close the same gap every boot
        # is a model that is wrong.
        _, budget = metrics.goodbye_size()
        assert budget <= metrics.screen_height, (budget, metrics.describe())
    finally:
        window.shutdown()


def test_the_goodbye_buttons_keep_the_border_the_e2e_looks_for(tmp_path: Path) -> None:
    """``pixels.find_box`` reads the thin-top/thick-bottom asymmetry, so the
    ritual class is load-bearing for the test suite as well as for the child."""
    window = build_window(tmp_path)
    try:
        goodbye = window.screens["goodbye"]
        for button in (goodbye.show_button, goodbye.goodnight_button):
            assert button.has_css_class("ritual")
    finally:
        window.shutdown()


def test_the_thumbnails_are_what_goodbye_spends_first(tmp_path: Path) -> None:
    """The ruling's hierarchy, as arithmetic: the destination and the buttons
    scale with the whole layout, the thumbnails are chrome."""
    from dataclasses import replace

    from kidnix_shell.metrics import Metrics

    roomy = Metrics.for_screen(1920, 1080, dpi=96.0)
    tight = replace(roomy, chrome_fit=0.45)
    assert tight.goodbye_thumbnail < roomy.goodbye_thumbnail
    assert tight.goodbye_destination == roomy.goodbye_destination
    assert tight.goodbye_button == roomy.goodbye_button
    # ...and never below a floor, on either.
    assert tight.mm_of(tight.goodbye_thumbnail) >= 13.9
    assert tight.mm_of(tight.goodbye_button) >= 20.0


# --- the gate on a machine nobody has set up (spec 7d #11) --------------


def test_the_gate_opens_on_choose_a_pin_when_there_is_none(ctx: ShellContext) -> None:
    """**Mags's sentence, as a test**: "make it refuse to start until I have
    picked my own four numbers, and please let me pick them somewhere he is not
    looking" (forum #56).

    The image ships ``parent.toml`` with no ``pin_hash``, so there is no pad to
    type the documented 1234 into first: the sheet opens on the flow that sets
    one, and nothing else is reachable until it is done.
    """
    from kidnix_shell.screens.grownup import NO_PIN_TITLE, GrownupSheet

    ctx.config = ParentConfig()  # i.e. the shipped state: no PIN
    assert ctx.config.must_set_pin
    sheet = GrownupSheet(ctx)
    assert sheet._stack.get_visible_child_name() == "pin"
    assert sheet._pin_title.get_label() == NO_PIN_TITLE
    assert sheet._pin_help.get_visible()


def test_the_mandatory_flow_cannot_be_escaped_into_the_actions(ctx: ShellContext) -> None:
    """Cancel is a way out of the *screen*, never a way past it."""
    from kidnix_shell.screens.grownup import GrownupSheet

    ctx.config = ParentConfig()
    sheet = GrownupSheet(ctx)
    sheet._cancel_pin()
    assert sheet._stack.get_visible_child_name() == "pin"


def test_choosing_a_pin_twice_closes_the_gate(ctx: ShellContext) -> None:
    """Typed twice, and only a match counts. Once it is chosen the gate is
    closed **for this session** whether or not the root-owned file could be
    written -- the sheet says which of the two happened, and never pretends."""
    from kidnix_shell.screens.grownup import GrownupSheet

    ctx.config = ParentConfig()
    sheet = GrownupSheet(ctx)

    for digit in "8471":
        sheet._push(digit)
    for digit in "8470":  # a mismatch: start again, still on the flow
        sheet._push(digit)
    assert sheet._stack.get_visible_child_name() == "pin"
    assert ctx.config.must_set_pin

    for digit in "8471":
        sheet._push(digit)
    for digit in "8471":
        sheet._push(digit)
    assert not ctx.config.must_set_pin
    assert ctx.config.check_pin("8471")
    assert not ctx.config.check_pin(DEFAULT_PIN)
    assert sheet._stack.get_visible_child_name() == "actions"
    # And it says, in writing, what actually happened to the file.
    assert sheet._pin_message.get_visible()


def test_a_configured_machine_opens_on_the_ordinary_pad(ctx: ShellContext) -> None:
    from kidnix_shell.screens.grownup import GrownupSheet

    ctx.config.set_pin("2468")
    sheet = GrownupSheet(ctx)
    assert sheet._stack.get_visible_child_name() == "pin"
    assert sheet._pin_title.get_label() == "Enter the grown-up PIN"
    assert not sheet._pin_help.get_visible()
    for digit in "2468":
        sheet._push(digit)
    assert sheet._stack.get_visible_child_name() == "actions"


# --- the burst-click detector, on the real windows ----------------------


def test_the_shell_watches_for_presses_that_hit_nothing(tmp_path: Path) -> None:
    """The detector is wired on both toplevels, unconditionally, and logs
    nothing on a machine that is not part of a study (spec 7d #10)."""
    from kidnix_shell.research import BURST_LOG_PREFIX

    window = build_window(tmp_path)
    try:
        assert not window.research.burst_logging
        for at in range(4):
            window.bursts.press(at * 0.2, on_target=False)
        assert window.bursts.bursts == 1
    finally:
        window.shutdown()
    assert BURST_LOG_PREFIX == "burst-click"
