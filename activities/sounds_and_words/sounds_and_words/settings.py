"""What the parent said the school has taught, and where this child's history lives.

Two files, and neither of them is written by the child:

``/etc/kidnix/sounds_and_words.toml``
    The **ceiling**. Root-owned, the same place and the same ownership rule as
    the shell's ``parent.toml`` (:mod:`kidnix_shell.settings`): the child owns
    ``$XDG_CONFIG_HOME`` and a child-writable ceiling is not a ceiling. Falls
    back to ``/usr/share/kidnix/sounds_and_words.toml``, which is the image's
    shipped default, because bootc's three-way merge makes ``/etc`` the
    parent's copy and ``/usr/share`` ours.

``$XDG_STATE_HOME/kidnix/profiles/<id>/sounds-and-words/history.json``
    The **schedule**. Per child (``KIDNIX_PROFILE_ID``), because two siblings
    sharing one Leitner box means neither one's spacing is real. JSON, indented,
    with the dates written out: research 10 section 4.3 says a parent can read
    the model in a text editor, and that is only true if it is legible.

**The dev default is Phase 2, set 3** -- ``s a t p i n m d g o c k``, twelve
GPCs and seventy-two words. It is what a machine with no config file uses, and
it is chosen low on purpose: research 10 section 4.5, *"starting too low costs
nothing; a five-year-old re-reading sat, pat, tap is not harmed"*, whereas a
default that guessed high would show a child a sound the school has not taught,
which is the one thing this activity may never do.

Nothing here infers, advances or widens a ceiling. The only way the ceiling
moves is a grown-up editing that file (week 5 gives them a pane to do it in).
"""

from __future__ import annotations

import json
import logging
import os
import tomllib
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date
from enum import StrEnum
from pathlib import Path

from .ceiling import Ceiling
from .corpus import Corpus
from .schedule import History
from .schemes import DEFAULT_SCHEME, resolve_ceiling

log = logging.getLogger(__name__)

__all__ = [
    "CONFIG_NAME",
    "DEV_DEFAULT_LAST_GRAPHEME",
    "DEV_DEFAULT_SCHEME",
    "Narration",
    "ParentCeiling",
    "Progress",
    "config_candidates",
    "load_narration",
    "load_parent_ceiling",
    "load_progress",
    "progress_dir",
    "resolve",
    "save_progress",
]

#: The file the grown-up's answers land in.
CONFIG_NAME = "sounds_and_words.toml"

#: Root-owned config, in order: the parent's copy, then the image's default.
#: A list rather than a tuple so a test can point it somewhere writable --
#: nothing derived from the child's own environment is ever added to it.
CONFIG_SEARCH_PATH: list[Path] = [Path("/etc/kidnix"), Path("/usr/share/kidnix")]

#: Letters and Sounds, because it is the only ordering kidnix ships in full.
DEV_DEFAULT_SCHEME = DEFAULT_SCHEME
#: Phase 2, set 3: ``g o c k``. The last grapheme of the third of L&S's four
#: Phase 2 sets, so a machine with no config still has twelve GPCs, seventy-two
#: words and every one of them provably taught to a child in their first term.
DEV_DEFAULT_LAST_GRAPHEME = "k"

class Narration(StrEnum):
    """Whether Read it reads the book out loud. ``[read] narration``, parent's.

    Takacs, Swart & Bus (2015) is the reason there is narration at all --
    narrated text with congruent illustration beats a plain adult reading. It
    is the reason the default is not ``always``, too: the same meta-analysis is
    about a *story being read to a child*, and the point of this module is a
    child reading it themselves, out loud, to somebody. A voice that starts on
    its own every page is a voice that reads the book for them.

    ``optional``
        the default. Nothing is spoken until the child presses *"read it to
        me"* -- which is a thing a child who is stuck should be able to do
        without asking, and which is also how a grown-up hears what the words
        are meant to sound like.
    ``always``
        the sentence is read as each page arrives. For a child who cannot yet
        get through a page alone and for whom being stuck is worse than being
        read to; also what a parent choosing an audio-first setup would want.
    ``never``
        no voice and no button. For a household that wants the reading to be
        the child's own, and for a machine where the voice is a distraction.

    There is no fourth value and no per-book override. It is one answer for one
    child, and it lives in the same root-owned file as the ceiling.
    """

    OPTIONAL = "optional"
    ALWAYS = "always"
    NEVER = "never"

    @property
    def offers_button(self) -> bool:
        """Is there a *"read it to me"* button on the page?"""
        return self is not Narration.NEVER

    @property
    def speaks_on_arrival(self) -> bool:
        """Does the page read itself as it appears?"""
        return self is Narration.ALWAYS


#: What a machine with no ``[read]`` table uses.
DEFAULT_NARRATION = Narration.OPTIONAL


