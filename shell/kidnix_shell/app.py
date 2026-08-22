"""The application: one window, one band, one stack of surfaces.

Everything that changes state passes through :class:`ShellWindow`, which is the
only thing that touches the state machine, the session and the launcher. The
screens ask; this decides.
"""

from __future__ import annotations

import logging
import os
import subprocess
import time
from datetime import datetime
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gdk, GLib, Gtk  # noqa: E402

from .activities import Activity  # noqa: E402
from .band import Band, BandActions  # noqa: E402
from .context import ShellContext  # noqa: E402
from .journal import Entry, Journal, JournalImporter, JournalWatcher  # noqa: E402
from .launcher import AUTOSAVE_GRACE_SECONDS, Launcher, RunningActivity  # noqa: E402
from .metrics import Metrics, ScreenOverride, detect_metrics  # noqa: E402
from .screens import Screen  # noqa: E402
from .screens.ending import EndingOfferScreen, PutAwayScreen  # noqa: E402
from .screens.goodbye import GoodbyeScreen  # noqa: E402
from .screens.grownup import GrownupSheet  # noqa: E402
from .screens.home import HomeScreen  # noqa: E402
from .screens.journal import JournalScreen  # noqa: E402
from .screens.sleeping import SleepingScreen  # noqa: E402
from .screens.whos_here import WhosHereScreen  # noqa: E402
from .session import (  # noqa: E402
    DailyUsage,
    Phase,
    Session,
    SessionPolicy,
    StartRefusal,
    budget_day,
)
from .settings import ParentConfig, Paths, Profile  # noqa: E402
from .sound import BACK, KEEP, SLEEP, TAP, Earcons  # noqa: E402
from .speech import GLibScheduler, SpeechManager, select_backend  # noqa: E402
from .state import Event, State, StateMachine  # noqa: E402
from .theme import dynamic_css  # noqa: E402
from .widgets import SpeechUI  # noqa: E402

log = logging.getLogger(__name__)

APP_ID = "org.kidnix.Shell"
TICK_MS = 500
#: S7: "Show a grown-up" borrows My Things for two minutes, then comes back.
SHOWING_SECONDS = 120
#: Spec 7a: Back on Put away is dead for three seconds, so a child cannot
#: undo the ritual by drumming on the band -- and then it works, so an
#: accidental "All done" is recoverable.
PUT_AWAY_BACK_LOCK_SECONDS = 3.0
#: How long "Let's keep that" is on screen when the *child* ended the session
#: (the clock-driven path is timed by the session itself). Long enough to see
#: the work fly into My Things, and to cover the SIGTERM grace.
PUT_AWAY_SECONDS = 6
#: Re-measure the monitor every few ticks: a child's machine gets a projector
#: plugged into it, and the shell has to still fit afterwards.
MONITOR_CHECK_TICKS = 8
#: How many times the measured-overflow backstop may shrink the layout.
MAX_FIT_ATTEMPTS = 3


def _signature(metrics: Metrics) -> tuple[int, int, int, int]:
    """What has to change before the layout is worth rebuilding."""
    return (
        metrics.screen_width,
        metrics.screen_height,
        round(metrics.dpi),
        metrics.scale_factor,
    )


STATE_TO_SCREEN = {
    State.CHOOSING: "choosing",
    State.HOME: "home",
    State.JOURNAL: "journal",
    State.SHOWING: "journal",
    State.IN_ACTIVITY: "home",  # the shell sits behind the activity's window
    State.ENDING_OFFER: "ending",
    State.PUT_AWAY: "put_away",
    State.GOODBYE: "goodbye",
    State.SLEEPING: "sleeping",
    State.GROWNUP: "home",  # the sheet is a dialog over whatever is underneath
}


