"""Letters that came back: the grown-up's inbox, imported into My Things.

``docs/research/05-learning-science.md`` section 3, on the strongest activity in
the list:

    **Show the reply.** A one-way outbox is not an audience; the reply must come
    back *into the child's journal* and be announced.

The letter goes out as a folder a grown-up carries (``letters_to_family``'s
outbox; no egress, SYNTHESIS H1), and the answer comes back the same way: a
grown-up drops a picture, a recording or a few words into
``/var/lib/kidnix/inbox/<profile>/`` from their own account. This module is the
other half of that sentence -- the reply becoming **a card in the child's own My
Things**, with the picture on it or the words on it, and Grandad's voice behind
it exactly like the child's own voice notes.

`docs/design/letters-to-family.md` section 7 is the contract, and it is followed
here point for point:

**Where.** ``/var/lib/kidnix/inbox/<profile>/``, one reply per directory or per
loose file. The shell **sweeps it once, when the child says who they are**,
rather than watching it: a reply is not urgent, and inotify on ``/var/lib`` from
the child's session is a permissions question nobody needs to answer for a thing
that can wait until the next sitting.

**Read-only, in both directions.** The inbox is ``0750 parent:kid``: the child's
session can list it and read it and can write nothing at all. So the import
never moves, renames, marks or deletes anything in there -- it is a grown-up's
folder -- and "already imported" is remembered on **our** side of the fence, in
``<profile state>/letters.json``. The idempotence test that matters is the one
that asserts the inbox is byte-for-byte unchanged after a sweep.

**Twice-idempotent, on purpose.** The state file is the fast answer; the
Journal's own ``source_path`` index is the backstop. Delete ``letters.json`` and
the sweep still imports nothing, because :meth:`Journal.import_file` recognises
a file it has already stored. A grown-up who tidies up the child's state
directory must not thereby give them Grandad's letter twice.

**Announced, once, gently.** One spoken line at the first Home of the session --
*"There's a letter for you from Grandad. It's in My Things."* -- and then
nothing. No badge, no count, no pulse, no notification, and no second telling
(SYNTHESIS D6: nothing in this product summons a child back to it). That is what
:class:`Announcement` is: a line you can take exactly once.

**The card.** ``kind = "letter-reply"`` in ``meta.json``, spelled with a hyphen
because that is the slug the design note and ``kidnix_activity.journal.KIND_RE``
both use and a second spelling of one vocabulary is a second bug. A picture
thumbnails itself; a recording or a note gets a **drawn envelope card**, with
the sender's words on it in Andika, **verbatim** -- a grown-up's letter is not
corrected, re-cased or tidied on the way in any more than a child's is.
"""

from __future__ import annotations

import json
import logging
import os
import shutil
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from .i18n import N_, _
from .journal import THUMB_NAME, THUMB_SIZE, Entry, Journal
from .voice import NOTE_NAME

log = logging.getLogger(__name__)

__all__ = [
    "ANNOUNCEMENT",
    "CARD_TITLE",
    "INBOX_ROOT",
    "KIND",
    "Announcement",
    "Imported",
    "Reply",
    "announcement",
    "draw_envelope",
    "import_replies",
    "inbox_dir",
    "read_replies",
    "state_path",
]

#: Machine-local and root-created (``system_files/usr/lib/tmpfiles.d/
#: kidnix-letters.conf``). ``/var`` and not the child's home, because a grown-up
#: on their *own* login has to be able to drop a reply in without going into a
#: five-year-old's ``~/.local/share``.
INBOX_ROOT = Path("/var/lib/kidnix/inbox")

#: A developer has no ``/var/lib/kidnix``. This lets ``just demo`` and a manual
#: end-to-end try point the sweep at a scratch directory without patching code.
ROOT_VAR = "KIDNIX_INBOX_ROOT"

#: What we have already imported, in the child's own state directory beside
#: ``usage.toml`` and ``progress.toml``. JSON and not TOML because it is a map
#: of paths to a triple and nobody hand-edits it.
STATE_NAME = "letters.json"
STATE_SCHEMA = 1

#: The tile a reply belongs to, so the Journal card wears the Letters icon and
#: sits with the letters the child sent. ``letters`` is the manifest id.
ACTIVITY_ID = "letters"
ACTIVITY_NAME = N_("Letters")

