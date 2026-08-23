"""What every screen is handed.

Screens own layout and nothing else: they never touch the state machine, the
launcher or the session directly. They call the host, which is
:class:`kidnix_shell.app.ShellWindow`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Protocol

from .research import ResearchConfig
from .voice import VoiceNote

if TYPE_CHECKING:  # pragma: no cover - typing only
    from .access import AccessConfig
    from .activities import Activity
    from .journal import Entry, Journal
    from .metrics import Metrics
    from .next_after import NextAfter
    from .ritual import OfferAnswer
    from .session import Session
    from .settings import KidState, ParentConfig, Paths, Profile
    from .sound import Earcons
    from .speech import SpeechManager
    from .widgets import SpeechUI


class ShellHost(Protocol):
    """Everything a screen may ask the shell to do."""

    def choose_profile(self, profile: Profile) -> None: ...

    def choose_next_after(self, option: NextAfter) -> None: ...

    def launch(self, activity: Activity, resume: Path | None = None) -> None: ...

    def open_shelf(self, shelf: Activity) -> None: ...

    def resume_entry(self, entry: Entry) -> None: ...

    def go_home(self) -> None: ...

    def open_journal(self) -> None: ...

    def open_grownup(self) -> None: ...

    def close_grownup(self) -> None: ...

    def dismiss_offer(self, answer: OfferAnswer) -> None: ...

    def finish_now(self) -> None: ...

    def show_a_grownup(self) -> None: ...

    def goodnight(self) -> None: ...

    def start_session(self, minutes: int | None = None) -> None: ...

    def add_minutes(self, minutes: int) -> int: ...

    def logout(self) -> None: ...

    def speak(self, text: str) -> None: ...

    def set_access(self, access: AccessConfig) -> None: ...


@dataclass
class ShellContext:
    """Immutable-ish handles the screens share."""

    metrics: Metrics
    speech: SpeechManager
    speech_ui: SpeechUI
    journal: Journal
    session: Session
    config: ParentConfig
    paths: Paths
    earcons: Earcons
    host: ShellHost
    activities: list[Activity]
    profile: Profile
    #: Counters that outlive a day. Today: how many sessions have finished,
    #: which is the clock progressive disclosure runs on (spec 7b).
    kid_state: KidState
    demo: bool = False
    #: ``[access] calm``, or the desktop's own ``gtk-enable-animations``.
    #: Screens read it instead of asking GTK, so a headless test can set it.
    #: WCAG 2.2 SC 2.3.3: interaction-triggered motion must be disableable.
    reduced_motion: bool = False
    #: **This sitting's state, not the config's.** What the child said they
    #: would do next on S1b, or ``None`` if they skipped it or were never
    #: asked. Set when they pick, cleared when a new session starts, and read
    #: by S7 -- which falls back to the generated suggestion when it is None.
    next_after: NextAfter | None = None
    #: **Set when Put away had to SIGKILL an activity at the hard stop.** The
    #: words the shell uses have to be true (spec 7c): a session that ended
    #: this way does not get "Let's keep that" on S6 and does not get the keep
    #: earcon or the fly-into-My-Things animation on either S6 or S7, because
    #: nothing flew anywhere. Cleared when a new session starts.
    work_lost: bool = False
    #: One sentence for the Resting screen to say *instead of* its own line,
    #: consumed on arrival. Set when the shell has just refused a session at
    #: "Who's here?" -- the child asked for a turn and is owed an answer to
    #: that, not a description of the machine's state (panel ruling,
    #: 2026-08-23; forum #46, #59).
    rest_reason: str = ""
    #: Shelf id to its children, loaded once at start-up
    #: (:func:`kidnix_shell.activities.resolve_shelves`). Home reads it to know
    #: whether a shelf has anything on it; the shelf screen reads it to draw
    #: the tiles. Empty on a machine with no shelves, which is every machine
    #: before the GCompris curation landed.
    shelves: dict[str, list[Activity]] = field(default_factory=dict)
    #: ``/etc/kidnix/research.toml``, which ships with everything false. The
    #: gate on hover-speech logging, PIN-attempt logging and the burst-click
    #: detector (:mod:`kidnix_shell.research`).
    research: ResearchConfig = field(default_factory=ResearchConfig)
    #: "Tell me about it" -- the 20 s recorder on S6 and on Journal cards, or
    #: ``None`` on a machine with no microphone, where the button is not drawn
    #: at all (:mod:`kidnix_shell.voice`).
    voice: VoiceNote | None = None
