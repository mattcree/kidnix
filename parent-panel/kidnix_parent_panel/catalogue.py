"""What activities this machine actually has. Read-only, and its own reader.

The Activities tab is a list of the things a parent can tick, and it has to
show what the child sees: the **depictive icon** (not a vendor logo -- the
panel review's blocker was five tiles carrying two pictures between them) and
the manifest's own ``goal`` line, which is the one sentence in the whole schema
written for a grown-up.

This module deliberately does **not** import ``kidnix_shell.activities``.
That module's parser raises on a malformed manifest, resolves ``~`` against the
child's home, and reaches for GTK-adjacent things; the panel needs none of it
and must not fail to open because one manifest on the machine is broken. So
this is a small tolerant reader over the same TOML, and the fields it reads are
a strict subset of the documented schema
(``docs/spikes/activities-packaging.md`` §5).

Shelf children are included, because "Letters and numbers" is one tile on Home
and eighteen decisions underneath it, and a parent who wants to remove
*Ballcatch* and keep the rest has nowhere else to do that.
"""

from __future__ import annotations

import logging
import tomllib
from dataclasses import dataclass, field
from importlib.util import find_spec
from pathlib import Path

log = logging.getLogger(__name__)

SYSTEM_ACTIVITY_DIR = Path("/usr/share/kidnix/activities")

#: What the shell falls back to when a manifest's icon is not in the theme.
#: Mirrors ``kidnix_shell.widgets.category_icon`` so the panel and Home agree
#: about which picture a tile has.
CATEGORY_ICONS = {"make": "kidnix-make", "learn": "kidnix-learn", "play": "kidnix-play"}

CATEGORY_LABELS = {
    "make": "Making",
    "learn": "Learning",
    "play": "Playing",
}


@dataclass(frozen=True)
class Entry:
    """One tickable thing: an activity, a shelf, or a shelf's child."""

    id: str
    name: str
    goal: str = ""
    audio_label: str = ""
    icon: str = ""
    icon_kind: str = "icon-name"
    category: str = "play"
    age_min: int = 0
    age_max: int = 99
    order: int = 100
    kind: str = "activity"
    #: For a shelf child: the id of the shelf it hangs under. Empty otherwise.
    parent_id: str = ""
    #: For a shelf child: which heading of that shelf it sits under.
    group_name: str = ""
    #: True when a grown-up has to add content before the tile exists at all
    #: (Kiwix and its ZIM files). Shown as a note, never as a broken tile.
    content_required: bool = False
    path: Path | None = None

    @property
    def is_shelf(self) -> bool:
        return self.kind == "shelf"

    @property
    def is_shelf_child(self) -> bool:
        return bool(self.parent_id)

    @property
    def age_band_label(self) -> str:
        return f"{self.age_min} to {self.age_max}"

    def suits(self, band: tuple[int, int] | None) -> bool:
        """Does this overlap a child's age band?

        The same rule as ``kidnix_shell.activities.in_age_band``: an activity
        outside the band gets **no tile at all** rather than an outlined one,
        because there is nothing to ask a grown-up for. The panel greys the row
        and says which band it is for, so a parent can see why TuxMath is not on
        their four-year-old's list.
        """
        if band is None:
            return True
        low, high = band
        return self.age_min <= high and self.age_max >= low

    def category_label(self) -> str:
        return CATEGORY_LABELS.get(self.category, self.category.title())


@dataclass
class Catalogue:
    """Everything on the machine, in Home's own order."""

    entries: list[Entry] = field(default_factory=list)
    #: Manifests that would not parse. Shown as a note on the tab rather than
    #: swallowed: a parent whose machine has a broken manifest should be told
    #: which file, once, in the place where activities are listed.
    broken: list[tuple[Path, str]] = field(default_factory=list)

    @property
    def ids(self) -> frozenset[str]:
        return frozenset(e.id for e in self.entries)

    def top_level(self) -> list[Entry]:
        return [e for e in self.entries if not e.is_shelf_child]

    def children_of(self, shelf_id: str) -> list[Entry]:
        return [e for e in self.entries if e.parent_id == shelf_id]

    def get(self, entry_id: str) -> Entry | None:
        return next((e for e in self.entries if e.id == entry_id), None)


def parse_manifest(data: dict, path: Path, parent_id: str = "") -> Entry | None:
    """One manifest to an :class:`Entry`, or ``None`` with a warning.

    The only hard requirements are ``id`` and ``name``: without an id there is
    nothing to put in an allow-list, and without a name there is nothing to
    show. Everything else has a default, because a parent's list of tick-boxes
    is not the place to enforce the build's schema -- ``kidnix-activity
    validate`` and ``50-activities.sh`` already do that, at build time, where a
    failure can be fixed.
    """
    identifier = str(data.get("id", "")).strip()
    name = str(data.get("name", "")).strip()
    if not identifier or not name:
        return None
    kind = str(data.get("kind", "activity")).strip() or "activity"
    return Entry(
        id=identifier,
        name=name,
        goal=str(data.get("goal", "")).strip(),
        audio_label=str(data.get("audio_label", "")).strip(),
        icon=str(data.get("icon", "")).strip(),
        icon_kind=str(data.get("icon_kind", "icon-name")).strip() or "icon-name",
        category=str(data.get("category", "play")).strip() or "play",
        age_min=_int(data.get("age_min"), 0),
        age_max=_int(data.get("age_max"), 99),
        order=_int(data.get("order"), 100),
        kind=kind,
        parent_id=parent_id,
        group_name=str(data.get("shelf_group_name", "")).strip(),
        content_required=bool(data.get("content_required", False)),
        path=path,
    )


