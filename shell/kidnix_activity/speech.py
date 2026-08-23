"""One voice, and it is the same voice.

08 section 3.6 is "one voice": everything kidnix says to a child sounds like
the same person, at the same rate, in en-GB, and a new sentence **cancels** the
old one rather than queueing behind it -- a pre-reader sweeping a screen must
never build up a backlog they have to wait out.

An activity gets that by using the shell's own
:class:`kidnix_shell.speech.SpeechManager` rather than opening its own
speech-dispatcher connection with its own settings. Same backends in the same
order (``speechd``, then ``spd-say``, then silence with one log line), same
queue policy, same highlight timing, same hover dwell and settle gate if the
activity wires its widgets up to it.

The one thing added here is the **caption**. ``SpeechManager.on_caption`` is
called with every line, before the "is speech even on?" check, so there is no
path through it that says something without showing it. In the shell that hook
draws the strip under the band; in an activity the strip belongs to another
process, so the hook is a datagram to it
(:mod:`kidnix_activity.captions`). If nothing is listening the child still
hears the sentence and the log says once that the caption did not land.

**The activity speaks; the shell shows.** The datagram is not a request to say
anything -- a shell that spoke it too would be two voices a beat apart, which
is worse than either alone. ``docs/design/activity-sdk.md`` section 4.2 states
that as the listener's contract.
"""

from __future__ import annotations

import logging
from collections.abc import Mapping
from pathlib import Path
from typing import TYPE_CHECKING

from kidnix_shell.access import AccessConfig
from kidnix_shell.speech import SpeechBackend, SpeechManager, select_backend

from .captions import CaptionClient

if TYPE_CHECKING:  # pragma: no cover - typing only, and importing it needs GTK
    from kidnix_shell.widgets import SpeechUI

log = logging.getLogger(__name__)

__all__ = ["ActivitySpeech"]


class ActivitySpeech:
    """The activity's read-aloud: speech-dispatcher plus the caption hook.

    Thin on purpose. Everything about *how* kidnix speaks lives in the shell's
    :class:`~kidnix_shell.speech.SpeechManager`; this class owns two decisions
    and no behaviour:

    1. which caption sink the manager's hook points at, and
    2. that an activity's voice obeys the same ``[access]`` settings the shell
       does -- calm slows it down, mute silences it, and captions carry on
       either way, which is the whole reason mute is safe to offer.
    """

    def __init__(
        self,
        activity_id: str,
        *,
        manager: SpeechManager | None = None,
        captions: CaptionClient | None = None,
        backend: SpeechBackend | None = None,
        access: AccessConfig | None = None,
        socket_path: Path | None = None,
        env: Mapping[str, str] | None = None,
    ) -> None:
        self.activity_id = activity_id
        self.captions = (
            captions if captions is not None else CaptionClient(activity_id, socket_path, env=env)
        )
        self.manager = (
            manager if manager is not None else SpeechManager(backend or select_backend())
        )
        # The hook, and the reason this class exists.
        self.manager.on_caption = self._on_caption
        #: **The one** widget bridge, set by
        #: :class:`kidnix_activity.app.ActivityApplication` once GTK is up.
        #: There can only be one: :class:`~kidnix_shell.widgets.SpeechUI` takes
        #: ownership of ``SpeechManager.on_highlight``, so a second one would
        #: quietly stop the first one's widgets from ever wearing the ring.
        #: ``None`` in a headless process, which is every test in this package.
        self.ui: SpeechUI | None = None
        self.access = access or AccessConfig()
        self.apply_access(self.access)

    # -- settings --

    def apply_access(self, access: AccessConfig) -> None:
        """Take the child's ``[access]``: calm rate, volume, mute.

        Mute silences the *voice* and not the caption: the caption hook is
        called before the manager's own enabled check, which is what makes a
        muted machine still usable rather than merely quiet.
        """
        self.access = access
        self.manager.set_rate(access.speech_rate)
        # ``set_volume`` owns ``enabled``: zero is silence, not a broken voice,
        # and setting the flag ourselves as well would only give the two a way
        # to disagree.
        self.manager.set_volume(access.effective_volume)

    # -- speaking --

    def speak(self, text: str) -> bool:
        """Say one line now, cancelling whatever was being said."""
        return self.manager.speak(text)

    def speak_then(self, first: str, second: str) -> bool:
        """Two sentences in a fixed order. No queue, and never a third."""
        return self.manager.speak_then(first, second)

    def repeat(self) -> bool:
        """Say the last line again -- what a :class:`Prompt`'s replay does."""
        return self.manager.repeat()

    def cancel(self) -> None:
        """Stop talking. A child who has moved on is not waiting for us."""
        self.manager.cancel()

    @property
    def last_utterance(self) -> str:
        """The last thing said, or ``""``. The test hook and the replay's text."""
        return self.manager.last_utterance

    def close(self) -> None:
        """Let go of the backend. Called on the way out; safe to call twice."""
        try:
            self.manager.close()
        except Exception as exc:  # pragma: no cover - a backend already gone
            log.debug("closing the speech backend: %s", exc)

    # -- the hook --

    def _on_caption(self, text: str) -> None:
        self.captions.send(text)