#: ``meta.json``'s ``kind``. A lowercase slug, hyphenated: same vocabulary as
#: ``kidnix_activity.journal`` (whose ``KIND_RE`` an underscore would fail) and
#: the same word ``docs/design/letters-to-family.md`` sections 7 and 9 use.
KIND = "letter-reply"
META_NAME = "meta.json"
META_SCHEMA = 1
CAPTION_NAME = "caption.txt"

#: The three things a reply can be, as ``reply.json`` spells them.
IMAGE = "image"
AUDIO = "audio"
TEXT = "text"

#: What a grown-up's phone or laptop actually produces. Compared lower-cased --
#: a camera writes ``.JPG``.
IMAGE_SUFFIXES = (".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp")
AUDIO_SUFFIXES = (".ogg", ".opus", ".oga", ".mp3", ".wav", ".m4a", ".flac")
TEXT_SUFFIXES = (".txt", ".md")

#: The optional manifest a sender's tooling can write. Everything in it is a
#: hint: a reply whose ``reply.json`` is broken is still a reply, and the files
#: beside it are still read (see :func:`_manifest`).
REPLY_FILE = "reply.json"
#: A grown-up's way of saying who it is from when the folder is called something
#: else. One line, the first one wins.
FROM_NAME = "from.txt"
#: The words, when a directory has several text files in it.
WORDS_NAME = "words.txt"

#: How many replies one sweep will look at. The same cap the activity's shelf
#: uses: a household that dropped forty files in should not spend a child's
#: first minute of the afternoon copying them.
MAX_REPLIES = 8

#: What the card is called. Not "Reply" and not a filename: the child is being
#: told *who it is from*, which is the entire point of the feature.
CARD_TITLE = N_("A letter from {name}")

#: The one line, at the first Home. Gentle, and it says where the thing is
#: rather than asking the child to do anything about it (D6).
ANNOUNCEMENT = N_("There's a letter for you from {name}. It's in My Things.")

#: When even the folder name says nothing. Never "unknown" and never a digit.
SOMEONE = N_("someone")

#: Keep in step with ``theme.css`` and :data:`kidnix_shell.widgets.CHILD_FACE`:
#: the words on an envelope card are drawn in the face the rest of the product
#: reads in, or a grown-up's note is the one thing in kidnix set in Cantarell.
CARD_FACE = "Andika,Andika New Basic,Cantarell,Sans"

#: ``theme.css``: @kid-paper, @kid-ink, @kid-edge, @kid-primary.
_PAPER = (0.984, 0.969, 0.937)
_INK = (0.086, 0.094, 0.114)
_EDGE = (0.494, 0.514, 0.549)
_PRIMARY = (0.059, 0.541, 0.541)
_WHITE = (1.0, 1.0, 1.0)

#: ``(destination, words) -> drew_one``. Injected by the tests so the import
#: path can be asserted on a machine with no cairo; defaults to the real one.
EnvelopeDrawer = Callable[[Path, str], bool]


# -- where -------------------------------------------------------------------


def inbox_root(env: Mapping[str, str] | None = None) -> Path:
    """The inbox root: :data:`INBOX_ROOT`, or whatever ``KIDNIX_INBOX_ROOT`` says."""
    environ = os.environ if env is None else env
    raw = (environ.get(ROOT_VAR) or "").strip()
    return Path(raw) if raw else INBOX_ROOT


def inbox_dir(profile_id: str, root: Path | None = None) -> Path:
    """``<root>/<profile>``. An unset profile is ``_`` and never the root itself.

    Same rule as the activity's ``mailbox.profile_dir``: a machine that has
    never had profiles is a real state, and letting it collapse to the root
    would put two children's letters in one folder the day somebody added a
    second profile.
    """
    base = root if root is not None else inbox_root()
    return base / (profile_id.strip() or "_")


def state_path(profile_state: Path) -> Path:
    """Where "already imported" is remembered -- on our side of the fence."""
    return profile_state / STATE_NAME


# -- what --------------------------------------------------------------------


