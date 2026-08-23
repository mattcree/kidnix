"""Reading the child's own Journal, so a letter can send something they made.

The SDK writes entries (``kidnix_activity.journal.save_entry``) and the shell
reads them (``kidnix_shell.journal.Journal``); nothing in the SDK *reads* them,
because until now no activity needed to. This activity does: the strongest
version of "make a letter" is not "draw something new right now", it is **send
the dinosaur you were proud of on Tuesday**, and that lives in the Journal.

So this is the minimal reader, and it is minimal on purpose:

* **Read-only.** There is no writer in this module, no ``mkdir``, no ``open``
  for writing, and no code path that could rename, star or delete an entry. The
  child's Journal is the shell's, and a second writer with a slightly different
  idea of the layout is how it gets corrupted.
* **Copies, never links.** The caller copies the picture into the letter's own
  scratch directory before anything else touches it. A letter that pointed at a
  Journal file would break the day the shell rewrote that entry.
* **stdlib only.** ``json`` and ``pathlib``, and the layout is read from
  ``entry.json`` directly rather than through ``kidnix_shell.journal.Entry``.
  That is not a copy of the shell's parser -- it reads four keys out of nine and
  ignores the rest -- and it means this module is importable and fully tested on
  a machine with no shell installed at all, which is where the headless CI floor
  runs.
* **Pictures only.** ``mime`` starting ``image/``, with a version file that is
  really there. A letter cannot send a tune.
* **Broken entries are skipped, silently to the child.** A half-written
  ``entry.json`` from a power cut is one fewer picture to choose from, not a
  traceback in front of a five-year-old.

The layout it reads (spec section 5, and ``docs/design/activity-sdk.md``
section 8)::

    <journal>/YYYY/MM/DD/<entry-id>/
        entry.json    {"id", "title", "mime", "created", "versions": [...]}
        v001.png      the picture; the *last* version is the current one
        thumb.png     256 px, if the shell or the SDK made one
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from .i18n import N_, _

log = logging.getLogger(__name__)

__all__ = [
    "ENTRY_FILE",
    "ENTRY_GLOB",
    "SOMETHING_I_MADE",
    "THUMB_NAME",
    "JournalPicture",
    "read_entry",
    "recent_pictures",
]

ENTRY_FILE = "entry.json"
THUMB_NAME = "thumb.png"
#: What a picture with no caption is called out loud. A card in My Things
#: always has *something* to say, because a tile a pre-reader cannot hear is a
#: tile they cannot use.
SOMETHING_I_MADE = N_("A thing I made")
#: The shell's own four-level glob. ``.incoming`` is two levels deep, where this
#: cannot reach, which is exactly why the SDK assembles entries there.
ENTRY_GLOB = "*/*/*/*/" + ENTRY_FILE

#: How many recent pictures a child is offered. Four, because B2 caps a choice
#: screen at five and the fifth control on that row is "draw a new one" -- and
#: because a pre-reader picking between eight thumbnails of their own drawings
#: is doing visual search, not choosing.
DEFAULT_LIMIT = 4


@dataclass(frozen=True)
class JournalPicture:
    """One picture the child made, offered as something to send."""

    entry_id: str
    title: str
    picture: Path
    thumb: Path | None
    created: datetime
    activity_id: str = ""

    @property
    def tile_image(self) -> Path:
        """What to show on the tile: the thumbnail if there is one.

        The thumbnail is 256 px and the picture may be a 4K canvas; a row of
        four full-size PNGs decoded into a 30 mm tile is a visible pause on the
        machine we target, and the pause lands exactly where a child is
        choosing.
        """
        return self.thumb if self.thumb is not None else self.picture

    @property
    def speak_text(self) -> str:
        """The tile's spoken label: what the child called it.

        No date and no time -- "the dinosaur", not "the dinosaur from Tuesday".
        The shell's own My Things says the "when" because a shelf of forty
        cards needs it; a row of four does not, and every word saved is one a
        five-year-old does not have to sit through before pressing.
        """
        return self.title or _(SOMETHING_I_MADE)


def _parse_created(raw: str) -> datetime:
    try:
        return datetime.fromisoformat(raw)
    except (TypeError, ValueError):
        return datetime.min


def read_entry(entry_json: Path) -> JournalPicture | None:
    """One ``entry.json`` -> a picture, or ``None`` if it is not one.

    ``None`` covers: unreadable, not JSON, not a mapping, not an image, no
    versions, and a version file that is not on disk. Every one of them is a
    picture the child simply is not offered.
    """
    try:
        document = json.loads(entry_json.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        log.debug("skipping %s (%s)", entry_json, exc)
        return None
    if not isinstance(document, dict):
        return None

    mime = str(document.get("mime", ""))
    if not mime.startswith("image/"):
        return None

    versions = document.get("versions")
    if not isinstance(versions, list) or not versions:
        return None
    latest = versions[-1]
    if not isinstance(latest, dict):
        return None
    filename = str(latest.get("filename", "")).strip()
    if not filename or "/" in filename or filename.startswith("."):
        return None

    directory = entry_json.parent
    picture = directory / filename
    if not picture.is_file():
        return None
    thumb = directory / THUMB_NAME

    return JournalPicture(
        entry_id=str(document.get("id", directory.name)),
        title=str(document.get("title", "")).strip(),
        picture=picture,
        thumb=thumb if thumb.is_file() else None,
        created=_parse_created(str(document.get("created", ""))),
        activity_id=str(document.get("activity_id", "")),
    )


def recent_pictures(journal_root: Path, limit: int = DEFAULT_LIMIT) -> list[JournalPicture]:
    """The child's most recent pictures, newest first. Never raises, never writes.

    A journal that does not exist yet -- a brand-new profile, a developer's
    machine -- comes back empty, and the activity offers "draw one" instead,
    which is a complete flow on its own.
    """
    try:
        candidates = sorted(journal_root.glob(ENTRY_GLOB))
    except OSError as exc:  # pragma: no cover - an unreadable journal root
        log.warning("could not read the journal at %s (%s)", journal_root, exc)
        return []

    found: list[JournalPicture] = []
    for entry_json in candidates:
        picture = read_entry(entry_json)
        if picture is not None:
            found.append(picture)
    found.sort(key=lambda item: (item.created, item.entry_id), reverse=True)
    return found[: max(0, limit)]
