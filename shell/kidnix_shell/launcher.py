"""Launching and stopping activities (spec section 2, S3 and S6).

The shell is a launcher, not a host (ADR-0004): activities are separate
processes. Under gnome-kiosk the newest window is on top, so launching *is*
foregrounding; the shell window stays behind and takes the screen back when
the activity exits.

Two things matter here and are tested:

* **A clean environment.** The child's processes get an allow-listed
  environment with XDG directories under the kid home. Nothing from the
  shell's own environment leaks -- no ``KIDNIX_*`` internals, no inherited
  developer variables, no secrets.
* **A termination path that always terminates -- and never earlier than it
  has to.** Every activity declares how it answers "please finish"
  (:data:`kidnix_shell.activities.QUIT_MODES`, spec 7c): ``signal`` means
  SIGTERM ends it, ``confirm`` means SIGTERM puts a *question* on the child's
  screen and waits for them. :meth:`Launcher.request_stop` asks and returns;
  :meth:`Launcher.force_stop` is the SIGKILL, and since v0.1.6 it is reached
  only at the session's hard stop, because the alternative is deleting a
  drawing while saying "Let's keep that" (§19.3). The activity is started in
  its own process group so a misbehaving app that forks children cannot leave
  orphans on top of the shell.
* **A launch that failed is not a launch.** An activity that exits non-zero
  within :data:`FAST_FAIL_SECONDS` never really started; the child pressed a
  button and the screen flickered
  (`docs/spikes/e2e-scenario.md` section 3.1). Its stderr is captured to a
  temporary file so the shell can put the tail in the parent's journal instead
  of leaving the child with nothing at all.
"""

from __future__ import annotations

import contextlib
import logging
import os
import signal
import subprocess
import tempfile
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import IO, Any

from .activities import QUIT_CONFIRM, QUIT_SIGNAL
from .i18n import current_language

log = logging.getLogger(__name__)

#: The fallback grace for a stop with no activity behind it (the shell's own
#: shutdown, and test doubles that are not manifests). Per-activity graces come
#: from the manifest -- :data:`kidnix_shell.activities.DEFAULT_QUIT_GRACE`.
AUTOSAVE_GRACE_SECONDS = 5.0

#: Under this, a non-zero exit means the program did not open. Generous: Tux
#: Paint takes about a second to put a window up on the panel we ship on, and
#: a missing Flatpak fails in well under a tenth of that.
FAST_FAIL_SECONDS = 3.0

#: How much of a failed activity's stderr the parent's journal gets. Enough for
#: "app/... not installed"; not enough for a Mesa novel.
STDERR_TAIL_BYTES = 2048

#: Variables an activity legitimately needs to find the display, the session
#: bus and the user's runtime dir. Everything else is dropped.
ENV_ALLOWLIST = (
    "DISPLAY",
    "WAYLAND_DISPLAY",
    "XDG_RUNTIME_DIR",
    "XDG_SESSION_TYPE",
    "XDG_CURRENT_DESKTOP",
    "XDG_SESSION_DESKTOP",
    "DBUS_SESSION_BUS_ADDRESS",
    "PATH",
    "LANG",
    "LANGUAGE",
    "TZ",
    "DCONF_PROFILE",
    "GDK_BACKEND",
    "QT_QPA_PLATFORM",
    "SDL_VIDEODRIVER",
)

#: Locale variables are allow-listed by prefix.
ENV_ALLOWLIST_PREFIXES = ("LC_",)

#: The two variables the shell *adds*. Together they are the activity SDK's
#: whole input contract (``kidnix_activity.env``): which manifest this process
#: is, and whose things it may write.
ACTIVITY_ID_VAR = "KIDNIX_ACTIVITY_ID"
PROFILE_ID_VAR = "KIDNIX_PROFILE_ID"

DEFAULT_PATH = "/usr/local/bin:/usr/bin:/bin"


class Outcome:
    """How a stop attempt finished."""

    NOT_RUNNING = "not_running"
    EXITED = "exited"  # went away on its own before we asked
    TERMINATED = "terminated"  # SIGTERM was enough
    KILLED = "killed"  # needed SIGKILL