def load_narration(*, search: list[Path] | None = None, name: str = CONFIG_NAME) -> Narration:
    """Read ``[read] narration`` from the same root-owned file as the ceiling.

    Never raises, and an unknown value falls back to the default **and says so
    in the log**, exactly as the ceiling does: a grown-up's typo must not become
    "the computer is broken" to a child, and a silent fallback nobody can see
    is how a setting comes to look ignored.
    """
    directories = CONFIG_SEARCH_PATH if search is None else search
    for path in (directory / name for directory in directories):
        try:
            if not path.is_file():
                continue
            with path.open("rb") as handle:
                doc = tomllib.load(handle)
        except (OSError, tomllib.TOMLDecodeError) as exc:
            log.warning("could not read %s: %s; narration stays %s", path, exc, DEFAULT_NARRATION)
            continue
        section = doc.get("read")
        if not isinstance(section, dict) or "narration" not in section:
            continue
        raw = str(section.get("narration", "")).strip().lower()
        try:
            return Narration(raw)
        except ValueError:
            log.warning(
                "%s: [read] narration=%r is not one of %s; using %s",
                path,
                raw,
                ", ".join(option.value for option in Narration),
                DEFAULT_NARRATION,
            )
            continue
    return DEFAULT_NARRATION


#: Where a child's own copy lives, under the profile the shell exported.
PROGRESS_SUBDIR = "sounds-and-words"
PROGRESS_NAME = "history.json"

#: The shape of ``history.json``, so a later reader can tell what it is holding.
PROGRESS_SCHEMA = 1


@dataclass(frozen=True)
class ParentCeiling:
    """The grown-up's two answers, and where they were read from.

    ``source`` is ``None`` when nobody has answered and the dev default is
    standing in. That distinction is not cosmetic: the parent pane has to be
    able to say *"nobody has told us yet, so we are starting at the beginning"*
    rather than presenting kidnix's guess back to a parent as their own
    statement.
    """

    scheme: str = DEV_DEFAULT_SCHEME
    last_grapheme: str = DEV_DEFAULT_LAST_GRAPHEME
    source: Path | None = None

    @property
    def is_default(self) -> bool:
        """Did this come out of a file, or is it the built-in floor?"""
        return self.source is None

    def describe(self) -> str:
        """One line for the log at start-up, naming the file that decided it."""
        where = str(self.source) if self.source is not None else "(no config; dev default)"
        return f"scheme={self.scheme} last_grapheme={self.last_grapheme!r} from {where}"


def config_candidates(name: str = CONFIG_NAME) -> list[Path]:
    """Every place the ceiling may be written, in the order they are read."""
    return [directory / name for directory in CONFIG_SEARCH_PATH]


def load_parent_ceiling(
    *, search: list[Path] | None = None, name: str = CONFIG_NAME
) -> ParentCeiling:
    """Read ``[ceiling]`` from the first readable root-owned file.

    Never raises. A malformed file, a missing key or an unreadable path all
    come back as the dev default with a line in the log: an activity that
    refused to start because a grown-up mistyped a TOML key would have turned
    a typo into a child being told the computer is broken.
    """
    directories = CONFIG_SEARCH_PATH if search is None else search
    for path in (directory / name for directory in directories):
        try:
            if not path.is_file():
                continue
            with path.open("rb") as handle:
                doc = tomllib.load(handle)
        except (OSError, tomllib.TOMLDecodeError) as exc:
            log.warning("could not read %s: %s; using the default ceiling", path, exc)
            continue
        section = doc.get("ceiling")
        if not isinstance(section, dict):
            log.warning("%s has no [ceiling] table; using the default ceiling", path)
            continue
        scheme = str(section.get("scheme") or DEV_DEFAULT_SCHEME).strip()
        last = str(section.get("last_grapheme", "")).strip()
        if not last:
            log.warning("%s: [ceiling] last_grapheme is empty; using the default", path)
            continue
        return ParentCeiling(scheme=scheme, last_grapheme=last, source=path)
    return ParentCeiling()


def resolve(corpus: Corpus, parent: ParentCeiling | None = None) -> Ceiling:
    """Turn the grown-up's two answers into the hard gate.

    Delegates to :func:`sounds_and_words.schemes.resolve_ceiling`, which is
    where the conservative-intersection policy lives. A scheme or grapheme this
    corpus has never heard of falls back to the dev default rather than
    exploding -- and says so, once, in the log, because a silent fallback to a
    *lower* ceiling is safe and a silent fallback nobody can see is not.
    """
    parent = parent or load_parent_ceiling()
    try:
        return resolve_ceiling(corpus, parent.scheme, parent.last_grapheme)
    except KeyError as exc:
        log.warning(
            "%s; falling back to the default ceiling (%s, up to %r)",
            exc,
            DEV_DEFAULT_SCHEME,
            DEV_DEFAULT_LAST_GRAPHEME,
        )
        return resolve_ceiling(corpus, DEV_DEFAULT_SCHEME, DEV_DEFAULT_LAST_GRAPHEME)


