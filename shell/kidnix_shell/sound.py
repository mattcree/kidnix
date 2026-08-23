"""Earcons (08 section 3.6, spec 7a as revised by 7b).

Five short sounds, and only five: **keep** (a thing was saved), **tap** (a
child-facing control fired), **back** (we went back), **phase** (the session
moved on), **sleep** (the session is over). No music, no fanfare, no reward
chime -- an earcon here is punctuation, not applause, and non-negotiable 1
rules out anything that celebrates time on the device.

**Auditory icons where there is a referent (spec 7b, 09 section 10 #7).**
v0.1.3 shipped five abstract sine motifs. The only study of children and
earcons anywhere -- Jacko (1997, n=24) -- finds that recognition is driven by
*everyday-sound exposure*, not by musical structure, so an abstract interval is
a symbol a child has to be taught and a familiar sound is one they already own.
Four of the five now imitate the thing they mean:

============ ======================================= ==================
Earcon       Shape                                   Referent
============ ======================================= ==================
``keep``     five staggered bursts of high, crackly  paper being put away
             noise, each decaying fast
``back``     two soft knocks: a click on a low,       knuckles on a door
             quickly damped resonance
``sleep``    a slow-attack tone gliding down a        a yawn
             tenth, with a breathy noise layer
``tap``      an 8 ms transient on a short 1.5 kHz     a fingertip on a
             resonance                                 surface
``phase``    two sine tones, a falling fourth        *none* -- "the light
                                                       changed" has no sound
============ ======================================= ==================

**The honesty note, which belongs in the shipped code and not only in a
report.** None of this has been tested with a child, or with any listener. The
mapping from "shrinking noise burst" to "paper" is *our* extrapolation from one
1997 study of a different interface; the levels are aimed at roughly -14 LUFS
by construction rather than measured with a meter; and no kidnix earcon has
ever been heard on real speakers by anyone. The soundscape is a designed guess.
It is written down here so that the first person to hear it with a five-year-old
knows they are the experiment and not the confirmation.

They are still **generated, not shipped**: no binary blobs in git, no licence
ledger entry, and no chance of the file and the code drifting apart. The WAVs
are written once -- at image build time via ``python -m kidnix_shell.sound``,
or on first run into ``$XDG_CACHE_HOME/kidnix/sounds`` when ``/usr`` is
read-only. Synthesis is deterministic (a fixed noise seed per earcon), so the
same source always makes the same file.

Every earcon is <= 400 ms, including ``sleep``, which used to be 740.

Playback is GStreamer ``playbin``, set up lazily and asynchronously: a missing
GStreamer, a missing sink, or a broken pipeline logs **once** and the shell
carries on in silence. Nothing in this module may ever block the main loop.
"""

from __future__ import annotations

import contextlib
import logging
import math
import random
import struct
import time
import wave
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

from .access import AccessConfig

log = logging.getLogger(__name__)

#: 08 section 3.6: at most one earcon per quarter second, and never over speech.
MIN_GAP_SECONDS = 0.25

SAMPLE_RATE = 44_100
#: Every earcon is normalised to this peak times its own :attr:`Earcon.level`,
#: which is roughly -14 LUFS with these envelopes. Normalising is what lets a
#: noise burst and a sine sit at the same loudness without anyone guessing.
PEAK = 0.45
FADE_MS = 6.0  # a click at the edge of a 90 ms sound is the whole sound

