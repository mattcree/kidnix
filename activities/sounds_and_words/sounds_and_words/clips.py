"""Playing a recording of a person saying a sound.

:mod:`sounds_and_words.phonemes` decides *what* a GPC sounds like and whether
there is a recording of it; this module is the other half of that sentence --
the thing that actually makes a noise when there is. Until 2026-08-23 there was
no such thing anywhere in kidnix: the SDK speaks (speech-dispatcher, one voice,
captions) and has no audio player at all, so ``activity.py`` logged *"there is
no player yet"* and fell back to the spelled label. The audit's item 6 is that
the first real recording would then fail as a **missing player** rather than as
a wrong sound, which is a bad way to find out.

So there is a player, and it is deliberately the smallest one that can work.

Why GStreamer, and why ``playbin``
----------------------------------

It is already on the image (GNOME's own media stack), it is already the thing
PipeWire is wired to, and ``playbin`` is one object that takes a URI and a
volume and needs no knowledge of the container. An ``.ogg`` of a person saying
/s/ is 30 kB and 400 ms; anything more elaborate than one element and two
property sets would be building a media framework for a sound shorter than a
button click.

What this does **not** do, on purpose
-------------------------------------

* **It does not queue.** A new sound cancels the old one, exactly as
  :class:`kidnix_shell.speech.SpeechManager` does with sentences (08 section
  3.6, "one voice"): a child sweeping a row of four tiles must not build up a
  backlog of four phonemes they have to wait out.
* **It does not decide whether to make a sound.** ``[access] mute`` is the
  parent's answer and the caller applies it, because a muted machine must still
  show the caption -- which means falling back to the spoken label's path, not
  playing silently. See :meth:`sounds_and_words.activity.SoundsAndWords.
  say_phoneme`.
* **Calm does not silence it.** ``calm`` drops *earcons* and slows the voice
  (``kidnix_shell.access``); a phoneme is not an earcon, it is the content of
  the activity. Calm reaches it only through the volume the caller passes.
* **It never raises.** A missing GStreamer, a corrupt file, a busy sink: all of
  them are "no clip played", the caller says the label instead, and the child
  hears a sound either way. :class:`NullClipPlayer` is what a machine with no
  GStreamer gets, and it is also what the tests use.

The caption, and the one thing this cannot fix
----------------------------------------------

Everything kidnix *says* is written down, because the SDK's caption hook is
called before its own "is speech even on?" check
(``docs/design/activity-sdk.md`` section 4.2). A clip is not said, so a clip is
not captioned, and the shell's caption datagram has no "show this but do not
say it" key to borrow -- a delivered datagram **is** the utterance and the
shell speaks it (:mod:`kidnix_activity.captions`). That is an SDK change, not
an activity one, and ``docs/design/sounds-and-words.md`` section 15 records it
as the thing that must land in the same wave as the first recording. Today no
clip exists, so nothing is uncaptioned today.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from pathlib import Path
from typing import Protocol, runtime_checkable

log = logging.getLogger(__name__)

__all__ = [
    "ClipPlayer",
    "GstClipPlayer",
    "NullClipPlayer",
    "make_player",
]


@runtime_checkable
class ClipPlayer(Protocol):
    """What the activity needs from anything that can make a noise.

    Three methods, and :meth:`play` answers the only question the caller has:
    *did the child hear the recording?* ``False`` means "say the label", which
    is what makes every failure path end in a sound rather than in silence.
    """

    def play(self, path: Path, *, volume: float = 1.0) -> bool:
        """Play this file now, cancelling anything already playing."""
        ...

    def stop(self) -> None:
        """Stop. A child who has moved on is not waiting for us."""
        ...

    def close(self) -> None:
        """Let the audio device go. Safe to call twice."""
        ...


class NullClipPlayer:
    """No player. Says so once, records what it was asked for, plays nothing.

    This is not a stub for something unfinished -- it is the honest answer on a
    machine with no GStreamer, and it is what every headless test uses. The
    caller's fallback (the spelled label, spoken) is a real sound, so a child on
    such a machine loses the recording and loses nothing else.
    """

    def __init__(self, reason: str = "") -> None:
        self.reason = reason
        #: Everything :meth:`play` was asked for, in order. The test hook.
        self.played: list[Path] = []
        self._said = False

    def play(self, path: Path, *, volume: float = 1.0) -> bool:
        self.played.append(Path(path))
        if not self._said:
            self._said = True
            log.info(
                "no clip player (%s); phonemes fall back to their spelled labels",
                self.reason or "not built on this machine",
            )
        return False

    def stop(self) -> None:
        return None

    def close(self) -> None:
        return None


class GstClipPlayer:
    """One ``playbin``, reused. Cancels itself, and never raises at the caller.

    Built by :func:`make_player` rather than directly, because "is GStreamer
    here?" is a question with three answers (no PyGObject, no ``Gst``
    typelib, no ``playbin`` element) and none of them should reach an activity.
    """

    def __init__(self, element, gst) -> None:
        self._element = element
        self._gst = gst
        self._closed = False
        bus = element.get_bus()
        if bus is not None:  # pragma: no branch - playbin always has one
            bus.add_signal_watch()
            bus.connect("message::eos", self._done)
            bus.connect("message::error", self._failed)

    def play(self, path: Path, *, volume: float = 1.0) -> bool:
        if self._closed:  # pragma: no cover - the window is going away
            return False
        try:
            # NULL first: a playbin that is already PLAYING will not take a new
            # uri, and "the last sound keeps playing" is the queue this module
            # exists not to have.
            self._element.set_state(self._gst.State.NULL)
            self._element.set_property("uri", self._gst.filename_to_uri(str(Path(path))))
            self._element.set_property("volume", max(0.0, min(1.0, volume)))
            result = self._element.set_state(self._gst.State.PLAYING)
        except Exception as exc:  # pragma: no cover - a broken file or sink
            log.warning("could not play %s: %s", path, exc)
            self.stop()
            return False
        if result == self._gst.StateChangeReturn.FAILURE:  # pragma: no cover
            log.warning("the audio sink refused %s", path)
            self.stop()
            return False
        return True

    def stop(self) -> None:
        try:
            self._element.set_state(self._gst.State.NULL)
        except Exception as exc:  # pragma: no cover - already gone
            log.debug("stopping the clip player: %s", exc)

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        self.stop()

    # -- the bus --

    def _done(self, _bus, _message) -> None:
        """End of stream. Back to NULL so the next clip starts clean."""
        self.stop()

    def _failed(self, _bus, message) -> None:  # pragma: no cover - needs a bad file
        error, _debug = message.parse_error()
        log.warning("clip playback failed: %s", error)
        self.stop()


#: How a player is built. Injected by the tests, which is what makes the
#: activity's side of this provable with no audio device anywhere.
Factory = Callable[[], "ClipPlayer | None"]


def make_player(*, factory: Factory | None = None) -> ClipPlayer:
    """The best player this machine can offer. Never ``None``, never raises.

    ``factory`` is the test seam: anything returning a :class:`ClipPlayer` (or
    ``None`` for "I could not") is used in place of GStreamer.
    """
    if factory is not None:
        made = factory()
        return made if made is not None else NullClipPlayer("the factory declined")
    return _gst_player()


def _gst_player() -> ClipPlayer:
    """Try GStreamer. Every way it can be absent ends in a NullClipPlayer."""
    try:
        import gi

        gi.require_version("Gst", "1.0")
        from gi.repository import Gst
    except (ImportError, ValueError) as exc:
        return NullClipPlayer(f"GStreamer is not available: {exc}")
    try:
        if not Gst.is_initialized():
            Gst.init(None)
        # playbin3 where there is one; the older element is still what most of
        # the image's own media uses and it takes the same two properties.
        element = Gst.ElementFactory.make("playbin3", "kidnix-phoneme")
        if element is None:
            element = Gst.ElementFactory.make("playbin", "kidnix-phoneme")
        if element is None:
            return NullClipPlayer("GStreamer has no playbin element")
        return GstClipPlayer(element, Gst)
    except Exception as exc:  # pragma: no cover - a broken GStreamer install
        return NullClipPlayer(f"GStreamer would not start: {exc}")