@dataclass
class RunningActivity:
    """A live child process."""

    activity_id: str
    argv: list[str]
    process: Any  # subprocess.Popen, or a test double
    started_at: datetime
    resume_path: Path | None = None
    #: From the manifest (spec 7c): "signal" or "confirm".
    quit_mode: str = QUIT_SIGNAL
    #: From the manifest: how long to wait after asking, before asking again.
    quit_grace: float = AUTOSAVE_GRACE_SECONDS
    #: How many times the shell has asked this activity to finish. The second
    #: ask is the re-ask at the end of the grace; there is never a third.
    asked: int = 0
    env: dict[str, str] = field(default_factory=dict, repr=False)
    stderr_file: IO[bytes] | None = field(default=None, repr=False)

    @property
    def pid(self) -> int:
        return int(self.process.pid)

    def poll(self) -> int | None:
        return self.process.poll()

    @property
    def running(self) -> bool:
        return self.poll() is None

    @property
    def asks_before_quitting(self) -> bool:
        """Does SIGTERM put a question on the child's screen instead of ending it?"""
        return self.quit_mode == QUIT_CONFIRM

    def ran_for(self, now: datetime | None = None) -> float:
        """Seconds between launch and ``now``."""
        return ((now or datetime.now()) - self.started_at).total_seconds()

    def failed_to_open(self, code: int, now: datetime | None = None) -> bool:
        """Did this exit look like "the program is not there" rather than a quit?"""
        return code != 0 and self.ran_for(now) < FAST_FAIL_SECONDS

    def stderr_tail(self, limit: int = STDERR_TAIL_BYTES) -> str:
        """The last few kilobytes the activity complained about, or ``""``."""
        handle = self.stderr_file
        if handle is None:
            return ""
        try:
            handle.flush()
            size = handle.seek(0, os.SEEK_END)
            handle.seek(max(0, size - limit))
            return handle.read().decode("utf-8", "replace").strip()
        except (OSError, ValueError) as exc:  # pragma: no cover - closed file
            log.debug("could not read %s's stderr: %s", self.activity_id, exc)
            return ""

    def close_stderr(self) -> None:
        """Drop the temporary file (it is unlinked already; this frees the fd)."""
        if self.stderr_file is not None:
            with contextlib.suppress(OSError):  # pragma: no cover
                self.stderr_file.close()
            self.stderr_file = None


def build_env(
    home: Path,
    parent_env: Mapping[str, str] | None = None,
    extra: Mapping[str, str] | None = None,
    language: str = "",
) -> dict[str, str]:
    """The environment an activity is given. Deliberately small."""
    source = os.environ if parent_env is None else parent_env
    env: dict[str, str] = {}
    for key, value in source.items():
        if key in ENV_ALLOWLIST or key.startswith(ENV_ALLOWLIST_PREFIXES):
            env[key] = value

    env.setdefault("PATH", DEFAULT_PATH)
    env.setdefault("LANG", "en_GB.UTF-8")
    # **The child's language, not the session's** (ADR-0012). `LANG` above is
    # the machine's locale and stays what it was -- it is what sorts and
    # formats -- but `LANGUAGE` is gettext's own override, and it is what makes
    # an activity (and its own catalogue, via `kidnix_activity.i18n`) speak the
    # language of the profile that launched it rather than the one in
    # /etc/locale.conf. A monolingual machine sets it to en_GB, which no
    # catalogue answers to, which is the unchanged behaviour.
    env["LANGUAGE"] = language or current_language()
    env["HOME"] = str(home)
    env["USER"] = os.environ.get("USER", "kid")
    env["XDG_DATA_HOME"] = str(home / ".local" / "share")
    env["XDG_CONFIG_HOME"] = str(home / ".config")
    env["XDG_CACHE_HOME"] = str(home / ".cache")
    env["XDG_STATE_HOME"] = str(home / ".local" / "state")
    # SYNTHESIS H1: the child session has no egress. Belt and braces for
    # activities that would otherwise sit retrying a proxy for 30 seconds.
    env["no_proxy"] = "*"
    if extra:
        env.update(extra)
    return env


