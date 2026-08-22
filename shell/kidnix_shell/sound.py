"""Earcons (08 section 3.6).

The six-sound set is specified but not composed -- see ``data/sounds/README.md``
for why generated tones are worse than silence here. This module exists so the
call sites are in the code now and land the day the files do, and so the two
rules that matter are already enforced: at most one earcon per 250 ms, and
earcons duck under speech (they are simply skipped while the shell is talking).
"""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)

MIN_GAP_SECONDS = 0.25

FOCUS = "focus"
OPEN = "open"
BACK = "back"
KEEP = "keep"
ASK = "ask"
PHASE = "phase"


class Earcons:
    """Plays a short sound, or logs that it would have."""

    def __init__(self, directory: Path | None = None, enabled: bool = True) -> None:
        self.directory = directory or Path(__file__).parent / "data" / "sounds"
        self.enabled = enabled
        self._last = 0.0
        self._players: dict[str, Any] = {}
        self._warned = False

    def play(self, name: str, *, speaking: bool = False) -> bool:
        """Play ``name``. Returns whether a sound actually started."""
        if not self.enabled or speaking:
            return False
        now = time.monotonic()
        if now - self._last < MIN_GAP_SECONDS:
            return False
        path = self.directory / f"{name}.ogg"
        if not path.is_file():
            if not self._warned:
                log.debug("no earcons in %s yet; running silent", self.directory)
                self._warned = True
            return False
        self._last = now
        try:
            from gi.repository import Gtk

            player = self._players.get(name)
            if player is None:
                player = Gtk.MediaFile.new_for_filename(str(path))
                self._players[name] = player
            player.seek(0)
            player.play()
            return True
        except Exception as exc:  # pragma: no cover - audio is never fatal
            log.debug("earcon %s failed: %s", name, exc)
            return False