def load(directory: Path = SYSTEM_ACTIVITY_DIR) -> Catalogue:
    """Every manifest in ``directory``, plus every shelf's children.

    Never raises. A machine with no activity directory at all loads as an empty
    catalogue, which the Activities tab renders as one sentence rather than as
    a traceback -- that is the state a developer running the panel on their own
    laptop is in, and it must not look like a fault.
    """
    catalogue = Catalogue()
    if not directory.is_dir():
        log.info("no activity manifests in %s", directory)
        return catalogue

    for path in sorted(directory.glob("*.toml")):
        entry = _read(path, catalogue)
        if entry is None:
            continue
        catalogue.entries.append(entry)
        if entry.is_shelf:
            catalogue.entries.extend(_load_shelf_children(path, entry, catalogue))

    catalogue.entries.sort(key=lambda e: (e.parent_id, e.order, e.name.lower()))
    return catalogue


def _load_shelf_children(shelf_path: Path, shelf: Entry, catalogue: Catalogue) -> list[Entry]:
    """A shelf's children live in a SUBdirectory, so they cannot leak onto Home.

    Which is also why they are not found by the ``*.toml`` sweep above and have
    to be asked for by name, exactly as ``60-shell.sh`` validates them
    separately.
    """
    raw = _read_raw(shelf_path)
    children_dir = str(raw.get("children_dir", "")).strip() if raw else ""
    if not children_dir:
        return []
    folder = shelf_path.parent / children_dir
    if not folder.is_dir():
        log.info("shelf %r has no children directory at %s", shelf.id, folder)
        return []
    out: list[Entry] = []
    for path in sorted(folder.glob("*.toml")):
        entry = _read(path, catalogue, parent_id=shelf.id)
        if entry is not None:
            out.append(entry)
    return out


def _read(path: Path, catalogue: Catalogue, parent_id: str = "") -> Entry | None:
    raw = _read_raw(path, catalogue)
    if raw is None:
        return None
    entry = parse_manifest(raw, path, parent_id)
    if entry is None:
        catalogue.broken.append((path, "no id or no name"))
    return entry


def _read_raw(path: Path, catalogue: Catalogue | None = None) -> dict | None:
    try:
        with path.open("rb") as handle:
            return tomllib.load(handle)
    except (OSError, tomllib.TOMLDecodeError) as exc:
        log.warning("activity manifest %s is unreadable (%s)", path, exc)
        if catalogue is not None:
            catalogue.broken.append((path, str(exc)))
        return None


def _int(value: object, fallback: int) -> int:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return fallback
    return int(value)


# --- icons ----------------------------------------------------------------


def shell_icon_dir() -> Path | None:
    """Where ``kidnix_shell``'s own drawn icons are, if the shell is installed.

    Found through ``importlib`` rather than a hard path so the panel picks them
    up from ``/usr/lib/python3.N/site-packages`` on the image and from the
    source tree in a developer's checkout, and **without importing the shell**:
    ``kidnix_shell.widgets`` pulls in GTK, and the panel resolves icon paths in
    places where a display may not exist yet.
    """
    spec = find_spec("kidnix_shell")
    if spec is None or not spec.origin:
        return None
    candidate = Path(spec.origin).parent / "data" / "icons"
    return candidate if candidate.is_dir() else None


def icon_path(entry: Entry) -> Path | None:
    """The depictive picture for this row, or ``None`` for a theme lookup.

    Order matches the shell's: a manifest ``path`` icon, then one of the
    shell's own drawings by name, then the category fallback (a pencil, a book
    or a ball). The last of those is what the review called "five tiles
    carrying two pictures between them" -- it is still the fallback, but every
    shipped manifest now names a drawing of its own, and the panel showing the
    same picture is how a parent can tell.
    """
    if entry.icon_kind == "path" and entry.icon:
        candidate = Path(entry.icon)
        return candidate if candidate.is_file() else None
    folder = shell_icon_dir()
    if folder is None:
        return None
    for name in (entry.icon, CATEGORY_ICONS.get(entry.category, "kidnix-play")):
        if not name:
            continue
        candidate = folder / f"{name}.svg"
        if candidate.is_file():
            return candidate
    return None


__all__ = [
    "CATEGORY_ICONS",
    "CATEGORY_LABELS",
    "SYSTEM_ACTIVITY_DIR",
    "Catalogue",
    "Entry",
    "icon_path",
    "load",
    "parse_manifest",
    "shell_icon_dir",
]