#: **Every earcon fades in over at least this long** (06 section 7.4 #26, panel
#: ruling 7d #7, forum #39). Sudden unexpected sound is the most frequently
#: identified auditory sensory trigger for autistic children (06 section 4.3),
#: and until 2026-08-23 four of the five earcons attacked in **0.4-4.0 ms**.
#:
#: This is not free and the cost should not be hidden: an attack floor turns a
#: *tap* from a transient into a small swell, and a tap is press feedback, so
#: the child now hears the confirmation arrive over 150 ms rather than at once.
#: Sesame's own guidance would put press feedback under 100 ms. The ruling is
#: explicit and unconditional ("all earcons gain >= 150 ms fade-in regardless
#: of calm"), so it is implemented as written, and the trade is recorded here
#: and in the implementation notes rather than quietly softened: **if a child
#: test finds the tap now reads as laggy, the exception belongs to `tap` and
#: nothing else**, because a tap is the one sound the child themselves caused.
ATTACK_FLOOR_MS = 150.0
#: The tail an earcon keeps after its attack, so the fade-in is a fade-in and
#: not the whole sound.
MIN_TAIL_MS = 60.0
#: 08 section 3.6 said 400 ms. :data:`ATTACK_FLOOR_MS` has to fit inside a
#: sound before it can be a fade-in of one, so the ceiling moves with it.
MAX_EARCON_MS = 600.0

KEEP = "keep"
TAP = "tap"
BACK = "back"
#: The session moved from one phase to the next (spec section 6 / 08 3.6b).
PHASE = "phase"
SLEEP = "sleep"

#: v0.1.0 spoke of six sounds; 7a ruled four and v0.1.3 restored the fifth.
#: ``OPEN`` and ``FOCUS`` are aliases so call sites read naturally without
#: anyone inventing a new tone.
OPEN = TAP
FOCUS = TAP

NAMES: tuple[str, ...] = (KEEP, TAP, BACK, PHASE, SLEEP)

TONE = "tone"
GLIDE = "glide"
NOISE = "noise"


@dataclass(frozen=True)
class Layer:
    """One shaped sound inside an earcon.

    Layers overlap freely: ``start_ms`` places each one on the earcon's own
    timeline, which is what lets "two knocks" and "a breath under a glide" be
    described rather than spliced.
    """

    kind: str
    milliseconds: float
    #: Hz. For :data:`GLIDE`, the pitch it starts at.
    frequency: float = 440.0
    #: Hz. :data:`GLIDE` only: the pitch it arrives at.
    frequency_end: float | None = None
    start_ms: float = 0.0
    level: float = 1.0
    #: A slow attack is the difference between a knock and a yawn.
    attack_ms: float = 4.0
    #: Exponential decay constant. Bigger = shorter, drier.
    curve: float = 3.2
    #: One-pole filters for :data:`NOISE`. 0 means "leave it alone".
    lowpass_hz: float = 0.0
    highpass_hz: float = 0.0
    #: Irregular amplitude modulation, in Hz. This is what makes noise sound
    #: like paper rather than like a hiss.
    shimmer_hz: float = 0.0

    @property
    def end_ms(self) -> float:
        return self.start_ms + self.milliseconds


@dataclass(frozen=True)
class Earcon:
    """One sound: its layers, its loudness relative to the others, its story."""

    name: str
    layers: tuple[Layer, ...]
    #: Relative loudness after normalisation. ``phase`` is quieter on purpose:
    #: "the light changed" is news about the room, not about the child.
    level: float = 1.0
    #: The everyday sound this imitates, or why it does not imitate one. Kept
    #: in the data so the honesty note cannot drift away from the sound.
    referent: str = ""
    #: Fixed so synthesis is reproducible: the same code makes the same WAV.
    seed: int = 0

    @property
    def milliseconds(self) -> float:
        return max((layer.end_ms for layer in self.layers), default=0.0)


def _tone(frequency: float, milliseconds: float, **kwargs: Any) -> Layer:
    return Layer(kind=TONE, frequency=frequency, milliseconds=milliseconds, **kwargs)


def _glide(start: float, end: float, milliseconds: float, **kwargs: Any) -> Layer:
    return Layer(
        kind=GLIDE, frequency=start, frequency_end=end, milliseconds=milliseconds, **kwargs
    )


def _noise(milliseconds: float, **kwargs: Any) -> Layer:
    return Layer(kind=NOISE, milliseconds=milliseconds, **kwargs)


