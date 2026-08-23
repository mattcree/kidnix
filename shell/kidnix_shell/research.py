"""``/etc/kidnix/research.toml`` -- the switch every instrument is behind.

kidnix carries instrumentation for its own child-test protocols: hover-speech
dwell logging (:mod:`kidnix_shell.speech`), grown-up-gate PIN attempts
(:mod:`kidnix_shell.screens.grownup`) and the burst-click detector below. The
safety and privacy review of 2026-08-23 was blunt about why none of that may be
the shipped default: *"the research default and the shipped default are the
same file, the child is not told, and a future 'delete everything' in the
Journal will not touch it."*

So this module is the gate, and it is deliberately **failure-closed**: a missing
file, an unreadable one, a malformed one, a key of the wrong type -- every one
of those means *off*. The only way any of it turns on is a person editing a
root-owned file whose first paragraph explains what they are turning on
(``docs/spikes/panel-wave-c.md`` section 6b).

``enabled`` is a master switch: with it false nothing is logged whatever the
individual keys say. That is why every predicate here is an ``and``.

Pure: no GTK, no I/O beyond one ``tomllib.load``, so the whole contract is a
headless test.
"""

from __future__ import annotations

import logging
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)

#: The file's name in either root-owned config directory.
RESEARCH_FILE = "research.toml"

#: ≥ 3 presses inside 1 s on something that is not a control. 06's child-test
#: method review (CCI #54) asked for this by name: "the burst-click detector
#: does not exist", and it is the one measurement that tells a rater whether a
#: child is *exploring* a screen or has stopped believing it will answer them.
BURST_PRESSES = 3
BURST_WINDOW_SECONDS = 1.0
#: The one line a burst emits. Counted by control-less presses and nothing else:
#: no coordinates, no screen contents, nothing the child made.
BURST_LOG_PREFIX = "burst-click"


@dataclass(frozen=True)
class ResearchConfig:
    """``[research]``. Every field ships false and defaults false."""

    enabled: bool = False
    hover_instrumentation: bool = False
    hover_record_selection: bool = False
    pin_attempt_logging: bool = False
    burst_click_detection: bool = False
    #: Where a study's data may be written. Empty means "nowhere", which is the
    #: shipped value; the shell logs to the journal and writes no file of its
    #: own, so today this is documentation of intent rather than a path.
    journal_path: str = ""

    @property
    def hover_logging(self) -> bool:
        """May :mod:`kidnix_shell.speech` emit its per-utterance line?"""
        return self.enabled and self.hover_instrumentation

    @property
    def hover_selection(self) -> bool:
        """May that line carry ``selected=``?

        Separate from the line itself, and the separation is the point:
        dwell-without-outcome measures whether a screen is legible;
        dwell-with-outcome is a behavioural model of one child.
        """
        return self.hover_logging and self.hover_record_selection

    @property
    def pin_logging(self) -> bool:
        """May the grown-up gate log that a PIN was tried?"""
        return self.enabled and self.pin_attempt_logging

    @property
    def burst_logging(self) -> bool:
        """May the burst-click detector emit a line?

        Gated on ``enabled`` alone when the specific key is absent, because a
        study that turned instrumentation on wants the detector the method
        section asks for; a household that did not gets nothing either way.
        """
        return self.enabled and self.burst_click_detection


def parse_research(raw: Any, source: str = RESEARCH_FILE) -> ResearchConfig:
    """``[research]`` out of already-parsed TOML. Anything odd means off."""
    if raw is None:
        return ResearchConfig()
    if not isinstance(raw, dict):
        log.warning("%s: [research] must be a table; instrumentation stays off", source)
        return ResearchConfig()

    def flag(key: str, fallback: bool = False) -> bool:
        value = raw.get(key, fallback)
        if not isinstance(value, bool):
            if value is not None:
                log.warning("%s: research.%s must be true or false; using false", source, key)
            return False
        return value

    path = raw.get("journal_path", "")
    if not isinstance(path, str):
        log.warning("%s: research.journal_path must be a string; ignoring it", source)
        path = ""

    enabled = flag("enabled")
    return ResearchConfig(
        enabled=enabled,
        hover_instrumentation=flag("hover_instrumentation"),
        hover_record_selection=flag("hover_record_selection"),
        pin_attempt_logging=flag("pin_attempt_logging"),
        # Absent means "whatever the master switch says": the detector was
        # specified after the file was written, and a study that enabled
        # instrumentation asked for the method section's measurements.
        burst_click_detection=flag("burst_click_detection", enabled),
        journal_path=path.strip(),
    )


def load_research(path: Path | None) -> ResearchConfig:
    """Read ``research.toml``. Every failure is silence, not an exception."""
    if path is None or not path.is_file():
        return ResearchConfig()
    try:
        with path.open("rb") as handle:
            data = tomllib.load(handle)
    except (OSError, tomllib.TOMLDecodeError) as exc:
        log.warning("%s is unreadable (%s); instrumentation stays off", path, exc)
        return ResearchConfig()
    config = parse_research(data.get("research"), str(path))
    if config.enabled:
        # Loud, once, on the machine it is happening on. A study is a thing
        # somebody switched on and should be able to see they switched on.
        log.warning(
            "RESEARCH INSTRUMENTATION IS ON (%s): hover=%s selection=%s pin=%s burst=%s",
            path,
            config.hover_logging,
            config.hover_selection,
            config.pin_logging,
            config.burst_logging,
        )
    else:
        log.info("research instrumentation is off (%s)", path or "no research.toml")
    return config


def discover() -> ResearchConfig:
    """The root-owned ``research.toml``, or the off defaults.

    Read from the same root-owned search path as ``parent.toml`` and **never**
    from the child's own directories: a file the child could write is a file
    that could turn logging on.
    """
    from .settings import first_system_config

    return load_research(first_system_config(RESEARCH_FILE))


class BurstDetector:
    """Counts rapid presses that landed on nothing. Pure; the clock is injected.

    A five-year-old who presses the same empty patch of screen four times in a
    second has told a rater something a screenshot cannot: they expected
    something to happen there. That is the measurement CCI #54 asked for, and it
    is *one line per burst* -- not one per press, and nothing about where.

    It is deliberately blind to presses that hit a control: those already have
    their own meaning, and counting them would turn this into a keystroke log.
    """

    def __init__(
        self,
        presses: int = BURST_PRESSES,
        window_seconds: float = BURST_WINDOW_SECONDS,
        research: ResearchConfig | None = None,
    ) -> None:
        self.presses = max(2, presses)
        self.window_seconds = window_seconds
        self.research = research or ResearchConfig()
        self._times: list[float] = []
        #: How many bursts this session has seen. Not written anywhere.
        self.bursts = 0

    def press(self, now: float, *, on_target: bool = False) -> bool:
        """Record one press. Returns True on the press that completes a burst.

        A press that hit a control clears the run: the child found something.
        """
        if on_target:
            self._times.clear()
            return False
        cutoff = now - self.window_seconds
        self._times = [t for t in self._times if t >= cutoff]
        self._times.append(now)
        if len(self._times) < self.presses:
            return False
        count = len(self._times)
        # Cleared, so one burst is one line however long the drumming goes on.
        self._times.clear()
        self.bursts += 1
        if self.research.burst_logging:
            log.info("%s: presses=%d window_ms=%d", BURST_LOG_PREFIX, count, self.window_ms)
        return True

    @property
    def window_ms(self) -> int:
        return int(self.window_seconds * 1000)

    def reset(self) -> None:
        self._times.clear()