@dataclass(frozen=True)
class Reply:
    """One thing a grown-up put in the inbox. Never written to, only read."""

    path: Path
    from_name: str
    picture: Path | None = None
    voice: Path | None = None
    text: Path | None = None
    words: str = ""
    #: What ``reply.json`` said, if it said. Recorded in ``meta.json`` and
    #: deliberately *not* used as the entry's date -- see :func:`import_replies`.
    sent_at: str = ""
    modified: float = 0.0

    @property
    def kind(self) -> str:
        if self.picture is not None:
            return IMAGE
        if self.voice is not None:
            return AUDIO
        return TEXT

    @property
    def primary(self) -> Path | None:
        """The file the Journal entry is made of. ``None`` means "not a reply"."""
        return self.picture or self.voice or self.text


@dataclass(frozen=True)
class Imported:
    """A reply and the Journal entry it became."""

    entry: Entry
    reply: Reply


def read_replies(
    profile_id: str,
    root: Path | None = None,
    *,
    limit: int = MAX_REPLIES,
) -> list[Reply]:
    """Everything in this child's inbox, newest first. Never writes anything.

    A missing inbox is the normal case -- most children have not been written
    to, and a developer's machine has no ``/var/lib/kidnix`` at all -- and comes
    back as an empty list with no warning.
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
            reply = _from_directory(child) if child.is_dir() else _from_file(child)
        except OSError as exc:  # pragma: no cover - a folder that vanished mid-sweep
            log.warning("skipping %s in the inbox (%s)", child, exc)
            reply = None
        if reply is not None and reply.primary is not None:
            found.append(reply)
    found.sort(key=lambda reply: (-reply.modified, reply.path.name))
    return found[: max(0, limit)]


def _from_directory(directory: Path) -> Reply | None:
    files = sorted(child for child in directory.iterdir() if child.is_file())
    if not files:
        return None
    named = {child.name.lower(): child for child in files}
    manifest = _manifest(named.get(REPLY_FILE))

    listed = _listed_files(directory, manifest)
    pool = listed or [f for f in files if f.name.lower() not in (REPLY_FILE, FROM_NAME)]

    from_name = _text_of(manifest.get("from"))
    if not from_name and FROM_NAME in named:
        from_name = _first_line(named[FROM_NAME])
    if not from_name:
        from_name = name_from(directory.name)

    words_file = _words_file(named, pool)
    return Reply(
        path=directory,
        from_name=from_name,
        picture=_first_of(pool, IMAGE_SUFFIXES),
        voice=_first_of(pool, AUDIO_SUFFIXES),
        text=words_file,
        words=_all_of(words_file) if words_file is not None else "",
        sent_at=_text_of(manifest.get("sent_at")),
        modified=_mtime(directory),
    )


def _from_file(path: Path) -> Reply | None:
    """A loose file is a whole reply, named from its own stem."""
    suffix = path.suffix.lower()
    if suffix in IMAGE_SUFFIXES:
        picture, voice, text = path, None, None
    elif suffix in AUDIO_SUFFIXES:
        picture, voice, text = None, path, None
    elif suffix in TEXT_SUFFIXES:
        picture, voice, text = None, None, path
    else:
        return None
    return Reply(
        path=path,
        from_name=name_from(path.stem),
        picture=picture,
        voice=voice,
        text=text,
        words=_all_of(path) if text is not None else "",
        modified=_mtime(path),
    )


def _manifest(path: Path | None) -> dict[str, Any]:
    """``reply.json``, or an empty hint set.

    **A broken one is ignored, not fatal.** The files in the folder are the
    reply; ``reply.json`` only says things about them. A grown-up's tool that
    wrote half a JSON document must not cost a child their letter, so anything
    unreadable, unparseable or not an object comes back as no hints at all and
    the directory is read the way a directory with no manifest is read.
    """
    if path is None:
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        log.warning("ignoring %s (%s); reading the folder instead", path, exc)
        return {}
    if not isinstance(data, dict):
        log.warning("ignoring %s: it is not an object; reading the folder instead", path)
        return {}
    return data


def _listed_files(directory: Path, manifest: Mapping[str, Any]) -> list[Path]:
    """The ``files`` a manifest names, as real files inside this directory.

    A name with a separator or a ``..`` in it is dropped without ceremony: the
    inbox is a folder a grown-up can be *sent* things into, and a manifest that
    points outside its own directory is either a mistake or something worse.
    """
    raw = manifest.get("files")
    if isinstance(raw, str):
        raw = [raw]
    if not isinstance(raw, list):
        return []
    keep: list[Path] = []
    for item in raw:
        if not isinstance(item, str):
            continue
        name = item.strip()
        if not name or name != Path(name).name or name in {".", ".."}:
            log.warning("ignoring %r in %s: a reply lists its own files by name", item, directory)
            continue
        candidate = directory / name
        if candidate.is_file():
            keep.append(candidate)
    return keep


def _words_file(named: Mapping[str, Path], pool: Sequence[Path]) -> Path | None:
    explicit = named.get(WORDS_NAME)
    if explicit is not None:
        return explicit
    return _first_of([p for p in pool if p.name.lower() != FROM_NAME], TEXT_SUFFIXES)


def _first_of(files: Iterable[Path], suffixes: Sequence[str]) -> Path | None:
    for candidate in files:
        if candidate.suffix.lower() in suffixes:
            return candidate
    return None


def name_from(stem: str) -> str:
    """``2026-08-23-grandad`` -> ``Grandad``. A folder name, read as a person.

    The digits go because that string is **spoken to the child** and a
    five-year-old never hears a number out of this machine (01 #19, 03 #32).
    """
    parts = [part for part in stem.replace("_", "-").replace(" ", "-").split("-") if part]
    words = [part for part in parts if not part.isdigit()]
    if not words:
        return _(SOMEONE)
    return " ".join(word[:1].upper() + word[1:] for word in words)


def _text_of(value: Any) -> str:
    return " ".join(value.split()) if isinstance(value, str) else ""


def _first_line(path: Path) -> str:
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").strip().splitlines()
    except OSError:  # pragma: no cover - unreadable file in somebody else's folder
        return ""
    return lines[0].strip() if lines else ""


def _all_of(path: Path) -> str:
    """The words of a reply. Stripped at the ends and **not otherwise touched**."""
    try:
        return path.read_text(encoding="utf-8", errors="replace").strip()
    except OSError:  # pragma: no cover
        return ""


def _mtime(path: Path) -> float:
    try:
        return path.stat().st_mtime
    except OSError:  # pragma: no cover
        return 0.0


# -- remembering what came in ------------------------------------------------


def _load_state(path: Path) -> dict[str, dict[str, Any]]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}
    except (OSError, ValueError) as exc:
        # Losing this file costs a child nothing: the Journal's own source
        # index still recognises every reply already imported.
        log.warning("letters state %s unreadable (%s); starting fresh", path, exc)
        return {}
    imported = data.get("imported") if isinstance(data, dict) else None
    if not isinstance(imported, dict):
        return {}
    return {str(key): value for key, value in imported.items() if isinstance(value, dict)}


def _save_state(path: Path, imported: Mapping[str, dict[str, Any]]) -> None:
    document = {"schema": STATE_SCHEMA, "imported": dict(imported)}
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(".json.tmp")
        temporary.write_text(json.dumps(document, indent=2, sort_keys=True), encoding="utf-8")
        temporary.replace(path)
    except OSError as exc:  # a full disk must never end a child's session
        log.warning("could not record imported letters in %s (%s)", path, exc)


def _stamp(path: Path, when: datetime) -> dict[str, Any]:
    """Path + mtime + size, the triple ``JournalImporter._stat`` already uses.

    Recorded for a grown-up reading the file, **not** compared: section 7 #3 is
    "import once and only once", so the *presence* of the path is the answer. A
    reply whose folder gained a second file later is not a second letter.
    """
    try:
        info = path.stat()
    except OSError:  # pragma: no cover
        return {"mtime": 0.0, "size": 0, "imported": when.isoformat(timespec="seconds")}
    return {
        "mtime": info.st_mtime,
        "size": info.st_size,
        "imported": when.isoformat(timespec="seconds"),
    }


# -- the import --------------------------------------------------------------


def import_replies(
    journal: Journal,
    *,
    profile_id: str,
    state: Path,
    root: Path | None = None,
    now: datetime | None = None,
    envelope: EnvelopeDrawer | None = None,
) -> list[Imported]:
    """Import every reply this child has not had yet. Returns what was kept.

    Called once per sitting, at the moment the child says who they are, and
    before Home is built -- so the card is *already there* when they open My
    Things, rather than appearing under their hands two seconds later.

    The entry is dated **now**, not ``sent_at``: a letter posted last week
    arrived in the child's world today, and dating it backwards would file it
    under "Before" on the very screen the child was just told to look at.
    ``sent_at`` is kept in ``meta.json``, where a grown-up can see it.
    """
    when = now or datetime.now()
    known = _load_state(state)
    kept: list[Imported] = []
    # Oldest first, so the newest reply is imported last and therefore sits
    # first in a Journal ordered by `updated`.
    for reply in reversed(read_replies(profile_id, root)):
        key = str(reply.path)
        if key in known:
            continue
        entry = _import_one(journal, reply, when=when, envelope=envelope)
        known[key] = _stamp(reply.path, when)
        if entry is not None:
            kept.append(Imported(entry=entry, reply=reply))
    if known:
        _save_state(state, known)
    if kept:
        log.info("imported %d letter(s) for %s from the inbox", len(kept), profile_id or "_")
    return kept


def _import_one(
    journal: Journal,
    reply: Reply,
    *,
    when: datetime,
    envelope: EnvelopeDrawer | None,
) -> Entry | None:
    """One reply -> one Journal entry. ``None`` if the Journal already has it."""
    source = reply.primary
    if source is None:  # pragma: no cover - read_replies drops these already
        return None
    entry = journal.import_file(
        source,
        ACTIVITY_ID,
        activity_name=_(ACTIVITY_NAME),
        now=when,
    )
    if entry is None:
        # Byte for byte what is already in there: the state file was lost, or
        # a grown-up dropped the same picture in twice. Not a second card.
        log.info("the Journal already has the letter at %s", reply.path)
        return None
    _finish(entry, reply, envelope or draw_envelope)
    return entry


def _finish(entry: Entry, reply: Reply, envelope: EnvelopeDrawer) -> None:
    """Turn a plain imported file into a letter: title, words, voice, card."""
    entry.title = _(CARD_TITLE).format(name=reply.from_name)
    entry.save()

    if reply.words:
        # Verbatim. A grown-up's spelling is not corrected on the way in, for
        # the same reason a child's is not (05 section 3).
        _write(entry.directory / CAPTION_NAME, reply.words)

    if reply.voice is not None:
        # Copied to `note.ogg` even when it is also `v001.ogg`, because that is
        # the name `kidnix_shell.voice` looks for: it is what puts the ear badge
        # on the card and what plays when the child taps it in "Show a grown-up".
        try:
            shutil.copy2(reply.voice, entry.directory / NOTE_NAME)
        except OSError as exc:  # pragma: no cover - a disk that filled mid-import
            log.warning("could not keep the voice of %s (%s)", reply.path, exc)

    thumb = entry.directory / THUMB_NAME
    if not thumb.is_file():
        # Not a picture, so there is nothing to scale: draw the card instead.
        # A letter with no card would fall back to the Letters icon and every
        # reply in My Things would look like every other one.
        envelope(thumb, reply.words)

    _write(
        entry.directory / META_NAME,
        json.dumps(
            {
                "schema": META_SCHEMA,
                "kind": KIND,
                "from": reply.from_name,
                "source": str(reply.path),
                "sent_at": reply.sent_at,
                "reply_kind": reply.kind,
                "caption": reply.words,
                "files": [version.filename for version in entry.versions],
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
    )


def _write(path: Path, text: str) -> None:
    try:
        path.write_text(text, encoding="utf-8")
    except OSError as exc:  # pragma: no cover
        log.warning("could not write %s (%s)", path, exc)


# -- the card for a letter that is not a picture -----------------------------


def draw_envelope(destination: Path, words: str = "", size: int = THUMB_SIZE) -> bool:
    """Draw an envelope card as ``destination``. ``False`` if it cannot.

    Cairo and Pango, because the same two draw every other glyph the child sees
    and the words on this card have to be the face they read in everywhere else.
    Failure is not an error: a card with no thumbnail falls back to the Letters
    icon, which is worse-looking and works.
    """
    try:
        import cairo
        import gi

        gi.require_version("Pango", "1.0")
        gi.require_version("PangoCairo", "1.0")
        from gi.repository import Pango, PangoCairo

        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, size, size)
        context = cairo.Context(surface)
        context.set_source_rgb(*_PAPER)
        context.paint()
        # A hairline so the card has an edge of its own against a cream screen
        # (the same 3.57:1 border theme.css uses on everything else).
        inset = max(1.0, size * 0.012)
        context.set_line_width(inset)
        context.set_source_rgb(*_EDGE)
        context.rectangle(inset / 2, inset / 2, size - inset, size - inset)
        context.stroke()

        line = words.strip()
        if line:
            _envelope(context, size * 0.06, size * 0.06, size * 0.26)
            _words(context, Pango, PangoCairo, line, size)
        else:
            _envelope(context, size * 0.16, size * 0.28, size * 0.68)

        destination.parent.mkdir(parents=True, exist_ok=True)
        surface.write_to_png(str(destination))
        return True
    except Exception as exc:  # pragma: no cover - no cairo, no fonts, no disk
        log.debug("no envelope card for %s: %s", destination, exc)
        return False


def _envelope(context: Any, x: float, y: float, width: float) -> None:
    """A closed envelope: a body, an outline and the fold across the top."""
    height = width * 0.68
    stroke = max(2.0, width * 0.045)
    context.set_line_width(stroke)
    context.rectangle(x, y, width, height)
    context.set_source_rgb(*_WHITE)
    context.fill_preserve()
    context.set_source_rgb(*_INK)
    context.stroke()
    context.move_to(x, y)
    context.line_to(x + width / 2, y + height * 0.58)
    context.line_to(x + width, y)
    context.set_source_rgb(*_PRIMARY)
    context.stroke()


def _words(context: Any, pango: Any, pangocairo: Any, line: str, size: int) -> None:
    """The sender's words on the card, in Andika, exactly as they wrote them.

    Ellipsised at the bottom when there are more words than a 256 px card can
    hold -- the whole of them is in ``caption.txt`` beside the entry, which is
    where a grown-up reads a long letter from.

    Three lines of "hello ada" and a whole paragraph both sit in the middle of
    the space below the envelope: text pinned to the top of a mostly empty card
    reads as a card that failed to finish drawing.
    """
    margin = size * 0.09
    top = size * 0.36
    room = size - top - margin
    layout = pangocairo.create_layout(context)
    layout.set_text(line, -1)
    points = max(8, size // 22)
    layout.set_font_description(pango.FontDescription.from_string(f"{CARD_FACE} {points}"))
    layout.set_width(int((size - 2 * margin) * pango.SCALE))
    layout.set_height(int(room * pango.SCALE))
    layout.set_wrap(pango.WrapMode.WORD_CHAR)
    layout.set_ellipsize(pango.EllipsizeMode.END)
    _width, height = layout.get_pixel_size()
    context.set_source_rgb(*_INK)
    context.move_to(margin, top + max(0.0, (room - height) / 2))
    pangocairo.show_layout(context, layout)


# -- the one gentle line -----------------------------------------------------


def announcement(imported: Sequence[Imported]) -> str:
    """One sentence, naming one person. ``""`` when nothing came.

    **One line however many letters arrived**, naming the most recent sender.
    Not a count -- a number is the thing this product does not say to a child
    (01 #19) and "you have three letters" is a to-do list. The other cards are
    in My Things, in time order, where the child will meet them.
    """
    if not imported:
        return ""
    return _(ANNOUNCEMENT).format(name=imported[-1].reply.from_name)


class Announcement:
    """A line that can be taken exactly once.

    The sweep happens at "Who's here?"; the line belongs at the **first Home**
    of that sitting, after Home has said what it says. Between those two moments
    it lives here, and :meth:`take` empties it -- so a child who goes Home,
    into an activity, and Home again is told once and never again (SYNTHESIS
    D6). It is the whole of "no badge, no repeat", in seven lines.
    """

    def __init__(self) -> None:
        self._line = ""

    @property
    def pending(self) -> bool:
        return bool(self._line)

    def offer(self, imported: Sequence[Imported]) -> str:
        """Hold the line for the letters just imported. Replaces any older one."""
        self._line = announcement(imported)
        return self._line

    def take(self) -> str:
        """The line, once. Every call after the first is ``""``."""
        line, self._line = self._line, ""
        return line

    def clear(self) -> None:
        self._line = ""
