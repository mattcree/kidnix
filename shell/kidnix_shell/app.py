"""The application: two windows, one band, one stack of surfaces.

Everything that changes state passes through :class:`ShellWindow`, which is the
only thing that touches the state machine, the session and the launcher. The
screens ask; this decides.

**Two toplevels, one process** (v0.1.5, ``docs/spikes/band-over-activity.md``).
The band used to be a strip inside the single fullscreen shell window, which
meant it vanished for the whole of ``IN_ACTIVITY`` -- the largest hole in the
build, and the reason the CCI audit failed B3, C1 and D3 together. It is now
its own toplevel, :class:`BandWindow`, titled ``kidnix-band``, which gnome-kiosk
pins to the top strip and keeps above everything; :class:`ShellWindow` is titled
``kidnix-content`` and owns the area below it. They are two windows on **one**
:class:`GtkApplication`, because two processes sharing an application id do not
get two windows -- the second merely re-activates the first.

The start-up sequence is forced by the compositor and is described in
:mod:`kidnix_shell.kiosk`:

1. ``/usr/bin/kidnix-shell`` (before gnome-session) installs a geometry-free
   seed, which is the only way gnome-kiosk ever watches the file at all;
2. the shell measures the monitor and writes **phase A** -- the catch-all *is*
   the band strip;
3. the band window is created and presented, and takes that strip;
4. once it is mapped the shell writes **phase B** -- the catch-all is
   everything *below* the band -- and settles;
5. the content window is presented, lands below the band, and so does every
   activity launched for the rest of the session.

Launching and quitting activities needs no compositor interaction at all.
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
gi.require_version("Gsk", "4.0")
gi.require_version("Graphene", "1.0")
from gi.repository import Adw, Gdk, GLib, Graphene, Gsk, Gtk  # noqa: E402

from .access import AccessConfig  # noqa: E402
from .activities import Activity  # noqa: E402
from .band import Band, BandActions, CaptionStrip  # noqa: E402
from .context import ShellContext  # noqa: E402
from .journal import Entry, Journal, JournalImporter, JournalWatcher  # noqa: E402
from .keyboard import Keyboard  # noqa: E402
from .kiosk import BAND_TITLE, CONTENT_TITLE, WindowConfig, placed  # noqa: E402
from .launcher import Launcher, RunningActivity  # noqa: E402
from .metrics import Metrics, ScreenOverride, detect_metrics, pin_font_dpi  # noqa: E402
from .next_after import NextAfter  # noqa: E402
from .research import BurstDetector, ResearchConfig  # noqa: E402
from .resting import refusal_line  # noqa: E402
from .ritual import (  # noqa: E402
    OFFER_QUESTION,
    OfferAnswer,
    RitualAction,
    back_delay_seconds,
    next_action,
    put_away_line,
    undo_line,
)
from .screens import Screen  # noqa: E402
from .screens.ending import EndingOfferScreen, PutAwayScreen  # noqa: E402
from .screens.goodbye import GoodbyeScreen  # noqa: E402
from .screens.grownup import GrownupSheet  # noqa: E402
from .screens.home import HomeScreen  # noqa: E402
from .screens.journal import JournalScreen  # noqa: E402
from .screens.next_after import NextAfterScreen  # noqa: E402
from .screens.shelf import ShelfScreen  # noqa: E402
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
from .settings import (  # noqa: E402
    KidState,
    ParentConfig,
    Paths,
    Profile,
    migrate_profile_data,
)
from .sound import BACK, KEEP, PHASE, SLEEP, TAP, Earcons  # noqa: E402
from .speech import GLibScheduler, SpeechManager, select_backend  # noqa: E402
from .state import Event, State, StateMachine  # noqa: E402
from .sun import idle_fraction  # noqa: E402
from .theme import dynamic_css  # noqa: E402
from .voice import GstRecorder, VoiceNote  # noqa: E402
from .widgets import SpeechUI  # noqa: E402

log = logging.getLogger(__name__)

APP_ID = "org.kidnix.Shell"
TICK_MS = 500
#: S7: "Show a grown-up" borrows My Things, and now **keeps** it.
#:
#: It was two minutes, on a wall clock, and it yanked itself back -- cutting a
#: parent off mid-sentence at the one moment kidnix builds co-use, which is the
#: strongest protective moderator in 02 (forum #52). Ten minutes is a backstop
#: against a machine left on a sofa, not a limit on a conversation: the way out
#: is Back, and nothing revokes the screen while anyone is still looking at it.
SHOWING_SECONDS = 600
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
#: Seven since 2026-08-23: S1b gained a ninth option ("Not sure yet"), which is
#: a third row on a 4x3 panel, and the tree then measures a few pixels over its
#: budget. Each step spends a little chrome rather than shrinking everything, so
#: closing a 1% overshoot genuinely takes several of them -- and stopping early
#: leaves the overshoot on screen, which is the clipping this exists to prevent.
MAX_FIT_ATTEMPTS = 16
#: Spec S5 in the band: how long the two ending choices stay in the band when
#: the child is inside an activity and there is no shell surface to put them
#: on. Long enough to notice and answer without looking up from a drawing;
#: short enough that the band is back to its usual shape well before Put away.
#: Not answering is a legitimate answer (:mod:`kidnix_shell.ritual`), so when it
#: expires the offer is latched as answered rather than asked again.
BAND_OFFER_SECONDS = 20
#: How long to give gnome-kiosk to notice a window-config write before we
#: create the window that write is for. **Measured in the VM** (a throwaway
#: toplevel probed every 100 ms after a write): the new config was in force
#: 260 ms later, so 400 ms is head-room rather than a guess. It is not a
#: correctness guarantee -- :func:`kiosk.placed` is -- just the first thing to
#: try, and it is paid twice, at login only.
KIOSK_RELOAD_MS = 400
#: How long to wait for the compositor to answer a presented band window with
#: the strip it was asked for, before assuming it will not and starting again
#: with a fresh toplevel.
BAND_PLACE_TIMEOUT_MS = 2500
#: How often to ask the band window what size it ended up.
BAND_POLL_MS = 100
#: How many fresh toplevels to try before giving up on a band window at all and
#: falling back to v0.1.4's single fullscreen window.
BAND_PLACE_ATTEMPTS = 3


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
    State.SHELF: "shelf",
    State.JOURNAL: "journal",
    State.SHOWING: "journal",
    State.IN_ACTIVITY: "home",  # the shell sits behind the activity's window
    State.ENDING_OFFER: "ending",
    State.PUT_AWAY: "put_away",
    State.GOODBYE: "goodbye",
    State.SLEEPING: "sleeping",
    State.GROWNUP: "home",  # the sheet is a dialog over whatever is underneath
}


class BandWindow(Adw.ApplicationWindow):
    """The band, as a toplevel of its own (v0.1.5).

    It exists so that gnome-kiosk has something to pin to the top strip and
    keep above a fullscreen activity. It has no logic: the :class:`Band` inside
    it is still built and driven by :class:`ShellWindow`, which is the only
    thing in the shell that touches the state machine.

    Its **title** is the whole of its identity to the compositor. Both windows
    share the application id ``org.kidnix.Shell`` -- one process, one
    ``GtkApplication`` -- so ``match-class`` cannot tell them apart, and
    ``match-title`` is what the ``[band]`` section keys off (and the only kind
    of match that works for ``set-above`` at all; see :mod:`kidnix_shell.kiosk`
    rules R3 and R4).
    """

    def __init__(self, application: Adw.Application, metrics: Metrics) -> None:
        super().__init__(application=application)
        self.set_title(BAND_TITLE)
        self.add_css_class("kidnix")
        # Nothing in the band is resizable and nothing may drag it: telling the
        # compositor so is one fewer way for it to be given a size we did not
        # ask for.
        self.set_resizable(False)
        self.set_size(metrics)

    def set_size(self, metrics: Metrics) -> None:
        """Ask for the strip -- and the size *request* is the load-bearing half.

        ``Adw.ApplicationWindow`` (``AdwWindow``) enforces a **360 x 200 px
        minimum**, whatever its content measures. GTK sends that minimum to the
        compositor as ``xdg_toplevel.set_min_size``, mutter honours it as a
        constraint, and a 92 px band therefore came up 200 px tall no matter
        what ``window-config.ini`` said -- measured in the VM, and the second
        half of the v0.1.5.0 regression.

        ``gtk_widget_set_size_request()`` *replaces* a widget's measured
        minimum rather than raising it, so this is what lets the band be
        shorter than libadwaita's floor. It is safe to override precisely
        because ``ShellWindow._check_measured_fit`` has already proved the
        band's own tree fits inside ``band_height``.

        The default size matters only on a developer's desktop, where there is
        no gnome-kiosk to place the window at all.
        """
        width = metrics.screen_width or 1280
        # The band *window* is the row of controls plus the caption strip:
        # gnome-kiosk gives it one rectangle and both live in it.
        height = metrics.band_window_height
        self.set_size_request(width, height)
        self.set_default_size(width, height)


class ShellWindow(Adw.ApplicationWindow):
    """The child's whole computer -- everything below the band."""

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
        shelves: dict[str, list[Activity]] | None = None,
        research: ResearchConfig | None = None,
    ) -> None:
        super().__init__(application=application)
        self.set_title(CONTENT_TITLE)
        self.add_css_class("kidnix")

        #: The machine's paths. Everything a *child* owns hangs off
        #: ``paths.for_profile(...)`` instead -- see :meth:`_use_profile`.
        self.paths = paths
        self.demo = demo
        self._screen_override = screen
        self._fit_attempts = 0
        #: What the last measured-fit pass measured, so a pass that changed
        #: nothing can be recognised as one (see ``_check_measured_fit``).
        self._last_measured: dict[str, tuple[int, int]] | None = None
        # Before anything measures anything: the shell's type scale is already
        # the accessibility decision, and the session's text-scaling factor
        # must not be applied to it a second time (see `metrics.pin_font_dpi`).
        was = pin_font_dpi()
        if was is not None and abs(was - self.metrics_font_dpi()) > 0.5:
            log.info(
                "the session draws text at %.0f dpi (text-scaling-factor %.2f); the shell "
                "draws its own at %.0f, because its point sizes are already a child's",
                was,
                was / self.metrics_font_dpi(),
                self.metrics_font_dpi(),
            )
        #: ``[access]`` (:mod:`kidnix_shell.access`), and the runtime copy the
        #: grown-up sheet's volume row edits. Read before the metrics, because
        #: whether captions are on decides how tall the band window is.
        self.access: AccessConfig = config.access
        self.metrics: Metrics = detect_metrics(screen, captions=self.access.captions)
        self._signature = _signature(self.metrics)
        log.info("display metrics: %s", self.metrics.describe())

        # Only the real kiosk session writes gnome-kiosk's window-config.ini.
        # `--windowed` is a developer on their own desktop, where there is no
        # gnome-kiosk to talk to and where $XDG_CONFIG_HOME is *their* config
        # directory, not the child's.
        self._manage_kiosk = fullscreen
        self.window_config = WindowConfig(paths.config_home)

        # -- services --
        # Spec 7b: the hover dwell is a parent-tunable number, because it is
        # the first thing the child test (P5) will move.
        #: ``/etc/kidnix/research.toml``. Read once, here, and handed to
        #: everything that could log: nothing in the shell decides for itself
        #: whether it is being studied (spec 7d #10).
        self.research = research if research is not None else ResearchConfig()
        self.speech = SpeechManager(
            backend=select_backend(speech_backend),
            scheduler=GLibScheduler(),
            dwell_ms=config.hover_dwell_ms,
            research=self.research,
        )
        log.info(
            "read-aloud backend: %s (hover dwell %d ms, settle-gated)",
            self.speech.backend.name,
            self.speech.dwell_ms,
        )
        self.speech.set_rate(self.access.speech_rate)
        self.speech.set_volume(self.access.effective_volume)
        self.speech_ui = SpeechUI(self.speech)
        # **The captioned hook.** Nothing can be spoken without being shown:
        # `SpeechManager.speak` calls this before it even asks whether speech
        # is enabled (accessibility review B2).
        self.speech.on_caption = self._on_caption
        #: One key controller for both toplevels, one focus ring across them
        #: (accessibility review B1). Escape is the shell's own Back, so it can
        #: never mean something the band's Back does not.
        self.keys = Keyboard(on_back=self.on_back)
        # /usr is read-only on the image, so the generated earcons land in the
        # child's cache when the package directory cannot be written.
        self.earcons = Earcons(cache_dir=paths.sounds_cache, access=self.access)

        #: Whose things are open right now. The first profile's, until "Who's
        #: here?" says otherwise -- a shell that came up on nobody's journal
        #: would have nothing to show on the tile thumbnails.
        self.profile_paths = paths.for_profile(config.profiles[0].id)
        migrate_profile_data(paths, config.profiles[0].id)

        self.journal = Journal(self.profile_paths.journal_root)
        self.journal.load()
        # The importer watches the *activities'* directories, which are shared
        # by every child on the machine (Tux Paint saves where Tux Paint
        # saves). Which profile a new file lands in is therefore "whoever is
        # logged in", which is right for one machine per child and is the
        # honest limit of profiles that share one Unix account -- see the
        # implementation notes.
        self.importer = JournalImporter(self.journal, activities)
        self.watcher = JournalWatcher(self.importer, on_import=self._on_new_work)

        usage = DailyUsage.for_now(self.profile_paths.usage_state, datetime.now())
        self.session = Session(policy=policy, usage=usage)
        self.launcher = Launcher(paths.home)
        self.launcher.on_exit = self._on_activity_exit

        self.machine = StateMachine(State.CHOOSING, on_change=self._on_state_change)
        self._sheet: GrownupSheet | None = None
        self._showing_handle: int | None = None
        self._goodbye_handle: int | None = None
        self._band_offer_handle: int | None = None
        self._content_handle: int | None = None
        self._band_handle: int | None = None
        self._nag_handle: int | None = None
        self._content_deadline = 0.0
        self._slept_at: datetime | None = None
        self._back_locked_until = 0.0
        self._ticks = 0
        self._last_phase: Phase | None = None
        #: Where the sun is when the clock is not driving it (:func:`sun.
        #: idle_fraction`). 0.0 is the start of a day's computer time.
        self._sun_fraction = 0.0
        #: True while the two ending choices are in the band (v0.1.5). It is
        #: what stops :mod:`kidnix_shell.ritual` re-presenting the offer every
        #: tick, because this route does not change the state.
        self._offer_on_band = False
        #: My Things pressed inside an activity: open the Journal once the
        #: activity has actually finished.
        self._journal_after_activity = False
        #: v0.1.6, spec 7c: Put away has asked a running activity to finish and
        #: is waiting for it to actually go. The child is still looking at
        #: their own program -- nothing is raised over it -- so the state does
        #: not move, and this is what stops the tick asking again.
        self._put_away_pending = False
        #: Which event takes the child to S6 when the activity finally goes:
        #: the clock's, or "All done"/"End session now".
        self._put_away_event = Event.PUT_AWAY_DUE
        #: The one re-ask, scheduled for the activity's own ``quit_grace``.
        self._reask_handle: int | None = None
        #: "All done" while an activity was still finishing: Goodbye is timed
        #: from S6's arrival, not from the press.
        self._goodbye_after_put_away = False
        #: Set once the compositor has answered the band window with the strip
        #: it asked for -- not when GTK mapped it. See :func:`kiosk.placed`.
        self._band_placed = False
        self._band_attempts = 0
        self._band_deadline = 0.0
        self._startup_begun = False
        #: v0.1.4's layout, as a fallback: band and surfaces in one fullscreen
        #: window. Only reached if the compositor will not place the band.
        self._one_window = False
        self._shutting_down = False

        #: Which shelf the child is standing in, if any. Set by
        #: :meth:`open_shelf`, cleared by Back to Home, and read after an
        #: activity exits so the child lands back where they launched from
        #: rather than one level out (``panel-wave-c`` section 2).
        self._shelf: Activity | None = None
        #: Presses that hit no control at all, counted for the child test's
        #: burst detector (CCI #54). It logs nothing unless ``research.toml``
        #: says it may; it is constructed either way so the wiring is not a
        #: conditional the study has to trust.
        self.bursts = BurstDetector(research=self.research)

        self.kid_state = KidState.load(self.profile_paths.progress_state)
        log.info(
            "%d session(s) completed by %s",
            self.kid_state.sessions_completed,
            config.profiles[0].id,
        )

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
            shelves=shelves or {},
            research=self.research,
            voice=self._build_voice(),
        )

        # -- layout --
        self._load_css()

        # The band window is *created* here and deliberately not presented.
        # A GTK window that has never been presented has no Wayland toplevel
        # and so has had no initial configure, which means nothing about the
        # compositor's placement is decided yet -- and the layout below is
        # still free to change the band's height. `present_all()` writes phase
        # A once, with the final numbers, and only then puts it on screen.
        self.band_window = BandWindow(application, self.metrics)
        self.band_window.connect("close-request", self._on_close)
        # One controller, **both** toplevels: Tab cannot cross a Wayland
        # toplevel boundary, so whichever window the compositor focused, the
        # key arrives at the same handler and the same ring (review B1).
        self.keys.attach(self)
        self.keys.attach(self.band_window)

        self._build_content()

        if fullscreen:
            # The *content* window is deliberately NOT fullscreen: phase B
            # gives it `0,band_height W x (H - band_height)`, and a window that
            # also asks for the whole monitor gets an answer neither side
            # agrees on -- measured in the VM, GTK reported 1280x741 for a
            # window the compositor had constrained to 1280x708, which makes
            # the geometry check below unable to tell right from wrong. Asking
            # for exactly the rectangle we expect makes the two agree, and
            # `_poll_content_placed` can then be believed.
            self.set_content_size(self.metrics)
        else:
            # Development window: big enough to look like the real thing,
            # never bigger than the share of the panel it would really get.
            # `required_size()` budgets for the band, which is somebody else's
            # window now, so it comes back off.
            needed_width, needed_height = self.metrics.required_size()
            width = max(needed_width, 1366)
            spare = self.metrics.band_window_height
            height = max(needed_height - spare, 768 - spare)
            if self.metrics.screen_width and self.metrics.content_height:
                width = min(width, self.metrics.screen_width)
                height = min(height, self.metrics.content_height)
            self.set_default_size(width, max(1, height))

        # Keyboard is never required, but Escape must never be a trap either.
        self.connect("close-request", self._on_close)

        self._watch_for_bursts()
        self.watcher.start()
        self._tick_handle = GLib.timeout_add(TICK_MS, self._tick)
        self._show_state()
        self._check_measured_fit()
        # Render the earcons (about 13 ms) off the first frame rather than off
        # the first thing the child presses.
        GLib.idle_add(self._warm_earcons)

    # -- the burst-click detector (spec 7d #10, CCI #54) ---------------

    def _watch_for_bursts(self) -> None:
        """Notice a child pressing a patch of screen that is not a button.

        The child-test method review named this as missing by name: an ABAB
        design cannot tell "exploring" from "has stopped believing the screen
        will answer" without it, and three presses in a second on nothing at
        all is the observable difference.

        It is one gesture on each toplevel, in the **capture** phase and
        claiming nothing, so it sees every press before any control does and
        changes none of them. What lands on a control is discovered by asking
        GTK what is under the pointer (:meth:`Gtk.Widget.pick`) rather than by
        waiting to see whether a handler ran -- a press that a ``ChildButton``
        claims never bubbles back here at all.

        Nothing is written unless ``research.toml`` says so; the wiring is
        unconditional so that turning the study on does not also turn on a code
        path nobody has run.
        """
        for window in (self, self.band_window):
            gesture = Gtk.GestureClick.new()
            gesture.set_button(0)
            gesture.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
            gesture.connect("pressed", self._on_any_press)
            window.add_controller(gesture)

    def _on_any_press(self, gesture: Gtk.GestureClick, _n: int, x: float, y: float) -> None:
        widget = gesture.get_widget()
        on_target = False
        try:
            picked = widget.pick(x, y, Gtk.PickFlags.DEFAULT)
            while picked is not None:
                if isinstance(picked, Gtk.Button):
                    on_target = True
                    break
                picked = picked.get_parent()
        except Exception:  # pragma: no cover - picking must never break a press
            return
        if self.bursts.press(time.monotonic(), on_target=on_target):
            log.debug("burst of presses on nothing (state %s)", self.machine.state.value)

    # -- "tell me about it" (spec 7d #9) -------------------------------

    @staticmethod
    def _build_voice() -> VoiceNote | None:
        """The recorder, or ``None`` on a machine with no microphone.

        Probed **here**, once, at start-up, rather than when a child presses
        something: the answer decides whether the button is drawn at all, and a
        mic button that appears and then does nothing is exactly the control
        spec 7a took Ask out of the band to avoid.
        """
        note = VoiceNote(recorder=GstRecorder(), scheduler=GLibScheduler())
        if not note.available:
            log.info("no microphone; 'tell me about it' is off for this run")
            note.close()
            return None
        log.info("voice notes are available (%.0f s maximum)", note.max_seconds)
        return note

    # -- whose machine this is right now (spec 7d #11) -----------------

    def _use_profile(self, profile: Profile) -> None:
        """Point the Journal, the budget and the progress counter at one child.

        Until 2026-08-23 there was one of each per *machine*, so a second child
        opened their sibling's My Things, inherited their spent afternoon and
        their grown grid -- "profiles are cosmetic" (forum #4) was literally
        true. Everything a child owns now hangs off ``paths.for_profile``, and
        this is the single place that swaps it.

        The old single-profile layout is migrated into the **first** profile,
        once, idempotently (:func:`kidnix_shell.settings.migrate_profile_data`)
        so that nobody's existing drawings disappear on the morning of an
        upgrade.
        """
        self.ctx.profile = profile
        # Before the early return below: every activity is told whose things it
        # may write (``KIDNIX_PROFILE_ID``), and the SDK's Journal writer needs
        # it on the *first* profile too -- which is the one this method is
        # called with when nothing has changed yet.
        self.launcher.profile_id = profile.id
        paths = self.paths.for_profile(profile.id)
        if paths == self.profile_paths:
            return
        migrate_profile_data(self.paths, profile.id)
        self.profile_paths = paths
        self.journal.root = paths.journal_root
        self.journal.load()
        self.session.usage = DailyUsage.for_now(paths.usage_state, datetime.now())
        self.kid_state = KidState.load(paths.progress_state)
        self.ctx.kid_state = self.kid_state
        log.info(
            "profile %r: journal %s, %d session(s) completed, %d minute(s) used today",
            profile.id,
            paths.journal_root,
            self.kid_state.sessions_completed,
            self.session.usage.seconds // 60,
        )

    # -- access (captions, calm, volume) ------------------------------

    @staticmethod
    def animations_enabled() -> bool:
        """``gtk-enable-animations``: the desktop's own reduced-motion answer.

        The image's dconf sets it and the shell never read it. A parent who
        turned motion off system-wide should not have to find a second switch.
        """
        try:  # pragma: no cover - requires a display
            settings = Gtk.Settings.get_default()
            if settings is None:
                return True
            return bool(settings.get_property("gtk-enable-animations"))
        except Exception:  # pragma: no cover
            return True

    def _on_caption(self, text: str) -> None:
        """Every spoken line, written down for four seconds (review B2)."""
        if self.access.captions:
            self.captions.show_caption(text)

    def _calm_class(self) -> None:
        """Mark both windows so the stylesheet and the tests can see calm mode."""
        calm = self.access.reduced_motion(self.animations_enabled())
        for window in (self, *(() if self._one_window else (self.band_window,))):
            if calm:
                window.add_css_class("calm")
            else:
                window.remove_css_class("calm")

    def set_access(self, access: AccessConfig) -> None:
        """Take a new ``[access]`` -- the grown-up sheet's rows call this.

        Volume, mute and calm's soundscape apply at once. Captions changing
        moves the band window's height, which the compositor decided at the
        band's first configure (window-config R2), so that one waits for a
        restart and says so rather than half-applying.
        """
        was_captions = self.access.captions
        self.access = access
        self.ctx.config.access = access
        self.speech.set_rate(access.speech_rate)
        self.speech.set_volume(access.effective_volume)
        self.earcons.set_access(access)
        self.stack.set_transition_duration(access.transition_ms(self.animations_enabled()))
        self.captions.set_visible(access.captions)
        if not access.captions:
            self.captions.clear()
        self._calm_class()
        if access.captions != was_captions:
            log.info(
                "captions %s; the band keeps its strip until the shell restarts", access.captions
            )

    @staticmethod
    def metrics_font_dpi() -> float:
        """The density the shell's own point sizes are specified at."""
        from .labels import FONT_DPI

        return FONT_DPI

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

        Since v0.1.5 it fills **two** toplevels: the band goes into
        :class:`BandWindow` and the stack of surfaces stays here.
        """
        self.speech_ui.forget_all()
        self.ctx.metrics = self.metrics
        self.ctx.reduced_motion = self.access.reduced_motion(self.animations_enabled())
        self._apply_tint(self.ctx.profile)

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
                on_finish_this=lambda: self.dismiss_offer(OfferAnswer.FINISH_THIS),
                on_one_more=lambda: self.dismiss_offer(OfferAnswer.ONE_MORE),
            ),
            reduced_motion=self.ctx.reduced_motion,
        )
        self.captions = CaptionStrip(self.metrics)
        self.captions.set_visible(self.access.captions)
        band_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        band_box.append(self.band)
        band_box.append(self.captions)
        if not self._one_window:
            self.band_window.set_size(self.metrics)
            self.band_window.set_content(band_box)
            if self._manage_kiosk:
                self.set_content_size(self.metrics)
        self._band_box = band_box

        self.stack = Gtk.Stack()
        # Reduced motion, from `[access] calm` *or* from the desktop's own
        # `gtk-enable-animations` -- which the image sets and nothing in the
        # shell read until now (WCAG 2.2 SC 2.3.3; accessibility review B3).
        self.stack.set_transition_duration(self.access.transition_ms(self.animations_enabled()))
        self.stack.set_transition_type(Gtk.StackTransitionType.SLIDE_LEFT_RIGHT)
        self.stack.set_vexpand(True)
        self.screens: dict[str, Screen] = {
            "choosing": WhosHereScreen(self.ctx),
            "next_after": NextAfterScreen(self.ctx),
            "home": HomeScreen(self.ctx),
            "shelf": ShelfScreen(self.ctx),
            "journal": JournalScreen(self.ctx),
            "ending": EndingOfferScreen(self.ctx),
            "put_away": PutAwayScreen(self.ctx),
            "goodbye": GoodbyeScreen(self.ctx),
            "sleeping": SleepingScreen(self.ctx),
        }
        for name, screen in self.screens.items():
            self.stack.add_named(screen, name)
        if self._one_window:
            # The fallback: v0.1.4's layout, band and surfaces in one window.
            root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
            root.append(band_box)
            root.append(self.stack)
            self._root = root
        else:
            self._root = self.stack
        self.set_content(self._root)
        self.keys.forget()
        self.keys.set_surfaces(self.band, None)
        self._calm_class()

    def set_content_size(self, metrics: Metrics) -> None:
        """Ask for the area under the band, the same way the band asks for its strip.

        ``Adw.ApplicationWindow``'s 360x200 minimum is not binding here, but the
        size *request* still matters: it is what GTK sends as
        ``xdg_toplevel.set_min_size``, and matching it to what
        ``window-config.ini`` says keeps GTK's idea of the window and the
        compositor's the same, which is what makes the geometry log trustworthy.
        """
        width = metrics.screen_width or 1280
        height = metrics.content_height or 800
        self.set_size_request(width, height)
        self.set_default_size(width, height)

    # -- the compositor (see kidnix_shell.kiosk) -----------------------
    #
    # The whole of start-up is one question asked twice: "has gnome-kiosk read
    # the file yet?" It cannot be answered by writing and hoping, because a
    # window's geometry is decided at its first configure and nothing tells us
    # when that happened. It CAN be answered by looking at what the window
    # ended up being (`kiosk.placed`), which is the compositor's own reply, so
    # that is what this does: write, wait a beat, present, and then *confirm*
    # before doing anything that depends on it. If the confirmation fails the
    # shell tries again with a fresh toplevel, and if it keeps failing it falls
    # back to v0.1.4's single window rather than leaving a child with a screen
    # that has no way out of it.

    def _write_band_phase(self) -> None:
        """Phase A: the catch-all *is* the band strip."""
        if not self._manage_kiosk:
            return
        self.window_config.band_phase(
            self.metrics.screen_width, self.metrics.screen_height, self.metrics.band_window_height
        )

    def _write_activity_phase(self) -> None:
        """Phase B: the catch-all is everything below the band.

        Only ever called once the band is confirmed placed. Calling it earlier
        is the v0.1.5.0 bug: the band's initial configure had not happened, the
        file monitor coalesced phase A and phase B into one reload, and the
        band was placed by phase B -- in the content rectangle, above the
        content window, which was then invisible underneath it.
        """
        if not self._manage_kiosk:
            return
        if self.window_config.activity_phase(
            self.metrics.screen_width, self.metrics.screen_height, self.metrics.band_window_height
        ):
            log.info("window config: %s", self.window_config.describe())

    # -- start-up ------------------------------------------------------

    def present_all(self) -> None:
        """Bring the shell up, in the order the compositor needs.

        The band goes first and alone. Phase B is not written until the band
        has *demonstrably* taken its strip, and the content window is not
        presented until phase B has had time to land -- otherwise it would be
        placed inside the band's own rectangle.
        """
        if not self._manage_kiosk:
            # Development on an ordinary desktop: no gnome-kiosk to sequence
            # for, and two floating windows the window manager places itself.
            self.band_window.present()
            self.present()
            return
        if self._band_placed or self._one_window:
            # Not the first time round: an activity finished, or the ritual
            # wants the screen back. Only the content window has to move.
            self.present()
            return
        if self._startup_begun:
            return
        self._startup_begun = True
        self._begin_band_attempt()

    def _begin_band_attempt(self) -> None:
        """Write phase A, let it land, then put the band on screen."""
        self._band_attempts += 1
        self._write_band_phase()
        log.info(
            "placing the band (attempt %d/%d): %s",
            self._band_attempts,
            BAND_PLACE_ATTEMPTS,
            self.window_config.describe(),
        )
        self._content_handle = GLib.timeout_add(KIOSK_RELOAD_MS, self._present_band)

    def _present_band(self) -> bool:
        self._content_handle = None
        self.band_window.present()
        self._band_deadline = time.monotonic() + BAND_PLACE_TIMEOUT_MS / 1000.0
        self._band_handle = GLib.timeout_add(BAND_POLL_MS, self._poll_band_placed)
        return False

    def _poll_band_placed(self) -> bool:
        """Ask the band window what the compositor actually made it.

        Returning ``True`` keeps polling. This is the only thing in the shell
        that knows whether the band has its strip, and everything else waits
        on it.
        """
        width, height = self.band_window.get_width(), self.band_window.get_height()
        if placed(width, height, self.metrics.screen_width, self.metrics.band_window_height):
            self._band_handle = None
            self._band_placed = True
            log.info("band window placed at %dx%d", width, height)
            self._on_band_placed()
            return False
        if time.monotonic() < self._band_deadline:
            return True

        self._band_handle = None
        log.warning(
            "the band window came up %dx%d, not %dx%d -- gnome-kiosk had not read "
            "phase A when it configured the toplevel",
            width,
            height,
            self.metrics.screen_width,
            self.metrics.band_window_height,
        )
        if self._band_attempts >= BAND_PLACE_ATTEMPTS:
            self._fall_back_to_one_window()
            return False
        # A window's geometry is settled for good at its first configure, so
        # the only way to ask again is to ask with a new window. The file has
        # said phase A for seconds by now, so the retry is not a repeat of the
        # same race.
        self._recreate_band_window()
        self._begin_band_attempt()
        return False

    def _on_band_placed(self) -> None:
        """The one transition of the session (spike section 3a).

        The band's initial config is consumed, so phase B's ``lock-on-area``
        can never reach it, and every window created from here on -- the
        content window and every activity -- is placed below it.
        """
        self._write_activity_phase()
        self._content_handle = GLib.timeout_add(KIOSK_RELOAD_MS, self._present_content)

    def _present_content(self) -> bool:
        self._content_handle = None
        self.present()
        # The spike's open question 3 asked for this: say out loud what both
        # windows actually got, so a regression is a grep in the journal rather
        # than a screenshot somebody has to notice.
        self._content_deadline = time.monotonic() + BAND_PLACE_TIMEOUT_MS / 1000.0
        self._content_handle = GLib.timeout_add(BAND_POLL_MS, self._poll_content_placed)
        return False

    def _poll_content_placed(self) -> bool:
        width, height = self.get_width(), self.get_height()
        if placed(width, height, self.metrics.screen_width, self.metrics.content_height):
            self._content_handle = None
            self._log_geometry("ok")
            return False
        if time.monotonic() < self._content_deadline:
            return True
        self._content_handle = None
        self._log_geometry("WRONG")
        return False

    def _log_geometry(self, verdict: str) -> None:
        """The one line a regression has to be visible in. Also the e2e's hook."""
        log.info(
            "shell geometry %s: band 0,0 %dx%d (wanted %dx%d), content 0,%d %dx%d (wanted %dx%d)",
            verdict,
            self.band_window.get_width(),
            self.band_window.get_height(),
            self.metrics.screen_width,
            self.metrics.band_window_height,
            self.metrics.band_window_height,
            self.get_width(),
            self.get_height(),
            self.metrics.screen_width,
            self.metrics.content_height,
        )

    def _recreate_band_window(self) -> None:
        """A fresh toplevel, so the compositor configures it again from scratch."""
        old = self.band_window
        old.set_content(None)  # the Band widget outlives its window
        application = self.get_application()
        assert application is not None
        self.band_window = BandWindow(application, self.metrics)
        self.band_window.connect("close-request", self._on_close)
        self.keys.attach(self.band_window)
        self.band_window.set_content(self._band_box)
        if self.machine.state is State.SLEEPING:
            self.band_window.add_css_class("sleeping")
        old.destroy()

    def _fall_back_to_one_window(self) -> None:
        """Give up on the band window and be v0.1.4 instead.

        A machine a five-year-old cannot get out of is the one outcome that is
        not allowed (AGENTS non-negotiable 8), and a band window the compositor
        has parked over the whole screen is exactly that. So if the strip
        cannot be had, the band goes back inside the content window, the
        content window goes fullscreen, and the shell behaves the way it did
        before this feature existed: everything works, the band is simply
        hidden while an activity is on top. Loud, because it is a regression
        somebody has to come and look at.
        """
        log.error(
            "could not place the band window in %d attempts; falling back to one "
            "fullscreen window (the band will be hidden during activities)",
            self._band_attempts,
        )
        self._one_window = True
        self.band_window.set_content(None)
        self.band_window.destroy()
        # Back to gnome-kiosk's own defaults, so activities are fullscreen as
        # they were in v0.1.4 rather than locked into a rectangle under a band
        # that is not there.
        if self._manage_kiosk:
            self.window_config.seed()
        self._build_content()
        self._show_state()
        self.set_size_request(-1, -1)
        self.fullscreen()
        self.present()

    def _apply_metrics(self, metrics: Metrics) -> None:
        log.info("relaying out: %s", metrics.describe())
        self.metrics = metrics
        self._build_content()
        # A different panel means a different strip. Rewriting phase B is worth
        # doing -- every activity launched from here on gets the right area --
        # but it cannot move the two windows that already exist: gnome-kiosk
        # consumed their geometry at their first configure (rule R2). A monitor
        # hotplug mid-session therefore leaves the band where it was until the
        # shell restarts, and says so.
        if self._band_placed:
            log.info("the band keeps its old strip until the shell restarts (window-config R2)")
            self._write_activity_phase()
        # Before the band is placed this writes nothing at all. That is the
        # v0.1.5.0 fix: the measured-fit backstop runs three times in the first
        # second and changed the band's height each time, and every one of
        # those writes landed inside gnome-kiosk's file-monitor window. One
        # write, with the final numbers, from `present_all()`.
        self._show_state()

    def _check_measured_fit(self) -> None:
        """Belt to the arithmetic's braces: measure, and shrink if we overflow.

        :mod:`kidnix_shell.metrics` models the layout, but CSS padding, font
        metrics and icon sizes are GTK's business, not ours. So after building,
        ask GTK how big the thing actually wants to be, and if that is larger
        than the space it is allowed, shrink and rebuild. This is what makes
        "the shell never exceeds the monitor" a fact rather than an intention.

        Since v0.1.5 there are **two budgets, not one**, because there are two
        windows: the band gets ``W x band_height`` and the content window gets
        ``W x (H - band_height)``, and gnome-kiosk gives each of them exactly
        that and nothing more (``lock-on-area``). A content tree that measured
        the full monitor height would have fitted the old single window and
        overflowed the new one -- the band's height would simply have been cut
        off the bottom of Home, which is the v0.1.0 clipping bug wearing a new
        hat.
        """
        screen_width = self.metrics.screen_width
        content_height = self.metrics.content_height
        band_height = self.metrics.band_window_height
        if not screen_width or not content_height:
            return
        if self._fit_attempts >= MAX_FIT_ATTEMPTS:
            # Loud, because this is the state that produced "shell geometry
            # WRONG" in the VM: a tree taller than its window is a *minimum
            # size* GTK forwards to the compositor, and a minimum the
            # compositor cannot satisfy is a window that ignores
            # `lock-on-area` and overhangs the panel.
            log.error(
                "the layout still does not fit after %d passes; the content window will "
                "overflow its strip. Last: %s",
                MAX_FIT_ATTEMPTS,
                self.metrics.describe(),
            )
            return
        try:
            measured = {
                "content": (
                    self._root.measure(Gtk.Orientation.HORIZONTAL, -1)[0],
                    self._root.measure(Gtk.Orientation.VERTICAL, -1)[0],
                    screen_width,
                    # In the one-window fallback `_root` contains the band too,
                    # so its budget is the whole panel again.
                    self.metrics.screen_height if self._one_window else content_height,
                ),
            }
            if not self._one_window:
                measured["band"] = (
                    self._band_box.measure(Gtk.Orientation.HORIZONTAL, -1)[0],
                    self._band_box.measure(Gtk.Orientation.VERTICAL, -1)[0],
                    screen_width,
                    band_height,
                )
        except Exception as exc:  # pragma: no cover - measuring must never fail
            log.debug("could not measure the layout (%s)", exc)
            return

        ratios = []
        overflowing: dict[str, tuple[int, int]] = {}
        for what, (wanted_w, wanted_h, room_w, room_h) in measured.items():
            if wanted_w <= room_w and wanted_h <= room_h:
                log.info("%s measures %dx%d, fits %dx%d", what, wanted_w, wanted_h, room_w, room_h)
                continue
            overflowing[what] = (wanted_w, wanted_h)
            if what == "content":
                log.warning("  the tallest surface is %s", self._tallest_screen())
            log.warning(
                "%s measures %dx%d but its window is %dx%d",
                what,
                wanted_w,
                wanted_h,
                room_w,
                room_h,
            )
            ratios.append(min(room_w / wanted_w, room_h / wanted_h))
        if not ratios:
            return

        # A pass that measured exactly what the last pass measured bought
        # nothing, whatever it spent. Only this method can see that -- the
        # metrics cannot know which of the sizes it moved the tallest screen
        # actually uses -- so it is this method that tells `shrunk_by` to stop
        # spending chrome and start spending `fit`. Without it the backstop
        # loops on "shrinking by 0.984" until it runs out of attempts and
        # leaves the overflow on screen (the v0.1.7 geometry regression).
        stalled = overflowing == self._last_measured
        self._last_measured = overflowing

        ratio = min(ratios) * 0.99
        self._fit_attempts += 1
        log.warning("shrinking by %.3f%s", ratio, " (chrome bought nothing)" if stalled else "")
        self._apply_metrics(self.metrics.shrunk_by(ratio, force_fit=stalled))
        self._check_measured_fit()

    def _tallest_screen(self) -> str:
        """Which surface is setting the stack's minimum height, and by how much.

        A ``Gtk.Stack`` measures as tall as its tallest child even when that
        child is not visible, so "the content window does not fit" is always a
        statement about *one* screen -- and until this line existed, finding
        out which one meant editing the shell and re-flashing an image.
        """
        sizes: list[tuple[int, str]] = []
        for name, screen in self.screens.items():
            try:
                height = screen.measure(Gtk.Orientation.VERTICAL, -1)[0]
                width = screen.measure(Gtk.Orientation.HORIZONTAL, -1)[0]
            except Exception:  # pragma: no cover - measuring must never fail
                continue
            sizes.append((height, f"{name} {width}x{height}"))
        sizes.sort(reverse=True)
        return ", ".join(row for _, row in sizes[:3])

    def _check_monitor(self) -> None:
        """The panel may change under us (a projector, a dock, a hotplug)."""
        metrics = detect_metrics(self._screen_override, captions=self.access.captions)
        signature = _signature(metrics)
        if signature == self._signature:
            return
        log.info("the monitor changed: %s", metrics.describe())
        self._signature = signature
        self._fit_attempts = 0
        self._last_measured = None
        self._apply_metrics(metrics)
        self._check_measured_fit()

    # -- state --------------------------------------------------------

    def _on_state_change(self, previous: State, current: State, event: Event) -> None:
        log.info("state %s -> %s (%s)", previous.value, current.value, event.value)
        # Leaving the shelf for anywhere that is not inside it forgets it. The
        # three exceptions are the three ways of being *still* in it: the shelf
        # itself, an activity launched from it, and the grown-up sheet, which
        # is a modal over wherever the child was and puts them back.
        if current not in (State.SHELF, State.IN_ACTIVITY, State.GROWNUP):
            self._shelf = None
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
        shelf_screen = self.screens["shelf"]
        assert isinstance(shelf_screen, ShelfScreen)
        # One screen serves every shelf, so it is told which one it is *before*
        # `on_enter` builds the tiles. A rebuilt layout (a monitor change, the
        # measured-fit backstop) comes back through here too, which is why the
        # answer lives on the window rather than on the screen.
        shelf_screen.set_shelf(self._shelf)

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

        # The band is hidden on Sleeping -- nothing in it is for a machine that
        # has said goodnight -- but its *window* stays mapped. Unmapping it
        # would cost the band its placement: a re-mapped window gets a fresh
        # first configure, and by then the file says phase B, which would put
        # the band below itself. The strip it leaves behind is painted the
        # Sleeping screen's colour instead, so the two windows read as one.
        sleeping = state is State.SLEEPING
        self.band.set_visible(not sleeping)
        # The dim surface is painted on the **windows**, not on a centred box
        # inside one: `sleeping.py` added its class to its own Screen, which is
        # halign/valign CENTER, so the low-arousal screen rendered as a small
        # dark rectangle on full-brightness cream -- the brightest thing in the
        # product at the moment it is meant to be the quietest (forum #36,
        # #38). Two vocabularies, two classes (kidnix_shell.resting).
        rest_class = ""
        if sleeping:
            rest_class = "sleeping" if self.session.policy.is_bedtime(datetime.now()) else "resting"
        for window in (self, *(() if self._one_window else (self.band_window,))):
            for css_class in ("sleeping", "resting"):
                if css_class == rest_class:
                    window.add_css_class(css_class)
                else:
                    window.remove_css_class(css_class)
        self.band.set_journal_sensitive(
            state in (State.HOME, State.SHELF, State.JOURNAL, State.IN_ACTIVITY)
        )
        if state is not State.IN_ACTIVITY:
            self.screens[name].on_enter()
        # **Focus, on every arrival** (review B1: nothing called `grab_focus`
        # anywhere, so a fresh Home had zero FOCUSED nodes in the AT-SPI tree).
        # After `on_enter`, because that is what rebuilds Home's grid -- and
        # `ChildButton` speaks on focus, so a child who tabs nowhere still
        # hears where they have landed.
        self.keys.set_surfaces(
            self.band, None if state is State.IN_ACTIVITY else self.screens[name]
        )
        self.keys.focus_first()

    # -- the tick -----------------------------------------------------

    def _tick(self) -> bool:
        now = datetime.now()
        self.launcher.check()
        self._ticks += 1
        if self._ticks % MONITOR_CHECK_TICKS == 0:
            self._check_monitor()

        if self.session.running:
            self._sun_fraction = self.session.fraction_spent(now)
            self.band.set_progress(
                self._sun_fraction,
                self.session.is_warm(now),
                self.session.time_left_words(now),
            )
            phase = self.session.phase(now)
            self._announce_phase(phase)
            self._advance_ritual(phase)
        else:
            self._last_phase = None
            # **The sun stays down.** This used to be ``set_progress(0.0)``,
            # and fraction 0 means *start of day*: Goodbye showed a full, high
            # sun over "the sun has gone down for today", which for a
            # pre-reader is the picture contradicting the ritual at the exact
            # second they are checking whether it is really over (forum #7).
            # It comes back up on entering "Who's here?" and nowhere else.
            self._sun_fraction = idle_fraction(self.machine.state, self._sun_fraction)
            self.band.set_progress(
                self._sun_fraction,
                self._sun_fraction >= 1.0,
                time_left_words(1.0 - self._sun_fraction, running=False),
            )
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
        action = next_action(
            phase,
            self.machine.state,
            offer_answered=self.session.offer_answered,
            offer_shown=self._offer_on_band,
            put_away_asked=self._put_away_pending,
        )
        if action is RitualAction.PRESENT_OFFER:
            self._present_ending_offer()
        elif action is RitualAction.PUT_AWAY:
            self._begin_put_away()
        elif action is RitualAction.HARD_STOP:
            self._hard_stop()
        elif action is RitualAction.GOODBYE:
            self.session.end(datetime.now())
            self.machine.try_fire(Event.GOODBYE_DUE)

    # -- the ending ritual --------------------------------------------

    def _present_ending_offer(self) -> None:
        """S5, T-6. Two shapes, and neither of them is a modal.

        Until v0.1.5 an offer that arrived during an activity was raised as a
        **fullscreen window over the child's drawing** -- which is exactly the
        interruption 02 #4 argues against, and the CCI audit named it as a
        consequence of the band gap rather than a decision. Now:

        * on a shell surface the offer is a screen in the content window, which
          is where the child already is;
        * inside an activity nothing covers the drawing at all. The band
          changes -- the sun is already low and warm -- and the two choices
          appear in it for :data:`BAND_OFFER_SECONDS`, spoken once.
        """
        if self.launcher.running and self.machine.state is State.IN_ACTIVITY:
            self._offer_in_band()
            return
        self._clear_band_offer()
        self.machine.try_fire(Event.ENDING_OFFER_DUE)

    def _offer_in_band(self) -> None:
        if self._offer_on_band:
            return
        log.info("ending offer, in the band (the child is in an activity)")
        self._offer_on_band = True
        self.band.set_offer_mode(True)
        self.speech.speak(OFFER_QUESTION)
        if self._band_offer_handle is not None:
            GLib.source_remove(self._band_offer_handle)
        self._band_offer_handle = GLib.timeout_add_seconds(
            BAND_OFFER_SECONDS, self._band_offer_expired
        )

    def _band_offer_expired(self) -> bool:
        """Nobody answered. That is an answer, and the shell stops asking.

        The alternative is re-presenting it on the next tick for the whole
        four-minute window, which is the bug the offer latch exists to prevent
        (`docs/spikes/e2e-scenario.md` section 3.2). Put away still arrives at
        T-2 exactly as it would have.
        """
        self._band_offer_handle = None
        if self._offer_on_band:
            log.info("the band offer went unanswered; not asking again")
            self.session.answer_offer()
        self._clear_band_offer()
        return False

    def _clear_band_offer(self) -> None:
        """Give Undo and My Things their places back."""
        if self._band_offer_handle is not None:
            GLib.source_remove(self._band_offer_handle)
            self._band_offer_handle = None
        self._offer_on_band = False
        self.band.set_offer_mode(False)

    def _begin_put_away(self, event: Event = Event.PUT_AWAY_DUE) -> None:
        """S6, T-2. Two shapes, and neither of them destroys a drawing.

        Until v0.1.5.1 this raised the content window over whatever the child
        was doing, sent SIGTERM and SIGKILLed five seconds later. For Tux Paint
        that meant the child could not see the tick they had to press --  the
        shell was in front of it -- so they did not press it, so
        "Let's keep that." was followed by the drawing being deleted (§19.3).
        Spec 7c's ruling, and this method:

        * **on a shell surface**, nothing has changed: S6 is a screen, the work
          flies into My Things, and anything still running is asked to go;
        * **inside an activity**, the shell asks and then *waits*
          (:meth:`_ask_activity_to_finish`). The content window stays where it
          is, behind the activity. S6 appears when the activity has actually
          gone, which is the moment "Let's keep that" becomes true.
        """
        self._clear_band_offer()
        if self.launcher.running:
            self._ask_activity_to_finish(event)
            return
        self._enter_put_away(event)

    def _enter_put_away(self, event: Event) -> None:
        """Show S6. Only ever called with the screen actually free."""
        if not self.machine.try_fire(event) and self.machine.state is not State.PUT_AWAY:
            self._goodbye_after_put_away = False
            return
        self.band.set_finishing_mode(False)
        # Spec 7a: three seconds of dead Back, so the ritual is not undone by a
        # child drumming on the band -- and then Back works again.
        self._back_locked_until = time.monotonic() + PUT_AWAY_BACK_LOCK_SECONDS
        self.present()  # take the screen back
        # Sweep first so the thing the child just made is in the Journal before
        # the animation claims to have put it there.
        self.watcher.sweep_now()
        if not self.ctx.work_lost:
            self.earcons.play(KEEP, speaking=True)
        if self._goodbye_after_put_away:
            # "All done" or "End session now" -- the clock is not driving this
            # ending, so Goodbye is timed from here rather than from the press,
            # which may have been a whole quit dialogue ago.
            self._goodbye_after_put_away = False
            self._schedule_goodbye()

    def _ask_activity_to_finish(self, event: Event) -> None:
        """Ask, say so, and wait. The child's program keeps the screen.

        The band loses everything except Back, the sun and the Ear
        (:meth:`Band.set_finishing_mode`) -- there is one thing to do and the
        band should not offer a second. What the shell *says* depends on the
        manifest's quit contract: an activity that answers SIGTERM with its own
        question needs the child told that the question is theirs, because
        nothing on that screen says so to a pre-reader.
        """
        self._put_away_pending = True
        self._put_away_event = event
        self._journal_after_activity = False
        self.band.set_finishing_mode(True)
        self.band.set_journal_sensitive(False)
        # Sweep first: whatever has already been autosaved is in My Things
        # before the shell says a word about keeping it.
        self.watcher.sweep_now()
        self.launcher.request_stop()
        grace = self.launcher.grace_seconds
        log.info(
            "put-away: asked %s to finish (quit=%s, grace %.0fs); waiting, not killing",
            self.launcher.current.activity_id if self.launcher.current else "?",
            "confirm" if self.launcher.asks_before_quitting else "signal",
            grace,
        )
        self._say_put_away_line()
        self._cancel_reask()
        self._reask_handle = GLib.timeout_add(int(grace * 1000), self._reask_once)

    def _say_put_away_line(self) -> None:
        """The band's half of S6 (spec 7c), and the earcon that goes with it.

        The sentence depends on the manifest: an activity in ``confirm`` mode
        has just put its own tick and cross on screen, and nothing there tells
        a pre-reader that the question is theirs to answer -- so the shell
        says it. The keep earcon *is* the sound of something being kept, so it
        does not play when there is nothing to keep.
        """
        lost = self.ctx.work_lost
        if not lost:
            self.earcons.play(KEEP, speaking=True)
        mode = "confirm" if self.launcher.asks_before_quitting else "signal"
        self.speech.speak(put_away_line(mode, lost=lost))

    def _reask_now(self) -> None:
        """Back, during the wait: ask again, and repeat the line."""
        if not self.launcher.running:
            return
        self.earcons.play(BACK)
        self.launcher.request_stop()
        self._say_put_away_line()

    def _reask_once(self) -> bool:
        """The grace ran out. Ask again -- once -- and then keep waiting.

        Not a SIGKILL: a child who has not found the tick yet has not lost
        their drawing, they are five. The second SIGTERM is for the activity
        that missed the first one, and the repeated line is for the child who
        missed the first one. The only kill is :meth:`_hard_stop`.
        """
        self._reask_handle = None
        if not self._put_away_pending or not self.launcher.running:
            return False
        log.info("put-away: no answer after the grace; asking once more")
        self.launcher.request_stop()
        self._say_put_away_line()
        return False

    def _cancel_put_away_wait(self) -> None:
        """Stop waiting for an activity to finish, and give the band back."""
        self._put_away_pending = False
        self._goodbye_after_put_away = False
        self._cancel_reask()
        self.band.set_finishing_mode(False)
        self.band.set_journal_sensitive(self.machine.state is State.IN_ACTIVITY)

    def _cancel_reask(self) -> None:
        if self._reask_handle is not None:
            GLib.source_remove(self._reask_handle)
            self._reask_handle = None

    def _hard_stop(self) -> None:
        """T-0 with the activity still on screen. The only SIGKILL (spec 7c).

        The hard stop is still the hard stop. What changes is that it is now
        the *whole* of the kill path rather than a five-second timer, and that
        it is honest about what it cost: the launcher logs the loss for the
        parent, and :attr:`ShellContext.work_lost` stops S6 and S7 claiming to
        have kept something they did not.
        """
        self._cancel_reask()
        if self.launcher.running:
            self.ctx.work_lost = True
            self.launcher.hard_stop()
        self._put_away_pending = False
        self.watcher.sweep_now()
        self._enter_put_away(self._put_away_event)

    # -- ShellHost ----------------------------------------------------

    def choose_profile(self, profile: Profile) -> None:
        # Only Who's here? offers profiles; refuse anywhere else rather than
        # quietly starting a clock behind a screen that is not asking.
        if not self.machine.can(Event.CHOOSE_PROFILE):
            return
        # Whose journal, whose budget, whose grid -- before the clock starts,
        # because `may_start` reads this child's usage and not the machine's.
        self._use_profile(profile)
        self._apply_tint(profile)
        now = datetime.now()
        refusal = self.session.may_start(now)
        if refusal is not StartRefusal.OK:
            self._refuse(refusal)
            return
        self.session.start(now)
        # A new sitting: last time's answer to "what's next after?" is not this
        # time's, and Goodbye must not show a picture nobody chose today. Nor
        # is last time's lost work this time's.
        self.ctx.next_after = None
        self.ctx.work_lost = False
        if profile.skip_next_choice:
            log.info("%s skips S1b (skip_next_choice)", profile.id)
            self.machine.try_fire(Event.SKIP_NEXT_CHOICE)
            return
        self.machine.try_fire(Event.CHOOSE_PROFILE)

    def choose_next_after(self, option: NextAfter) -> None:
        """S1b: the child said what happens after. Spec 7b / SYNTHESIS D4.

        "Not sure yet" is a real answer and it is *not* a plan: it takes the
        child to Home and leaves Goodbye on its generated fallback. Coco's
        named failure mode is rigidity -- a child treating the machine's
        statements as inviolable rules -- and a screen with no way to decline
        the question is how that starts (forum, child-psychologist MAJOR 5).
        """
        if not self.machine.can(Event.CHOOSE_NEXT_AFTER):
            return
        self.ctx.next_after = None if option.skips else option
        log.info("next after this session: %s", option.id)
        self.earcons.play(TAP, speaking=True)
        self.machine.try_fire(Event.CHOOSE_NEXT_AFTER)

    def _refuse(self, refusal: StartRefusal) -> None:
        """No silent denials, and no adult error messages (SYNTHESIS C3).

        Two things about this changed on 2026-08-23. It no longer says "See you
        tomorrow" -- suggestions.py's own docstring has forbidden that phrasing
        all along (D6: the system has no interest in whether the child comes
        back), and it was firing on the child's flattest day (forum #28, #47).
        And because :meth:`Session.may_start` now refuses everything below the
        session floor, this lands at **Who's here**, before the child has told
        the computer what they are doing afterwards: a plan must never be
        collected for a session that cannot happen (forum #46, #59, #60).

        The sentence is handed to the Resting screen rather than spoken over
        its arrival, so the child hears one answer to the question they asked.
        """
        line = refusal_line(bedtime=refusal is StartRefusal.BEDTIME)
        self.ctx.rest_reason = line
        if not self.machine.try_fire(Event.GOODNIGHT):
            # Nowhere to put the screen (the gate, mid-sheet): say it anyway.
            self.ctx.rest_reason = ""
            self.speech.speak(line)

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

    def open_shelf(self, shelf: Activity) -> None:
        """A shelf tile was tapped: one more screen of tiles, and only one.

        The shelf's own ``exec`` is deliberately never run (it is the fallback
        for a shell that has no shelf screen, and for GCompris it is a single
        curated activity rather than the 198-activity menu). What is opened is
        :class:`kidnix_shell.screens.shelf.ShelfScreen`, over this shelf's
        children.
        """
        if not shelf.is_shelf or not self.machine.can(Event.OPEN_SHELF):
            return
        self._shelf = shelf
        self.earcons.play(TAP)
        log.info(
            "opening the %r shelf (%d children)", shelf.id, len(self.ctx.shelves.get(shelf.id, []))
        )
        self.machine.try_fire(Event.OPEN_SHELF)

    def resume_entry(self, entry: Entry) -> None:
        activity = next((a for a in self.ctx.activities if a.id == entry.activity_id), None)
        if activity is None:
            self.speech.speak("That one isn't here any more.")
            return
        path = entry.latest_path if activity.supports_resume else None
        self.launch(activity, path)

    def _on_activity_exit(self, running: RunningActivity, code: int) -> None:
        log.info("%s finished (%s)", running.activity_id, code)
        self._cancel_reask()
        if not self._put_away_pending:
            # Put away has to keep the content window where it is until S6 is
            # actually on screen; `_enter_put_away` presents it itself.
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
        self._activity_finished()

    def _activity_finished(self) -> None:
        """Everything that has to happen once the activity is really gone.

        Reached from two directions -- the launcher noticing the process exited
        on its own, and Put away killing it -- and it must do the same thing
        both times or the shell strands itself in ``IN_ACTIVITY``.
        """
        if self._nag_handle is not None:
            GLib.source_remove(self._nag_handle)
            self._nag_handle = None
        self._cancel_reask()
        if self._put_away_pending:
            # The child answered the activity's question (or it went quietly).
            # *Now* the shell may have the screen back, and only now is
            # "Let's keep that" a true sentence (spec 7c).
            self._put_away_pending = False
            self._journal_after_activity = False
            self._enter_put_away(self._put_away_event)
            return
        if self.machine.state is State.IN_ACTIVITY:
            # Held across the transition: ACTIVITY_EXITED lands on Home, and
            # arriving at Home is what *forgets* a shelf, so the answer has to
            # be taken before the question is asked.
            shelf = self._shelf
            self.machine.try_fire(Event.ACTIVITY_EXITED)
            if shelf is not None and not self._journal_after_activity:
                # Back from a game goes back to the shelf it was chosen from,
                # not one level further out. A child who came in through
                # "Letters & numbers" and lands on Home has been moved without
                # being shown the move (panel-wave-c section 2).
                self._shelf = shelf
                self.machine.try_fire(Event.OPEN_SHELF)
        if self._journal_after_activity:
            # My Things was pressed *inside* the activity: the child asked to
            # go and look at their things, and the activity had to finish
            # first. Now it has.
            self._journal_after_activity = False
            self.open_journal()

    def _end_activity(self, *, then_journal: bool = False) -> None:
        """Ask the running activity to finish, from the band (v0.1.5).

        Back and My Things are reachable during an activity for the first time,
        because the band is on screen. Both mean "I have finished with this",
        and neither may take the child to a shell surface that is still hidden
        behind a running program -- so the shell asks the activity to quit and
        lets ``ACTIVITY_EXITED`` do the navigating when it actually has.

        **It asks; it does not insist, and this is the whole design.** Measured
        on the real image: Tux Paint catches SIGTERM (SDL turns it into
        ``SDL_QUIT``) and answers it by putting *its own* picture-coded
        "Do you really want to quit?" on screen -- a tick and a cross, two
        large targets -- and waiting. Only when the child taps the tick does it
        autosave and exit. A shell that SIGKILLed after five seconds would
        therefore destroy the drawing every single time, which is the one
        outcome "making over consuming" cannot survive. So Back sends SIGTERM
        and then waits, for as long as the child needs.

        Spec 7a's SIGTERM -> grace -> SIGKILL ruling is about **Put away**, and
        it still holds there: the hard stop is the hard stop. Back is not the
        hard stop. Back asks.

        The Journal is swept *first*, so that if the child reaches My Things
        before the activity has gone, what they made is already there.
        """
        self.earcons.play(BACK)
        self._journal_after_activity = then_journal
        self.watcher.sweep_now()
        if not self.launcher.running:
            # It went away on its own between the tick and the press.
            self.machine.try_fire(Event.ACTIVITY_EXITED)
            if then_journal:
                self._journal_after_activity = False
                self.open_journal()
            return
        log.info(
            "the band asked the activity to finish (%s)", "my things" if then_journal else "back"
        )
        if self.launcher.request_stop():
            if self._nag_handle is not None:
                GLib.source_remove(self._nag_handle)
            self._nag_handle = GLib.timeout_add(
                int(self.launcher.grace_seconds * 1000), self._activity_is_asking
            )

    def _activity_is_asking(self) -> bool:
        """It did not go. Say why, rather than leaving a child pressing Back.

        An activity that is still there a few seconds after SIGTERM is almost
        always showing its own confirmation. The child can answer it -- Tux
        Paint's is a tick and a cross -- but nothing on screen tells a
        pre-reader that the question is *theirs* to answer, so the shell says
        so out loud.
        """
        self._nag_handle = None
        if not self.launcher.running:
            return False
        # Whatever the child asked for, they are still in the activity, so a
        # Journal that opens later would arrive from nowhere.
        self._journal_after_activity = False
        name = self._running_activity_name() or "It"
        log.info("%s is still running after SIGTERM; it is asking the child something", name)
        self.speech.speak(f"{name} is asking if you're done.")
        return False

    def _running_activity(self) -> Activity | None:
        """The manifest behind the program on screen, if we still have it.

        Looked up in the shelves as well as on Home: a game launched from the
        "Letters & numbers" shelf is not in ``ctx.activities`` at all, and
        until this looked there the shell could not name the thing the child
        was actually inside.
        """
        running = self.launcher.current
        if running is None:
            return None
        pools: list[list[Activity]] = [self.ctx.activities, *self.ctx.shelves.values()]
        for pool in pools:
            for activity in pool:
                if activity.id == running.activity_id:
                    return activity
        return None

    def _running_activity_name(self) -> str:
        """What the child calls the thing they are in ("Draw"), or a fallback."""
        activity = self._running_activity()
        return activity.name if activity is not None else ""

    def _running_undo_key(self) -> str:
        """The running activity's own undo keystroke, if its manifest names one."""
        activity = self._running_activity()
        return activity.undo_key if activity is not None else ""

    def _on_new_work(self, entries: list[Entry]) -> None:
        log.info("kept %d new thing(s)", len(entries))
        self.earcons.play(KEEP)

    def go_home(self) -> None:
        self.machine.try_fire(Event.BACK)

    def open_journal(self) -> None:
        if self._put_away_pending:
            # My Things is not on the band during the wait; if anything else
            # reaches this, it must not send a second SIGTERM behind the
            # child's back. Say where they are instead.
            self._say_put_away_line()
            return
        if self.machine.state is State.IN_ACTIVITY:
            # My Things during an activity: end the activity, then open the
            # Journal (v0.1.5). Opening it *underneath* a running program would
            # be a screen the child cannot see, pressed from a band they can.
            self._end_activity(then_journal=True)
            return
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

    def dismiss_offer(self, answer: OfferAnswer) -> None:
        """S5: the child answered, and the answers are no longer the same answer.

        Until 2026-08-23 both buttons did exactly this much: latch the offer,
        say a sentence, return the child where they were. Put away landed at
        T-2 either way, so "Finish this one" was a promise the clock did not
        keep and the choice was theatre (forum #20, #29). Now:

        * **Finish this one** defers put-away to one beat before the hard stop
          (:meth:`kidnix_shell.session.Session.answer_offer`). The child keeps
          the activity until T-1 unless they finish sooner, and the sentence
          says exactly that.
        * **One last little thing** takes them to **Home**, where opening one
          more activity is Home continuing to work, and leaves put-away where
          it was -- which is what makes room for the little thing to fit.
        * **Ask for more time** dismisses, and says who can add time without
          sending a five-year-old off to negotiate for it.

        Answered *from the band*, during an activity, the transition is a no-op
        (``DISMISS_OFFER`` is not valid in ``IN_ACTIVITY``) and that is still
        correct: the child is already inside the thing they said they would
        finish. The consequence is on the clock, not on the navigation.
        """
        self._clear_band_offer()
        # Latch first: the answer counts even if the transition is a no-op
        # because a later tick already moved the child on.
        self.session.answer_offer(defer_put_away=answer.defers_put_away)
        self.speech.speak(answer.speech)
        self.machine.try_fire(Event.DISMISS_OFFER)
        if answer.returns_home and self.machine.state is State.JOURNAL:
            # "One last little thing" means Home: My Things is a place to look
            # at what is already made, not a place to make the last thing.
            self.machine.try_fire(Event.BACK)

    def finish_now(self) -> None:
        """Child- or grown-up-initiated ending: the same ritual, never a cut.

        The Home "All done" tile and the grown-up sheet's "End session now" are
        the same path. The clock is not involved, so Goodbye has to be timed
        here rather than waiting for :class:`Phase.ENDED`.
        """
        self._goodbye_after_put_away = True
        self._begin_put_away(Event.IM_FINISHED)

    def _schedule_goodbye(self) -> None:
        """S6 -> S7, when the clock is not the thing doing the ending."""
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
        now = datetime.now()
        bedtime = self.session.policy.is_bedtime(now)
        self.session.end(now)
        if self.machine.try_fire(Event.GOODNIGHT) and bedtime:
            # The sleep motif is a *yawn* -- a sleep-onset cue. It belongs to
            # the real lockout and nowhere near four in the afternoon, where
            # pairing it with "the nice thing stopped" is backwards for exactly
            # the children who find bedtime hardest (forum #17).
            self.earcons.play(SLEEP, speaking=True)

    def start_session(self, minutes: int | None = None) -> None:
        now = datetime.now()
        self.ctx.work_lost = False
        length = None if minutes is None else minutes * 60
        if not self.session.start(now, length):
            self._refuse(self.session.may_start(now))
            return
        self.machine.try_fire(Event.START_SESSION)

    def add_minutes(self, minutes: int) -> int:
        now = datetime.now()
        added = self.session.add_minutes(minutes, now)
        if added and self._put_away_pending and self.session.phase(now) is Phase.RUNNING:
            # A grown-up moved the hard stop while the shell was waiting for an
            # activity to finish. The ending is off; the activity has already
            # been asked and may still go, in which case the child simply comes
            # back to Home. What must not happen is S6 arriving in the middle
            # of a session that was just extended.
            log.info("put-away: the ending was called off; the child carries on")
            self._cancel_put_away_wait()
        if added and self.machine.state in (State.GOODBYE, State.PUT_AWAY, State.SLEEPING):
            self.machine.try_fire(Event.START_SESSION)
        return added

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
        if self._put_away_pending:
            # Put away is already asking (spec 7c). Back means the same thing
            # here as it does anywhere else in an activity -- "I'm finished" --
            # so it asks again rather than contradicting the shell's own
            # request, and it says the line again for a child who missed it.
            self._reask_now()
            return
        if self.machine.state is State.IN_ACTIVITY:
            # v0.1.5: the band is on screen during an activity, so Back is the
            # child's way out of one -- and it has to actually *end* it, not
            # navigate away and leave the program on top of Home. ADR-0010 #5
            # retires here: Tux Paint's own Quit tool and its unreadable
            # "Do you really want to quit?" modal exist only because this
            # button did not.
            self._end_activity()
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

        **Inside an activity it says where the child's undo actually is**
        (:func:`kidnix_shell.ritual.undo_line`, and the note above it). The
        panel asked for ``undo_key`` routing; the manifest key exists and is
        read, and the *sending* half does not, because no mechanism for it on
        this machine is one a child's session may have -- a GTK client cannot
        inject into another Wayland client, mutter does not implement
        ``virtual-keyboard-v1``, and ``ydotool`` would mean handing the kid
        account ``/dev/uinput``. So the press is answered with a true sentence,
        spoken and captioned, naming the activity's own control. Honest and
        audible beats clever and intermittent -- the same rule as "Nothing to
        undo".
        """
        if self.machine.state is State.IN_ACTIVITY:
            self.speech.speak(undo_line(self._running_activity_name(), self._running_undo_key()))
            return
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
        """Save a PNG of the shell as the child sees it (development, review).

        GNOME 45+ restricts ``org.gnome.Shell.Screenshot`` to the Shell's own
        UI and Mutter implements no wlr-screencopy, so no external tool can
        photograph the kiosk. Rendering our *own* widget tree needs no
        permission at all: paint it into a snapshot and hand the node to the
        renderer we are already using.

        Since v0.1.5 the shell is two toplevels, so this **composites** them --
        the band's tree at ``0,0`` and the content tree at ``0,band_height`` --
        into one image the size of the panel, which is what the compositor puts
        in front of the child. If the band cannot be rendered (no renderer yet,
        which happens on a window nobody has presented) the content window is
        written on its own and the log says so, rather than the whole capture
        failing.
        """
        try:
            band_height = self.metrics.band_window_height
            width = self.get_width() or self.metrics.screen_width or 1280
            height = self.get_height() or self.metrics.content_height or 800
            content = self._snapshot_node(self, width, height)
            band = (
                None
                if self._one_window
                else self._snapshot_node(self.band_window, width, band_height)
            )
            renderer = self._renderer()
            if content is None or renderer is None:
                log.warning("nothing to capture yet")
                return False

            snapshot = Gtk.Snapshot()
            if band is not None:
                snapshot.append_node(band)
                snapshot.translate(Graphene.Point().init(0, band_height))
            snapshot.append_node(content)
            node = snapshot.to_node()
            if node is None:  # pragma: no cover - both trees were empty
                log.warning("nothing to capture yet")
                return False
            texture = renderer.render_texture(node, None)
            path.parent.mkdir(parents=True, exist_ok=True)
            texture.save_to_png(str(path))
            log.info(
                "wrote %s (%dx%d%s)",
                path,
                width,
                height + (band_height if band is not None else 0),
                "" if band is not None else ", content only -- the band would not render",
            )
            return True
        except Exception as exc:
            log.warning("could not capture the window: %s", exc)
            return False

    def _renderer(self) -> Gsk.Renderer | None:
        """Whichever of the two windows has one. Neither is presented in tests."""
        windows = (self,) if self._one_window else (self, self.band_window)
        for window in windows:
            native = window.get_native()
            renderer = native.get_renderer() if native is not None else None
            if renderer is not None:
                return renderer
        return None

    @staticmethod
    def _snapshot_node(window: Gtk.Widget, width: int, height: int) -> Gsk.RenderNode | None:
        """One window's tree as a render node.

        Two routes, because the first one has a hole. ``Gtk.WidgetPaintable``
        hands back the widget's *last painted* content, and returns nothing at
        all when the widget is waiting for a redraw -- which is the normal
        state of a window nobody is compositing, i.e. every automated
        screenshot run. So if the paintable comes back empty we walk the tree
        ourselves, which always has an answer.
        """
        paintable = Gtk.WidgetPaintable.new(window)
        snapshot = Gtk.Snapshot()
        paintable.snapshot(snapshot, width, height)
        node = snapshot.to_node()
        if node is not None:
            return node
        direct = Gtk.Snapshot()
        window.do_snapshot(window, direct)
        return direct.to_node()

    # -- shutdown ------------------------------------------------------

    def _on_close(self, _window: Gtk.Window) -> bool:
        self.shutdown()
        return False

    def shutdown(self) -> None:
        if self._shutting_down:
            # Closing either toplevel gets us here, and so does the
            # application's own shutdown; doing it twice removes freed sources.
            return
        self._shutting_down = True
        for handle in (
            self._tick_handle,
            self._showing_handle,
            self._goodbye_handle,
            self._band_offer_handle,
            self._content_handle,
            self._band_handle,
            self._nag_handle,
            self._reask_handle,
        ):
            if handle is not None:
                GLib.source_remove(handle)
        self._tick_handle = None
        self._showing_handle = None
        self._goodbye_handle = None
        self._reask_handle = None
        self._band_offer_handle = None
        self._content_handle = None
        self._band_handle = None
        self._nag_handle = None
        if not self._one_window:
            self.band_window.destroy()
        self.watcher.stop()
        self.launcher.stop()
        self.session.end(datetime.now())
        self.speech.close()
        self.earcons.close()
        if self.ctx.voice is not None:
            # A recording still running at shutdown is still the child's: stop
            # closes the Ogg container properly rather than truncating it.
            self.ctx.voice.close()


class ShellApplication(Adw.Application):
    """Two windows, no menus, no about dialog, no preferences for the child.

    One ``GtkApplication`` for both toplevels is not a convenience, it is a
    requirement: two *processes* sharing an application id do not get two
    windows -- the second one's ``activate`` is delivered to the first, which
    simply presents the window it already has. The spike hit that and had to be
    rewritten around it.
    """

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
        shelves: dict[str, list[Activity]] | None = None,
        research: ResearchConfig | None = None,
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
        self._shelves = shelves or {}
        self._research = research if research is not None else ResearchConfig()
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
                shelves=self._shelves,
                research=self._research,
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
        self.window.present_all()

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
        if self._start_on == "resting":
            # Not driven: *earned*. Spending the budget and then pressing the
            # child's own face is the real path to the refusal, so the
            # screenshot shows what a child would actually get -- the warm no
            # at Who's here, before any plan has been collected, and the
            # daytime vocabulary behind it.
            window.session.usage.seconds = window.session.policy.daily_budget
            window.choose_profile(self._config.profiles[0])
            return False
        window.choose_profile(self._config.profiles[0])
        if self._start_on == "next-after":
            return False
        if self._config.next_after:
            window.choose_next_after(self._config.next_after[0])
        if self._start_on == "goodbye":
            if self._demo:
                # A Goodbye with nothing made shows half the screen: the whole
                # ruling is "the destination, then what was made".
                from .demo import seed_work

                seed_work(self._activities)
                window.watcher.sweep_now()
            window.machine.try_fire(Event.IM_FINISHED)
            window.session.end(datetime.now())
            window.machine.try_fire(Event.GOODBYE_DUE)
        if self._start_on in ("put-away", "journal", "shelf"):
            # The screens that need something to have been *made*: S6 has a
            # thumbnail flying into My Things and a mic to talk about it, and a
            # Journal with nothing in it photographs its empty state.
            from .demo import seed_work

            if self._demo:
                seed_work(self._activities)
                window.watcher.sweep_now()
        if self._start_on == "shelf":
            shelf = next((a for a in self._activities if a.is_shelf), None)
            if shelf is not None:
                window.open_shelf(shelf)
        if self._start_on == "journal":
            window.open_journal()
        if self._start_on == "put-away":
            window.machine.try_fire(Event.IM_FINISHED)
        if self._start_on == "offer":
            # The band offer, added to the band rather than replacing Undo and
            # My Things. Driven directly: the shape of the band is the point,
            # not the route to it.
            window.band.set_offer_mode(True)
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
