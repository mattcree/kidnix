"""The shell's half of the caption wire (``docs/design/activity-sdk.md`` §4).

An activity is another process. Its window covers everything below the band,
and the caption strip -- the thing that makes "nothing essential is audio-only"
true (accessibility review B2) -- lives in the **shell's** band window. So an
activity that spoke on its own would be captionless for the whole of the time a
child spends inside it, which is most of the session.

:mod:`kidnix_activity.captions` is the other half and has been shipping since
the SDK landed: one JSON object per UNIX datagram to
``$XDG_RUNTIME_DIR/kidnix/captions.sock``::

    {"speak": "Press the big button.", "source": "hello-draw"}

This module is what receives it. Three decisions are worth stating, because
each one is a place the obvious implementation is wrong:

**1. The shell says the line; the activity does not.** The SDK's design note
originally said "display it, never speak it", on the reasoning that the
activity had already spoken it and two voices a beat apart is worse than
either. The trouble is that "two voices" is exactly what that produces the
moment anything else is talking: the shell's own read-aloud cancels its
utterance and the activity's does not, they run on two speech-dispatcher
connections with two settings, and neither knows about the other. So the wire
now carries the *whole* utterance rather than a shadow of it:
:class:`~kidnix_shell.speech.SpeechManager` speaks it and captions it, exactly
as it does for a line the shell wrote itself, which is one voice, one queue and
one caption path (08 §3.6). The SDK's side of that is
:attr:`SpeechManager.on_caption` returning **True** for "I have handed this
over" -- ``kidnix_activity.speech.ActivitySpeech`` returns the datagram's
delivery result, so it speaks locally if and only if the socket was not there.
No socket, no shell, a full queue: the child still hears the sentence.

**2. Only during an activity.** A datagram that arrives while the child is on
Home is from a process that should not be talking -- an activity that outlived
its window, or something that found the socket. It is dropped with a debug
line. The gate is deliberately the state and not "is something running", so
there is one answer and the state machine owns it.

**3. Everything on this socket is untrusted.** The text is displayed and
spoken, never executed, and never logged as the child's own words.
``captions.decode`` collapses it to one line and caps it at
``MAX_TEXT_CHARS``, which is also what stops a newline in a datagram forging a
second line in the journal. The ``source`` id is sanitised again here before it
reaches a log line, because it is a string from the same untrusted object.

Rate-limiting is per source and small (:data:`RATE_LIMIT_PER_SECOND`): four
lines a second is already faster than anything can be said, so a sender above
it is either broken or hostile, and either way the band owes it nothing. It
costs one WARNING and then silence, rather than a warning per datagram -- a
loop that logged per message would be the denial of service it was written to
prevent.

The parsing, the gate and the limiter are :class:`CaptionRouter`, which is pure
and has no GTK in it. :class:`CaptionListener` is the socket around it.
"""

from __future__ import annotations

import logging
import os
import time
from collections import deque
from collections.abc import Callable
from pathlib import Path
from typing import Any, Protocol

from kidnix_activity.captions import SOCKET_DIRNAME, SOCKET_NAME, decode

log = logging.getLogger(__name__)

#: How many captions one source may send per :data:`RATE_WINDOW_SECONDS`.
#: A spoken sentence takes about two seconds; four a second is a bug.
RATE_LIMIT_PER_SECOND = 4
RATE_WINDOW_SECONDS = 1.0

#: How many distinct ``source`` ids the limiter will track. The id comes off
#: the wire, so a sender that made a new one up every time would otherwise grow
#: the table forever; past this the table is emptied and everyone starts again,
#: which costs a misbehaving sender nothing it did not already have.
MAX_TRACKED_SOURCES = 32

#: The biggest datagram we will read. ``MAX_TEXT_CHARS`` is 500 characters, so
#: 4 KiB is room for the JSON around a full one in the worst UTF-8 case.
DATAGRAM_MAX_BYTES = 4096

#: What is logged when a source has no id, or an id that is not printable.
UNKNOWN_SOURCE = "unknown"

