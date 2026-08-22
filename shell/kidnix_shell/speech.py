"""Read-aloud (spec section 3).

Every focusable thing in the shell carries a ``speak_text``. It is spoken on
keyboard focus, on pointer hover after a 300 ms dwell (once per enter), and on
activation. The Ear button repeats the last utterance. A new utterance always
cancels the previous one -- a pre-reader exploring a screen must never build up
a backlog they have to wait out.

Backends, in order of preference:

1. ``speechd`` -- the python3-speechd SSIP client, what the image ships.
2. ``spd-say`` -- the same daemon over a subprocess, for hosts where the Python
   bindings are missing but the CLI is there.
3. :class:`NullBackend` -- logs once and stays quiet (spec: "degrade silently").

The dwell timer is injected (:class:`Scheduler`) so tests drive it with a fake
clock and never import GTK.
"""

from __future__ import annotations

import contextlib
import logging
import shutil
import subprocess
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, Protocol

log = logging.getLogger(__name__)

#: 08 section 3.6 wants ~600 ms; the spec pins it at 300 ms so exploration is
#: quick enough that a child sweeping the pointer hears the grid.
HOVER_DWELL_MS = 300

#: How long to wait before trying speech-dispatcher again after a failure.
#: Long enough that a dead daemon costs nothing, short enough that a restart of
#: speech-dispatcher is invisible to the child.
RECONNECT_SECONDS = 5.0

#: en-GB, "slightly slower than default". speechd rate is -100..100.
SPEECH_RATE = -20
SPEECH_LANGUAGE = "en-GB"

#: Rough speaking speed, used only to decide how long the highlight ring stays
#: on. No backend tells us reliably when it stopped.
MS_PER_CHARACTER = 70
MIN_HIGHLIGHT_MS = 500
MAX_HIGHLIGHT_MS = 6000


class SpeechBackend(Protocol):
    """What the manager needs from a voice."""

    name: str

    def speak(self, text: str) -> None: ...

    def cancel(self) -> None: ...

    def close(self) -> None: ...


class NullBackend:
    """No voice available. Logs once, then silence (spec section 3)."""

    name = "null"

    def __init__(self) -> None:
        self._warned = False

    def speak(self, text: str) -> None:
        if not self._warned:
            log.warning("speech-dispatcher unavailable; read-aloud is off")
            self._warned = True
        log.debug("would speak: %s", text)

    def cancel(self) -> None:
        pass

    def close(self) -> None:
        pass


