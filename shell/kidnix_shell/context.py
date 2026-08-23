"""What every screen is handed.

Screens own layout and nothing else: they never touch the state machine, the
launcher or the session directly. They call the host, which is
:class:`kidnix_shell.app.ShellWindow`.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:  # pragma: no cover - typing only
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
