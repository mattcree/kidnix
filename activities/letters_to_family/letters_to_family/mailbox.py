"""The outbox and the inbox: two ordinary directories, and a contract.

This is the whole of the "how does a letter get to Grandad, and how does his
answer get back" problem, and the answer is deliberately not a protocol:

    **H1. No network egress from the child session by default.**
    -- docs/research/SYNTHESIS.md section 2

    **Show the reply.** A one-way outbox is not an audience; the reply must come
    back *into the child's journal* and be announced.
    -- docs/research/05-learning-science.md section 3

So the letter is written into a folder, and **a grown-up carries it**. Nothing
in the child session opens a socket, and there is no queue, no retry, no
"sending..." spinner and no status that can ever say "sent" -- because this
program would not know.

::

    /var/lib/kidnix/outbox/<profile>/<timestamp>-<recipient>/
        letter.png      the whole letter as one picture: the drawing, the
                        child's own words, and who it is for. What a grown-up
                        actually attaches to an email or prints and posts.
        picture.png     the drawing on its own, for a grown-up who wants it
        note.ogg        the voice note, if there is one
        caption.txt     the child's words, byte for byte, if there are any
        letter.json     who it is for, when it was made, and status =
                        "waiting for a grown-up to send"

    /var/lib/kidnix/inbox/<profile>/
        <anything>/     one reply: a picture, a sound, some words, a from.txt
        <anything.png>  or a single loose file, which is also one reply

**The inbox is a grown-up's drop point, and since 2026-08-24 it is no longer
what the shelf reads.** The shell sweeps it once a sitting and imports each
reply into the child's Journal (``kidnix_shell.inbox``), and
:func:`letters_to_family.journal_read.shelf_replies` reads *those* -- calling
:func:`inbox_replies` underneath only to catch a reply that arrived since the
last sweep. That is section 7 step 5 of the design note, and the reason is that
"the child has already been given this one" is a fact only the shell has:
reading the folder meant every letter stayed on the shelf forever.

**The outbox is write-only from here and the inbox is read-only from here.**
This module cannot delete anything in either, and there is no code path that
marks a letter sent, moves it, or empties the inbox: those are a grown-up's,
and pretending otherwise would put the machine in charge of an audience it
cannot reach.

**If /var/lib/kidnix/outbox is not writable, the letter is not lost.** The
Journal entry is written first and always -- it is the child's, it is on their
own disk, and it is what My Things shows. The outbox is a *copy* for the
grown-up. :func:`post` returns ``None`` and logs when it cannot make that copy,
which on a developer's machine with no ``/var/lib/kidnix`` is the normal case.

**Both directories exist on the image** as of 2026-08-23:
``system_files/usr/lib/tmpfiles.d/kidnix-letters.conf`` creates them at boot,
because ``/var`` is machine-local in a bootc image and nothing under it can
travel in the container. The outbox is ``kid``'s and the inbox is ``parent``'s,
which is the same asymmetry this module already has in code: a child writes
letters and does not write their own replies. A developer's checkout still has
neither, and still degrades to the Journal alone -- which is the correct
degradation and not a silent one.
"""

from __future__ import annotations

import json
import logging
import shutil
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path

from .i18n import _
from .letter import (
    CAPTION_NAME,
    CARD_NAME,
    META_NAME,
    PICTURE_NAME,
    SOMEONE,
    VOICE_NAME,
    Letter,
)
from .words import reply_line

log = logging.getLogger(__name__)

__all__ = [
    "AUDIO_SUFFIXES",
    "IMAGE_SUFFIXES",
    "INBOX_ROOT",
    "OUTBOX_ROOT",
    "TEXT_SUFFIXES",
    "Reply",
    "inbox_dir",
    "inbox_replies",
    "outbox_dir",
    "post",
    "profile_dir",
]

#: Machine-local, root-created, per profile. ``/var`` and not the child's home
#: because a grown-up on their *own* account has to be able to find it without
#: going into a child's ``~/.local/share``, and because ``/var`` survives a
#: bootc upgrade untouched.
OUTBOX_ROOT = Path("/var/lib/kidnix/outbox")
#: Where a grown-up drops what came back. Same reasoning, other direction.
INBOX_ROOT = Path("/var/lib/kidnix/inbox")

#: What counts as the picture in a reply. Lower-case comparison; a grown-up's
#: phone writes ``.JPG``.
IMAGE_SUFFIXES = (".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp")
#: What counts as the voice. ``.ogg`` first because it is what we write.
AUDIO_SUFFIXES = (".ogg", ".opus", ".oga", ".mp3", ".wav", ".m4a", ".flac")
#: What counts as the words.
TEXT_SUFFIXES = (".txt", ".md")

