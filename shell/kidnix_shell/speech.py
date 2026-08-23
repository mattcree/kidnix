"""Read-aloud (spec section 3, revised by 7b).

Every focusable thing in the shell carries a ``speak_text``. It is spoken on
keyboard focus (immediately -- focus is deliberate in a way hover is not, and
no delay is what every screen reader does), on pointer hover once the pointer
has **settled**, and on activation. The Ear button repeats the last utterance.
A new utterance always cancels the previous one -- a pre-reader exploring a
screen must never build up a backlog they have to wait out.

**The hover gate (spec 7b, 09 section 2).** v0.1.3 spoke after a flat 300 ms
inside the widget, which is the bottom of the range adults rate usable and
leaves no headroom for a five-year-old's overshoot-and-correct trajectory: a
pointer crossing half a grid on the way to a target set off every tile it
touched. So there are two conditions now, and both must hold:

1. **450 ms** of dwell (:data:`HOVER_DWELL_MS`, configurable as
   ``hover_dwell_ms`` in ``parent.toml``), and
2. the pointer's speed has been under :data:`SETTLE_VELOCITY_PX_S` for all of
   it, measured over the last :data:`VELOCITY_WINDOW_MS`. A sweep *across* a
   tile restarts the clock rather than starting it.

Both numbers are extrapolated from adult gaze-dwell research (Paulus & Remijn
2021); there is no child evidence for read-aloud-on-hover anywhere, which is
the honest reason every hover utterance is instrumented -- see
:data:`HOVER_LOG_PREFIX` and child-test protocol P5.

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
import math
import shutil
import subprocess
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, Protocol

log = logging.getLogger(__name__)

#: Spec 7b / 09 section 2: 450 ms, up from v0.1.3's 300 ms. Extrapolated from
#: adult gaze-dwell work; the first parameter to tune with a real child (P5).
HOVER_DWELL_MS = 450

#: The settle gate. While the pointer is moving faster than this it is *going
#: somewhere*, not looking at anything, and the dwell clock is held at zero.
#: 40 px/s is about a millimetre a second on the panel we test on -- a hand at
#: rest, not a hand travelling.
SETTLE_VELOCITY_PX_S = 40.0
#: Velocity is measured over the last motion events inside this window, so one
#: jittery sample from a trackpad cannot cancel a deliberate hover.
VELOCITY_WINDOW_MS = 150

#: How long after a hover utterance an activation of the *same* control still
#: counts as "the speech was wanted" (protocol P5's follow-through proxy).
HOVER_SELECTION_WINDOW_MS = 3000

#: Every hover utterance emits exactly one line with this prefix, at INFO, in
#: the systemd journal on the family's own machine and nowhere else. P5's whole
#: metric is the proportion of these with ``selected=True``: if utterances per
#: minute climb while that proportion falls, the threshold is too low.
#: The id is the control's, never anything the child typed or made.
HOVER_LOG_PREFIX = "hover-speech"

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
#: The pause between two sentences said in sequence (:meth:`SpeechManager.
#: speak_then`). A beat, not a gap -- long enough that the second sentence is
#: heard as a new sentence rather than as the end of the first.
SENTENCE_GAP_MS = 400


def _highlight_ms(text: str) -> int:
    """Roughly how long ``text`` takes to say. The only estimate we have."""
    return max(MIN_HIGHLIGHT_MS, min(MAX_HIGHLIGHT_MS, len(text) * MS_PER_CHARACTER))


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


@dataclass(frozen=True)
class _PendingHoverLog:
    """One hover utterance, waiting to find out whether it was wanted (P5)."""

    log_id: str
    dwell_ms: int
    key: str


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
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.backend: SpeechBackend = backend or NullBackend()
        self.scheduler: Scheduler = scheduler or GLibScheduler()
        self.dwell_ms = dwell_ms
        self.enabled = enabled
        self._clock = clock
        self.last_utterance: str = ""
        self.speaking_key: str | None = None
        self.on_highlight: Callable[[str, bool], None] | None = None
        self._dwell_handle: int | None = None
        self._dwell_key: str | None = None
        self._dwell_started: float = 0.0
        #: ``(key, text, log_id)`` for the widget the pointer is settling on.
        self._armed: tuple[str, str, str] | None = None
        #: (time, x, y) samples inside the widget the pointer is currently on.
        self._track: list[tuple[float, float, float]] = []
        self._highlight_handle: int | None = None
        #: hover keys already spoken since the pointer entered them
        self._spoken_since_enter: set[str] = set()
        #: The one hover utterance still waiting to find out whether it was
        #: followed by a selection (protocol P5).
        self._pending_log: _PendingHoverLog | None = None
        self._pending_log_handle: int | None = None
        #: The one pending second sentence of :meth:`speak_then`.
        self._sequel_handle: int | None = None

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
        # The one INFO line the read-aloud path emits. It is what makes the
        # voice observable from outside the machine (tests/e2e/), and it is
        # the shell's own UI text -- never anything the child typed or made.
        log.info("speaking: %s", text)
        self.backend.speak(text)
        self.last_utterance = text
        self._start_highlight(key, text)
        return True

    def speak_then(self, first: str, second: str, key: str | None = None) -> bool:
        """Two sentences, in that order, the second after the first has landed.

        The shell has never needed a queue -- a new utterance cancelling the
        old one is exactly right for a child sweeping a grid -- but S7 needs
        two sentences in a fixed order, because the ruling on the Goodbye
        screen is that the child's own destination is spoken **last, as its own
        sentence**, rather than as the tail of a sentence about counting
        (forum #24). This is that, and nothing more: no queue, no backlog, and
        a second call replaces a pending second sentence rather than stacking
        one behind it.

        The gap is estimated the same way the highlight is
        (:data:`MS_PER_CHARACTER`), because no backend tells us reliably when
        it stopped talking. The scheduler is injected, so the whole thing is
        testable headless.
        """
        second = (second or "").strip()
        if not second:
            return self.speak(first, key)
        if self._sequel_handle is not None:
            self.scheduler.cancel(self._sequel_handle)
            self._sequel_handle = None
        if not self.speak(first, key):
            return self.speak(second)
        delay = _highlight_ms(first) + SENTENCE_GAP_MS

        def say_second() -> None:
            self._sequel_handle = None
            self.speak(second)

        self._sequel_handle = self.scheduler.schedule(delay, say_second)
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
        """A control fired. Also closes P5's loop if hover just spoke it."""
        if key is not None:
            self._note_selection(key)
        return self.speak(text, key)

    # -- hover dwell + settle gate (spec 7b) --

    def hover_enter(self, key: str, text: str, log_id: str | None = None) -> None:
        """Pointer entered a widget: arm the dwell, and start watching it move.

        The clock starts here on the assumption that the pointer has *arrived*.
        :meth:`hover_motion` is what discovers otherwise: any sample above the
        velocity threshold pushes the whole dwell back, so a sweep across a
        grid says nothing at all and a hand that comes to rest says one thing.
        """
        self._cancel_dwell()
        self._track = []
        if key in self._spoken_since_enter:
            return
        self._arm_dwell(key, text, log_id or key)

    def hover_motion(self, key: str, x: float, y: float) -> None:
        """A pointer sample inside the widget ``key``. Cheap; called often."""
        if self._dwell_key != key:
            return
        now = self._clock()
        self._track.append((now, x, y))
        cutoff = now - VELOCITY_WINDOW_MS / 1000.0
        # Keep one sample from before the window so a slow drift still has a
        # baseline to be measured against.
        while len(self._track) > 2 and self._track[1][0] < cutoff:
            self._track.pop(0)
        if self.pointer_velocity() >= SETTLE_VELOCITY_PX_S and self._armed is not None:
            # Still travelling: the dwell has not begun.
            self._restart_dwell(*self._armed)

    def pointer_velocity(self) -> float:
        """Pointer speed in px/s over the last :data:`VELOCITY_WINDOW_MS`.

        Zero when there is nothing to measure -- a pointer that entered and
        never moved again is the definition of settled.
        """
        if len(self._track) < 2:
            return 0.0
        first, last = self._track[0], self._track[-1]
        seconds = last[0] - first[0]
        if seconds <= 0:
            return 0.0
        distance = math.hypot(last[1] - first[1], last[2] - first[2])
        return distance / seconds

    def hover_leave(self, key: str) -> None:
        """Pointer left: drop any pending dwell and re-arm this widget."""
        if self._dwell_key == key:
            self._cancel_dwell()
            self._track = []
        self._spoken_since_enter.discard(key)

    # -- the dwell timer itself --

    def _arm_dwell(self, key: str, text: str, log_id: str) -> None:
        self._armed = (key, text, log_id)
        self._dwell_key = key
        self._restart_dwell(key, text, log_id)

    def _restart_dwell(self, key: str, text: str, log_id: str) -> None:
        if self._dwell_handle is not None:
            self.scheduler.cancel(self._dwell_handle)
        self._dwell_started = self._clock()

        def fire() -> None:
            dwell_ms = round((self._clock() - self._dwell_started) * 1000) or self.dwell_ms
            self._dwell_handle = None
            self._dwell_key = None
            self._armed = None
            self._spoken_since_enter.add(key)
            self._log_hover(log_id, dwell_ms, key)
            self.speak(text, key)

        self._dwell_handle = self.scheduler.schedule(self.dwell_ms, fire)

    def _cancel_dwell(self) -> None:
        if self._dwell_handle is not None:
            self.scheduler.cancel(self._dwell_handle)
        self._dwell_handle = None
        self._dwell_key = None
        self._armed = None

    # -- protocol P5 instrumentation --

    def _log_hover(self, log_id: str, dwell_ms: int, key: str) -> None:
        """Hold the line back until we know whether a selection followed.

        One line per utterance, with a real boolean in it rather than a
        placeholder somebody would have to join up later. If the child picks
        the same control inside :data:`HOVER_SELECTION_WINDOW_MS`, the line is
        emitted at once with ``selected=True``; otherwise the timer emits it
        with ``selected=False``.
        """
        self._flush_hover_log()
        self._pending_log = _PendingHoverLog(log_id=log_id, dwell_ms=dwell_ms, key=key)
        self._pending_log_handle = self.scheduler.schedule(
            HOVER_SELECTION_WINDOW_MS, self._flush_hover_log
        )

    def _note_selection(self, key: str) -> None:
        """``selected=True`` only for the control hover actually spoke."""
        pending = self._pending_log
        if pending is None or pending.key != key:
            return
        self._flush_hover_log(selected=True)

    def _flush_hover_log(self, selected: bool = False) -> None:
        pending, self._pending_log = self._pending_log, None
        if self._pending_log_handle is not None:
            self.scheduler.cancel(self._pending_log_handle)
            self._pending_log_handle = None
        if pending is None:
            return
        log.info(
            "%s: id=%s dwell_ms=%d selected=%s",
            HOVER_LOG_PREFIX,
            pending.log_id,
            pending.dwell_ms,
            selected,
        )

    # -- highlight ring --

    def _start_highlight(self, key: str | None, text: str) -> None:
        if key is None:
            return
        self.speaking_key = key
        if self.on_highlight is not None:
            self.on_highlight(key, True)
        duration = _highlight_ms(text)

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
        # Do not lose the last hover of the session: P5 wants every one.
        self._flush_hover_log()
        self.backend.close()