# -- this child's history ---------------------------------------------------


def progress_dir(env: Mapping[str, str] | None = None) -> Path:
    """``$XDG_STATE_HOME/kidnix/profiles/<id>/sounds-and-words``.

    The same spelling :class:`kidnix_shell.settings.Paths` uses for
    ``profile_state``, computed here without importing it so that the pure half
    of this activity stays importable on a machine with no shell and no GTK.
    ``tests/test_sdk_agreement.py`` asserts the two answers are identical
    wherever the SDK *is* importable, which is what stops them drifting.

    An empty or absent ``KIDNIX_PROFILE_ID`` gives the pre-profiles layout,
    exactly as the SDK does: it is the right answer on a machine that has never
    had profiles, and the only one we are entitled to when the shell did not
    say which child is sitting there.
    """
    environ = dict(os.environ if env is None else env)
    home = Path(environ.get("HOME", str(Path.home())))
    state = environ.get("XDG_STATE_HOME")
    root = (Path(state) if state else home / ".local" / "state") / "kidnix"
    profile = environ.get("KIDNIX_PROFILE_ID", "").strip()
    if profile:
        root = root / "profiles" / profile
    return root / PROGRESS_SUBDIR


@dataclass
class Progress:
    """This child's Leitner boxes, plus the day counter they are indexed by.

    ``schedule.History`` counts in *days since this child first opened the
    activity*, which keeps the arithmetic in one place and the file free of
    date parsing. ``first_day`` is what turns that integer back into a real
    date, and it is stored so a machine that is off for a fortnight resumes
    with the right intervals rather than a fortnight of "everything is due".
    """

    history: History
    first_day: date | None = None
    last_day: date | None = None

    def day_index(self, today: date) -> int:
        """Which day number ``today`` is. Zero on the first ever session."""
        if self.first_day is None:
            return 0
        return max(0, (today - self.first_day).days)

    def touch(self, today: date) -> int:
        """Record that a session happened today. Returns the day index.

        A clock that has gone *backwards* -- a machine whose RTC was wrong on
        first boot and is right now -- would otherwise give a negative day and
        make everything permanently overdue. ``max(0, ...)`` in
        :meth:`day_index` handles the arithmetic; re-basing ``first_day`` here
        handles the cause, and a note in the log says it happened.
        """
        if self.first_day is None:
            self.first_day = today
        elif today < self.first_day:
            log.info("clock moved backwards (%s < %s); re-basing the schedule", today, self.first_day)
            self.first_day = today
        self.last_day = today
        return self.day_index(today)

    def to_dict(self) -> dict:
        return {
            "schema": PROGRESS_SCHEMA,
            "first_day": self.first_day.isoformat() if self.first_day else None,
            "last_day": self.last_day.isoformat() if self.last_day else None,
            "gpcs": self.history.to_dict(),
        }

    @classmethod
    def from_dict(cls, doc: Mapping) -> Progress:
        def parsed(key: str) -> date | None:
            raw = doc.get(key)
            if not isinstance(raw, str):
                return None
            try:
                return date.fromisoformat(raw)
            except ValueError:
                log.warning("history.json: %s=%r is not a date; ignoring it", key, raw)
                return None

        gpcs = doc.get("gpcs")
        return cls(
            history=History.from_dict(gpcs if isinstance(gpcs, dict) else {}),
            first_day=parsed("first_day"),
            last_day=parsed("last_day"),
        )


def load_progress(path: Path) -> Progress:
    """Read the child's history, or start an empty one.

    Never raises. A corrupt file costs the spacing schedule, which the child
    cannot see and which rebuilds itself over a few sessions; refusing to open
    the activity would cost them the activity. The bad file is left on disk
    rather than overwritten, so whoever debugs it still has it.
    """
    try:
        with path.open("rb") as handle:
            doc = json.load(handle)
    except FileNotFoundError:
        return Progress(History())
    except (OSError, ValueError) as exc:
        log.warning("could not read %s: %s; starting a fresh schedule", path, exc)
        return Progress(History())
    if not isinstance(doc, dict):
        log.warning("%s is not an object; starting a fresh schedule", path)
        return Progress(History())
    return Progress.from_dict(doc)


def save_progress(path: Path, progress: Progress) -> Path:
    """Write the history, atomically. Returns the path it wrote.

    Written beside the real file and renamed over it: a session that is being
    killed at put-away time (SIGTERM, five seconds, spec 7a) must not be able
    to leave a half-written JSON file that the next session refuses to read.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".new")
    payload = json.dumps(progress.to_dict(), indent=2, sort_keys=True) + "\n"
    temporary.write_text(payload, encoding="utf-8")
    temporary.replace(path)
    return path