class ShellWindow(Adw.ApplicationWindow):
    """The child's whole computer."""

    def __init__(
        self,
        application: Adw.Application,
        *,
        paths: Paths,
        config: ParentConfig,
        policy: SessionPolicy,
        activities: list[Activity],
        demo: bool = False,
        fullscreen: bool = True,
        speech_backend: str | None = None,
        screen: ScreenOverride | None = None,
    ) -> None:
        super().__init__(application=application)
        self.set_title("kidnix")
        self.add_css_class("kidnix")

        self.paths = paths
        self.demo = demo
        self._screen_override = screen
        self._fit_attempts = 0
        self.metrics: Metrics = detect_metrics(screen)
        self._signature = _signature(self.metrics)
        log.info("display metrics: %s", self.metrics.describe())

        # -- services --
        self.speech = SpeechManager(
            backend=select_backend(speech_backend), scheduler=GLibScheduler()
        )
        log.info("read-aloud backend: %s", self.speech.backend.name)
        self.speech_ui = SpeechUI(self.speech)
        # /usr is read-only on the image, so the generated earcons land in the
        # child's cache when the package directory cannot be written.
        self.earcons = Earcons(cache_dir=paths.sounds_cache)

        self.journal = Journal(paths.journal_root)
        self.journal.load()
        self.importer = JournalImporter(self.journal, activities)
        self.watcher = JournalWatcher(self.importer, on_import=self._on_new_work)

        usage = DailyUsage.for_now(paths.usage_state, datetime.now())
        self.session = Session(policy=policy, usage=usage)
        self.launcher = Launcher(paths.home)
        self.launcher.on_exit = self._on_activity_exit

        self.machine = StateMachine(State.CHOOSING, on_change=self._on_state_change)
        self._offer_window: Gtk.Window | None = None
        self._sheet: GrownupSheet | None = None
        self._showing_handle: int | None = None
        self._kill_handle: int | None = None
        self._goodbye_handle: int | None = None
        self._slept_at: datetime | None = None
        self._back_locked_until = 0.0
        self._ticks = 0

        profile = config.profiles[0]
        self.ctx = ShellContext(
            metrics=self.metrics,
            speech=self.speech,
            speech_ui=self.speech_ui,
            journal=self.journal,
            session=self.session,
            config=config,
            paths=paths,
            earcons=self.earcons,
            host=self,
            activities=activities,
            profile=profile,
            demo=demo,
        )

        # -- layout --
        self._load_css()
        self._build_content()

        if fullscreen:
            self.fullscreen()
        else:
            # Development window: big enough to look like the real thing,
            # never bigger than the panel it is on.
            needed_width, needed_height = self.metrics.required_size()
            width = max(needed_width, 1366)
            height = max(needed_height, 768)
            if self.metrics.screen_width and self.metrics.screen_height:
                width = min(width, self.metrics.screen_width)
                height = min(height, self.metrics.screen_height)
            self.set_default_size(width, height)

        # Keyboard is never required, but Escape must never be a trap either.
        self.connect("close-request", self._on_close)

        self.watcher.start()
        self._tick_handle = GLib.timeout_add(TICK_MS, self._tick)
        self._show_state()
        self._check_measured_fit()
        # Render the earcons (about 13 ms) off the first frame rather than off
        # the first thing the child presses.
        GLib.idle_add(self._warm_earcons)

    # -- appearance ---------------------------------------------------

    def _load_css(self) -> None:
        provider = Gtk.CssProvider()
        provider.load_from_path(str(Path(__file__).parent / "theme.css"))
        display = Gdk.Display.get_default()
        if display is not None:
            Gtk.StyleContext.add_provider_for_display(
                display, provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
            )
        self._tint_provider = Gtk.CssProvider()
        if display is not None:
            Gtk.StyleContext.add_provider_for_display(
                display, self._tint_provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION + 1
            )

    def _apply_tint(self, profile: Profile) -> None:
        """Colour = whose it is (08 section 3.4), and type at the layout's scale."""
        self._tint_provider.load_from_string(dynamic_css(self.metrics, profile))

    # -- fitting the screen -------------------------------------------

    def _build_content(self) -> None:
        """(Re)build the band and every screen at the current metrics.

        Called once at startup and again whenever the metrics change -- a
        different monitor, or the measured-overflow backstop below. Screens own
        no state that outlives them (everything lives in the Journal, the
        session and the state machine), so throwing them away is safe.
        """
        self.speech_ui.forget_all()
        self.ctx.metrics = self.metrics
        self._apply_tint(self.ctx.profile)

        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.band = Band(
            self.metrics,
            self.speech_ui,
            BandActions(
                on_back=self.on_back,
                on_undo=self.on_undo,
                on_my_things=self.open_journal,
                on_ear=self.on_ear,
                on_grownup=self.open_grownup,
                on_ask=self.on_ask,
            ),
        )
        root.append(self.band)

        self.stack = Gtk.Stack()
        self.stack.set_transition_duration(400)
        self.stack.set_transition_type(Gtk.StackTransitionType.SLIDE_LEFT_RIGHT)
        self.stack.set_vexpand(True)
        self.screens: dict[str, Screen] = {
            "choosing": WhosHereScreen(self.ctx),
            "home": HomeScreen(self.ctx),
            "journal": JournalScreen(self.ctx),
            "ending": EndingOfferScreen(self.ctx),
            "put_away": PutAwayScreen(self.ctx),
            "goodbye": GoodbyeScreen(self.ctx),
            "sleeping": SleepingScreen(self.ctx),
        }
        for name, screen in self.screens.items():
            self.stack.add_named(screen, name)
        root.append(self.stack)
        self._root = root
        self.set_content(root)

    def _apply_metrics(self, metrics: Metrics) -> None:
        log.info("relaying out: %s", metrics.describe())
        self.metrics = metrics
        self._build_content()
        self._show_state()

    def _check_measured_fit(self) -> None:
        """Belt to the arithmetic's braces: measure, and shrink if we overflow.

        :mod:`kidnix_shell.metrics` models the layout, but CSS padding, font
        metrics and icon sizes are GTK's business, not ours. So after building,
        ask GTK how big the thing actually wants to be, and if that is larger
        than the monitor, shrink and rebuild. This is what makes "the shell
        never exceeds the monitor" a fact rather than an intention.
        """
        screen_width = self.metrics.screen_width
        screen_height = self.metrics.screen_height
        if not screen_width or not screen_height:
            return
        if self._fit_attempts >= MAX_FIT_ATTEMPTS:
            return
        try:
            wanted_width = self._root.measure(Gtk.Orientation.HORIZONTAL, -1)[0]
            wanted_height = self._root.measure(Gtk.Orientation.VERTICAL, -1)[0]
        except Exception as exc:  # pragma: no cover - measuring must never fail
            log.debug("could not measure the layout (%s)", exc)
            return
        if wanted_width <= screen_width and wanted_height <= screen_height:
            log.info(
                "layout measures %dx%d, fits %dx%d",
                wanted_width,
                wanted_height,
                screen_width,
                screen_height,
            )
            return
        ratio = min(screen_width / wanted_width, screen_height / wanted_height) * 0.99
        self._fit_attempts += 1
        log.warning(
            "layout measures %dx%d but the monitor is %dx%d; shrinking by %.3f",
            wanted_width,
            wanted_height,
            screen_width,
            screen_height,
            ratio,
        )
        self._apply_metrics(self.metrics.shrunk_by(ratio))
        self._check_measured_fit()

    def _check_monitor(self) -> None:
        """The panel may change under us (a projector, a dock, a hotplug)."""
        metrics = detect_metrics(self._screen_override)
        signature = _signature(metrics)
        if signature == self._signature:
            return
        log.info("the monitor changed: %s", metrics.describe())
        self._signature = signature
        self._fit_attempts = 0
        self._apply_metrics(metrics)
        self._check_measured_fit()

    # -- state --------------------------------------------------------

    def _on_state_change(self, previous: State, current: State, event: Event) -> None:
        log.info("state %s -> %s (%s)", previous.value, current.value, event.value)
        if current is State.SLEEPING:
            self._slept_at = datetime.now()
        elif previous is State.SLEEPING:
            self._slept_at = None
        self._show_state()

    def _show_state(self) -> None:
        state = self.machine.state
        name = STATE_TO_SCREEN[state]
        journal_screen = self.screens["journal"]
        assert isinstance(journal_screen, JournalScreen)
        journal_screen.showing_mode = state is State.SHOWING

        previous = self.stack.get_visible_child_name()
        if previous != name:
            # Forward through the ritual, backward towards Home: the direction
            # of the slide is the child's sense of where they are.
            forward = state not in (State.HOME, State.CHOOSING)
            self.stack.set_transition_type(
                Gtk.StackTransitionType.SLIDE_LEFT
                if forward
                else Gtk.StackTransitionType.SLIDE_RIGHT
            )
            if previous is not None and previous in self.screens:
                self.screens[previous].on_leave()
            self.stack.set_visible_child_name(name)

        self.band.set_visible(state is not State.SLEEPING)
        self.band.set_journal_sensitive(state in (State.HOME, State.JOURNAL, State.IN_ACTIVITY))
        if state is not State.IN_ACTIVITY:
            self.screens[name].on_enter()

    # -- the tick -----------------------------------------------------

    def _tick(self) -> bool:
        now = datetime.now()
        self.launcher.check()
        self._ticks += 1
        if self._ticks % MONITOR_CHECK_TICKS == 0:
            self._check_monitor()

        if self.session.running:
            self.band.set_progress(self.session.fraction_spent(now), self.session.is_warm(now))
            self._advance_ritual(self.session.phase(now))
        else:
            self.band.set_progress(0.0, False)
            self._maybe_wake(now)
        return True  # GLib.SOURCE_CONTINUE

    def _maybe_wake(self, now: datetime) -> None:
        """Spec 7a: Sleeping ends at the next allowed window, a new day, or the gate.

        Deliberately *not* "as soon as there is budget left": Goodnight means
        the sitting is over, and re-waking thirty seconds later would teach a
        child that the ending is negotiable. The shell wakes on its own when
        the budget day has rolled (04:00, :func:`session.budget_day`) or when
        the bedtime window that put it to sleep has ended. Anything sooner is
        the grown-up's decision, from the gate.
        """
        if self.machine.state is not State.SLEEPING or self._slept_at is None:
            return
        if self.session.may_start(now) is not StartRefusal.OK:
            return
        new_day = budget_day(now) != budget_day(self._slept_at)
        window_over = self.session.policy.is_bedtime(self._slept_at)
        if new_day or window_over:
            log.info("waking: the session is allowed again")
            self.machine.try_fire(Event.WAKE)

    def _advance_ritual(self, phase: Phase) -> None:
        state = self.machine.state
        if state is State.GROWNUP:
            return  # never yank the sheet out from under a parent mid-task
        if phase is Phase.ENDING_OFFER and state in (
            State.HOME,
            State.IN_ACTIVITY,
            State.JOURNAL,
        ):
            self._present_ending_offer()
        elif phase is Phase.PUT_AWAY and state in (
            State.HOME,
            State.IN_ACTIVITY,
            State.JOURNAL,
            State.ENDING_OFFER,
        ):
            self._begin_put_away()
        elif phase is Phase.ENDED and state is State.PUT_AWAY:
            self.session.end(datetime.now())
            self.machine.try_fire(Event.GOODBYE_DUE)

    # -- the ending ritual --------------------------------------------

    def _present_ending_offer(self) -> None:
        self.machine.try_fire(Event.ENDING_OFFER_DUE)
        if not self.launcher.running:
            return
        # Spec S5: with an activity on screen the shell raises the offer as its
        # own window -- under gnome-kiosk the newest window is on top -- and
        # closes it again afterwards so the activity comes back.
        window = Gtk.Window(application=self.get_application())
        window.set_title("kidnix")
        window.add_css_class("kidnix")
        window.set_child(EndingOfferScreen(self.ctx))
        window.fullscreen()
        window.present()
        self._offer_window = window

    def _begin_put_away(self, event: Event = Event.PUT_AWAY_DUE) -> None:
        self._close_offer_window()
        if not self.machine.try_fire(event) and self.machine.state is not State.PUT_AWAY:
            return
        # Spec 7a: three seconds of dead Back, so the ritual is not undone by a
        # child drumming on the band -- and then Back works again.
        self._back_locked_until = time.monotonic() + PUT_AWAY_BACK_LOCK_SECONDS
        self.present()  # take the screen back from the activity
        # Sweep first so the thing the child just made is in the Journal before
        # the animation claims to have put it there.
        self.watcher.sweep_now()
        if self.launcher.request_stop():
            self._kill_handle = GLib.timeout_add(
                int(AUTOSAVE_GRACE_SECONDS * 1000), self._force_kill
            )
        self.earcons.play(KEEP, speaking=True)

    def _force_kill(self) -> bool:
        self._kill_handle = None
        self.launcher.force_stop()
        self.watcher.sweep_now()
        return False

    def _close_offer_window(self) -> None:
        if self._offer_window is not None:
            self._offer_window.close()
            self._offer_window = None

    # -- ShellHost ----------------------------------------------------

    def choose_profile(self, profile: Profile) -> None:
        # Only Who's here? offers profiles; refuse anywhere else rather than
        # quietly starting a clock behind a screen that is not asking.
        if not self.machine.can(Event.CHOOSE_PROFILE):
            return
        self.ctx.profile = profile
        self._apply_tint(profile)
        now = datetime.now()
        refusal = self.session.may_start(now)
        if refusal is not StartRefusal.OK:
            self._refuse(refusal)
            return
        self.session.start(now)
        self.machine.try_fire(Event.CHOOSE_PROFILE)

    def _refuse(self, refusal: StartRefusal) -> None:
        """No silent denials, and no adult error messages (SYNTHESIS C3)."""
        if refusal is StartRefusal.BEDTIME:
            self.speech.speak("It's night time. kidnix is going to sleep.")
        else:
            self.speech.speak("That's all the time for today. See you tomorrow.")
        self.machine.try_fire(Event.GOODNIGHT)

    def launch(self, activity: Activity, resume: Path | None = None) -> None:
        # No launching from the ending ritual or from Sleeping: an activity
        # that started there would end up on top of a screen with no way back.
        if self.launcher.running or not self.machine.can(Event.LAUNCH_ACTIVITY):
            return
        running = self.launcher.launch(activity, resume)
        if running is None:
            # C3: back to a known-good state with a friendly line.
            self.speech.speak("That one didn't want to open. Try another.")
            return
        self.earcons.play(TAP)
        self.machine.try_fire(Event.LAUNCH_ACTIVITY)

    def resume_entry(self, entry: Entry) -> None:
        activity = next((a for a in self.ctx.activities if a.id == entry.activity_id), None)
        if activity is None:
            self.speech.speak("That one isn't here any more.")
            return
        path = entry.latest_path if activity.supports_resume else None
        self.launch(activity, path)

    def _on_activity_exit(self, running: RunningActivity, code: int) -> None:
        log.info("%s finished (%s)", running.activity_id, code)
        self.present()
        kept = self.watcher.sweep_now()
        if kept:
            self.earcons.play(KEEP)
        if self.machine.state is State.IN_ACTIVITY:
            self.machine.try_fire(Event.ACTIVITY_EXITED)

    def _on_new_work(self, entries: list[Entry]) -> None:
        log.info("kept %d new thing(s)", len(entries))
        self.earcons.play(KEEP)

    def go_home(self) -> None:
        self.machine.try_fire(Event.BACK)

    def open_journal(self) -> None:
        self.machine.try_fire(Event.OPEN_JOURNAL)

    def open_grownup(self) -> None:
        if self._sheet is not None:
            return
        self.machine.try_fire(Event.OPEN_GROWNUP)
        self._sheet = GrownupSheet(self.ctx)
        self._sheet.present(self)

    def close_grownup(self) -> None:
        self._sheet = None
        self.machine.try_fire(Event.CLOSE_GROWNUP)

    def dismiss_offer(self, one_last_thing: bool) -> None:
        self._close_offer_window()
        if one_last_thing:
            self.speech.speak("One last little thing, then.")
        self.machine.try_fire(Event.DISMISS_OFFER)

    def finish_now(self) -> None:
        """Child- or grown-up-initiated ending: the same ritual, never a cut.

        The Home "All done" tile and the grown-up sheet's "End session now" are
        the same path. The clock is not involved, so Goodbye has to be timed
        here rather than waiting for :class:`Phase.ENDED`.
        """
        self._begin_put_away(Event.IM_FINISHED)
        if self.machine.state is not State.PUT_AWAY:
            return
        if self._goodbye_handle is not None:
            GLib.source_remove(self._goodbye_handle)
        self._goodbye_handle = GLib.timeout_add_seconds(PUT_AWAY_SECONDS, self._goodbye_now)

    def _goodbye_now(self) -> bool:
        self._goodbye_handle = None
        # If the child took the recovery route (Back on Put away) we are not
        # in the ritual any more and must not drag them into Goodbye.
        if self.machine.state is State.PUT_AWAY:
            self.session.end(datetime.now())
            self.machine.try_fire(Event.GOODBYE_DUE)
        return False

    def show_a_grownup(self) -> None:
        if not self.machine.try_fire(Event.SHOW_A_GROWNUP):
            return
        if self._showing_handle is not None:
            GLib.source_remove(self._showing_handle)
        self._showing_handle = GLib.timeout_add_seconds(SHOWING_SECONDS, self._showing_done)

    def _showing_done(self) -> bool:
        self._showing_handle = None
        self.machine.try_fire(Event.SHOWING_DONE)
        return False

    def goodnight(self) -> None:
        self.session.end(datetime.now())
        if self.machine.try_fire(Event.GOODNIGHT):
            self.earcons.play(SLEEP, speaking=True)

    def start_session(self, minutes: int | None = None) -> None:
        now = datetime.now()
        length = None if minutes is None else minutes * 60
        if not self.session.start(now, length):
            self._refuse(self.session.may_start(now))
            return
        self.machine.try_fire(Event.START_SESSION)

    def add_minutes(self, minutes: int) -> None:
        added = self.session.add_minutes(minutes, datetime.now())
        if added and self.machine.state in (State.GOODBYE, State.PUT_AWAY, State.SLEEPING):
            self.machine.try_fire(Event.START_SESSION)

    def logout(self) -> None:
        log.info("logging out at the grown-up's request")
        # gnome-session is what GDM started us under; falling back to quitting
        # is right because the session's only window going away ends it too.
        for argv in (["gnome-session-quit", "--logout", "--no-prompt"],):
            try:
                subprocess.Popen(argv)
                return
            except OSError:
                continue
        application = self.get_application()
        if application is not None:
            application.quit()

    def speak(self, text: str) -> None:
        self.speech.speak(text)

    # -- band actions --------------------------------------------------

    def on_back(self) -> None:
        if self.machine.state is State.HOME:
            self.speech.speak("You're home.")
            return
        if self.machine.state is State.PUT_AWAY and time.monotonic() < self._back_locked_until:
            # Three seconds of nothing (spec 7a). Not greyed out, not moved,
            # not hidden: the band never changes shape under a child.
            return
        self.earcons.play(BACK)
        self.machine.try_fire(Event.BACK)

    def on_undo(self) -> None:
        """Undo is on every surface (spec 7a) and honest when it is empty.

        A control that appears and disappears costs a five-year-old more than
        one that is always in the same place and sometimes says "Nothing to
        undo" -- spatial stability beats availability signalling here.
        """
        journal_screen = self.screens["journal"]
        in_journal = self.machine.state is State.JOURNAL
        if in_journal and isinstance(journal_screen, JournalScreen) and journal_screen.undo_star():
            return
        self.speech.speak("Nothing to undo.")

    def on_ear(self) -> None:
        if not self.speech.repeat():
            self.speech.speak("I haven't said anything yet.")

    def on_ask(self) -> None:
        self.speech.speak("Asking a grown-up is coming soon.")

    def _warm_earcons(self) -> bool:
        self.earcons.ensure_sounds()
        return False

    # -- development helpers -------------------------------------------

    def capture(self, path: Path) -> bool:
        """Save a PNG of our own window (development and design review).

        GNOME 45+ restricts ``org.gnome.Shell.Screenshot`` to the Shell's own
        UI and Mutter implements no wlr-screencopy, so no external tool can
        photograph the kiosk. Rendering our *own* widget tree needs no
        permission at all: paint it into a snapshot and hand the node to the
        renderer we are already using.
        """
        try:
            from gi.repository import Gsk  # noqa: F401  -- ensures the typelib

            width = self.get_width() or self.metrics.screen_width or 1280
            height = self.get_height() or self.metrics.screen_height or 800
            paintable = Gtk.WidgetPaintable.new(self)
            snapshot = Gtk.Snapshot()
            paintable.snapshot(snapshot, width, height)
            node = snapshot.to_node()
            native = self.get_native()
            renderer = native.get_renderer() if native is not None else None
            if node is None or renderer is None:
                log.warning("nothing to capture yet")
                return False
            texture = renderer.render_texture(node, None)
            path.parent.mkdir(parents=True, exist_ok=True)
            texture.save_to_png(str(path))
            log.info("wrote %s (%dx%d)", path, width, height)
            return True
        except Exception as exc:
            log.warning("could not capture the window: %s", exc)
            return False

    # -- shutdown ------------------------------------------------------

    def _on_close(self, _window: Gtk.Window) -> bool:
        self.shutdown()
        return False

    def shutdown(self) -> None:
        for handle in (
            self._tick_handle,
            self._showing_handle,
            self._kill_handle,
            self._goodbye_handle,
        ):
            if handle is not None:
                GLib.source_remove(handle)
        self._tick_handle = None
        self._showing_handle = None
        self._kill_handle = None
        self._goodbye_handle = None
        self.watcher.stop()
        self.launcher.stop()
        self.session.end(datetime.now())
        self.speech.close()
        self.earcons.close()


