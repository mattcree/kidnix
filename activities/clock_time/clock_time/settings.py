"""What the grown-up said: which year, and what this family's day looks like.

One file, root-owned, in the same place and with the same ownership rule as the
shell's ``parent.toml`` and Sounds & Words' ceiling
(:mod:`kidnix_shell.settings`, :mod:`sounds_and_words.settings`)::

    /etc/kidnix/clock_time.toml          the parent's copy
    /usr/share/kidnix/clock_time.toml    the image's default

``/etc`` first because bootc's three-way merge makes ``/etc`` theirs and
``/usr/share`` ours. Root-owned because the child owns ``$XDG_CONFIG_HOME``,
and a setting a child can edit is not a parent's setting -- the year band in
particular is a statement about *what the school has taught*, and nothing in
this activity is entitled to infer, advance or widen it.

The schema, in full::

    [clock]
    mode = "y1"                 # "y1" (default) or "y2"

    [[routine]]
    id = "tea"                  # a slug; also the picture's filename
    name = "Tea"                # what the family calls it
    time = "17:30"              # 24-hour, HH:MM
    picture = "tea"             # optional; defaults to id

**Nothing here ever raises.** A missing file, a malformed one, a typo in a
time, a routine with no items -- all of them come back as the defaults with a
line in the log. A five-year-old told the computer is broken because a grown-up
mistyped a TOML key has been failed twice.
"""

from __future__ import annotations

import logging
import tomllib
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path

from .routine import DEFAULT_ROUTINE, Routine, RoutineItem, parse_hhmm
from .words import Mode

log = logging.getLogger(__name__)

__all__ = [
    "CONFIG_NAME",
    "CONFIG_SEARCH_PATH",
    "MAX_ROUTINE_ITEMS",
    "ParentSettings",
    "config_candidates",
    "load_settings",
    "read_document",
    "settings_from_document",
]

#: The file the grown-up's answers land in.
CONFIG_NAME = "clock_time.toml"

#: Root-owned config, in the order it is read. A list rather than a tuple so a
#: test can point it somewhere writable; nothing derived from the child's own
#: environment is ever appended to it.
CONFIG_SEARCH_PATH: list[Path] = [Path("/etc/kidnix"), Path("/usr/share/kidnix")]

#: The brief asks for six to eight. Eight is the cap because a ninth tile takes
#: the strip below the 20 mm floor on the panel kidnix ships for (ADR-0011),
#: and a target that is under the floor is not a target. Extras are dropped
#: with a line in the log rather than silently squeezing the rest.
MAX_ROUTINE_ITEMS = 8


@dataclass(frozen=True)
class ParentSettings:
    """The two answers, and the file they came from.

    ``source`` is ``None`` when nobody has answered. That distinction is not
    cosmetic: a parent pane must be able to say *"nobody has told us, so we are
    starting at o'clock and half past"* rather than presenting kidnix's guess
    back to a parent as their own statement.
    """

    mode: Mode = Mode.Y1
    #: `default_factory` rather than `Routine(DEFAULT_ROUTINE)`: the value is
    #: immutable either way, but a call in a dataclass default is evaluated
    #: once at import and is the shape of a bug even when this one is not.
    routine: Routine = field(default_factory=Routine)
    source: Path | None = None

    @property
    def is_default(self) -> bool:
        return self.source is None

    def describe(self) -> str:
        """One line for the log at start-up, naming the file that decided it."""
        where = str(self.source) if self.source is not None else "(no config; defaults)"
        names = ", ".join(item.id for item in self.routine)
        return f"mode={self.mode.value} routine=[{names}] from {where}"


def config_candidates(name: str = CONFIG_NAME) -> list[Path]:
    """Every place the file may be written, in the order it is read."""
    return [directory / name for directory in CONFIG_SEARCH_PATH]


def read_document(path: Path) -> Mapping[str, object] | None:
    """Parse one TOML file. ``None`` on anything at all going wrong."""
    try:
        if not path.is_file():
            return None
        with path.open("rb") as handle:
            return tomllib.load(handle)
    except (OSError, tomllib.TOMLDecodeError) as exc:
        log.warning("could not read %s: %s; using the defaults", path, exc)
        return None


def settings_from_document(
    doc: Mapping[str, object], source: Path | None = None
) -> ParentSettings:
    """Turn a parsed file into settings, dropping whatever does not make sense.

    Partial credit, deliberately: a file with a good ``[clock]`` and one broken
    routine entry keeps the mode and keeps the seven good moments. An
    all-or-nothing reader would throw away a grown-up's whole afternoon over a
    missing colon.
    """
    section = doc.get("clock")
    raw_mode = section.get("mode") if isinstance(section, dict) else None
    raw = str(raw_mode).strip() if raw_mode is not None else ""
    mode = Mode.parse(raw)
    if raw and raw.lower().replace(" ", "").replace("year", "y") not in {m.value for m in Mode}:
        log.warning("clock.mode=%r is not \"y1\" or \"y2\"; using y1", raw)

    entries = doc.get("routine")
    items: list[RoutineItem] = []
    if entries is not None and not isinstance(entries, list):
        log.warning("routine must be a list of [[routine]] tables; using the default day")
        entries = None
    for index, entry in enumerate(entries or []):
        item = _item_from(entry, index)
        if item is not None:
            items.append(item)
    if entries and not items:
        log.warning("no usable [[routine]] entries; using the default day")
    if len(items) > MAX_ROUTINE_ITEMS:
        dropped = [item.id for item in items[MAX_ROUTINE_ITEMS:]]
        log.warning(
            "the strip holds %d moments; dropping %s", MAX_ROUTINE_ITEMS, ", ".join(dropped)
        )
        items = items[:MAX_ROUTINE_ITEMS]

    routine = Routine.of(items) if items else Routine(DEFAULT_ROUTINE)
    return ParentSettings(mode=mode, routine=routine, source=source)


def _item_from(entry: object, index: int) -> RoutineItem | None:
    if not isinstance(entry, dict):
        log.warning("routine entry %d is not a table; skipping it", index + 1)
        return None
    item_id = str(entry.get("id", "")).strip()
    name = str(entry.get("name", "")).strip()
    when = parse_hhmm(str(entry.get("time", "")))
    if not item_id:
        log.warning("routine entry %d has no id; skipping it", index + 1)
        return None
    if when is None:
        log.warning("routine %r has no readable time (want \"HH:MM\"); skipping it", item_id)
        return None
    picture = str(entry.get("picture", "")).strip() or item_id
    return RoutineItem(id=item_id, name=name or item_id.replace("_", " ").capitalize(),
                       at=when, picture=picture)


def load_settings(*, search: list[Path] | None = None, name: str = CONFIG_NAME) -> ParentSettings:
    """Read the first readable root-owned file, or hand back the defaults."""
    directories = CONFIG_SEARCH_PATH if search is None else search
    for path in (directory / name for directory in directories):
        doc = read_document(path)
        if doc is None:
            continue
        if not doc:
            # Every line of it is a comment. It parses to nothing, and nothing
            # is not an answer: `is_default` has to stay True so a parent pane
            # can say "nobody has told us yet" rather than handing kidnix's own
            # defaults back to a grown-up as their own statement. The image
            # ships exactly such a file -- system_files/etc/kidnix/clock_time.toml --
            # so this is the normal case on a machine nobody has configured,
            # not an edge one.
            log.info("%s sets nothing; using the built-in defaults", path)
            continue
        return settings_from_document(doc, source=path)
    return ParentSettings()