#: The directory the socket lives in, made 0700, and the socket itself 0600.
#: The child's session is one Unix user, so this is a marker of intent rather
#: than a wall -- but a socket that anything on the machine could write to is
#: a way to put words under the band, and that is worth not offering.
DIR_MODE = 0o700
SOCKET_MODE = 0o600


class Speaker(Protocol):
    """The one thing the router needs: the shell's captioned speech path."""

    def speak(self, text: str, key: str | None = None) -> bool: ...


def safe_source(source: str) -> str:
    """A ``source`` id fit to put in a log line.

    It arrives from another process inside a JSON object, so it is text the
    shell did not write. Everything that is not a slug character goes, and what
    is left is truncated -- a log line is a place a name can be forged, and an
    id is not worth one.
    """
    cleaned = "".join(char for char in source if char.isalnum() or char in "-_.")[:32]
    return cleaned or UNKNOWN_SOURCE


class CaptionRouter:
    """Datagram in, one spoken-and-captioned line out. No GTK, no socket.

    ``is_active`` is asked afresh for every datagram rather than being wired to
    a signal: the state machine is the authority on whether a child is inside
    an activity, and a cached copy of an authority is a second one.
    """

    def __init__(
        self,
        speech: Speaker,
        *,
        is_active: Callable[[], bool] | None = None,
        clock: Callable[[], float] = time.monotonic,
        limit: int = RATE_LIMIT_PER_SECOND,
        window: float = RATE_WINDOW_SECONDS,
    ) -> None:
        self.speech = speech
        self.is_active = is_active if is_active is not None else (lambda: True)
        self._clock = clock
        self.limit = limit
        self.window = window
        #: Recent arrivals per source, newest last.
        self._recent: dict[str, deque[float]] = {}
        #: Sources currently over the limit, so the WARNING is said once.
        self._warned: set[str] = set()
        # Counters, for the tests and for anyone reading the state at runtime.
        self.shown = 0
        self.malformed = 0
        self.ignored = 0
        self.limited = 0

    def handle(self, payload: bytes) -> bool:
        """One datagram. Returns whether it reached the voice."""
        parsed = decode(payload)
        if parsed is None:
            self.malformed += 1
            # Debug, not warning: a truncated or foreign datagram is a
            # misconfiguration on somebody's desktop, not an event a parent's
            # machine should be noisy about.
            log.debug("a datagram on the caption socket was not a caption (%d bytes)", len(payload))
            return False
        text, source = parsed
        who = safe_source(source)
        if not self.is_active():
            self.ignored += 1
            log.debug("caption from %s ignored: no activity is on screen", who)
            return False
        if not self._allow(who):
            return False
        self.shown += 1
        # The same call the shell makes for its own lines: `on_caption` puts it
        # in the strip before the "is speech even on?" check, so a muted or
        # voiceless machine still shows it (review B2). No `key`: the highlight
        # ring belongs to a widget in *this* process and there is not one.
        self.speech.speak(text)
        return True

    def _allow(self, who: str) -> bool:
        now = self._clock()
        if len(self._recent) > MAX_TRACKED_SOURCES:
            # See MAX_TRACKED_SOURCES: forget everyone rather than grow.
            self._recent.clear()
            self._warned.clear()
        recent = self._recent.setdefault(who, deque())
        cutoff = now - self.window
        while recent and recent[0] <= cutoff:
            recent.popleft()
        if len(recent) >= self.limit:
            self.limited += 1
            if who not in self._warned:
                self._warned.add(who)
                log.warning(
                    "%s is sending captions faster than %d a second; dropping the rest",
                    who,
                    self.limit,
                )
            return False
        recent.append(now)
        # Back under the limit: the next burst is a new event and says so once.
        self._warned.discard(who)
        return True


