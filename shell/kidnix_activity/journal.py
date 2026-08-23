"""Writing into the child's Journal, from the activity that made the thing.

The shell imports an activity's work by *watching* the directories the manifest
declares (``journal_watch``/``journal_glob``, inotify, debounced two seconds)
and copying whatever appears. That is the right contract for a program we did
not write -- Tux Paint knows nothing about kidnix and never will -- and the
wrong one for a program we did:

* the watcher has to **guess a title** from a filename, which is why
  ``friendly_title`` exists and why it has to reject anything that looks like a
  timestamp;
* there is no way to attach a **caption** or a **voice note**, because a file
  on disk carries neither;
* the entry appears **two seconds later**, so a child who presses "keep" and
  goes straight to My Things finds it empty;
* and every activity needs a scratch directory that exists only to be watched.

So a first-party activity writes the entry itself, and this is that. The layout
is the shell's, exactly (spec section 5) -- the same ``entry.json``, the same
``v001.png``, the same ``thumb.png`` -- because My Things reads it with the
shell's own loader and a second spelling would be a second bug::

    $XDG_DATA_HOME/kidnix/profiles/<profile>/journal/YYYY/MM/DD/<entry-id>/
        entry.json      the shell's Entry, written with the shell's dataclass
        v001.png        what the child made
        thumb.png       256 px, images only
        caption.txt     what they called it, if they said
        note.ogg        "tell me about it", if they recorded one
        meta.json       ours: the kind, and whatever the activity wants back

Four decisions worth stating, because each is a trap somebody would otherwise
fall into:

**``meta`` goes in its own file.** ``entry.json`` is written by
:class:`kidnix_shell.journal.Entry`, whose ``to_dict`` is ``asdict`` -- so any
key we added to it would be silently dropped the next time the shell rewrote
the entry, which it does every time a child stars something. ``meta.json`` is
ours and nothing else touches it.

**``source_path`` is empty.** The shell uses it to recognise a file it has
already imported; an SDK entry was never imported from anywhere, and pointing
it at a temporary file would make the importer's ``entry_for_source`` match a
path that will not exist tomorrow. Resume does not need it either -- the shell
resumes from ``entry.latest_path``, the copy inside the entry directory.

**The entry is assembled somewhere else and renamed into place.** ``Journal.
load()`` globs ``*/*/*/*/entry.json``, so a half-written entry directory sitting
in the day's folder is an entry the shell can find and fail to parse. Everything
is built under ``<journal>/.incoming/`` -- two levels deep, where that glob
cannot reach -- and moved with a single ``rename``, which within one filesystem
is atomic.

**Nothing is ever deleted** (SYNTHESIS C2). There is no ``delete_entry`` here
and there will not be one.
"""

from __future__ import annotations

import contextlib
import json
import logging
import os
import re
import shutil
from collections.abc import Callable, Mapping, Sequence
from datetime import datetime
from pathlib import Path
from typing import Any

from kidnix_shell.journal import (
    THUMB_NAME,
    Entry,
    Version,
    guess_mime,
    make_thumbnail,
    sha256_file,
)
from kidnix_shell.voice import NOTE_NAME

from .env import ACTIVITY_ID_VAR, LaunchEnv

log = logging.getLogger(__name__)

__all__ = [
    "CAPTION_NAME",
    "META_NAME",
    "JournalError",
    "save_entry",
    "title_for",
]

CAPTION_NAME = "caption.txt"
META_NAME = "meta.json"

#: Where an entry is assembled before it is moved into its day. Two levels
#: below the journal root, so ``Journal.load()``'s four-level glob cannot see
#: a half-written one.
INCOMING_DIR = ".incoming"

#: What an activity says the thing *is*: ``picture``, ``word``, ``letter``,
#: ``tune``. Free-form on purpose -- the suite is not finished and a closed
#: vocabulary would have to be edited by every new activity -- but a slug, so
#: it can be a directory name, a log field and a filter later without escaping.
KIND_RE = re.compile(r"^[a-z][a-z0-9-]{0,31}$")

#: The version of ``meta.json``'s own shape, so a later reader can tell.
META_SCHEMA = 1

#: A title longer than this is a sentence, and a sentence is what
#: ``caption.txt`` is for. Matches ``kidnix_shell.journal.friendly_title``.
MAX_TITLE_CHARS = 24

#: 01 #19 / 03 #32: the child never sees or hears a digit. A caption with a
#: timestamp in it does not become a title.
_MANY_DIGITS = re.compile(r"\d{4,}")

#: ``(source, destination) -> made_one``. Injected by the tests; defaults to
#: the shell's GdkPixbuf thumbnailer, so an activity and the importer produce
#: byte-identical thumbnails for the same file.
Thumbnailer = Callable[[Path, Path], bool]


class JournalError(RuntimeError):
    """The entry could not be written, and the caller has to know.

    Deliberately loud. Everything else in this SDK degrades quietly -- a dead
    speech-dispatcher, a missing caption socket, an unknown monitor -- because
    the child can carry on without it. Losing the thing they just made is the
    one failure that is not survivable, so it raises, the activity's own error
    path decides what to say, and the reason is in the parent's journal.
    """