def _rustle() -> tuple[Layer, ...]:
    """Paper being put away: bursts of high, crackly noise, each dying fast."""
    return tuple(
        _noise(
            70.0,
            start_ms=start,
            level=level,
            attack_ms=3.0,
            curve=5.0,
            highpass_hz=1800.0,
            lowpass_hz=9000.0,
            shimmer_hz=70.0,
        )
        for start, level in ((0.0, 0.70), (45.0, 1.0), (95.0, 0.85), (140.0, 0.60), (180.0, 0.45))
    )


def _knock(start_ms: float, level: float) -> tuple[Layer, ...]:
    """Knuckles on a door: a click, then a low resonance that stops quickly."""
    return (
        _noise(
            12.0,
            start_ms=start_ms,
            level=0.8 * level,
            attack_ms=0.5,
            curve=9.0,
            highpass_hz=400.0,
            lowpass_hz=3500.0,
        ),
        _tone(180.0, 90.0, start_ms=start_ms, level=level, attack_ms=1.0, curve=7.0),
        _tone(298.0, 55.0, start_ms=start_ms, level=0.35 * level, attack_ms=1.0, curve=9.0),
    )


#: The five sounds. A child should be able to tell them apart with their eyes
#: shut, which is the entire specification.
EARCONS: dict[str, Earcon] = {
    KEEP: Earcon(
        name=KEEP,
        layers=_rustle(),
        referent="paper being gathered up and put away",
        seed=1301,
    ),
    TAP: Earcon(
        name=TAP,
        layers=(
            _noise(8.0, level=0.9, attack_ms=0.4, curve=10.0, highpass_hz=2500.0),
            _tone(1500.0, 70.0, level=0.55, attack_ms=1.0, curve=9.0),
        ),
        level=0.85,
        referent="a fingertip on a hard surface",
        seed=2207,
    ),
    BACK: Earcon(
        name=BACK,
        layers=_knock(0.0, 1.0) + _knock(120.0, 0.8),
        referent="two soft knocks on a door",
        seed=3313,
    ),
    # No referent: "the session moved on" is not a thing that makes a noise, so
    # this one stays an abstract motif -- a gentle step *down* a fourth, at the
    # lowest level of the five. It has to be tellable with the eyes shut from
    # BACK (knocks, not tones) and from SLEEP (a glide, twice as long).
    PHASE: Earcon(
        name=PHASE,
        layers=(
            _tone(880.0, 120.0, level=1.0, curve=3.4),
            _tone(659.26, 250.0, start_ms=120.0, level=0.9, curve=3.0),
        ),
        level=0.62,
        referent="none -- an abstract motif, because the light changing is silent",
        seed=4409,
    ),
    SLEEP: Earcon(
        name=SLEEP,
        layers=(
            _glide(430.0, 175.0, 360.0, level=1.0, attack_ms=90.0, curve=1.6),
            _glide(860.0, 350.0, 330.0, level=0.35, attack_ms=90.0, curve=2.4),
            _noise(
                360.0,
                level=0.22,
                attack_ms=120.0,
                curve=1.4,
                lowpass_hz=1400.0,
                highpass_hz=250.0,
                shimmer_hz=12.0,
            ),
        ),
        level=0.9,
        referent="a yawn -- a slow opening, then a long fall",
        seed=5501,
    ),
}


# --- synthesis -----------------------------------------------------------


def _envelope(index: int, count: int, attack: int, curve: float, fade: int) -> float:
    """Attack, exponential decay, and a fade at both edges so nothing clicks."""
    value = math.exp(-curve * index / count)
    if attack > 0 and index < attack:
        value *= index / attack
    if index < fade:
        value *= index / fade
    remaining = count - index
    if remaining < fade:
        value *= remaining / fade
    return value