class CaptionListener:
    """The socket: bind it, read it on the main loop, and let go on the way out.

    A ``Gio.Socket`` with a source on the default main context, so a datagram
    is delivered between frames like every other event the shell handles.
    Nothing here ever blocks: the socket is non-blocking and one datagram is
    taken per callback, so a sender in a loop costs the main loop one read per
    iteration rather than a stall.

    **No ack.** The SDK sends from an unbound socket, which has no address to
    reply to (measured: ``receive_bytes_from`` hands back ``None``), so an ack
    could never arrive. The delivery signal the sender actually has is the one
    that matters -- ``sendto`` failing when nothing is bound -- and that is what
    decides whether it speaks the line itself.
    """

    def __init__(
        self,
        speech: Speaker,
        *,
        path: Path | None = None,
        is_active: Callable[[], bool] | None = None,
        router: CaptionRouter | None = None,
    ) -> None:
        self.path = path
        self.router = router if router is not None else CaptionRouter(speech, is_active=is_active)
        self._socket: Any = None
        self._source: Any = None
        self._bound: Path | None = None

    @property
    def listening(self) -> bool:
        return self._socket is not None

    @staticmethod
    def default_path() -> Path | None:
        """``$XDG_RUNTIME_DIR/kidnix/captions.sock``, or ``None`` without one."""
        runtime = os.environ.get("XDG_RUNTIME_DIR", "").strip()
        if not runtime:
            return None
        return Path(runtime) / SOCKET_DIRNAME / SOCKET_NAME

    def start(self) -> bool:
        """Bind and listen. Never raises: a shell with no captions still runs."""
        from gi.repository import Gio, GLib

        path = self.path if self.path is not None else self.default_path()
        if path is None:
            log.info("no XDG_RUNTIME_DIR: activities cannot send their captions to the band")
            return False
        self.path = path
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            os.chmod(path.parent, DIR_MODE)
            self._remove_stale(path)
            sock = Gio.Socket.new(
                Gio.SocketFamily.UNIX, Gio.SocketType.DATAGRAM, Gio.SocketProtocol.DEFAULT
            )
            sock.set_blocking(False)
            sock.bind(Gio.UnixSocketAddress.new(str(path)), True)
            os.chmod(path, SOCKET_MODE)
        except (OSError, GLib.Error) as exc:
            # The strip stays empty for activities and everything else works.
            log.warning("could not listen for captions at %s (%s)", path, exc)
            return False
        self._socket = sock
        self._bound = path
        source = sock.create_source(GLib.IOCondition.IN, None)
        source.set_callback(self._on_readable)
        source.attach(None)
        self._source = source
        log.info("listening for activity captions at %s", path)
        return True

    @staticmethod
    def _remove_stale(path: Path) -> None:
        """Unlink a socket left by a shell that did not get to say goodbye.

        Only a socket. Anything else at that path is somebody else's file and
        the bind is allowed to fail loudly rather than take it.
        """
        try:
            if path.is_socket():
                path.unlink()
                log.debug("removed a stale caption socket at %s", path)
        except OSError as exc:  # pragma: no cover - a runtime dir we cannot write
            log.debug("could not remove %s (%s)", path, exc)

    def _on_readable(self, *_args: object) -> bool:
        from gi.repository import GLib

        sock = self._socket
        if sock is None:  # pragma: no cover - stop() destroys the source first
            return False  # GLib.SOURCE_REMOVE
        try:
            data, _address = sock.receive_bytes_from(DATAGRAM_MAX_BYTES, 0, None)
        except GLib.Error as exc:  # would-block, or a socket going away
            log.debug("caption socket read failed (%s)", exc)
            return True
        payload = data.get_data() if data is not None else None
        if payload:
            self.router.handle(bytes(payload))
        return True  # GLib.SOURCE_CONTINUE

    def stop(self) -> None:
        """Detach, close, and take the socket file with us. Safe to call twice."""
        source, self._source = self._source, None
        sock, self._socket = self._socket, None
        bound, self._bound = self._bound, None
        if source is not None:
            source.destroy()
        if sock is not None:
            try:
                sock.close()
            except Exception as exc:  # pragma: no cover - already closed
                log.debug("closing the caption socket: %s", exc)
        if bound is not None:
            try:
                bound.unlink(missing_ok=True)
            except OSError as exc:  # pragma: no cover
                log.debug("could not remove %s (%s)", bound, exc)