class ShellApplication(Adw.Application):
    """One window, no menus, no about dialog, no preferences for the child."""

    def __init__(
        self,
        *,
        paths: Paths,
        config: ParentConfig,
        policy: SessionPolicy,
        activities: list[Activity],
        demo: bool = False,
        fullscreen: bool = True,
        speech_backend: str | None = None,
        run_seconds: float | None = None,
        screen: ScreenOverride | None = None,
        screenshot: Path | None = None,
    ) -> None:
        super().__init__(application_id=APP_ID)
        self._paths = paths
        self._config = config
        self._policy = policy
        self._activities = activities
        self._demo = demo
        self._fullscreen = fullscreen
        self._speech_backend = speech_backend
        self._run_seconds = run_seconds
        self._screen = screen
        self._screenshot = screenshot
        self.window: ShellWindow | None = None

    def do_activate(self) -> None:
        if self.window is None:
            self.window = ShellWindow(
                self,
                paths=self._paths,
                config=self._config,
                policy=self._policy,
                activities=self._activities,
                demo=self._demo,
                fullscreen=self._fullscreen,
                speech_backend=self._speech_backend,
                screen=self._screen,
            )
            if self._screenshot is not None:
                delay = max(1.0, (self._run_seconds or 3.0) - 0.5)
                GLib.timeout_add(int(delay * 1000), self._capture)
            if self._run_seconds:
                GLib.timeout_add_seconds(int(self._run_seconds), self._auto_quit)
        self.window.present()

    def _capture(self) -> bool:
        if self.window is not None and self._screenshot is not None:
            self.window.capture(self._screenshot)
        return False

    def _auto_quit(self) -> bool:
        log.info("--run-seconds elapsed; quitting")
        if self.window is not None:
            self.window.shutdown()
        self.quit()
        return False

    def do_shutdown(self) -> None:
        if self.window is not None:
            self.window.shutdown()
        Adw.Application.do_shutdown(self)


def looks_headless() -> bool:
    return not (os.environ.get("WAYLAND_DISPLAY") or os.environ.get("DISPLAY"))
