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
    from .session import Session
    from .settings import ParentConfig, Paths, Profile
    from .sound import Earcons
    from .speech import SpeechManager
    from .widgets import SpeechUI


class ShellHost(Protocol):
    """Everything a screen may ask the shell to do."""

    def choose_profile(self, profile: Profile) -> None: ...

    def launch(self, activity: Activity, resume: Path | None = None) -> None: ...

    def resume_entry(self, entry: Entry) -> None: ...

    def go_home(self) -> None: ...

    def open_journal(self) -> None: ...

    def open_grownup(self) -> None: ...

    def close_grownup(self) -> None: ...

    def dismiss_offer(self, one_last_thing: bool) -> None: ...

    def finish_now(self) -> None: ...

    def show_a_grownup(self) -> None: ...

    def goodnight(self) -> None: ...

    def start_session(self, minutes: int | None = None) -> None: ...

    def add_minutes(self, minutes: int) -> None: ...

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
    demo: bool = False
