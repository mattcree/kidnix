""" "Tell me about it" -- a twenty-second voice note (spec 7d #9).

The cheapest big win in the whole panel review, in the early-years teacher's
words: *"nothing in this machine records the child's voice. A five-year-old who
has just made something wants to tell you about it, and the one thing they can
do fluently at five is talk."* It lands in two places: the "Let's keep that"
screen, at the moment the thing was made, and on a Journal card afterwards.

What it is, and every clause here is a decision:

* **One press starts, a second press stops**, and it stops itself at
  :data:`MAX_SECONDS`. No hold-to-talk (a five-year-old cannot keep a button
  down and think at the same time), no countdown (there are no digits anywhere
  in this shell), and no "are you sure?".
* **A level meter while it runs**, because the only thing a pre-reader can use
  to tell "it is listening" from "it is broken" is seeing their own voice move
  something.
* **It plays back once**, immediately, and then stops. A note the child never
  hears is a note they have no reason to believe in.
* **No retakes UI.** Pressing the button again simply records again over the
  old one. A "keep or discard?" dialogue would be asking a five-year-old to
  judge their own recording, which is a different product.
* **No transcription, ever, and no research logging.** The file is an ordinary
  OGG in the entry's own directory, next to the drawing, where
  ``kidnix-export`` picks it up and ``kidnix-wipe`` deletes it. Nothing reads
  it but a person.
* **It degrades silently.** No microphone, no GStreamer, no PipeWire: the
  button is simply not there. A mic button that does nothing teaches a child
  that buttons lie (spec 7a's rule about Ask).

The recorder is injected everywhere, so all of the above is testable with a
:class:`FakeRecorder` and no audio hardware at all.
"""

from __future__ import annotations

import contextlib
import logging
from collections.abc import Callable
from pathlib import Path
from typing import Any, Protocol

log = logging.getLogger(__name__)

#: What the file is called, inside the Journal entry's own directory. Beside
#: ``entry.json``, ``v001.png`` and ``thumb.png``, so a parent browsing the
#: journal in Files finds the drawing and the child talking about it together.
NOTE_NAME = "note.ogg"

#: **Twenty seconds, and it is a ceiling, not a target** (spec 7d #9). Long
#: enough for "I made a dinosaur and he's got a hat on"; short enough that a
#: forgotten recording is twenty seconds of room noise rather than an afternoon.
MAX_SECONDS = 20.0

#: How often the meter is refreshed. Ten times a second is smooth enough to
#: read as "this is my voice" and slow enough to cost nothing.
LEVEL_POLL_MS = 100

#: The GStreamer sources we try, in order. ``pipewiresrc`` is what the image
#: actually has (PipeWire is the session's audio server); ``autoaudiosrc`` is
#: for a developer's machine and for anything that is not PipeWire. If neither
#: builds there is no microphone and the button does not appear.
SOURCES: tuple[str, ...] = ("pipewiresrc", "autoaudiosrc")

#: Vorbis at quality 0.3 is about 80 kbit/s mono -- a couple of hundred
#: kilobytes for the whole twenty seconds, in a format that opens in anything.
#: Deliberately not Opus-in-Ogg only because vorbisenc is the encoder we can
#: rely on being present alongside the earcon playback we already use;
#: :data:`ENCODERS` tries the better one first anyway.
ENCODERS: tuple[tuple[str, str], ...] = (
    ("opusenc", "opusenc bitrate=48000"),
    ("vorbisenc", "vorbisenc quality=0.3"),
)


def note_path(entry_dir: Path) -> Path:
    """Where the voice note for a journal entry lives."""
    return entry_dir / NOTE_NAME


def has_note(entry_dir: Path | None) -> bool:
    """Is there a voice note here? Drives the Journal card's ear badge."""
    if entry_dir is None:
        return False
    candidate = note_path(entry_dir)
    try:
        return candidate.is_file() and candidate.stat().st_size > 0
    except OSError:  # pragma: no cover - a disk that vanished mid-session
        return False