#: The file a grown-up can put a name in, when the folder is called something
#: else. One line, first line wins.
FROM_NAME = "from.txt"
#: The words of a reply, when there are several text files.
WORDS_NAME = "words.txt"


def profile_dir(root: Path, profile_id: str) -> Path:
    """``<root>/<profile>``, with an unset profile going to ``_``.

    ``for_profile("")`` is a real state -- a machine that has never had profiles
    and a developer running the activity by hand both hit it -- and it must not
    silently become the root itself, or two children's letters would share one
    folder the first time somebody added a profile.
    """
    return root / (profile_id.strip() or "_")


def outbox_dir(letter: Letter, profile_id: str, root: Path | None = None) -> Path:
    """Where this letter's copy for the grown-up goes. Computed, not created."""
    return profile_dir(root if root is not None else OUTBOX_ROOT, profile_id) / letter.outbox_name()


def inbox_dir(profile_id: str, root: Path | None = None) -> Path:
    """Where a grown-up drops replies for this child."""
    return profile_dir(root if root is not None else INBOX_ROOT, profile_id)


# -- out ---------------------------------------------------------------------


def post(
    letter: Letter,
    card: Path,
    profile_id: str,
    root: Path | None = None,
    *,
    entry_id: str = "",
) -> Path | None:
    """Copy the finished letter into the outbox. ``None`` if it cannot.

    Called **after** the Journal entry has been written, never instead of it.
    Every failure here -- no ``/var/lib/kidnix``, a read-only mount, a full disk
    -- is logged and swallowed, because the child's work is already safe and the
    only thing lost is a convenience for the grown-up. Raising would turn a
    permissions problem on a directory a child has never heard of into a
    five-year-old being told their letter did not work.
    """
    target = outbox_dir(letter, profile_id, root)
    try:
        target.mkdir(parents=True, exist_ok=True)
        if card.is_file():
            shutil.copy2(card, target / CARD_NAME)
        if letter.has_picture and letter.picture is not None:
            shutil.copy2(letter.picture, target / PICTURE_NAME)
        if letter.has_voice and letter.voice is not None:
            shutil.copy2(letter.voice, target / VOICE_NAME)
        if letter.caption:
            # Byte for byte, and with no trailing newline added: the file is
            # the child's words and nothing else. `write_text` with an explicit
            # encoding, because a grown-up's letter may well have an emoji or a
            # name with an accent in it.
            (target / CAPTION_NAME).write_text(letter.caption, encoding="utf-8")
        document = dict(letter.meta())
        document["schema"] = 1
        document["entry_id"] = entry_id
        document["profile"] = profile_id
        document["files"] = sorted(child.name for child in target.iterdir())
        (target / META_NAME).write_text(
            json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
    except OSError as exc:
        log.warning(
            "could not write the outbox copy at %s (%s); the letter is safe in the "
            "Journal and a grown-up can export it from there",
            target,
            exc,
        )
        return None
    log.info("outbox copy written to %s", target)
    return target


# -- in ----------------------------------------------------------------------


@dataclass(frozen=True)
class Reply:
    """One reply the child can be shown. Read-only, always.

    **Two things build one of these now** (2026-08-24), and the shelf cannot
    tell them apart on purpose:

    * :func:`inbox_replies`, from a folder a grown-up dropped in -- and
    * :func:`letters_to_family.journal_read.letter_replies`, from the card the
      shell already made of that folder in the child's own Journal, which is
      the end state ``docs/design/letters-to-family.md`` section 7 step 5 asks
      for.

    The Journal is the real source now; the inbox is a grown-up's drop point
    and is read only as the fallback for a reply that arrived since the shell
    last swept (:func:`letters_to_family.journal_read.shelf_replies`), so that
    nothing a grown-up put in ever simply fails to appear.

    Nothing here writes. There is no code path in this activity that deletes a
    reply, empties the inbox or marks one read -- the inbox is somebody else's
    folder, and "read" is the shell's business, recorded in its own state file.
    """

    path: Path
    from_name: str
    picture: Path | None = None
    voice: Path | None = None
    words: str = ""
    modified: float = 0.0
    #: The inbox path this reply *came from*, as ``meta.json`` recorded it, on
    #: a reply read back out of the Journal. ``""`` on one read straight from
    #: the inbox, where :attr:`path` is that same thing. It is the dedupe key:
    #: an imported reply and its still-present inbox folder are one letter and
    #: must not be two tiles.
    source: str = ""
    #: The 256 px card beside a Journal entry -- the picture scaled down, or
    #: the envelope the shell drew for a letter that is words or a voice.
    #: ``None`` on an inbox reply, which has no card of its own.
    thumb: Path | None = None

    @property
    def has_picture(self) -> bool:
        return self.picture is not None

    @property
    def has_voice(self) -> bool:
        return self.voice is not None

    @property
    def tile_image(self) -> Path | None:
        """What the shelf's tile shows, or ``None`` for the placeholder.

        The card first when there is one: it is 256 px where the picture may be
        a whole camera frame, and for a letter that is only words or only a
        voice it is the envelope the shell drew, which is the difference
        between six identical placeholders and six letters.
        """
        return self.thumb or self.picture

    @property
    def speak_text(self) -> str:
        """What the tile says. The sender, because that is who it is from."""
        return reply_line(self.from_name)


def _first_with_suffix(files: Sequence[Path], suffixes: Iterable[str]) -> Path | None:
    wanted = tuple(suffixes)
    for candidate in files:
        if candidate.suffix.lower() in wanted:
            return candidate
    return None


def _name_from(stem: str) -> str:
    """``2026-08-23-grandad`` -> ``Grandad``. A folder name a person typed.

    Leading date-ish and numeric segments are dropped because a grown-up who
    names a folder with a date has not named the sender, and a digit is the one
    thing that must not reach the child's ear (01 #19).
    """
    parts = [part for part in stem.replace("_", "-").replace(" ", "-").split("-") if part]
    words = [part for part in parts if not part.isdigit()]
    if not words:
        return _(SOMEONE)
    return " ".join(word[:1].upper() + word[1:] for word in words)


def _read_line(path: Path) -> str:
    try:
        first = path.read_text(encoding="utf-8", errors="replace").strip().splitlines()
    except OSError:  # pragma: no cover - unreadable file in somebody else's dir
        return ""
    return first[0].strip() if first else ""


def _read_words(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace").strip()
    except OSError:  # pragma: no cover
        return ""


def _mtime(path: Path) -> float:
    try:
        return path.stat().st_mtime
    except OSError:  # pragma: no cover
        return 0.0


def _reply_from_directory(directory: Path) -> Reply | None:
    try:
        files = sorted(child for child in directory.iterdir() if child.is_file())
    except OSError:  # pragma: no cover - a directory that vanished mid-listing
        return None
    if not files:
        return None

    named = {child.name.lower(): child for child in files}
    from_name = ""
    if FROM_NAME in named:
        from_name = _read_line(named[FROM_NAME])
    if not from_name:
        from_name = _name_from(directory.name)

    words_file = named.get(WORDS_NAME) or _first_with_suffix(
        [f for f in files if f.name.lower() != FROM_NAME], TEXT_SUFFIXES
    )
    return Reply(
        path=directory,
        from_name=from_name,
        picture=_first_with_suffix(files, IMAGE_SUFFIXES),
        voice=_first_with_suffix(files, AUDIO_SUFFIXES),
        words=_read_words(words_file) if words_file is not None else "",
        modified=_mtime(directory),
    )


def _reply_from_file(path: Path) -> Reply | None:
    suffix = path.suffix.lower()
    if suffix in IMAGE_SUFFIXES:
        picture, voice, words = path, None, ""
    elif suffix in AUDIO_SUFFIXES:
        picture, voice, words = None, path, ""
    elif suffix in TEXT_SUFFIXES:
        picture, voice, words = None, None, _read_words(path)
    else:
        return None
    return Reply(
        path=path,
        from_name=_name_from(path.stem),
        picture=picture,
        voice=voice,
        words=words,
        modified=_mtime(path),
    )


def inbox_replies(
    profile_id: str, root: Path | None = None, *, limit: int = 8
) -> list[Reply]:
    """Everything a grown-up has dropped in, newest first. Never writes.

    **Not what the shelf shows any more**: it is the fallback half of
    :func:`letters_to_family.journal_read.shelf_replies`, for the reply that
    has not been swept into the Journal yet. Read on its own it has no idea
    which letters the child has already been given, which is exactly why the
    shelf stopped reading it (2026-08-24).

    A missing inbox is the normal case on a machine where nobody has written
    back yet, and it comes back as an empty list with no log line and no error:
    "no letters yet" is a thing this activity says gently, on a screen, in
    words.
    """
    directory = inbox_dir(profile_id, root)
    try:
        children = sorted(directory.iterdir())
    except FileNotFoundError:
        return []
    except OSError as exc:
        log.warning("could not read the inbox at %s (%s)", directory, exc)
        return []

    found: list[Reply] = []
    for child in children:
        if child.name.startswith("."):
            continue
        try:
            reply = _reply_from_directory(child) if child.is_dir() else _reply_from_file(child)
        except OSError:  # pragma: no cover
            reply = None
        if reply is not None:
            found.append(reply)
    found.sort(key=lambda reply: (-reply.modified, reply.path.name))
    return found[: max(0, limit)]