def _shimmer(count: int, rate_hz: float, sample_rate: int, rng: random.Random) -> list[float]:
    """Held random gains, linearly interpolated: crackle rather than hiss."""
    hold = max(1, int(sample_rate / max(1.0, rate_hz)))
    knots = [rng.uniform(0.25, 1.0) for _ in range(count // hold + 2)]
    gains = []
    for index in range(count):
        position = index / hold
        low = int(position)
        blend = position - low
        gains.append(knots[low] * (1.0 - blend) + knots[low + 1] * blend)
    return gains


def _layer_samples(layer: Layer, sample_rate: int, rng: random.Random) -> list[float]:
    """One layer, as floats around zero, before mixing and normalising."""
    count = max(1, int(sample_rate * layer.milliseconds / 1000.0))
    attack = int(sample_rate * layer.attack_ms / 1000.0)
    fade = max(1, int(sample_rate * FADE_MS / 1000.0))

    if layer.kind == NOISE:
        source = [rng.uniform(-1.0, 1.0) for _ in range(count)]
        if layer.lowpass_hz > 0:
            source = _one_pole(source, layer.lowpass_hz, sample_rate)
        if layer.highpass_hz > 0:
            low = _one_pole(source, layer.highpass_hz, sample_rate)
            source = [raw - filtered for raw, filtered in zip(source, low, strict=True)]
        if layer.shimmer_hz > 0:
            gains = _shimmer(count, layer.shimmer_hz, sample_rate, rng)
            source = [value * gain for value, gain in zip(source, gains, strict=True)]
    else:
        source = []
        phase = 0.0
        end = layer.frequency if layer.frequency_end is None else layer.frequency_end
        for index in range(count):
            position = index / count
            # Glide in log-frequency: a fall that sounds even to an ear rather
            # than even to a plotter.
            frequency = layer.frequency * (end / layer.frequency) ** position
            phase += 2.0 * math.pi * frequency / sample_rate
            source.append(math.sin(phase))

    return [
        value * layer.level * _envelope(index, count, attack, layer.curve, fade)
        for index, value in enumerate(source)
    ]


def _one_pole(samples: list[float], cutoff_hz: float, sample_rate: int) -> list[float]:
    """A one-pole low-pass. Crude, cheap, and enough to shape noise."""
    alpha = 1.0 - math.exp(-2.0 * math.pi * cutoff_hz / sample_rate)
    out = []
    state = 0.0
    for value in samples:
        state += alpha * (value - state)
        out.append(state)
    return out


def with_attack_floor(earcon: Earcon, floor_ms: float = ATTACK_FLOOR_MS) -> Earcon:
    """The same earcon, with every layer given a >= ``floor_ms`` fade-in.

    Applied to the *layers* rather than to the mixed buffer, and that is the
    only honest way to do it: ramping a finished 70 ms sound over 150 ms would
    be 80 ms of silence followed by a fragment, which is a delay, not a fade.
    So a short layer is lengthened enough to have 150 ms of its own material
    to fade in, and its decay is relaxed in proportion so the tail does not
    eat the attack it now has.
    """
    if floor_ms <= 0:
        return earcon
    layers = []
    for layer in earcon.layers:
        if layer.attack_ms >= floor_ms:
            layers.append(layer)
            continue
        wanted = floor_ms + MIN_TAIL_MS
        length = max(layer.milliseconds, wanted)
        # A decay constant is per-sound, not per-millisecond: stretching the
        # sound without stretching the curve would leave it as short as it was.
        curve = layer.curve * (layer.milliseconds / length) if length > 0 else layer.curve
        layers.append(
            replace(layer, attack_ms=floor_ms, milliseconds=length, curve=max(0.8, curve))
        )
    return replace(earcon, layers=tuple(layers))


def mix(earcon: Earcon, sample_rate: int = SAMPLE_RATE) -> list[float]:
    """Every layer, summed onto one timeline and **normalised**.

    Normalisation is the point of doing it here: a noise burst and a sine have
    nothing in common until something makes their peaks agree, and a child's
    ear should not hear "back" as half the loudness of "keep" because of an
    arithmetic accident. The peak lands on ``PEAK * earcon.level`` exactly.
    """
    earcon = with_attack_floor(earcon)
    rng = random.Random(earcon.seed)
    total = max(1, int(sample_rate * earcon.milliseconds / 1000.0))
    buffer = [0.0] * total
    for layer in earcon.layers:
        offset = int(sample_rate * layer.start_ms / 1000.0)
        for index, value in enumerate(_layer_samples(layer, sample_rate, rng)):
            position = offset + index
            if position < total:
                buffer[position] += value

    loudest = max((abs(value) for value in buffer), default=0.0)
    if loudest <= 0:
        return buffer
    scale = (PEAK * earcon.level) / loudest
    return [value * scale for value in buffer]


def render(earcon: Earcon, sample_rate: int = SAMPLE_RATE) -> bytes:
    """Render one earcon to 16-bit mono PCM frames."""
    return b"".join(
        struct.pack("<h", int(max(-1.0, min(1.0, value)) * 32767))
        for value in mix(earcon, sample_rate)
    )


def write_wav(path: Path, earcon: Earcon, sample_rate: int = SAMPLE_RATE) -> Path:
    """Write one earcon. Atomic: a half-written WAV would play as a crackle."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".wav.tmp")
    with wave.open(str(temporary), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(sample_rate)
        handle.writeframes(render(earcon, sample_rate))
    temporary.replace(path)
    return path


def generate(directory: Path, *, force: bool = False) -> list[Path]:
    """Make sure every earcon exists in ``directory``. Returns what was written."""
    written = []
    for name, earcon in EARCONS.items():
        path = directory / f"{name}.wav"
        if force or not path.is_file():
            written.append(write_wav(path, earcon))
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
        self._volume = 1.0

    def set_volume(self, volume: float) -> None:
        """``playbin``'s own volume, 0.0-1.0. Under the hardware ceiling."""
        self._volume = max(0.0, min(1.0, volume))
        for player in self._players.values():
            with contextlib.suppress(Exception):
                player.set_property("volume", self._volume)

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
                player.set_property("volume", self._volume)
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
        self.volume = 1.0

    def set_volume(self, volume: float) -> None:
        self.volume = volume

    def play(self, path: Path) -> bool:
        self.played.append(path)
        return True

    def close(self) -> None:
        pass


class Earcons:
    """Plays one of the five sounds, or explains once why it cannot.

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
        access: AccessConfig | None = None,
    ) -> None:
        self.directory = directory or package_sounds_dir()
        self.cache_dir = cache_dir
        self.enabled = enabled
        #: ``[access]``: the volume, the mute and calm mode's shorter set.
        #: The image's 70% hardware ceiling is underneath all of it and is not
        #: reachable from here -- this is the *control* the ceiling is not.
        self.access = access or AccessConfig()
        self.player = player if player is not None else GstPlayer()
        self.set_volume(self.access.effective_volume)
        self._last = 0.0
        self._paths: dict[str, Path] = {}
        self._warned = False
        self._ready = False

    # -- files --

    def ensure_sounds(self) -> dict[str, Path]:
        """Find or generate the five WAVs. Called once, off the first play."""
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

    def set_access(self, access: AccessConfig) -> None:
        """Take a new ``[access]`` -- the grown-up sheet's volume row does this."""
        self.access = access
        self.set_volume(access.effective_volume)

    def set_volume(self, volume: float) -> None:
        setter = getattr(self.player, "set_volume", None)
        if setter is not None:
            setter(max(0.0, min(1.0, volume)))

    def play(self, name: str, *, speaking: bool = False) -> bool:
        """Play ``name``. Returns whether a sound actually started.

        ``speaking=True`` means the shell is talking: earcons duck under the
        voice rather than competing with it.

        Calm mode keeps :data:`kidnix_shell.access.CALM_EARCONS` and drops the
        rest, and a muted or zero-volume shell plays nothing at all. Both
        answers come from :meth:`~kidnix_shell.access.AccessConfig.
        earcon_allowed`, so "which sounds are on" is one pure function with a
        headless test rather than a condition spread over five call sites.
        """
        if not self.enabled or speaking:
            return False
        if not self.access.earcon_allowed(name):
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
