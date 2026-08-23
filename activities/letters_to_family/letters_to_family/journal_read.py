"""Reading the child's own Journal: what to send, and what came back.

The SDK writes entries (``kidnix_activity.journal.save_entry``) and the shell
reads them (``kidnix_shell.journal.Journal``); nothing in the SDK *reads* them,
because until now no activity needed to. This activity does, twice:

1. **Something to send.** The strongest version of "make a letter" is not "draw
   something new right now", it is **send the dinosaur you were proud of on
   Tuesday**, and that lives in the Journal (:func:`recent_pictures`).
2. **The letters that came back.** Since 2026-08-24 the "Letters for you" shelf
   reads this child's imported replies from the Journal rather than the inbox
   -- ``docs/design/letters-to-family.md`` section 7 step 5, and the reason is
   that "already seen" is a fact only the shell has. The inbox is a grown-up's
   drop point; the shell sweeps it once a sitting and writes a card per reply,
   and a shelf that read the folder instead showed every letter forever
   (:func:`letter_replies`, :func:`shelf_replies`).

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
* **Pictures only, to send.** ``mime`` starting ``image/``, with a version file
  that is really there. A letter cannot send a tune. (A reply that *came back*
  may be a voice or a few words; that is the other direction, and
  :func:`read_reply` reads it from ``meta.json``.)
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
from typing import Any

from .i18n import N_, _
from .letter import SOMEONE
from .mailbox import Reply, inbox_replies

log = logging.getLogger(__name__)

__all__ = [
    "CAPTION_FILE",
    "ENTRY_FILE",
    "ENTRY_GLOB",
    "META_FILE",
    "REPLY_KIND",
    "SHELF_LIMIT",
    "SOMETHING_I_MADE",
    "THUMB_NAME",
    "VOICE_FILE",
    "JournalPicture",
    "letter_replies",
    "read_entry",
    "read_reply",
    "recent_pictures",
    "shelf_replies",
]

ENTRY_FILE = "entry.json"
THUMB_NAME = "thumb.png"
#: The rest of a reply's entry, written by ``kidnix_shell.inbox`` when it
#: imported it: ``meta.json`` says what the entry *is* and who it is from,
#: ``caption.txt`` holds the sender's words verbatim, and ``note.ogg`` is the
#: name the whole product uses for a voice beside a card.
META_FILE = "meta.json"
CAPTION_FILE = "caption.txt"
VOICE_FILE = "note.ogg"
#: ``meta.json``'s ``kind`` for a reply. One vocabulary, spelled the way
#: ``kidnix_shell.inbox.KIND`` and section 7 of the design note spell it; a
#: second spelling would be a second bug.
REPLY_KIND = "letter-reply"
#: How many letters the shelf shows. The same cap the sweep uses: a household
#: that dropped forty files in must not spend a child's afternoon on them.
SHELF_LIMIT = 8
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


# -- the letters that came back ----------------------------------------------
#
# `docs/design/letters-to-family.md` section 7 step 5, landed 2026-08-24:
# **this activity's shelf reads the Journal, not the inbox.** The shell sweeps
# the inbox once a sitting and writes one card per reply; reading those cards
# is what makes a reply the child has already met stop coming back forever,
# because "already imported" is a fact the shell records and the inbox cannot.
#
# The layout, exactly as `kidnix_shell.inbox` writes it (section 7 step 2)::
#
#     <journal>/YYYY/MM/DD/<entry-id>/
#         entry.json    id, title, mime, created, versions
#         meta.json     {"kind": "letter-reply", "from": ..., "source": ...}
#         v001.png      the picture, when the reply was one
#         thumb.png     the 256 px card: the picture scaled, or a drawn envelope
#         caption.txt   the sender's words, verbatim
#         note.ogg      the sender's voice
#
# Read-only, like everything else in this module: no writer, no mkdir, no
# rename. Marking a reply read is the shell's, and the shell does it by having
# imported it.


def _read_json(path: Path) -> dict[str, Any]:
    """One JSON object, or ``{}``. A broken file is one fewer letter, not a crash."""
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        log.debug("skipping %s (%s)", path, exc)
        return {}
    return document if isinstance(document, dict) else {}


def _read_text(path: Path) -> str:
    """A whole text file, stripped at the ends and **not otherwise touched**.

    A grown-up's spelling is not corrected on the way out any more than it was
    on the way in (``kidnix_shell.inbox._finish``).
    """
    try:
        return path.read_text(encoding="utf-8", errors="replace").strip()
    except OSError:
        return ""


def _string(value: Any) -> str:
    return " ".join(value.split()) if isinstance(value, str) else ""


def _when(created: str, directory: Path) -> float:
    """When this letter arrived, as one number the inbox can be sorted against.

    ``created`` is the moment the shell imported it, which is the moment the
    letter arrived *in the child's world* -- the shell dates entries now and
    not ``sent_at`` for exactly that reason. An entry with no readable date
    falls back to the folder's own mtime rather than to zero, so a broken
    ``created`` costs a letter its place in the order and not its place on the
    shelf.
    """
    stamp = _parse_created(created)
    if stamp is not datetime.min:
        try:
            return stamp.timestamp()
        except (OSError, OverflowError, ValueError):  # pragma: no cover - a date from 1601
            pass
    try:
        return directory.stat().st_mtime
    except OSError:  # pragma: no cover - a folder that vanished mid-read
        return 0.0


def _version_file(directory: Path, document: dict[str, Any]) -> Path | None:
    """The current version's file, if it is really on disk."""
    versions = document.get("versions")
    if not isinstance(versions, list) or not versions:
        return None
    latest = versions[-1]
    if not isinstance(latest, dict):
        return None
    filename = str(latest.get("filename", "")).strip()
    if not filename or "/" in filename or filename.startswith("."):
        return None
    candidate = directory / filename
    return candidate if candidate.is_file() else None