class Recorder(Protocol):
    """What :class:`VoiceNote` needs from a microphone."""

    name: str

    @property
    def available(self) -> bool:
        """Is there anything to record with? Decides whether the button exists."""

    @property
    def recording(self) -> bool: ...

    @property
    def level(self) -> float:
        """0.0-1.0, for the meter. Never negative, never above one."""

    def start(self, path: Path) -> bool: ...

    def stop(self) -> None: ...

    def close(self) -> None: ...


class NullRecorder:
    """No microphone. Says so once, and is never offered to the child."""

    name = "null"

    def __init__(self, reason: str = "no microphone") -> None:
        self.reason = reason
        self.started: list[Path] = []

    @property
    def available(self) -> bool:
        return False

    @property
    def recording(self) -> bool:
        return False

    @property
    def level(self) -> float:
        return 0.0

    def start(self, path: Path) -> bool:
        log.info("no voice note (%s)", self.reason)
        return False

    def stop(self) -> None:
        pass

    def close(self) -> None:
        pass


class FakeRecorder:
    """Test double. Writes a plausible file and moves the meter on demand."""

    name = "fake"

    def __init__(self, available: bool = True) -> None:
        self._available = available
        self._recording = False
        self._path: Path | None = None
        self.level = 0.0
        self.started: list[Path] = []
        self.stops = 0
        self.closed = False

    @property
    def available(self) -> bool:
        return self._available

    @property
    def recording(self) -> bool:
        return self._recording

    def start(self, path: Path) -> bool:
        if not self._available:
            return False
        self._path = path
        self._recording = True
        self.started.append(path)
        return True

    def stop(self) -> None:
        self.stops += 1
        if not self._recording:
            return
        self._recording = False
        self.level = 0.0
        if self._path is not None:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            self._path.write_bytes(b"OggS-fake-voice-note")

    def close(self) -> None:
        self.closed = True
        self._recording = False


