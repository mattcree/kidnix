"""Who a letter can go to: the ``[[family]]`` list a grown-up wrote.

The single most important sentence in ``docs/research/05-learning-science.md``
section 3 about this activity is that the recipient is **real and named**:

    A real, named recipient from a parent-approved list. The child sees a photo
    and a name, never an address.

So there is no "add someone" here, no free-text field, and no way for a child to
reach anybody a grown-up has not written down. The list comes from the same
root-owned file the shell reads its PIN and its profiles from, in the same
order, with the same ``/etc`` beats ``/usr/share`` rule::

    /etc/kidnix/parent.toml          the machine's copy (the panel writes this)
    /usr/share/kidnix/parent.toml    the image's default (the fallback)

The schema is the parent panel's, verbatim -- ``kidnix_parent_panel.model
.Recipient`` and the block ``config_io.render_parent_toml`` writes::

    [[family]]
    id = "grandad"
    name = "Grandad"
    relation = "Grandpa"
    photo = "/var/lib/kidnix/photos/grandad.jpg"

``relation`` and ``photo`` are optional and often empty -- the panel's Family tab
will happily record a name and nothing else. A **missing or unreadable photo is
normal**, not an error: :attr:`Recipient.photo_path` is then ``None`` and the
activity draws a placeholder (:func:`letters_to_family.draw.draw_placeholder`)
rather than showing a broken-image icon to a five-year-old.

**Nothing here ever raises.** A missing file, a malformed one, a ``[[family]]``
block with no name -- every one of them comes back as "there is nobody to write
to yet", which is a screen this activity has and knows how to say out loud. A
child told the computer is broken because a grown-up mistyped a TOML key has
been failed twice.
"""

from __future__ import annotations

import logging
import os
import re
import tomllib
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

log = logging.getLogger(__name__)

__all__ = [
    "CONFIG_NAME",
    "CONFIG_SEARCH_PATH",
    "FAMILY_KEY",
    "Recipient",
    "by_id",
    "config_candidates",
    "load_recipients",
    "read_document",
    "recipients_from_document",
    "slugify",
]

#: The file the grown-up's answers land in. The shell's, not ours -- we are a
#: reader of somebody else's file and we never write to it.
CONFIG_NAME = "parent.toml"

#: Where to look, in order. A list rather than a tuple so a test can point it
#: somewhere writable; nothing derived from the *child's* own environment is
#: ever appended to it, because a list of people a child may write to that the
#: child can edit is not a parent-approved list.
CONFIG_SEARCH_PATH: list[Path] = [Path("/etc/kidnix"), Path("/usr/share/kidnix")]

#: The top-level array of tables. Top-level and not ``[parent.family]``: the
#: panel's ``PanelModel.to_dict`` nests it under ``parent`` for its own
#: bookkeeping, but ``config_io.render_parent_toml`` writes ``[[family]]`` at
#: the root of the file, and the file is what is on the machine.
FAMILY_KEY = "family"

_NOT_SLUG = re.compile(r"[^a-z0-9]+")


def slugify(text: str) -> str:
    """``"Grandad Bill"`` -> ``"grandad-bill"``. A directory name, and an id.

    Used for two things: an ``id`` for a ``[[family]]`` block that has no ``id``
    (the panel always writes one; a hand-edited file may not), and the recipient
    half of an outbox directory's name, which a grown-up will read in Files.
    """
    cleaned = _NOT_SLUG.sub("-", (text or "").strip().lower()).strip("-")
    return cleaned or "someone"