class SpdSayBackend:
    """Fallback via the ``spd-say`` CLI, one process per utterance."""

    name = "spd-say"

    def __init__(self, executable: str = "spd-say") -> None:
        self.executable = executable
        self._proc: subprocess.Popen[bytes] | None = None

    def speak(self, text: str) -> None:
        self.cancel()
        try:
            self._proc = subprocess.Popen(
                [
                    self.executable,
                    "-l",
                    SPEECH_LANGUAGE,
                    "-r",
                    str(SPEECH_RATE),
                    "--",
                    text,
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except OSError as exc:
            log.warning("spd-say failed: %s", exc)

    def cancel(self) -> None:
        with contextlib.suppress(OSError, subprocess.SubprocessError):
            subprocess.run(
                [self.executable, "-C"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
                timeout=2,
            )

    def close(self) -> None:
        self.cancel()


def open_ssip_client() -> Any:
    """Connect to speech-dispatcher. Raises if the daemon is not there."""
    import speechd  # imported lazily: absent on some dev hosts

    client = speechd.SSIPClient("kidnix-shell")
    client.set_language(SPEECH_LANGUAGE)
    client.set_rate(SPEECH_RATE)
    client.set_punctuation(speechd.PunctuationMode.NONE)
    return client


class SpeechdBackend:
    """The real thing: an SSIP client to speech-dispatcher.

    **Connects lazily and reconnects.** The spike
    (``docs/spikes/session-integration.md`` §5.1) found that connecting at
    startup is what makes ``python3-speechd`` autospawn a daemon inside the
    shell's own cgroup; the unit now wants ``speech-dispatcher.socket``, but
    the shell must not depend on the daemon being up at the moment it starts
    either. So the socket is opened on the first utterance, and if
    speech-dispatcher restarts (or was never there) we retry at most once every
    :data:`RECONNECT_SECONDS` and log the state change **once**, not per event
    -- a child hovering a grid of tiles must not fill the journal.
    """

    name = "speechd"

    def __init__(
        self,
        client: Any = None,
        connect: Callable[[], Any] | None = None,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._client = client
        self._connect = connect or open_ssip_client
        self._clock = clock
        self._next_attempt = 0.0
        self._down = False
        self._ever_connected = client is not None
        self.connects = 0
        self.failures = 0

    @classmethod
    def create(cls) -> SpeechdBackend:
        """Check that the bindings exist; do *not* open a socket yet."""
        import speechd  # noqa: F401  -- presence check only

        return cls()

    @property
    def connected(self) -> bool:
        return self._client is not None

    def _ensure(self) -> Any:
        if self._client is not None:
            return self._client
        now = self._clock()
        if (self._ever_connected or self._down) and now < self._next_attempt:
            return None
        self._next_attempt = now + RECONNECT_SECONDS
        try:
            self._client = self._connect()
        except Exception as exc:
            self.failures += 1
            if not self._down:
                log.warning("speech-dispatcher is not answering (%s); retrying quietly", exc)
                self._down = True
            return None
        self.connects += 1
        if self._down:
            log.info("speech-dispatcher is back")
        self._down = False
        self._ever_connected = True
        return self._client

    def _drop(self, exc: Exception) -> None:
        """The daemon went away mid-session. Say so once, then reconnect later."""
        if not self._down:
            log.warning("speech-dispatcher went away (%s); will reconnect", exc)
            self._down = True
        client, self._client = self._client, None
        self._next_attempt = self._clock() + RECONNECT_SECONDS
        if client is not None:
            with contextlib.suppress(Exception):
                client.close()

    def speak(self, text: str) -> None:
        client = self._ensure()
        if client is None:
            return
        try:
            client.cancel()
            client.speak(text)
        except Exception as exc:  # the daemon can go away mid-session
            self._drop(exc)

    def cancel(self) -> None:
        # Never *opens* a connection: cancelling nothing is free, and this is
        # called on every utterance.
        client = self._client
        if client is None:
            return
        try:
            client.cancel()
        except Exception as exc:
            self._drop(exc)

    def close(self) -> None:
        client, self._client = self._client, None
        if client is not None:
            with contextlib.suppress(Exception):
                client.close()


class FakeBackend:
    """Test double. Records what was said and when it was cancelled."""

    name = "fake"

    def __init__(self) -> None:
        self.spoken: list[str] = []
        self.cancels = 0
        self.closed = False

    def speak(self, text: str) -> None:
        self.spoken.append(text)

    def cancel(self) -> None:
        self.cancels += 1

    def close(self) -> None:
        self.closed = True


def select_backend(prefer: str | None = None) -> SpeechBackend:
    """Pick the best available voice. Never raises, never opens a socket.

    Selection is a *module import* check only: the socket is opened on the
    first utterance so that nothing here can block the shell's startup on a
    daemon that has not come up yet.
    """
    if prefer == "null":
        return NullBackend()
    if prefer in (None, "speechd"):
        try:
            return SpeechdBackend.create()
        except Exception as exc:
            log.info("speechd python bindings unavailable (%s); trying spd-say", exc)
    if prefer in (None, "spd-say") and shutil.which("spd-say"):
        return SpdSayBackend()
    return NullBackend()


# --- timers --------------------------------------------------------------


class Scheduler(Protocol):
    """Just enough of GLib's main loop to be faked in a test."""

    def schedule(self, delay_ms: int, callback: Callable[[], None]) -> int: ...

    def cancel(self, handle: int) -> None: ...


class GLibScheduler:
    """Real timers on the GTK main loop."""

    def schedule(self, delay_ms: int, callback: Callable[[], None]) -> int:
        from gi.repository import GLib

        def once() -> bool:
            callback()
            return False  # GLib.SOURCE_REMOVE

        return int(GLib.timeout_add(delay_ms, once))

    def cancel(self, handle: int) -> None:
        from gi.repository import GLib

        GLib.source_remove(handle)


@dataclass
class FakeScheduler:
    """Deterministic scheduler for tests: nothing fires until you advance it."""

    pending: dict[int, tuple[int, Callable[[], None]]] = field(default_factory=dict)
    now_ms: int = 0
    _next: int = 1

    def schedule(self, delay_ms: int, callback: Callable[[], None]) -> int:
        handle = self._next
        self._next += 1
        self.pending[handle] = (self.now_ms + delay_ms, callback)
        return handle

    def cancel(self, handle: int) -> None:
        self.pending.pop(handle, None)

    def advance(self, ms: int) -> None:
        self.now_ms += ms
        due = sorted((at, handle) for handle, (at, _) in self.pending.items() if at <= self.now_ms)
        for _, handle in due:
            entry = self.pending.pop(handle, None)
            if entry is not None:
                entry[1]()


# --- the manager ---------------------------------------------------------


class SpeechManager:
    """One voice for the whole shell (08 section 3.6: "One voice").

    ``on_highlight(key, speaking)`` is the paired visual: the widget that is
    being spoken wears the reserved highlight ring while the voice is on it.
    """

    def __init__(
        self,
        backend: SpeechBackend | None = None,
        scheduler: Scheduler | None = None,
        dwell_ms: int = HOVER_DWELL_MS,
        enabled: bool = True,
    ) -> None:
        self.backend: SpeechBackend = backend or NullBackend()
        self.scheduler: Scheduler = scheduler or GLibScheduler()
        self.dwell_ms = dwell_ms
        self.enabled = enabled
        self.last_utterance: str = ""
        self.speaking_key: str | None = None
        self.on_highlight: Callable[[str, bool], None] | None = None
        self._dwell_handle: int | None = None
        self._dwell_key: str | None = None
        self._highlight_handle: int | None = None
        #: hover keys already spoken since the pointer entered them
        self._spoken_since_enter: set[str] = set()

    # -- speaking --

    def speak(self, text: str, key: str | None = None) -> bool:
        """Say something now, cancelling whatever was being said."""
        text = (text or "").strip()
        if not text:
            return False
        self._stop_highlight()
        if not self.enabled:
            self.last_utterance = text
            return False
        self.backend.speak(text)
        self.last_utterance = text
        self._start_highlight(key, text)
        return True

    def repeat(self) -> bool:
        """The Ear. Says the last thing again; silent if there is nothing yet."""
        if not self.last_utterance:
            return False
        return self.speak(self.last_utterance, self.speaking_key)

    def cancel(self) -> None:
        self.backend.cancel()
        self._stop_highlight()

    def speak_focus(self, text: str, key: str | None = None) -> bool:
        """Keyboard (or programmatic) focus landed on a widget."""
        return self.speak(text, key)

    def speak_activation(self, text: str, key: str | None = None) -> bool:
        return self.speak(text, key)

    # -- hover dwell --

    def hover_enter(self, key: str, text: str) -> None:
        """Pointer entered a widget: speak it after the dwell, once."""
        self._cancel_dwell()
        if key in self._spoken_since_enter:
            return
        self._dwell_key = key

        def fire() -> None:
            self._dwell_handle = None
            self._dwell_key = None
            self._spoken_since_enter.add(key)
            self.speak(text, key)

        self._dwell_handle = self.scheduler.schedule(self.dwell_ms, fire)

    def hover_leave(self, key: str) -> None:
        """Pointer left: drop any pending dwell and re-arm this widget."""
        if self._dwell_key == key:
            self._cancel_dwell()
        self._spoken_since_enter.discard(key)

    def _cancel_dwell(self) -> None:
        if self._dwell_handle is not None:
            self.scheduler.cancel(self._dwell_handle)
        self._dwell_handle = None
        self._dwell_key = None

    # -- highlight ring --

    def _start_highlight(self, key: str | None, text: str) -> None:
        if key is None:
            return
        self.speaking_key = key
        if self.on_highlight is not None:
            self.on_highlight(key, True)
        duration = max(MIN_HIGHLIGHT_MS, min(MAX_HIGHLIGHT_MS, len(text) * MS_PER_CHARACTER))

        def done() -> None:
            self._highlight_handle = None
            self._clear_highlight()

        self._highlight_handle = self.scheduler.schedule(duration, done)

    def _stop_highlight(self) -> None:
        if self._highlight_handle is not None:
            self.scheduler.cancel(self._highlight_handle)
            self._highlight_handle = None
        self._clear_highlight()

    def _clear_highlight(self) -> None:
        if self.speaking_key is not None and self.on_highlight is not None:
            self.on_highlight(self.speaking_key, False)
        self.speaking_key = None

    # -- lifecycle --

    def close(self) -> None:
        self._cancel_dwell()
        self._stop_highlight()
        self.backend.close()