class GstRecorder:
    """The real one: one GStreamer pipeline, built lazily, never blocking.

    ``<source> ! audioconvert ! audioresample ! level ! <encoder> ! oggmux !
    filesink``. The ``level`` element is what makes the meter honest -- it is
    the peak of the audio actually going into the file, not an animation.

    Everything here is failure-tolerant on purpose: a child's session must never
    end because a microphone was unplugged. Any failure at any stage means the
    recorder reports itself unavailable and the mic button is not drawn.
    """

    name = "gstreamer"

    def __init__(self, source: str | None = None) -> None:
        self._gst: Any = None
        self._pipeline: Any = None
        #: The pipeline that has been sent EOS and is finishing its file.
        self._closing: Any = None
        self._broken = False
        self._probed = False
        self._source = source
        self._encoder = ""
        self._level = 0.0
        self._path: Path | None = None
        #: Called (on the GLib main loop) when a recording has been written.
        self.on_finished: Callable[[Path], None] | None = None

    # -- probing --

    def _init_gst(self) -> Any:
        if self._gst is not None or self._broken:
            return self._gst
        try:
            import gi

            gi.require_version("Gst", "1.0")
            from gi.repository import Gst

            if not Gst.is_initialized():
                Gst.init(None)
            self._gst = Gst
        except Exception as exc:
            log.info("no GStreamer (%s); voice notes are off for this run", exc)
            self._broken = True
        return self._gst

    def _probe(self) -> bool:
        """Find a source and an encoder that exist. Cached for the run."""
        if self._probed:
            return not self._broken
        self._probed = True
        gst = self._init_gst()
        if gst is None:
            return False
        try:
            candidates = (self._source,) if self._source else SOURCES
            for element in candidates:
                if element and gst.ElementFactory.find(element) is not None:
                    self._source = element
                    break
            else:
                log.info("no audio source element (%s); voice notes are off", ", ".join(SOURCES))
                self._broken = True
                return False
            for factory, pipeline_fragment in ENCODERS:
                if gst.ElementFactory.find(factory) is not None:
                    self._encoder = pipeline_fragment
                    break
            else:
                log.info("no Ogg audio encoder installed; voice notes are off")
                self._broken = True
                return False
        except Exception as exc:  # pragma: no cover - a broken GStreamer
            log.info("could not probe GStreamer (%s); voice notes are off", exc)
            self._broken = True
            return False
        log.info("voice notes: %s -> %s", self._source, self._encoder.split()[0])
        return True

    @property
    def available(self) -> bool:
        return self._probe()

    @property
    def recording(self) -> bool:
        return self._pipeline is not None

    @property
    def level(self) -> float:
        return self._level

    # -- recording --

    def start(self, path: Path) -> bool:
        if not self._probe():
            return False
        if self._pipeline is not None:
            self.stop()
        gst = self._gst
        assert gst is not None
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            # `location` is a real path from the Journal, never anything typed.
            description = (
                f"{self._source} ! audioconvert ! audioresample "
                f"! level interval=50000000 ! {self._encoder} ! oggmux "
                f'! filesink location="{path}"'
            )
            pipeline = gst.parse_launch(description)
            bus = pipeline.get_bus()
            bus.add_signal_watch()
            bus.connect("message::element", self._on_element)
            bus.connect("message::eos", self._on_eos)
            bus.connect("message::error", self._on_error)
            pipeline.set_state(gst.State.PLAYING)
        except Exception as exc:
            log.info("could not start recording (%s); voice notes are off for this run", exc)
            self._broken = True
            return False
        self._pipeline = pipeline
        self._path = path
        self._level = 0.0
        return True

    def stop(self) -> None:
        """Ask for an end-of-stream so the Ogg container is closed properly.

        Setting the pipeline straight to NULL truncates the file: oggmux has to
        see EOS to write its last page. The state change happens on the bus
        callback; this returns at once.
        """
        pipeline, self._pipeline = self._pipeline, None
        self._level = 0.0
        if pipeline is None or self._gst is None:
            return
        try:
            pipeline.send_event(self._gst.Event.new_eos())
            self._closing = pipeline
        except Exception as exc:  # pragma: no cover - audio is never fatal
            log.info("could not stop recording cleanly (%s)", exc)
            self._teardown(pipeline)

    def _on_element(self, _bus: Any, message: Any) -> None:
        structure = message.get_structure()
        if structure is None or structure.get_name() != "level":
            return
        try:
            peaks = structure.get_value("peak")
        except Exception:  # pragma: no cover - GStreamer version differences
            return
        if not peaks:
            return
        # `level` reports dB, negative, with 0 as full scale. -50 dB is a quiet
        # room and 0 is shouting into the microphone, so that is the range the
        # meter draws -- anything quieter is simply the bottom of the bar.
        loudest = max(float(peak) for peak in peaks)
        self._level = max(0.0, min(1.0, (loudest + 50.0) / 50.0))

    def _on_eos(self, _bus: Any, _message: Any) -> None:
        self._teardown(self._closing or self._pipeline)
        if self._path is not None and self.on_finished is not None:
            self.on_finished(self._path)

    def _on_error(self, _bus: Any, message: Any) -> None:
        error, _debug = message.parse_error()
        log.info("voice note pipeline error (%s); voice notes are off for this run", error)
        self._broken = True
        self._teardown(self._closing or self._pipeline)

    def _teardown(self, pipeline: Any) -> None:
        self._closing = None
        self._pipeline = None
        self._level = 0.0
        if pipeline is None or self._gst is None:
            return
        with contextlib.suppress(Exception):  # audio is never fatal
            pipeline.set_state(self._gst.State.NULL)

    def close(self) -> None:
        self.stop()
        self._teardown(self._closing)


