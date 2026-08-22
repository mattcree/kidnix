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
from .next_after import NextAfter  # noqa: E402
from .ritual import RitualAction, back_delay_seconds, next_action  # noqa: E402
from .screens import Screen  # noqa: E402
from .screens.ending import EndingOfferScreen, PutAwayScreen  # noqa: E402
from .screens.goodbye import GoodbyeScreen  # noqa: E402
from .screens.grownup import GrownupSheet  # noqa: E402
from .screens.home import HomeScreen  # noqa: E402
from .screens.journal import JournalScreen  # noqa: E402
from .screens.next_after import NextAfterScreen  # noqa: E402
from .screens.sleeping import SleepingScreen  # noqa: E402
from .screens.whos_here import WhosHereScreen  # noqa: E402
from .session import (  # noqa: E402
    DailyUsage,
    Phase,
    Session,
    SessionPolicy,
    StartRefusal,
    budget_day,
    time_left_words,
)
from .settings import KidState, ParentConfig, Paths, Profile  # noqa: E402
from .sound import BACK, KEEP, PHASE, SLEEP, TAP, Earcons  # noqa: E402
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
#: accidental "All done" is recoverable. The number lives in
#: :mod:`kidnix_shell.ritual` now, with the rule that it is the *only* one.
PUT_AWAY_BACK_LOCK_SECONDS = back_delay_seconds(State.PUT_AWAY)
#: How long "Let's keep that" is on screen when the *child* ended the session
#: (the clock-driven path is timed by the session itself). Long enough to see
#: the work fly into My Things, and to cover the SIGTERM grace.
PUT_AWAY_SECONDS = 6
#: Re-measure the monitor every few ticks: a child's machine gets a projector
#: plugged into it, and the shell has to still fit afterwards.
MONITOR_CHECK_TICKS = 8
#: How many times the measured-overflow backstop may relax the layout. Higher
#: since v0.1.3, because each step now spends *chrome* first (a gap, the band's
#: spare height) rather than shrinking every target at once, so a step is
#: smaller and it takes more of them to close a 40 px overshoot. All of them
#: happen before the window is presented.
MAX_FIT_ATTEMPTS = 5


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
    State.NEXT_CHOICE: "next_after",
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
        # Spec 7b: the hover dwell is a parent-tunable number, because it is
        # the first thing the child test (P5) will move.
        self.speech = SpeechManager(
            backend=select_backend(speech_backend),
            scheduler=GLibScheduler(),
            dwell_ms=config.hover_dwell_ms,
        )
        log.info(
            "read-aloud backend: %s (hover dwell %d ms, settle-gated)",
            self.speech.backend.name,
            self.speech.dwell_ms,
        )
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
        self._last_phase: Phase | None = None

        self.kid_state = KidState.load(paths.progress_state)
        log.info("%d session(s) completed on this machine", self.kid_state.sessions_completed)

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
            kid_state=self.kid_state,
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
                on_sun=self.on_sun,
            ),
        )
        root.append(self.band)

        self.stack = Gtk.Stack()
        self.stack.set_transition_duration(400)
        self.stack.set_transition_type(Gtk.StackTransitionType.SLIDE_LEFT_RIGHT)
        self.stack.set_vexpand(True)
        self.screens: dict[str, Screen] = {
            "choosing": WhosHereScreen(self.ctx),
            "next_after": NextAfterScreen(self.ctx),
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
        if current is State.GOODBYE and previous is not State.SHOWING:
            # Reaching Goodbye is what "a completed session" means, and it is
            # the only clock progressive disclosure runs on (spec 7b). Not a
            # streak: nothing shows it to the child and nothing resets it.
            total = self.kid_state.complete_session()
            log.info("session %d completed; Home may have grown", total)
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
            self.band.set_progress(
                self.session.fraction_spent(now),
                self.session.is_warm(now),
                self.session.time_left_words(now),
            )
            phase = self.session.phase(now)
            self._announce_phase(phase)
            self._advance_ritual(phase)
        else:
            self._last_phase = None
            self.band.set_progress(0.0, False, time_left_words(0.0, running=False))
            self._maybe_wake(now)
        return True  # GLib.SOURCE_CONTINUE

    def _announce_phase(self, phase: Phase) -> None:
        """08 section 3.6b's session-phase earcon -- the audio half of the sun.

        It plays exactly once, on the step into :class:`Phase.ENDING_OFFER`,
        which is the one transition with no sound of its own: Put away already
        has the keep motif and Goodnight has the sleep motif, and two earcons
        inside a quarter of a second is one earcon and a swallowed one.

        A child whose eyes are on their drawing, not on the band, is told that
        the light has changed before the screen tells them.
        """
        previous, self._last_phase = self._last_phase, phase
        if previous is None or phase is previous:
            return
        if phase is Phase.ENDING_OFFER:
            self.earcons.play(PHASE)

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
        """One tick of the ending ritual. The policy is in :mod:`ritual`."""
        action = next_action(phase, self.machine.state, offer_answered=self.session.offer_answered)
        if action is RitualAction.PRESENT_OFFER:
            self._present_ending_offer()
        elif action is RitualAction.PUT_AWAY:
            self._begin_put_away()
        elif action is RitualAction.GOODBYE:
            self.session.end(datetime.now())
            self.machine.try_fire(Event.GOODBYE_DUE)

    # -- the ending ritual --------------------------------------------

    def _present_ending_offer(self) -> None:
        self._close_offer_window()
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
        # A new sitting: last time's answer to "what's next after?" is not this
        # time's, and Goodbye must not show a picture nobody chose today.
        self.ctx.next_after = None
        if profile.skip_next_choice:
            log.info("%s skips S1b (skip_next_choice)", profile.id)
            self.machine.try_fire(Event.SKIP_NEXT_CHOICE)
            return
        self.machine.try_fire(Event.CHOOSE_PROFILE)

    def choose_next_after(self, option: NextAfter) -> None:
        """S1b: the child said what happens after. Spec 7b / SYNTHESIS D4."""
        if not self.machine.can(Event.CHOOSE_NEXT_AFTER):
            return
        self.ctx.next_after = option
        log.info("next after this session: %s", option.id)
        self.earcons.play(TAP, speaking=True)
        self.machine.try_fire(Event.CHOOSE_NEXT_AFTER)

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
        if running.failed_to_open(code):
            # It never opened. The child pressed a button and the screen
            # flickered; SYNTHESIS C3 says say something, in the child's words,
            # and put the reason where the parent will find it instead.
            tail = running.stderr_tail()
            log.warning(
                "%s exited %s after %.1fs -- it did not open. stderr tail:\n%s",
                running.activity_id,
                code,
                running.ran_for(),
                tail or "(nothing on stderr)",
            )
            self.speech.speak("That one didn't open. Let's try something else.")
        elif kept:
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
        """S5: the child answered. The offer does not come back this session.

        Both answers do the same thing to the machine -- return the child to
        wherever they were and leave them alone until Put away. The difference
        is in what it means on Home: "one last little thing" is permission to
        open one more activity, which is simply Home continuing to work.
        """
        self._close_offer_window()
        # Latch first: the answer counts even if the transition is a no-op
        # because a later tick already moved the child on.
        self.session.answer_offer()
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
        """Back. Immediate, everywhere, with exactly one documented exception.

        Spec 7b: **no exit friction of any kind.** The one delay in the shell
        is ``ritual.BACK_DELAY_SECONDS``, which has one row in it -- the three
        seconds on Put away that keep a child drumming on the band from undoing
        the ritual. Asking the table rather than writing a second ``if`` here
        is what lets ``tests/test_ritual.py`` assert there is no second row.
        """
        if self.machine.state is State.HOME:
            self.speech.speak("You're home.")
            return
        if (
            back_delay_seconds(self.machine.state) > 0
            and time.monotonic() < self._back_locked_until
        ):
            # Not greyed out, not moved, not hidden: the band never changes
            # shape under a child.
            return
        if self.machine.state is State.NEXT_CHOICE:
            # Back out of S1b: the sitting has not really started, so stop the
            # clock and hand them back the question they were answering.
            self.session.end(datetime.now())
            self.ctx.next_after = None
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

    def on_sun(self) -> None:
        """Tapping the sun (08 section 4.6).

        The sentence is already the button's ``speak_text`` -- kept current by
        every tick -- and :class:`ChildButton` speaks that before calling here,
        so there is nothing left to say. This exists so the gesture has a
        named owner and so a later milestone (the timer study) has one place
        to count from.
        """
        log.debug("the child asked the sun")

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

        Two routes, because the first one has a hole. ``Gtk.WidgetPaintable``
        hands back the widget's *last painted* content, and returns nothing at
        all when the widget is waiting for a redraw -- which is the normal
        state of a window nobody is compositing, i.e. every automated
        screenshot run. So if the paintable comes back empty we walk the tree
        ourselves, which always has an answer.
        """
        try:
            from gi.repository import Gsk  # noqa: F401  -- ensures the typelib

            width = self.get_width() or self.metrics.screen_width or 1280
            height = self.get_height() or self.metrics.screen_height or 800
            paintable = Gtk.WidgetPaintable.new(self)
            snapshot = Gtk.Snapshot()
            paintable.snapshot(snapshot, width, height)
            node = snapshot.to_node()
            if node is None:
                direct = Gtk.Snapshot()
                self.do_snapshot(self, direct)
                node = direct.to_node()
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
        start_on: str = "choosing",
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
        self._start_on = start_on
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
            if self._start_on != "choosing" and self._config.profiles:
                # Development only (--start-on): a --screenshot run should
                # photograph the surface asked for, and the chooser is what a
                # six-second run would otherwise catch. After the first frame,
                # so the window has a renderer by the time anything paints.
                GLib.timeout_add(500, self._drive_to_start_surface)
            if self._screenshot is not None:
                delay = max(1.0, (self._run_seconds or 3.0) - 0.5)
                GLib.timeout_add(int(delay * 1000), self._capture)
            if self._run_seconds:
                GLib.timeout_add_seconds(int(self._run_seconds), self._auto_quit)
        self.window.present()

    def _drive_to_start_surface(self) -> bool:
        """Development only: walk the shell to ``--start-on`` in one pass."""
        window = self.window
        if window is None or not self._config.profiles:
            return False
        # No slide. A --screenshot run is often not being composited by
        # anything, so the frame clock does not tick, so a 400 ms stack
        # transition never advances and the window keeps painting the
        # surface it was already showing. Zero duration settles the tree
        # in one layout pass.
        window.stack.set_transition_duration(0)
        window.choose_profile(self._config.profiles[0])
        if self._start_on == "next-after":
            return False
        if self._config.next_after:
            window.choose_next_after(self._config.next_after[0])
        if self._start_on == "goodbye":
            window.machine.try_fire(Event.IM_FINISHED)
            window.session.end(datetime.now())
            window.machine.try_fire(Event.GOODBYE_DUE)
        return False

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
