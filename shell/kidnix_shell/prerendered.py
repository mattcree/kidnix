"""Pre-rendered speech: the good voice, on the strings a child actually hears.

``docs/spikes/tts-kokoro.md`` §6 said **no** to running Kokoro-82M as a
synthesiser on the reference laptop -- 460 MB of image, 415 MB resident, and a
hover label arriving 650-830 ms after the pointer settles, past the threshold
``docs/spikes/tts.md`` §2.3 used to reject the one-shot CLI -- and **yes** to
§7.1, which is this module's other half: the shell's speech is a nearly closed
vocabulary, so ``build_files/66-prerender-speech.sh`` renders it once at image
build time and ships the audio instead of the model.

What that buys, and what it costs
---------------------------------

Runtime cost is **zero**: no onnxruntime in the image, no 325 MB graph, no
resident server, no inference. Playing a clip is ``playbin`` on a 14 kB Ogg
file, which is the same machinery ``kidnix_shell.sound`` already uses for the
five earcons.

The costs are real and are all *deliberately* paid by falling back, never by
degrading:

* **Only exact text hits.** A composite sentence ("You drew two pictures") is
  not in the index and goes to Piper, in Piper's voice. That is the one place a
  session changes timbre, and it is a minority of utterances.
* **Only en_GB.** Kokoro v1.0 has no Welsh and no Polish voice, and reading a
  Welsh label in a British English voice would mispronounce exactly the letters
  ADR-0012 exists to get right. A Welsh or Polish profile finds no index and
  behaves precisely as it does today.
* **Only at the pace the clips were rendered at.** ``[access] speech_rate`` is
  a number a parent sets for their child and calm mode is a floor on it
  (:mod:`kidnix_shell.access`); a clip is a fixed recording and cannot follow
  either. So the index records the ``speechd_rate`` it was rendered for and
  :meth:`PrerenderedVoice.set_rate` switches the whole catalogue **off** the
  moment the live rate differs. A parent who slowed the voice down gets the
  slower voice, not the prettier one -- the accessibility setting wins.

Every one of those is a fallback to the current behaviour, so the failure mode
of this whole module is *inaudible*: a missing clip, a missing index, a missing
GStreamer or a rate the catalogue cannot serve all end at the backend's own
``speak``, which is what the shell did before it existed.
"""

from __future__ import annotations

import contextlib
import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .speech import speech_off

log = logging.getLogger(__name__)

#: Where ``build_files/66-prerender-speech.sh`` puts the catalogue. One
#: directory per language, because the lookup must never hand an English clip
#: to a Welsh profile.
SPEECH_ROOT = Path("/usr/share/kidnix/speech")

INDEX_NAME = "index.json"

#: The index schema this module understands. An index from the future is
#: ignored rather than half-read: a rolled-back shell must not guess at the
#: shape of a catalogue a newer build wrote.
SUPPORTED_VERSION = 1

#: **The line a boot test greps for.** ``tests/boot/bcvk_boot_test.py`` counts
#: it to prove a child heard the rendered voice and not the synthesised one --
#: the same trick ``kidnix-piperd``'s "spoke N chars" counter plays, and for the
#: same reason: every fault in this subsystem degrades to a working voice, so
#: success has to be observable or it cannot be tested at all.
#:
#: It carries the clip's **file name** (a sha1) and never the text: the journal
#: already gets "speaking: ..." from :mod:`kidnix_shell.speech`, and one line
#: per utterance saying the same words twice is noise.
PLAYED_LOG = "played clip"


def normalise_language(language: str) -> str:
    """``en-GB``/``en_gb`` -> ``en_GB``. Bare ``en`` stays ``en``.

    speech-dispatcher and gettext disagree about the separator and the shell
    passes whichever it has (:func:`kidnix_shell.speech.current_speech_language`
    returns the SSIP form). The directory on disk is the gettext form.
    """
    text = (language or "").strip().replace("-", "_")
    if "_" not in text:
        return text.lower()
    head, _, tail = text.partition("_")
    return f"{head.lower()}_{tail.upper()}"


@dataclass(frozen=True)
class Catalogue:
    """One language's rendered clips, as read off the disk."""

    language: str
    voice: str
    directory: Path
    #: exact spoken text -> file name (a sha1 plus ``.ogg``)
    clips: dict[str, str]
    #: The speech-dispatcher rate these were rendered at. Outside it, unused.
    speechd_rate: int

    def path(self, text: str) -> Path | None:
        name = self.clips.get(text)
        return None if name is None else self.directory / name


