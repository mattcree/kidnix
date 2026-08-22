"""Earcons (08 section 3.6, spec 7a).

Four short sounds, and only four: **keep** (a thing was saved), **tap** (a
child-facing control fired), **back** (we went back), **sleep** (the session is
over). No music, no fanfare, no reward chime -- an earcon here is punctuation,
not applause, and non-negotiable 1 rules out anything that celebrates time on
the device.

They are **generated, not shipped**. A sine pair with a decay envelope is what
these four gestures actually need (they are 100 ms of feedback, not a
soundtrack), and generating them means no binary blobs in git, no licence
ledger entry, and no chance of the file and the code drifting apart. The WAVs
are written once -- at image build time via ``python -m kidnix_shell.sound``,
or on first run into ``$XDG_CACHE_HOME/kidnix/sounds`` when ``/usr`` is
read-only.

Levels are aimed at roughly -14 LUFS by construction (peak 0.45, decaying
envelope, ~0.2 RMS over the tone); nothing here is measured with a meter, and
the number to trust is a parent's volume knob.

Playback is GStreamer ``playbin``, set up lazily and asynchronously: a missing
GStreamer, a missing sink, or a broken pipeline logs **once** and the shell
carries on in silence. Nothing in this module may ever block the main loop.
"""

from __future__ import annotations

import contextlib
import logging
import math
import struct
import time
import wave
from dataclasses import dataclass
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)

#: 08 section 3.6: at most one earcon per quarter second, and never over speech.
MIN_GAP_SECONDS = 0.25

SAMPLE_RATE = 44_100
PEAK = 0.45  # roughly -14 LUFS with the decay envelope below
FADE_MS = 6.0  # a click at the edge of a 90 ms sound is the whole sound

KEEP = "keep"
TAP = "tap"
BACK = "back"
SLEEP = "sleep"

#: v0.1.0 spoke of six sounds; 7a rules four. ``OPEN`` and ``FOCUS`` are kept
#: as aliases so call sites read naturally and nothing plays a fifth tone.
OPEN = TAP
FOCUS = TAP

NAMES: tuple[str, ...] = (KEEP, TAP, BACK, SLEEP)


@dataclass(frozen=True)
class Tone:
    """One note: a frequency, a length in milliseconds, a relative level."""

    frequency: float
    milliseconds: float
    level: float = 1.0


#: The four sounds. Rising = something was kept; falling = we went back; low
#: and slow = the day is over. A child should be able to tell them apart with
#: their eyes shut, which is the entire specification.
EARCONS: dict[str, tuple[Tone, ...]] = {
    KEEP: (Tone(659.26, 90), Tone(987.77, 200, 0.9)),  # E5 -> B5, "kept"
    TAP: (Tone(880.0, 80),),  # A5, one soft tick
    BACK: (Tone(587.33, 80), Tone(392.0, 150, 0.9)),  # D5 -> G4, falling
    SLEEP: (Tone(329.63, 220, 0.8), Tone(220.0, 520, 0.7)),  # E4 -> A3, low
}


def render(tones: tuple[Tone, ...], sample_rate: int = SAMPLE_RATE) -> bytes:
    """Render a sequence of tones to 16-bit mono PCM frames.

    Each tone is a sine with an exponential decay and short fades, so there is
    no click at either edge and no DC step between notes.
    """
    frames = bytearray()
    for tone in tones:
        count = max(1, int(sample_rate * tone.milliseconds / 1000.0))
        fade = max(1, int(sample_rate * FADE_MS / 1000.0))
        omega = 2.0 * math.pi * tone.frequency / sample_rate
        for index in range(count):
            position = index / count
            decay = math.exp(-3.2 * position)
            envelope = decay
            if index < fade:
                envelope *= index / fade
            remaining = count - index
            if remaining < fade:
                envelope *= remaining / fade
            value = math.sin(omega * index) * PEAK * tone.level * envelope
            frames += struct.pack("<h", int(max(-1.0, min(1.0, value)) * 32767))
    return bytes(frames)