class Launcher:
    """Runs at most one activity at a time -- there is no multitasking here."""

    def __init__(
        self,
        home: Path,
        parent_env: Mapping[str, str] | None = None,
        spawn: Callable[..., Any] | None = None,
        profile_id: str = "",
    ) -> None:
        self.home = home
        self.parent_env = parent_env
        self._spawn = spawn or subprocess.Popen
        self.current: RunningActivity | None = None
        self.on_exit: Callable[[RunningActivity, int], None] | None = None
        #: **Which child is sitting there** (:data:`PROFILE_ID_VAR`). Set by
        #: ``ShellWindow._use_profile`` and exported to every activity.
        #:
        #: An activity built on ``kidnix_activity`` writes its own Journal
        #: entries rather than leaving files for the importer to notice, and a
        #: child's Journal has lived under ``kidnix/profiles/<id>/`` since
        #: 2026-08-23. Without this the SDK would have to guess, and the only
        #: guess available -- the pre-profiles layout -- is a directory the
        #: shell no longer reads. Empty means "no profile chosen yet", which is
        #: the legacy layout and is what a machine with one child has always
        #: had.
        self.profile_id = profile_id

    # -- starting --

    def launch(self, activity: Any, resume_path: Path | None = None) -> RunningActivity | None:
        """Start ``activity``, resuming ``resume_path`` if it supports that."""
        if self.current is not None and self.current.running:
            log.warning(
                "refusing to launch %s: %s is still running",
                activity.id,
                self.current.activity_id,
            )
            return None

        argv = (
            activity.resume_argv(resume_path)
            if resume_path is not None
            else list(activity.exec_argv)
        )
        extra = {ACTIVITY_ID_VAR: activity.id}
        if self.profile_id:
            extra[PROFILE_ID_VAR] = self.profile_id
        env = build_env(self.home, self.parent_env, extra)

        # An unnamed temporary file rather than a pipe: nobody is reading it
        # while the activity runs, and a full pipe buffer would block a child's
        # drawing program mid-stroke. It is unlinked at creation, so it cannot
        # outlive the shell even if we crash.
        stderr_file: IO[bytes] | None = None
        try:
            # The file deliberately outlives this block -- it is the
            # activity's stderr for as long as the activity runs, and it is
            # closed by _forget() or by check() after on_exit.
            stderr_file = tempfile.TemporaryFile(prefix=f"kidnix-{activity.id}-")  # noqa: SIM115
        except OSError as exc:  # pragma: no cover - a full /tmp
            log.warning("no temporary file for %s's stderr (%s)", activity.id, exc)

        try:
            process = self._spawn(
                argv,
                env=env,
                cwd=str(self.home),
                # Its own process group: one killpg cleans up everything the
                # activity spawned.
                start_new_session=True,
                stdin=subprocess.DEVNULL,
                stderr=stderr_file,
            )
        except (OSError, ValueError) as exc:
            log.error("could not launch %s (%s): %s", activity.id, argv, exc)
            if stderr_file is not None:
                stderr_file.close()
            return None

        # `getattr` rather than attribute access: the tests (and the demo's
        # older manifests) hand in doubles that are not full Activities, and a
        # missing quit contract is the conservative one -- "signal", 5 s.
        quit_mode = str(getattr(activity, "quit", QUIT_SIGNAL))
        quit_grace = float(getattr(activity, "quit_grace", AUTOSAVE_GRACE_SECONDS))
        self.current = RunningActivity(
            activity_id=activity.id,
            argv=argv,
            process=process,
            started_at=datetime.now(),
            resume_path=resume_path,
            quit_mode=quit_mode,
            quit_grace=quit_grace,
            env=env,
            stderr_file=stderr_file,
        )
        log.info(
            "launched %s as pid %s (quit=%s, grace %.0fs): %s",
            activity.id,
            self.current.pid,
            quit_mode,
            quit_grace,
            argv,
        )
        return self.current

    # -- stopping --

    def stop(self, grace: float | None = None) -> str:
        """Ask the activity to quit, then insist. Blocks for at most ``grace``.

        The **shell's own shutdown** path, and nothing else: it is the one
        moment when there is no child to ask and no screen left to ask on. Put
        away goes through :meth:`request_stop` and waits (spec 7c); it reaches
        :meth:`force_stop` only at the session's hard stop.

        ``grace`` therefore defaults to :data:`AUTOSAVE_GRACE_SECONDS` and
        deliberately **not** to the activity's own ``quit_grace``: a confirm
        activity's thirty seconds are for a five-year-old finding a tick, and
        there is no longer a shell on screen for them to find it under. A
        logout that hung for half a minute per activity would be a worse bug
        than the one being avoided.
        """
        running = self.current
        if running is None:
            return Outcome.NOT_RUNNING
        if running.poll() is not None:
            self._forget(running)
            return Outcome.EXITED
        if grace is None:
            grace = AUTOSAVE_GRACE_SECONDS

        self._signal(running, signal.SIGTERM)
        try:
            running.process.wait(timeout=grace)
            log.info("%s exited after SIGTERM", running.activity_id)
            self._forget(running)
            return Outcome.TERMINATED
        except subprocess.TimeoutExpired:
            pass

        log.warning("%s ignored SIGTERM after %.0fs; killing", running.activity_id, grace)
        self._signal(running, signal.SIGKILL)
        try:
            running.process.wait(timeout=2)
        except subprocess.TimeoutExpired:  # pragma: no cover - unkillable process
            log.error("%s survived SIGKILL", running.activity_id)
        self._forget(running)
        return Outcome.KILLED

    def _forget(self, running: RunningActivity) -> None:
        running.close_stderr()
        self.current = None

    def request_stop(self) -> bool:
        """Send SIGTERM and return immediately. Returns False if nothing ran.

        This is *asking*, and since v0.1.6 asking is all Put away does until
        the hard stop: an activity in ``confirm`` mode is now showing the child
        its own question, and killing it would answer that question for them,
        wrongly (spec 7c). Safe to call twice -- the second call is the re-ask
        at the end of the grace, and :attr:`RunningActivity.asked` counts them.
        """
        running = self.current
        if running is None or running.poll() is not None:
            return False
        running.asked += 1
        log.info(
            "asking %s to quit (SIGTERM, quit=%s, ask %d)",
            running.activity_id,
            running.quit_mode,
            running.asked,
        )
        self._signal(running, signal.SIGTERM)
        return True

    @property
    def asks_before_quitting(self) -> bool:
        """Is the activity on screen one that answers SIGTERM with a question?"""
        return self.current is not None and self.current.asks_before_quitting

    @property
    def grace_seconds(self) -> float:
        """How long to wait for the current activity before asking again."""
        return AUTOSAVE_GRACE_SECONDS if self.current is None else self.current.quit_grace

    def hard_stop(self) -> str:
        """The session's hard stop: SIGKILL, and say out loud what it may cost.

        The only route to a SIGKILL during the ending ritual (spec 7c). It is
        separate from :meth:`force_stop` because the *log line* is the point:
        an activity that was still asking the child a question when the clock
        ran out has probably lost whatever was on its canvas, and the one place
        that can be said honestly is the parent's journal. The shell's words to
        the child change too -- it does not claim to have kept anything it
        did not keep (:func:`kidnix_shell.ritual.put_away_line`).
        """
        running = self.current
        if running is None or running.poll() is not None:
            return self.force_stop()
        log.warning("put-away: killed %s with unsaved work possible", running.activity_id)
        return self.force_stop()

    def force_stop(self) -> str:
        """SIGKILL whatever is still there. Safe to call when nothing is."""
        running = self.current
        if running is None:
            return Outcome.NOT_RUNNING
        if running.poll() is not None:
            self._forget(running)
            return Outcome.TERMINATED
        log.warning("%s ignored SIGTERM; killing", running.activity_id)
        self._signal(running, signal.SIGKILL)
        try:
            running.process.wait(timeout=2)
        except subprocess.TimeoutExpired:  # pragma: no cover
            log.error("%s survived SIGKILL", running.activity_id)
        self._forget(running)
        return Outcome.KILLED

    @staticmethod
    def _signal(running: RunningActivity, number: int) -> None:
        """Signal the whole process group, falling back to the process."""
        try:
            os.killpg(os.getpgid(running.pid), number)
            return
        except (OSError, AttributeError):
            pass
        try:
            running.process.send_signal(number)
        except OSError as exc:  # already reaped
            log.debug("signalling %s failed: %s", running.activity_id, exc)

    # -- polling --

    @property
    def running(self) -> bool:
        return self.current is not None and self.current.running

    def check(self) -> int | None:
        """Poll once; fire ``on_exit`` the first time the activity is gone.

        The GTK app calls this on a 500 ms tick rather than using SIGCHLD,
        which keeps everything on the main loop and out of signal handlers.
        """
        running = self.current
        if running is None:
            return None
        code = running.poll()
        if code is None:
            return None
        self.current = None
        log.info("%s exited with code %s", running.activity_id, code)
        try:
            # ``on_exit`` may want the stderr tail, so the file outlives the
            # callback and not the other way round.
            if self.on_exit is not None:
                self.on_exit(running, code)
        finally:
            running.close_stderr()
        return code