def title_for(kind: str, caption: str | None, activity_name: str) -> str:
    """A title a six-year-old could read back. Never a path, never a clock.

    The caption wins when it is short enough to *be* a title; otherwise the
    activity's own name, which is the word the child pressed to get here. The
    same digit rule as the shell's importer: four consecutive digits is a
    timestamp somebody let through, not a name.
    """
    line = " ".join((caption or "").split())
    if line and len(line) <= MAX_TITLE_CHARS and not _MANY_DIGITS.search(line):
        return line[0].upper() + line[1:]
    name = " ".join((activity_name or "").split())
    if name:
        return name
    return kind.replace("-", " ").capitalize()


def save_entry(
    kind: str,
    files: Sequence[Path],
    caption: str | None = None,
    voice: Path | None = None,
    meta: Mapping[str, Any] | None = None,
    *,
    activity_id: str = "",
    activity_name: str = "",
    journal_root: Path | None = None,
    now: datetime | None = None,
    env: Mapping[str, str] | None = None,
    launch: LaunchEnv | None = None,
    thumbnailer: Thumbnailer | None = None,
) -> Entry:
    """Keep what the child just made. Returns the :class:`Entry` it wrote.

    ``kind``
        what the thing is, as a slug: ``picture``, ``word``, ``letter``.
    ``files``
        the file (or files) to keep, in the order they should be versioned.
        They are **copied**, never moved: the activity may still be using them.
        Open formats only -- that is a rule of the product (spec section 5),
        not something this function can check.
    ``caption``
        one line, in the child's words or the activity's. Written to
        ``caption.txt`` and, when it is short enough, used as the title.
    ``voice``
        a "tell me about it" recording, stored as ``note.ogg`` so the shell's
        own player finds it without being told.
    ``meta``
        anything the activity wants back when the child resumes this card. Must
        be JSON-serialisable; it is written to ``meta.json`` and never read by
        the shell.

    Everything else is normally left alone: the activity id, the profile and
    the journal root come from the launch environment
    (:class:`~kidnix_activity.env.LaunchEnv`). They are parameters so that a
    test never has to touch ``os.environ`` -- and so that ``--demo`` can point
    an activity at a scratch journal.

    Raises :class:`JournalError` when it cannot write the entry, which includes
    the case where nobody said which activity this is.
    """
    when = now or datetime.now()
    context = launch if launch is not None else LaunchEnv.from_env(env)

    kind = (kind or "").strip()
    if not KIND_RE.match(kind):
        raise JournalError(f"kind {kind!r} must be a lowercase slug, e.g. 'picture'")

    activity = (activity_id or context.activity_id).strip()
    if not activity:
        raise JournalError(
            f"no activity id: the shell exports {ACTIVITY_ID_VAR}, and an entry written "
            "without one would be a card in My Things that resumes nothing"
        )

    root = journal_root if journal_root is not None else context.journal_root

    keep = _existing(files)
    if not keep:
        raise JournalError("nothing to save: none of the files given exist")

    payload = _encode_meta(meta)

    try:
        digest = sha256_file(keep[0])
    except OSError as exc:
        raise JournalError(f"could not read {keep[0]}: {exc}") from exc

    incoming = _incoming_dir(root, activity, when)
    try:
        # The name is chosen *before* anything is copied, so ``entry.json`` is
        # written once, with the id the directory will really have.
        target = _reserve(root, activity, digest, when)
        entry = _assemble(
            incoming,
            entry_id=target.name,
            kind=kind,
            files=keep,
            caption=caption,
            voice=voice,
            meta_json=payload,
            activity_id=activity,
            activity_name=activity_name,
            when=when,
            thumbnailer=thumbnailer or make_thumbnail,
        )
        final = _place(incoming, target)
    except JournalError:
        _discard(incoming)
        raise
    except OSError as exc:
        _discard(incoming)
        raise JournalError(f"could not write the journal entry under {root}: {exc}") from exc

    entry.directory = final
    log.info("journal kept %s (%s) from %s", entry.id, kind, activity)
    return entry


# -- the pieces -------------------------------------------------------------


def _existing(files: Sequence[Path]) -> list[Path]:
    """The files that are really there, in the order given, without duplicates."""
    keep: list[Path] = []
    seen: set[Path] = set()
    for raw in files:
        path = Path(raw)
        try:
            if not path.is_file():
                log.warning("not keeping %s: it is not a file", path)
                continue
            resolved = path.resolve()
        except OSError as exc:  # pragma: no cover - a vanished mount
            log.warning("not keeping %s: %s", path, exc)
            continue
        if resolved in seen:
            continue
        seen.add(resolved)
        keep.append(path)
    return keep


def _encode_meta(meta: Mapping[str, Any] | None) -> dict[str, Any]:
    """Check ``meta`` round-trips through JSON *before* anything is copied.

    A save that got as far as copying the drawing and then died on an
    unserialisable value would leave the entry half-built, so the one thing
    that can fail on the caller's data fails first.
    """
    data = dict(meta or {})
    try:
        json.dumps(data)
    except (TypeError, ValueError) as exc:
        raise JournalError(f"meta must be JSON-serialisable: {exc}") from exc
    return data