def read_reply(entry_json: Path) -> Reply | None:
    """One ``entry.json`` -> the letter it holds, or ``None`` if it is not one.

    ``meta.json``'s ``kind`` is the whole test: every other card in the child's
    Journal is something *they* made, and a drawing must never turn up on
    "Letters for you". A reply whose ``meta.json`` is missing or unreadable is
    therefore not a reply here -- it is still in My Things, where the shell put
    it, which is the safe way round for a file we cannot identify.
    """
    directory = entry_json.parent
    meta = _read_json(directory / META_FILE)
    if _string(meta.get("kind")) != REPLY_KIND:
        return None
    document = _read_json(entry_json)

    picture: Path | None = None
    if str(document.get("mime", "")).startswith("image/"):
        picture = _version_file(directory, document)
    voice = directory / VOICE_FILE
    thumb = directory / THUMB_NAME

    # The words are `caption.txt` first, because that is the file the design
    # note names and the one a grown-up would edit; `meta.json` carries the
    # same string and is the fallback for an entry whose caption went missing.
    words = _read_text(directory / CAPTION_FILE) or _string(meta.get("caption"))

    return Reply(
        path=directory,
        from_name=_string(meta.get("from")) or _(SOMEONE),
        picture=picture,
        voice=voice if voice.is_file() else None,
        words=words,
        modified=_when(str(document.get("created", "")), directory),
        source=_string(meta.get("source")),
        thumb=thumb if thumb.is_file() else None,
    )


def letter_replies(journal_root: Path, limit: int = SHELF_LIMIT) -> list[Reply]:
    """This child's imported letters, newest first. Never raises, never writes.

    ``journal_root`` is already one child's (``LaunchEnv.journal_root`` is
    ``.../profiles/<id>/journal``), which is what keeps one child's letters out
    of another's shelf without this module knowing anything about profiles.
    """
    try:
        candidates = sorted(journal_root.glob(ENTRY_GLOB))
    except OSError as exc:  # pragma: no cover - an unreadable journal root
        log.warning("could not read the journal at %s (%s)", journal_root, exc)
        return []

    found: list[Reply] = []
    for entry_json in candidates:
        reply = read_reply(entry_json)
        if reply is not None:
            found.append(reply)
    found.sort(key=lambda item: (-item.modified, item.path.name))
    return found[: max(0, limit)]


def shelf_replies(
    journal_root: Path,
    profile_id: str,
    inbox_root: Path | None = None,
    limit: int = SHELF_LIMIT,
) -> list[Reply]:
    """What "Letters for you" shows: the Journal, and anything not yet in it.

    The Journal is the source. The inbox is read afterwards **only** as the
    fallback for a reply that has not been swept yet -- a grown-up who drops a
    folder in while the child is sitting at the machine, or a machine where the
    shell has not started a session since it arrived. Without that, a letter
    could be on disk and invisible until the next login, which is a worse
    failure than showing it twice.

    So it is deduped by where the reply came from: ``meta.json``'s ``source``
    is the inbox path the shell imported, and an inbox reply whose path is one
    of those is the same letter and is dropped. The Journal's copy wins,
    because it is the one that carries the card and the sender's name.
    """
    kept = letter_replies(journal_root, limit=limit)
    imported = {reply.source for reply in kept if reply.source}
    kept.extend(
        reply
        for reply in inbox_replies(profile_id, inbox_root, limit=limit)
        if str(reply.path) not in imported
    )
    kept.sort(key=lambda item: (-item.modified, item.path.name))
    return kept[: max(0, limit)]
