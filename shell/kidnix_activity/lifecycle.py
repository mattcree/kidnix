"""How a first-party activity ends. There is no dialogue.

Spec 7c gives a manifest two ways to answer "please finish":

``signal``
    SIGTERM ends the program. It saves on the way out, or it had nothing to
    save. The shell asks and expects an answer in seconds.
``confirm``
    SIGTERM makes the program put a *question* on the child's screen. Tux Paint
    is why this exists (impl. notes section 19.2): SDL turns SIGTERM into
    ``SDL_QUIT`` and Tux Paint answers it with its own tick and cross.

**Every first-party activity is ``signal``, and this module is why.** The
``confirm`` path costs a five-year-old a decision at the exact moment the
session is ending, in a dialogue nobody designed for a pre-reader, with a
30-second grace behind it and a SIGKILL at the end of that. We own our own
activities, so we can simply save instead of asking -- and then the shell's
"Let's keep that" is true without anybody having to press anything.

The whole of it:

1. the SDK installs a handler for SIGTERM (and SIGINT, for the developer's
   Ctrl-C, which should behave identically);
2. the handler calls ``on_finish()`` **once**;
3. the process exits 0.

Three properties are worth stating because each of them was a bug somewhere
before it was a rule here:

* **Once.** Put away sends a second SIGTERM at the end of the grace
  (:meth:`kidnix_shell.launcher.Launcher.request_stop` counts the asks). A
  handler that ran the save again would race its own half-written file.
* **Exit 0 means it saved.** If ``on_finish()`` raises, we exit
  :data:`FAILED_EXIT_CODE` and log the traceback, because the parent's journal
  is the only place that can honestly say a drawing was lost. The shell
  currently treats any exit as "it has gone" -- the honest code costs nothing
  today and is there for when it does.
* **No GTK in here.** The handler is a plain callable, the installer and the
  exiter are injected, and every branch above is a unit test. What the GTK app
  adds (:mod:`kidnix_activity.app`) is ``GLib.unix_signal_add``, which is the
  only safe way to reach a main loop from a Unix signal.
"""

from __future__ import annotations

import logging
import signal
import sys
from collections.abc import Callable, Sequence

log = logging.getLogger(__name__)

#: What a first-party manifest must say. Asserted by
#: :mod:`kidnix_activity.manifest`.
QUIT_MODE = "signal"

#: The signals that mean "finish". SIGINT is here so that Ctrl-C in a terminal
#: does exactly what put-away does -- a developer who has never seen the save
#: path run has not tested it.
FINISH_SIGNALS: tuple[int, ...] = (signal.SIGTERM, signal.SIGINT)

SUCCESS_EXIT_CODE = 0
#: ``on_finish()`` raised. The child's work may not be on disk, and the one
#: place that can be said is the parent's journal.
FAILED_EXIT_CODE = 1

#: ``(signum, handler) -> None``. Injected so tests never touch real signals.
Installer = Callable[[int, Callable[[int, object], None]], None]
Exiter = Callable[[int], None]


class FinishHandler:
    """Turns "please finish" into one save and one exit.

    ``on_finish`` is the activity's save. It is called with no arguments, it
    may take as long as the manifest's ``quit_grace`` allows (5 seconds by
    default, which is spec 7a's autosave grace), and it must be safe to call
    when there is nothing to save.
    """

    def __init__(
        self,
        on_finish: Callable[[], None] | None = None,
        *,
        exiter: Exiter | None = None,
        signals: Sequence[int] = FINISH_SIGNALS,
    ) -> None:
        self.on_finish = on_finish
        self.signals = tuple(signals)
        self._exit: Exiter = exiter if exiter is not None else sys.exit
        #: Has the save already run? The second SIGTERM's answer.
        self.finished = False
        #: What :meth:`finish` decided, for the tests and for the log.
        self.exit_code: int | None = None
        #: Which signal got here first, or ``None`` if we were called directly.
        self.signal_number: int | None = None

    # -- installation --

    def install(self, installer: Installer | None = None) -> tuple[int, ...]:
        """Arm the handler. Returns the signals that were actually armed.

        ``installer`` defaults to :func:`signal.signal`; the GTK application
        passes ``GLib.unix_signal_add``'s wrapper instead, because a Python
        signal handler runs between bytecodes and a GTK save that touches
        widgets from there is undefined behaviour.
        """
        install = installer if installer is not None else _install_with_signal_module
        armed: list[int] = []
        for number in self.signals:
            try:
                install(number, self._on_signal)
            except (OSError, ValueError, RuntimeError) as exc:  # pragma: no cover
                # A non-main thread, or a signal this platform does not have.
                log.warning("could not install a handler for signal %s: %s", number, exc)
                continue
            armed.append(number)
        log.debug("finish handler armed for %s", armed)
        return tuple(armed)

    def _on_signal(self, signum: int, _frame: object = None) -> None:
        self.signal_number = int(signum)
        log.info("asked to finish (signal %s)", signum)
        self.finish(exit_process=True)

    # -- the save --

    def finish(self, *, exit_process: bool = True) -> int:
        """Save once, then exit. Returns the exit code either way.

        Idempotent: a second SIGTERM (put away re-asks at the end of the grace)
        finds ``finished`` already set and does nothing but exit again with the
        same code. That is deliberate -- re-running a save would race the file
        the first one is still writing.
        """
        if self.finished:
            code = self.exit_code if self.exit_code is not None else SUCCESS_EXIT_CODE
            log.debug("already finished; exiting %s again", code)
        else:
            self.finished = True
            code = self._run_save()
            self.exit_code = code
        if exit_process:
            self._exit(code)
        return code

    def _run_save(self) -> int:
        if self.on_finish is None:
            return SUCCESS_EXIT_CODE
        try:
            self.on_finish()
        except Exception:
            # Everything: a save that raised ImportError, MemoryError or a
            # bare `raise` still has to end the process, because the shell is
            # waiting and a child is watching a screen that will not go away.
            log.exception("saving on the way out failed; the child's work may not be kept")
            return FAILED_EXIT_CODE
        log.info("saved on the way out")
        return SUCCESS_EXIT_CODE

    def set_on_finish(self, on_finish: Callable[[], None] | None) -> None:
        """Point the handler at the activity's save, after construction."""
        self.on_finish = on_finish


def _install_with_signal_module(number: int, handler: Callable[[int, object], None]) -> None:
    signal.signal(number, handler)


def glib_installer() -> Installer:
    """An :data:`Installer` that goes through GLib's main loop.

    ``GLib.unix_signal_add`` dispatches the callback from the main loop rather
    than from the signal handler itself, so the save may touch widgets, the
    filesystem and anything else it likes. Used by
    :class:`kidnix_activity.app.ActivityApplication`; importable from here so
    the choice is documented in the module that owns the decision.
    """
    from gi.repository import GLib

    def install(number: int, handler: Callable[[int, object], None]) -> None:
        def once() -> bool:
            handler(number, None)
            return False  # GLib.SOURCE_REMOVE

        GLib.unix_signal_add(GLib.PRIORITY_HIGH, number, once)

    return install
