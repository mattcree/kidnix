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
* **A termination path that always terminates.** Put away (S6) asks nicely
  with SIGTERM, waits the autosave grace of 5 s, then SIGKILL. The activity is
  started in its own process group so a misbehaving app that forks children
  cannot leave orphans on top of the shell.
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

log = logging.getLogger(__name__)

#: Spec S6: SIGTERM, autosave grace, then SIGKILL.
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
) -> dict[str, str]:
    """The environment an activity is given. Deliberately small."""
    source = os.environ if parent_env is None else parent_env
    env: dict[str, str] = {}
    for key, value in source.items():
        if key in ENV_ALLOWLIST or key.startswith(ENV_ALLOWLIST_PREFIXES):
            env[key] = value

    env.setdefault("PATH", DEFAULT_PATH)
    env.setdefault("LANG", "en_GB.UTF-8")
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
    ) -> None:
        self.home = home
        self.parent_env = parent_env
        self._spawn = spawn or subprocess.Popen
        self.current: RunningActivity | None = None
        self.on_exit: Callable[[RunningActivity, int], None] | None = None

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
        env = build_env(self.home, self.parent_env, {"KIDNIX_ACTIVITY_ID": activity.id})

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

        self.current = RunningActivity(
            activity_id=activity.id,
            argv=argv,
            process=process,
            started_at=datetime.now(),
            resume_path=resume_path,
            env=env,
            stderr_file=stderr_file,
        )
        log.info("launched %s as pid %s: %s", activity.id, self.current.pid, argv)
        return self.current

    # -- stopping --

    def stop(self, grace: float = AUTOSAVE_GRACE_SECONDS) -> str:
        """Ask the activity to quit, then insist. Blocks for at most ``grace``.

        Called from Put away (S6). It is deliberately synchronous: the child is
        watching an animation and the shell has nothing better to do for five
        seconds.
        """
        running = self.current
        if running is None:
            return Outcome.NOT_RUNNING
        if running.poll() is not None:
            self._forget(running)
            return Outcome.EXITED

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

        Put away (S6) uses this rather than :meth:`stop` so the keep animation
        keeps running while the activity autosaves; the caller schedules
        :meth:`force_stop` after the grace period.
        """
        running = self.current
        if running is None or running.poll() is not None:
            return False
        log.info("asking %s to quit (SIGTERM)", running.activity_id)
        self._signal(running, signal.SIGTERM)
        return True

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