def load_catalogue(root: Path, language: str) -> Catalogue | None:
    """Read one ``index.json``. Returns ``None`` for every kind of absence."""
    directory = root / normalise_language(language)
    index_path = directory / INDEX_NAME
    try:
        data = json.loads(index_path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None
    except (OSError, ValueError) as exc:
        log.info(
            "pre-rendered speech index at %s is unreadable (%s); using the voice", directory, exc
        )
        return None
    if data.get("version") != SUPPORTED_VERSION:
        log.info(
            "pre-rendered speech index at %s is version %r, not %d; using the voice",
            directory,
            data.get("version"),
            SUPPORTED_VERSION,
        )
        return None
    clips = data.get("clips")
    if not isinstance(clips, dict) or not clips:
        return None
    return Catalogue(
        language=str(data.get("language") or language),
        voice=str(data.get("voice") or "?"),
        directory=directory,
        clips={
            str(text): str(entry["file"])
            for text, entry in clips.items()
            if isinstance(entry, dict) and entry.get("file")
        },
        speechd_rate=int(data.get("speechd_rate", 0)),
    )


# --- playback ----------------------------------------------------------------


class ClipPlayer:
    """One ``playbin``, reused, with cancel semantics and no queue.

    **No queue is the point.** ``SpeechManager`` has never had one -- a new
    utterance cancels the old one, which is exactly right for a child sweeping
    a grid of tiles -- so a single element that is rewound and restarted models
    the contract precisely. Two clips can never overlap, and
    :meth:`cancel` stops the current one dead.

    Everything is asynchronous and nothing here may ever block the main loop,
    for the same reason :class:`kidnix_shell.sound.GstPlayer` may not: a state
    change that waits is a shell that stutters.
    """

    name = "gstreamer"

    def __init__(self) -> None:
        self._gst: Any = None
        self._player: Any = None
        self._broken = False
        self._volume = 1.0

    def set_volume(self, volume: float) -> None:
        self._volume = max(0.0, min(1.0, volume))
        if self._player is not None:
            with contextlib.suppress(Exception):
                self._player.set_property("volume", self._volume)

    def _ensure(self) -> Any:
        if self._player is not None or self._broken:
            return self._player
        try:
            import gi

            gi.require_version("Gst", "1.0")
            from gi.repository import Gst

            if not Gst.is_initialized():
                Gst.init(None)
            player = Gst.ElementFactory.make("playbin", None)
            if player is None:
                raise RuntimeError("playbin is not installed")
            player.set_property("volume", self._volume)
            bus = player.get_bus()
            bus.add_signal_watch()
            bus.connect("message::eos", self._on_finished)
            bus.connect("message::error", self._on_error)
            self._gst = Gst
            self._player = player
        except Exception as exc:
            log.info("no GStreamer for pre-rendered speech (%s); using the voice", exc)
            self._broken = True
        return self._player

    def play(self, path: Path) -> bool:
        # `_broken` is checked here and not only in `_ensure`: once a pipeline
        # has errored (no sink, no decoder, a VM with no audio device at all)
        # the element still exists, so `_ensure` would happily hand it back and
        # every subsequent clip would be reported as played while nothing came
        # out. Returning False instead hands the whole session to Piper, which
        # is the fallback this module is built around.
        if self._broken:
            return False
        player = self._ensure()
        if player is None:
            return False
        try:
            # READY first: it both stops whatever was playing and rewinds, so a
            # clip played twice in a row starts from the beginning rather than
            # from wherever the last one ended.
            player.set_state(self._gst.State.READY)
            player.set_property("uri", path.as_uri())
            player.set_state(self._gst.State.PLAYING)
            return True
        except Exception as exc:  # pragma: no cover - audio is never fatal
            log.info("pre-rendered clip would not play (%s); using the voice", exc)
            self._broken = True
            return False

    def cancel(self) -> None:
        if self._player is None or self._gst is None:
            return
        with contextlib.suppress(Exception):
            self._player.set_state(self._gst.State.READY)

    def _on_finished(self, _bus: Any, _message: Any) -> None:
        self.cancel()

    def _on_error(self, _bus: Any, message: Any) -> None:
        error, _debug = message.parse_error()
        if not self._broken:
            log.info("pre-rendered clip pipeline error (%s); using the voice", error)
        self._broken = True
        if self._player is not None and self._gst is not None:
            with contextlib.suppress(Exception):
                self._player.set_state(self._gst.State.NULL)

    def close(self) -> None:
        if self._player is not None and self._gst is not None:
            with contextlib.suppress(Exception):
                self._player.set_state(self._gst.State.NULL)
        self._player = None


class NullClipPlayer:
    """Test double, and what a machine with no GStreamer effectively has."""

    name = "null"

    def __init__(self) -> None:
        self.played: list[Path] = []
        self.cancels = 0
        self.volume = 1.0
        self.closed = False

    def set_volume(self, volume: float) -> None:
        self.volume = volume

    def play(self, path: Path) -> bool:
        self.played.append(path)
        return True

    def cancel(self) -> None:
        self.cancels += 1

    def close(self) -> None:
        self.closed = True


# --- the lookup ---------------------------------------------------------------


class PrerenderedVoice:
    """Exact-text lookup into the rendered catalogue, and playback of the hit.

    Constructed once by :mod:`kidnix_shell.app` and handed to
    :class:`kidnix_shell.speech.SpeechManager`, which asks it first and falls
    back to its backend on any miss.
    """

    def __init__(
        self,
        root: Path | None = None,
        language: str = "en-GB",
        player: Any = None,
        rate: int | None = None,
    ) -> None:
        self.root = root if root is not None else SPEECH_ROOT
        #: Anything with play/cancel/set_volume/close. `ClipPlayer` in the
        #: shell, `NullClipPlayer` in the tests, and typed as the duck it is
        #: so a test double does not have to inherit anything.
        self.player: Any = player if player is not None else ClipPlayer()
        self._language = language
        self._catalogue: Catalogue | None = None
        self._loaded = False
        #: ``None`` means "nobody has told us a rate yet", which is the
        #: catalogue's own until :meth:`set_rate` says otherwise.
        self._rate: int | None = rate
        self.hits = 0
        self.misses = 0

    # -- the catalogue --

    @property
    def catalogue(self) -> Catalogue | None:
        if not self._loaded:
            self._loaded = True
            self._catalogue = load_catalogue(self.root, self._language)
            if self._catalogue is None:
                log.info(
                    "no pre-rendered speech for %s in %s; the voice speaks everything",
                    self._language,
                    self.root,
                )
            else:
                log.info(
                    "pre-rendered speech: %d clips in %s (%s), rendered for rate %d",
                    len(self._catalogue.clips),
                    self._catalogue.language,
                    self._catalogue.voice,
                    self._catalogue.speechd_rate,
                )
        return self._catalogue

    @property
    def usable(self) -> bool:
        """Is the catalogue both present and valid at the rate now in force?"""
        catalogue = self.catalogue
        if catalogue is None:
            return False
        return self._rate is None or self._rate == catalogue.speechd_rate

    def set_language(self, language: str) -> None:
        """A profile switch. Drops the catalogue and re-reads on next use."""
        if normalise_language(language) == normalise_language(self._language):
            return
        self._language = language
        self._loaded = False
        self._catalogue = None
        self.cancel()

    def set_rate(self, rate: int) -> None:
        """Calm mode, or a parent's own ``speech_rate``.

        A recording has one tempo. Rather than play it at the wrong one, the
        catalogue steps aside entirely and Piper -- which *can* follow the rate
        -- speaks the whole session. See the module docstring.
        """
        if rate == self._rate:
            return
        previous = self.usable
        self._rate = rate
        catalogue = self.catalogue
        if catalogue is not None and previous != self.usable:
            if self.usable:
                log.info("pre-rendered speech is back on: rate %d matches the catalogue", rate)
            else:
                log.info(
                    "pre-rendered speech is off: rate %d is not the %d these clips were "
                    "rendered at, so the voice speaks everything",
                    rate,
                    catalogue.speechd_rate,
                )
        self.cancel()

    def set_volume(self, volume: float) -> None:
        setter = getattr(self.player, "set_volume", None)
        if setter is not None:
            setter(volume)

    # -- speaking --

    def lookup(self, text: str) -> Path | None:
        """The clip for exactly this text, or ``None``. Never raises."""
        if not self.usable:
            return None
        catalogue = self.catalogue
        assert catalogue is not None
        path = catalogue.path(text)
        if path is None:
            return None
        # A catalogue whose files went missing is a broken image, but a child
        # must not be the one who finds out: treat it as a miss.
        return path if path.is_file() else None

    def speak(self, text: str) -> bool:
        """Play the clip for ``text``. ``False`` means "you say it"."""
        path = self.lookup(text)
        if path is None:
            self.misses += 1
            return False
        if not self.player.play(path):
            self.misses += 1
            return False
        self.hits += 1
        log.info("%s: %s", PLAYED_LOG, path.name)
        return True

    def cancel(self) -> None:
        with contextlib.suppress(Exception):
            self.player.cancel()

    def close(self) -> None:
        close = getattr(self.player, "close", None)
        if close is not None:
            with contextlib.suppress(Exception):
                close()


def select_prerendered(
    root: Path | None = None, language: str = "en-GB", rate: int | None = None
) -> PrerenderedVoice | None:
    """A voice if a catalogue exists for ``language``, else ``None``.

    Reads the index eagerly, so ``app.py`` can log "there are N clips" once at
    start-up rather than discovering it on the first hover. Returns ``None``
    rather than an inert object so the hook in :mod:`kidnix_shell.speech` is a
    plain ``is not None`` and there is no second code path to keep alive.
    """
    if speech_off():
        # The other mouth. `select_backend` returns a NullBackend on the same
        # switch, and a catalogue that kept playing through it would make the
        # off-switch look like it worked while the machine talked anyway.
        log.info("pre-rendered speech disabled by KIDNIX_SPEECH")
        return None
    voice = PrerenderedVoice(root=root, language=language, rate=rate)
    return voice if voice.catalogue is not None else None
