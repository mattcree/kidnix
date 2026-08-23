"""Running a helper without freezing the window.

Every privileged thing the panel does is a subprocess behind ``pkexec``, and
``pkexec`` blocks until a human has typed a password into an agent that is a
*different process*. Calling that from a GTK signal handler freezes the window
for as long as the parent takes to find their password -- and ``bootc upgrade``
takes minutes, during which a frozen window is indistinguishable from a crash.
A parent who force-quits a panel mid-``bootc`` is the one failure mode this
module exists to prevent.

So: the work happens on a thread, the answer comes back on the main loop
through ``GLib.idle_add``, and the control that started it is insensitive in
between. That is the whole module.

``synchronous=True`` runs it inline instead, and is used by the tests and by
``--screenshot``, where there is no main loop to come back to and a thread
would simply never be joined.
"""

from __future__ import annotations

import logging
import threading
from collections.abc import Callable
from typing import Any

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import GLib  # noqa: E402

log = logging.getLogger(__name__)


def run_async(
    work: Callable[[], Any],
    done: Callable[[Any], None],
    *,
    synchronous: bool = False,
) -> None:
    """Run ``work`` off the main loop, then call ``done`` on it.

    ``done`` always runs on the GTK main loop, so it may touch widgets. If
    ``work`` raises, ``done`` is called with the exception rather than the
    thread dying quietly -- a helper that blew up must produce a sentence in
    the window, not a silent button that stays greyed out forever.
    """
    if synchronous:
        done(_guarded(work))
        return

    def body() -> None:
        result = _guarded(work)
        GLib.idle_add(_once, done, result)

    threading.Thread(target=body, daemon=True, name="kidnix-panel-helper").start()


def _guarded(work: Callable[[], Any]) -> Any:
    try:
        return work()
    except Exception as exc:
        log.warning("a panel helper raised: %s", exc)
        return exc


def _once(done: Callable[[Any], None], result: Any) -> bool:
    done(result)
    return GLib.SOURCE_REMOVE


class Busy:
    """Make a control insensitive for the length of one job, and put it back.

    A context manager would be wrong here -- the job outlives the function that
    started it -- so this is two calls, and ``finish`` is safe to call twice.
    """

    def __init__(self, *widgets: Any) -> None:
        self._widgets = widgets
        self._done = False
        for widget in widgets:
            widget.set_sensitive(False)

    def finish(self) -> None:
        if self._done:
            return
        self._done = True
        for widget in self._widgets:
            widget.set_sensitive(True)


__all__ = ["Busy", "run_async"]