def _incoming_dir(root: Path, activity: str, when: datetime) -> Path:
    """A private directory to build in. Unique per process and per moment."""
    stem = f"{activity}-{when:%Y%m%d%H%M%S}-{os.getpid()}"
    base = root / INCOMING_DIR
    candidate = base / stem
    suffix = 1
    while candidate.exists():
        suffix += 1
        candidate = base / f"{stem}-{suffix}"
    candidate.mkdir(parents=True)
    return candidate


def _reserve(root: Path, activity: str, digest: str, when: datetime) -> Path:
    """Pick the entry's final directory, in the shell's own spelling.

    ``<activity>-<HHMMSS>-<six of the digest>`` is exactly what
    :meth:`kidnix_shell.journal.Journal._create_entry` produces, so a parent
    browsing the directory tree cannot tell which route an entry came in by --
    and neither can anything that has to sort them.
    """
    day = root / f"{when:%Y}" / f"{when:%m}" / f"{when:%d}"
    day.mkdir(parents=True, exist_ok=True)
    base = f"{activity}-{when:%H%M%S}-{digest[:6]}"
    target = day / base
    suffix = 1
    while target.exists():
        suffix += 1
        target = day / f"{base}-{suffix}"
    return target


def _assemble(
    directory: Path,
    *,
    entry_id: str,
    kind: str,
    files: Sequence[Path],
    caption: str | None,
    voice: Path | None,
    meta_json: dict[str, Any],
    activity_id: str,
    activity_name: str,
    when: datetime,
    thumbnailer: Thumbnailer,
) -> Entry:
    """Fill ``directory`` with a complete entry. Returns it, id not yet final."""
    stamp = when.isoformat(timespec="seconds")
    versions: list[Version] = []
    for index, source in enumerate(files, start=1):
        filename = f"v{index:03d}{source.suffix.lower()}"
        shutil.copy2(source, directory / filename)
        versions.append(
            Version(
                filename=filename,
                imported=stamp,
                size=source.stat().st_size,
                sha256=sha256_file(source),
            )
        )

    mime = guess_mime(files[0])
    entry = Entry(
        id=entry_id,
        activity_id=activity_id,
        created=stamp,
        updated=stamp,
        title=title_for(kind, caption, activity_name),
        # Empty on purpose -- see the module docstring. There is no source file
        # outside the journal for this entry, and claiming one would make the
        # shell's importer match a path that is about to be deleted.
        source_path="",
        mime=mime,
        versions=versions,
        directory=directory,
    )

    line = " ".join((caption or "").split())
    if line:
        (directory / CAPTION_NAME).write_text(line + "\n", encoding="utf-8")

    if voice is not None:
        _keep_voice(Path(voice), directory)

    if mime.startswith("image/"):
        # The first version is the picture; later ones are the same picture
        # saved again, exactly as the shell's importer treats them.
        made = thumbnailer(directory / versions[0].filename, directory / THUMB_NAME)
        if not made:
            log.info("no thumbnail for %s; My Things will use the activity's icon", files[0].name)

    (directory / META_NAME).write_text(
        json.dumps(
            {
                "schema": META_SCHEMA,
                "kind": kind,
                "activity_id": activity_id,
                "created": stamp,
                "caption": line,
                "files": [version.filename for version in versions],
                "meta": meta_json,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    entry.save()
    return entry


def _keep_voice(voice: Path, directory: Path) -> None:
    """Store the recording where :mod:`kidnix_shell.voice` looks for it."""
    if not voice.is_file():
        log.warning("no voice note at %s; the entry is kept without one", voice)
        return
    if voice.suffix.lower() != Path(NOTE_NAME).suffix:
        # Not fatal: the shell plays it through GStreamer, which sniffs the
        # container rather than trusting the name. Logged because a .wav that
        # is called note.ogg is a surprise waiting for whoever debugs it next.
        log.info(
            "voice note %s is not %s; storing it as %s anyway", voice.name, NOTE_NAME, NOTE_NAME
        )
    shutil.copy2(voice, directory / NOTE_NAME)


def _place(incoming: Path, target: Path) -> Path:
    """Move the finished entry into its day. One rename, and it is real."""
    incoming.rename(target)
    _tidy_incoming(incoming.parent)
    return target


def _tidy_incoming(incoming_root: Path) -> None:
    """Remove ``.incoming`` when it is empty. Never anything inside it.

    ``rmdir`` and not ``rmtree``: not-empty means another save is in flight and
    losing *that* one would be the bug this whole dance exists to avoid. Gone
    already is fine too.
    """
    with contextlib.suppress(OSError):
        incoming_root.rmdir()


def _discard(directory: Path) -> None:
    """Throw away a half-built entry. Only ever called on our own scratch dir."""
    shutil.rmtree(directory, ignore_errors=True)