@dataclass(frozen=True)
class Recipient:
    """One person a letter can be for. A name, a face, and nothing sendable.

    There is deliberately **no address of any kind on this object** -- no email,
    no phone number, no handle. The child session has no egress (SYNTHESIS H1)
    and the letter never leaves the machine by itself; a grown-up takes it out
    of the outbox and sends it. An address field here would be the first half of
    a feature this product does not have, sitting in a file a child can read.
    """

    id: str
    name: str
    relation: str = ""
    photo: str = ""

    @property
    def photo_path(self) -> Path | None:
        """The photo, if a grown-up gave one **and this account can read it**.

        ``None`` covers the ways this normally goes wrong: no ``photo`` key at
        all, a path typed with a typo in it, a photo on a USB stick that is no
        longer plugged in, and a file the *child's* account is not allowed to
        open. Every one of them draws a placeholder and none of them is an
        error the child is told about.

        **But it is an error the LOG is told about.** ``Path.is_file()`` eats
        ``PermissionError`` and answers False, which is how the commonest case
        of all became invisible: the parent panel used to store the path the
        file chooser gave it, which is nearly always under ``/var/home/parent``
        -- 0700, so ``kid`` cannot even stat it. Four chosen photographs became
        four identical drawn faces with nothing anywhere saying why. The panel
        now copies into ``/var/lib/kidnix/photos``; this branch is what makes
        the remaining cases (a hand-edited ``parent.toml``, a file whose mode
        was changed) findable in one ``journalctl`` instead of never.
        """
        if not self.photo.strip():
            return None
        candidate = Path(self.photo.strip()).expanduser()
        try:
            if not candidate.is_file():
                log.warning(
                    "the photo for %s is not a file this session can see (%s); "
                    "drawing a face instead",
                    self.name,
                    candidate,
                )
                return None
        except OSError as exc:  # pragma: no cover - a mount that went away mid-read
            log.warning("could not look at the photo for %s (%s): %s", self.name, candidate, exc)
            return None
        if not os.access(candidate, os.R_OK):
            log.warning(
                "the photo for %s exists but this account may not read it (%s); "
                "a photo for a child has to live somewhere the child can open, "
                "such as /var/lib/kidnix/photos",
                self.name,
                candidate,
            )
            return None
        return candidate

    @property
    def has_photo(self) -> bool:
        return self.photo_path is not None

    @property
    def speak_text(self) -> str:
        """What the tile says out loud. **The name, on its own.**

        "Grandad", not "Grandad, your grandpa" and not "Send a letter to
        Grandad": B5's two sentences of twelve words is a ceiling and this is
        one word. The relation is a note a grown-up wrote to tell two Grandads
        apart in the panel; it is not how a child refers to a person they know.
        """
        return self.name

    @property
    def slug(self) -> str:
        """The recipient half of an outbox directory name."""
        return slugify(self.id or self.name)


def config_candidates(search: Sequence[Path] | None = None) -> list[Path]:
    """The files that might have a ``[[family]]`` list, in reading order."""
    roots = list(CONFIG_SEARCH_PATH if search is None else search)
    return [root / CONFIG_NAME for root in roots]


def read_document(search: Sequence[Path] | None = None) -> tuple[dict, Path | None]:
    """The first ``parent.toml`` that parses, and where it came from.

    Returns ``({}, None)`` when there is no readable file anywhere, which on a
    developer's machine is the normal case and is not a failure.
    """
    for path in config_candidates(search):
        try:
            with path.open("rb") as handle:
                return tomllib.load(handle), path
        except FileNotFoundError:
            continue
        except (OSError, tomllib.TOMLDecodeError) as exc:
            log.warning("%s could not be read (%s); looking further down the path", path, exc)
            continue
    return {}, None


def recipients_from_document(document: Mapping) -> list[Recipient]:
    """Parse one already-loaded document. Pure, and the half worth testing.

    Order is the file's order, and the file's order is the order a grown-up put
    them in on the Family tab. A "who is this for?" screen that re-sorted itself
    between sessions would move a four-year-old's Nanna, and B1's spatial
    stability is the one thing a pre-reader navigates by.
    """
    rows = document.get(FAMILY_KEY)
    if not isinstance(rows, list):
        if rows is not None:
            log.warning("%s is not a list of tables; there is nobody to write to", FAMILY_KEY)
        return []

    found: list[Recipient] = []
    seen: set[str] = set()
    for raw in rows:
        if not isinstance(raw, Mapping):
            log.warning("skipping a [[%s]] entry that is not a table", FAMILY_KEY)
            continue
        name = str(raw.get("name", "")).strip()
        if not name:
            # A face with no name cannot be announced, and this activity is
            # announced before it is read. Skipping is the honest answer.
            log.warning("skipping a [[%s]] entry with no name", FAMILY_KEY)
            continue
        identifier = str(raw.get("id", "")).strip() or slugify(name)
        if identifier in seen:
            log.warning("skipping a second [[%s]] entry with id %r", FAMILY_KEY, identifier)
            continue
        seen.add(identifier)
        found.append(
            Recipient(
                id=identifier,
                name=name,
                relation=str(raw.get("relation", "")).strip(),
                photo=str(raw.get("photo", "")).strip(),
            )
        )
    return found


def load_recipients(search: Sequence[Path] | None = None) -> list[Recipient]:
    """Everyone a grown-up said this child may write to. Never raises."""
    document, path = read_document(search)
    people = recipients_from_document(document)
    if path is None:
        log.info("no %s found; there is nobody to write to yet", CONFIG_NAME)
    else:
        log.info("%d recipient(s) from %s", len(people), path)
    return people


def by_id(people: Sequence[Recipient], identifier: str) -> Recipient | None:
    """Find one. Used when resuming and when a screenshot run names one."""
    for person in people:
        if person.id == identifier:
            return person
    return None