def write_wav(path: Path, tones: tuple[Tone, ...], sample_rate: int = SAMPLE_RATE) -> Path:
    """Write one earcon. Atomic: a half-written WAV would play as a crackle."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".wav.tmp")
    with wave.open(str(temporary), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(sample_rate)
        handle.writeframes(render(tones, sample_rate))
    temporary.replace(path)
    return path


def generate(directory: Path, *, force: bool = False) -> list[Path]:
    """Make sure every earcon exists in ``directory``. Returns what was written."""
    written = []
    for name, tones in EARCONS.items():
        path = directory / f"{name}.wav"
        if force or not path.is_file():
            written.append(write_wav(path, tones))
    return written


def package_sounds_dir() -> Path:
    return Path(__file__).parent / "data" / "sounds"


class GstPlayer:
    """A ``playbin`` per sound, built lazily, never blocking.

    GStreamer is initialised on the first play. If anything at all goes wrong
    -- no GStreamer, no audio sink, no PulseAudio in a VM -- we log it once and
    become a no-op for the rest of the run.
    """

    name = "gstreamer"

    def __init__(self) -> None:
        self._gst: Any = None
        self._players: dict[str, Any] = {}
        self._broken = False

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
            log.info("no GStreamer (%s); earcons are off for this run", exc)
            self._broken = True
        return self._gst

    def play(self, path: Path) -> bool:
        gst = self._init_gst()
        if gst is None:
            return False
        try:
            player = self._players.get(str(path))
            if player is None:
                player = gst.ElementFactory.make("playbin", None)
                if player is None:
                    raise RuntimeError("playbin is not installed")
                player.set_property("uri", path.as_uri())
                bus = player.get_bus()
                bus.add_signal_watch()
                bus.connect("message::eos", self._on_finished, player)
                bus.connect("message::error", self._on_error, player)
                self._players[str(path)] = player
            # Rewind and play. Both calls are asynchronous by design: we never
            # wait for a state change on the main loop.
            player.set_state(gst.State.READY)
            player.set_state(gst.State.PLAYING)
            return True
        except Exception as exc:  # pragma: no cover - audio is never fatal
            log.info("earcon playback failed (%s); earcons are off for this run", exc)
            self._broken = True
            return False

    def _on_finished(self, _bus: Any, _message: Any, player: Any) -> None:
        if self._gst is not None:
            player.set_state(self._gst.State.READY)

    def _on_error(self, _bus: Any, message: Any, player: Any) -> None:
        error, _debug = message.parse_error()
        if not self._broken:
            log.info("earcon pipeline error (%s); earcons are off for this run", error)
        self._broken = True
        if self._gst is not None:
            player.set_state(self._gst.State.NULL)

    def close(self) -> None:
        if self._gst is None:
            return
        for player in self._players.values():
            with contextlib.suppress(Exception):  # pragma: no cover
                player.set_state(self._gst.State.NULL)
        self._players.clear()


class NullPlayer:
    """No audio. Used by the tests and by anything without GStreamer."""

    name = "null"

    def __init__(self) -> None:
        self.played: list[Path] = []

    def play(self, path: Path) -> bool:
        self.played.append(path)
        return True

    def close(self) -> None:
        pass


class Earcons:
    """Plays one of the four sounds, or explains once why it cannot.

    ``directory`` is searched first (the package's own ``data/sounds``), then
    ``cache_dir``; missing files are generated into whichever of the two is
    writable, so a read-only ``/usr`` still gets earcons.
    """

    def __init__(
        self,
        directory: Path | None = None,
        cache_dir: Path | None = None,
        enabled: bool = True,
        player: Any = None,
    ) -> None:
        self.directory = directory or package_sounds_dir()
        self.cache_dir = cache_dir
        self.enabled = enabled
        self.player = player if player is not None else GstPlayer()
        self._last = 0.0
        self._paths: dict[str, Path] = {}
        self._warned = False
        self._ready = False

    # -- files --

    def ensure_sounds(self) -> dict[str, Path]:
        """Find or generate the four WAVs. Called once, off the first play."""
        if self._ready:
            return self._paths
        self._ready = True
        for name in NAMES:
            existing = self._find(name)
            if existing is not None:
                self._paths[name] = existing
        missing = [name for name in NAMES if name not in self._paths]
        if not missing:
            return self._paths
        for target in (self.directory, self.cache_dir):
            if target is None:
                continue
            try:
                generate(target)
            except OSError as exc:
                log.debug("cannot write earcons to %s (%s)", target, exc)
                continue
            log.info("generated %d earcon(s) in %s", len(missing), target)
            for name in missing:
                path = target / f"{name}.wav"
                if path.is_file():
                    self._paths[name] = path
            break
        if len(self._paths) < len(NAMES) and not self._warned:
            log.info("no writable directory for earcons; running silent")
            self._warned = True
        return self._paths

    def _find(self, name: str) -> Path | None:
        for directory in (self.directory, self.cache_dir):
            if directory is None:
                continue
            candidate = directory / f"{name}.wav"
            if candidate.is_file():
                return candidate
        return None

    # -- playing --

    def play(self, name: str, *, speaking: bool = False) -> bool:
        """Play ``name``. Returns whether a sound actually started.

        ``speaking=True`` means the shell is talking: earcons duck under the
        voice rather than competing with it.
        """
        if not self.enabled or speaking:
            return False
        now = time.monotonic()
        if now - self._last < MIN_GAP_SECONDS:
            return False
        path = self.ensure_sounds().get(name)
        if path is None:
            if not self._warned:
                log.info("no earcon for %r; running silent", name)
                self._warned = True
            return False
        self._last = now
        return bool(self.player.play(path))

    def close(self) -> None:
        close = getattr(self.player, "close", None)
        if close is not None:
            close()


def main(argv: list[str] | None = None) -> int:  # pragma: no cover - build tool
    """``python -m kidnix_shell.sound [DIR]`` -- generate the earcons at build."""
    import sys

    args = list(sys.argv[1:] if argv is None else argv)
    force = "--force" in args
    args = [a for a in args if a != "--force"]
    directory = Path(args[0]) if args else package_sounds_dir()
    written = generate(directory, force=force)
    for path in written:
        print(f"wrote {path}")
    if not written:
        print(f"all {len(EARCONS)} earcons already in {directory}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