class VoiceNote:
    """The button's whole behaviour, with no GTK in it.

    One press starts, a second stops, and :data:`MAX_SECONDS` stops it anyway.
    The scheduler is :class:`kidnix_shell.speech.Scheduler` -- the same one the
    hover dwell uses -- so a test drives twenty seconds in one call.
    """

    def __init__(
        self,
        recorder: Recorder | None = None,
        scheduler: Any = None,
        player: Any = None,
        max_seconds: float = MAX_SECONDS,
    ) -> None:
        from .speech import GLibScheduler

        self.recorder: Recorder = recorder if recorder is not None else GstRecorder()
        self.scheduler = scheduler if scheduler is not None else GLibScheduler()
        self._player = player
        self.max_seconds = max_seconds
        #: ``(recording: bool)`` -- the button's own appearance.
        self.on_state: Callable[[bool], None] | None = None
        #: ``(level: float)`` -- the meter, ten times a second while recording.
        self.on_level: Callable[[float], None] | None = None
        #: ``(path)`` when a note has been written. The screen plays it back.
        self.on_saved: Callable[[Path], None] | None = None
        self._stop_handle: int | None = None
        self._meter_handle: int | None = None
        self._entry_dir: Path | None = None
        #: True once this note has been recorded at least once in this sitting:
        #: the only thing "again?" is asked about.
        self.retakes = 0

    @property
    def available(self) -> bool:
        return bool(self.recorder.available)

    @property
    def recording(self) -> bool:
        return bool(self.recorder.recording)

    def toggle(self, entry_dir: Path) -> bool:
        """One press. Returns whether a recording is running afterwards."""
        if self.recording:
            self.stop()
            return False
        return self.start(entry_dir)

    def start(self, entry_dir: Path) -> bool:
        if self.recording:
            return True
        target = note_path(entry_dir)
        existing = has_note(entry_dir)
        if not self.recorder.start(target):
            return False
        self._entry_dir = entry_dir
        if existing:
            # A second recording simply replaces the first. Counted so the
            # screen can say "again?" quietly, and for nothing else.
            self.retakes += 1
        self._stop_handle = self.scheduler.schedule(
            int(self.max_seconds * 1000), self._stop_on_time
        )
        self._meter_handle = self.scheduler.schedule(LEVEL_POLL_MS, self._tick_meter)
        self._announce(True)
        return True

    def _stop_on_time(self) -> None:
        """Twenty seconds. Not an interruption: it is what the button promised."""
        self._stop_handle = None
        if self.recording:
            log.info("voice note reached its %.0f second limit", self.max_seconds)
            self.stop()

    def _tick_meter(self) -> None:
        self._meter_handle = None
        if not self.recording:
            return
        if self.on_level is not None:
            self.on_level(max(0.0, min(1.0, self.recorder.level)))
        self._meter_handle = self.scheduler.schedule(LEVEL_POLL_MS, self._tick_meter)

    def stop(self) -> Path | None:
        """Stop, and hand back the path if there is now a note there."""
        self._cancel()
        was_recording = self.recording
        self.recorder.stop()
        self._announce(False)
        if self.on_level is not None:
            self.on_level(0.0)
        entry_dir, self._entry_dir = self._entry_dir, None
        if not was_recording or entry_dir is None:
            return None
        target = note_path(entry_dir)
        if self.on_saved is not None:
            self.on_saved(target)
        return target

    def play(self, entry_dir: Path) -> bool:
        """Play an existing note. Silent (and False) when there is not one."""
        if not has_note(entry_dir):
            return False
        player = self._player
        if player is None:
            from .sound import GstPlayer

            player = self._player = GstPlayer()
        return bool(player.play(note_path(entry_dir)))

    def _announce(self, recording: bool) -> None:
        if self.on_state is not None:
            self.on_state(recording)

    def _cancel(self) -> None:
        for name in ("_stop_handle", "_meter_handle"):
            handle = getattr(self, name)
            if handle is not None:
                self.scheduler.cancel(handle)
                setattr(self, name, None)

    def close(self) -> None:
        self._cancel()
        self.recorder.close()
        player = self._player
        if player is not None:
            close = getattr(player, "close", None)
            if close is not None:
                close()
