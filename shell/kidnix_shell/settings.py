"""XDG paths, child profiles and the parent-owned config (PIN, allow-list).

**Ownership is the whole point of this module.** The child's own account must
never be able to rewrite the PIN, the allow-list or the session policy -- they
are the only things standing between a five-year-old and an unbounded computer,
and ``~/.config`` belongs to the five-year-old. So:

* ``/etc/kidnix/parent.toml`` -- PIN hash, default session length, the activity
  allow-list, the child profiles. Root-owned. Falls back to
  ``/usr/share/kidnix/parent.toml`` (the image's defaults), and then to
  built-in defaults with a loud warning. **Never** read from the kid's home;
  the only exception is an explicit ``--config PATH`` from the command line,
  which is a developer typing a path, not the child.
* ``/etc/kidnix/session.toml`` -- session policy, same rules. Read by
  :mod:`kidnix_shell.session`.
* ``$XDG_STATE_HOME/kidnix/usage.toml`` and
  ``$XDG_DATA_HOME/kidnix/journal/`` -- today's usage, the things the child
  made, the favourites. Kid-owned, kid-writable, and nothing in them can widen
  what the child is allowed to do.

TOML both ways. ``tomllib`` cannot write, so there is a small dumper here for
the flat schema we actually use rather than a third-party dependency. Writing
is for the *parent's* tooling (and the tests); the shell running as the child
treats a config it read from a system path as read-only and says so.
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import os
import secrets
import sys
import tomllib
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any

from .access import AccessConfig, parse_access
from .next_after import DEFAULT_NEXT_AFTER, NextAfter, parse_next_after

log = logging.getLogger(__name__)

DEFAULT_PIN = "1234"  # spec S9: dev default, replaced by the parent

#: **The PIN the image actually ships**, hashed with the fixed public salt in
#: ``/usr/share/kidnix/parent.toml``. It is here so the shell can recognise it.
#:
#: ``is_default`` was only ever true when *no* ``pin_hash`` was found -- and the
#: shipped file has one, so on a stock install the "this machine has no parent
#: config" warning never appeared. "The one signal that the gate is open was
#: suppressed by the file that opens it" (forum #44), and the grandmother who
#: raised it put the consequence plainly: "the only way I would ever learn my
#: lock is not a lock is by reading a file I would never open" (#56).
#:
#: hardening.md section 6 already says the rule -- "still 1234 means
#: unconfigured, never secured". This is that rule, in code.
STARTER_PIN_SALT = "9f2c1a6d4b8e0357c9d1e2f3a4b5c6d7"
STARTER_PIN_HASH = "3d6495d0f726f531cef756cad4ee152a662ac68a68782658c75494d91c267f4d"
#: Spec 7b / 09 section 2: 450 ms, up from v0.1.3's 300 ms, and gated on the
#: pointer having settled. See :mod:`kidnix_shell.speech`.
DEFAULT_HOVER_DWELL_MS = 450
#: Bounds a hand edit. Below the floor the shell chatters at a child sweeping a
#: grid; above the ceiling hover-to-speak has stopped being ambient.
MIN_HOVER_DWELL_MS = 150
MAX_HOVER_DWELL_MS = 3000
PBKDF2_ROUNDS = 200_000
SYSTEM_CONFIG_DIR = Path("/etc/kidnix")
#: The image's shipped defaults, used when /etc has nothing (bootc's 3-way
#: merge means /etc is the parent's copy, /usr/share is ours).
SYSTEM_DEFAULT_DIR = Path("/usr/share/kidnix")

#: 08 section 3.4 -- colour is *whose it is*, shape is *what it is*. Each
#: profile owns a two-colour identity used for its avatar, band tint, focus
#: rings and journal cards.
#:
#: **Rechosen 2026-08-23 under colour-vision simulation.** The old pairs 2
#: (green ``#2e7d32``) and 4 (rust ``#bf360c``) are 1.09:1 apart in luminance
#: and simulate to ``#6d6d35`` and ``#757500`` under deuteranopia -- the same
#: colour, to the ~8% of boys who are colour-blind and mostly do not know it,
#: on the one signal that says whose computer this is. Green became navy
#: ``#1a237e`` and violet moved to ``#5e35b1``; the shipped teal/pink profile
#: is untouched. Every pair is now at least 0.40 apart in a weighted linear
#: distance under *both* deuteranopia and protanopia (Vienot 1999), against
#: 0.11 before -- ``tests/test_theme_css.py`` recomputes all of it.
#:
#: Four colours **cannot** be made pairwise 3:1 apart in luminance: each step
#: needs 3x and four of them need 27x, while the whole legal range under
#: "a band button must stand out from the band" is 6.3x. That is arithmetic,
#: not an oversight, which is why :data:`PROFILE_BADGES` exists.
PROFILE_COLOURS: tuple[tuple[str, str], ...] = (
    ("#0f8a8a", "#f06292"),  # teal / pink
    ("#1a237e", "#ffd54f"),  # navy / butter
    ("#5e35b1", "#80deea"),  # violet / cyan
    ("#bf360c", "#aed581"),  # rust / leaf
)

#: **Shape is the other half of identity** (M2, forum #22). Colour alone
#: cannot say whose computer this is -- not under CVD, not in greyscale, not
#: to a child who has not learned "the green one is mine". Each profile also
#: owns a small glyph, drawn in the corner of its face on Who's here, and it
#: is chosen so the four are told apart by *silhouette*: a point, a round, a
#: crescent and a horizontal line survive being 6 mm across and out of focus.
PROFILE_BADGES: tuple[str, ...] = ("star", "leaf", "moon", "wave")

#: Where root-owned config may live, in order. Module-level so a test (or a
#: developer with a container) can point it somewhere else; nothing derived
#: from the child's environment is ever added to it.
CONFIG_SEARCH_PATH: list[Path] = [SYSTEM_CONFIG_DIR, SYSTEM_DEFAULT_DIR]


def system_config_candidates(name: str) -> list[Path]:
    return [directory / name for directory in CONFIG_SEARCH_PATH]


def first_system_config(name: str) -> Path | None:
    """The first readable root-owned copy of ``name``, or ``None``."""
    for candidate in system_config_candidates(name):
        if candidate.is_file():
            return candidate
    return None


def is_system_path(path: Path | None) -> bool:
    """True if ``path`` is inside one of the root-owned config directories."""
    if path is None:
        return False
    return any(path == directory / path.name for directory in CONFIG_SEARCH_PATH)


#: Where a child's own things live under ``kidnix/``. **One directory per
#: profile since 2026-08-23** (spec 7d #11): until then a second child on the
#: same machine shared the first one's Journal, their daily budget and their
#: progressive-disclosure counter, so "profiles are cosmetic" (forum #4) was
#: literally true -- the colour changed and nothing else did. A parent panel
#: reviewer put the consequence plainly: "one journal, one budget, one
#: disclosure counter per machine" is a blocker for a second child.
PROFILES_DIR = "profiles"


@dataclass(frozen=True)
class Paths:
    """Every directory the shell touches, resolved once and passed around.

    Built from the environment so tests can point the whole shell at a tmpdir.

    ``profile`` is which child's things these are. Empty is the **legacy**
    layout -- ``kidnix/journal``, ``kidnix/usage.toml`` -- which is what every
    machine built before 2026-08-23 has on disk and what
    :func:`migrate_profile_data` moves out of the way exactly once.
    """

    home: Path
    data_home: Path
    config_home: Path
    cache_home: Path
    state_home: Path
    runtime_dir: Path | None = None
    #: The profile id these paths belong to. ``""`` is the pre-profiles layout.
    profile: str = ""

    @classmethod
    def from_env(cls, env: dict[str, str] | None = None) -> Paths:
        environ = dict(os.environ if env is None else env)
        home = Path(environ.get("HOME", str(Path.home())))

        def xdg(key: str, default: Path) -> Path:
            raw = environ.get(key)
            return Path(raw) if raw else default

        runtime = environ.get("XDG_RUNTIME_DIR")
        return cls(
            home=home,
            data_home=xdg("XDG_DATA_HOME", home / ".local" / "share"),
            config_home=xdg("XDG_CONFIG_HOME", home / ".config"),
            cache_home=xdg("XDG_CACHE_HOME", home / ".cache"),
            state_home=xdg("XDG_STATE_HOME", home / ".local" / "state"),
            runtime_dir=Path(runtime) if runtime else None,
        )

    def for_profile(self, profile_id: str) -> Paths:
        """The same machine, this child's things.

        A whole :class:`Paths` rather than three extra properties, so nothing
        downstream has to remember to ask for the per-profile spelling: the
        Journal, the usage file and the progress file all move together or none
        of them does.
        """
        return replace(self, profile=profile_id or "")

    def _owned(self, base: Path) -> Path:
        """``<base>/kidnix`` for the legacy layout, ``.../profiles/<id>`` now."""
        root = base / "kidnix"
        return root / PROFILES_DIR / self.profile if self.profile else root

    @property
    def profile_data(self) -> Path:
        """This child's data directory. What ``kidnix-export`` copies."""
        return self._owned(self.data_home)

    @property
    def profile_state(self) -> Path:
        """This child's state directory: usage and progress."""
        return self._owned(self.state_home)

    @property
    def journal_root(self) -> Path:
        """Spec section 5: ``$XDG_DATA_HOME/kidnix/profiles/<id>/journal/``.

        The profile segment is inside ``kidnix/`` rather than beside it so that
        one export, one wipe and one backup still take everything: a parent
        reasoning about "where does my child's work live" gets one answer.
        """
        return self.profile_data / "journal"

    @property
    def parent_config(self) -> Path | None:
        """The parent config, or ``None`` if the machine has no root-owned one.

        Deliberately *not* falling back to ``$XDG_CONFIG_HOME``: the child owns
        that directory, and a child-writable PIN is not a PIN.
        """
        return first_system_config("parent.toml")

    @property
    def session_config(self) -> Path | None:
        """The session policy. Same ownership rule as the parent config."""
        return first_system_config("session.toml")

    @property
    def sounds_cache(self) -> Path:
        """Where generated earcons land when ``/usr`` is read-only."""
        return self.cache_home / "kidnix" / "sounds"

    @property
    def usage_state(self) -> Path:
        """Kid-owned: how much of **this child's** budget today has been spent.

        Per profile since 2026-08-23. Sharing it meant a second child's first
        sitting of the day started with their sibling's hour already spent --
        the daily budget is a policy about one child's afternoon, not about the
        machine's.
        """
        return self.profile_state / "usage.toml"

    @property
    def progress_state(self) -> Path:
        """Kid-owned: how many sessions have been completed, ever.

        Deliberately *not* in ``usage.toml``: that file resets every day at
        04:00, and progressive disclosure (spec 7b, SYNTHESIS B2) counts across
        the whole life of the machine. Nothing in here can widen what the child
        is allowed to do -- the ceiling is still the allow-list.

        Per profile: progressive disclosure counts *this child's* sessions, and
        a younger sibling should not inherit an older one's grid.
        """
        return self.profile_state / "progress.toml"


#: What :func:`migrate_profile_data` moves, relative to ``kidnix/`` in the data
#: and state directories respectively. Journal first, because it is the one
#: whose loss a child would notice.
LEGACY_DATA = ("journal",)
LEGACY_STATE = ("usage.toml", "progress.toml")


def migrate_profile_data(paths: Paths, profile_id: str) -> list[Path]:
    """Move a pre-profiles machine's data into its **first** profile. Once.

    Every machine built before 2026-08-23 has ``kidnix/journal`` and
    ``kidnix/usage.toml`` where the profile directories now go. Doing nothing
    would present a child with an empty My Things on the morning of an upgrade,
    which is the one failure "nothing is ever deleted" (SYNTHESIS C2) exists to
    prevent -- so the old layout is *moved*, not copied and not left behind.

    Three properties, and all three are tested:

    * **Idempotent.** A destination that already exists is never touched; the
      second run finds nothing to move and says nothing.
    * **Non-destructive.** ``Path.rename`` within one filesystem, and a
      destination that exists is a reason to stop rather than to overwrite. If
      a machine somehow has both, the profile's own copy wins and the legacy
      one is left where a parent can find it.
    * **Never fatal.** A read-only disk, a permission problem, a half-mounted
      home: logged, and the session carries on with an empty Journal rather
      than not starting.

    Returns what was moved, for the log line and for the test.
    """
    if not profile_id:
        return []
    target = paths.for_profile(profile_id)
    moved: list[Path] = []
    plan = [
        (paths.data_home / "kidnix" / name, target.profile_data / name) for name in LEGACY_DATA
    ] + [(paths.state_home / "kidnix" / name, target.profile_state / name) for name in LEGACY_STATE]
    for source, destination in plan:
        if not source.exists() or destination.exists():
            continue
        try:
            destination.parent.mkdir(parents=True, exist_ok=True)
            source.rename(destination)
        except OSError as exc:
            log.warning("could not move %s to %s (%s); leaving it alone", source, destination, exc)
            continue
        moved.append(destination)
        log.info("moved %s into profile %r", source, profile_id)
    if moved:
        log.info("migrated %d item(s) into the first profile (%s)", len(moved), profile_id)
    return moved


# --- PIN -----------------------------------------------------------------


def hash_pin(pin: str, salt: str | None = None) -> tuple[str, str]:
    """Return ``(salt_hex, hash_hex)``. Never store the PIN itself."""
    salt_hex = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", pin.encode("utf-8"), bytes.fromhex(salt_hex), PBKDF2_ROUNDS
    )
    return salt_hex, digest.hex()


def verify_pin(pin: str, salt_hex: str, hash_hex: str) -> bool:
    if not salt_hex or not hash_hex:
        return False
    try:
        _, candidate = hash_pin(pin, salt_hex)
    except ValueError:  # malformed salt in a hand-edited config
        return False
    return hmac.compare_digest(candidate, hash_hex)


# --- profiles ------------------------------------------------------------


@dataclass(frozen=True)
class Profile:
    """A child. v0.1 ships one; the data model supports N (spec section 1.7)."""

    id: str
    name: str
    colour_primary: str = PROFILE_COLOURS[0][0]
    colour_secondary: str = PROFILE_COLOURS[0][1]
    avatar: str = "face-smile"
    #: The shape half of "colour = whose it is" (:data:`PROFILE_BADGES`). A
    #: name, not a path: the icon is ``kidnix-badge-<badge>`` in the shell's
    #: own set, so a hand-edited config cannot point it at a file.
    badge: str = PROFILE_BADGES[0]
    #: 01 #35 / SYNTHESIS B8: a *fine* band, set by the parent. ``"4-5"`` is
    #: the shipped default, which puts the target five-year-old in the middle
    #: of it. An empty string means "the parent has not said", and nothing is
    #: filtered -- we do not guess a child's age.
    age_band: str = "4-5"
    #: Spec 7b: skip S1b "What's next after?" for this child and go straight
    #: Home. The screen is a good idea with evidence behind it (Coco's Videos)
    #: and it is still one more thing between a child and the thing they came
    #: to do, so a parent may turn it off per child.
    skip_next_choice: bool = False
    #: **This child's language** (ADR-0012, docs/design/i18n.md). ``""`` means
    #: "the machine's" (``[access] language``, then the environment). It is per
    #: *child* and not per machine because 23.8% of English primary pupils have
    #: a first language other than English (DfE Jan 2026) and a bilingual
    #: household is one where the siblings do not always match. Anything
    #: gettext understands: ``"cy"``, ``"pl"``, ``"en_GB"``.
    #:
    #: Changing it mid-session reinstalls the catalogue and **rebuilds the
    #: screens** (:meth:`kidnix_shell.app.ShellWindow._use_profile`); a
    #: same-language switch does nothing at all.
    language: str = ""
    #: **This child's own allow-list** (parent-panel section 7.2). ``()`` means
    #: "the parent has not narrowed it for this child", and the machine-wide
    #: :attr:`ParentConfig.allowed_activity_ids` is used instead -- the same
    #: empty-means-all reading as that list, one level down. Never a
    #: *narrowing* of the machine list: a per-child list that is set replaces
    #: it outright, because the panel writes the machine list as the **union**
    #: of the active children's and intersecting the two would hand a child
    #: less than the parent ticked for them.
    allowed_activity_ids: tuple[str, ...] = ()

    @property
    def speak_text(self) -> str:
        return self.name

    @property
    def age_range(self) -> tuple[int, int] | None:
        """``(low, high)`` from :attr:`age_band`, or ``None`` if unset/unparsable."""
        from .activities import parse_age_band

        return parse_age_band(self.age_band)


DEFAULT_PROFILE = Profile(id="child", name="Me")


def _allow_list(raw: Any) -> tuple[str, ...]:
    """A profile's ``allowed_activity_ids``. Anything odd becomes ``()``.

    ``()`` is "the parent has not narrowed it for this child", which falls
    back to the machine-wide list -- so a hand-edited profile with a string
    where a list should be widens rather than locks a child out.
    """
    if not isinstance(raw, (list, tuple)):
        if raw is not None:
            log.warning("parent config: a profile's allowed_activity_ids is not a list; ignoring")
        return ()
    return tuple(str(item) for item in raw)


def shelf_child_allowed(
    allowed: Sequence[str],
    child_id: str,
    shelf_id: str,
    children: Iterable[str],
) -> bool:
    """May this child open one game *inside* a shelf? (spec 7d #12)

    An allow-list has two levels for a shelf -- the shelf's own id and its
    children's -- and the parent panel writes both
    (``kidnix_parent_panel.ui.activities``: the expander's switch is the shelf,
    the rows inside it are the children). A parent who hand-edits
    ``parent.toml`` writes only the first, because the shelf's id is the one
    written in the file's own example and the one they saw on Home. Reading
    such a list per child gave eighteen tiles that all said "Ask a grown-up for
    this one" behind a tile that opened, which is the opposite of what the
    parent asked for.

    So the rule, and it is exactly two sentences:

    * a child is allowed when **its own id** is in the list, and
    * when **the shelf's id** is in the list and *no* child of that shelf is
      listed at all -- naming the shelf and nothing under it means the shelf.

    A parent who expressed per-child choices is honoured to the letter: as soon
    as one child of the shelf appears, the shelf's own entry stops standing in
    for the others, and an unlisted sibling is refused. Empty is "everything",
    the same reading as everywhere else in this file.

    Pure, and it takes the *effective* list
    (:meth:`ParentConfig.effective_allow_list`) rather than a config, because
    which of the two lists decides is not this rule's business.
    """
    if not allowed:
        return True
    if child_id in allowed:
        return True
    if shelf_id not in allowed:
        return False
    return not any(child in allowed for child in children)


def shelf_tile_allowed(allowed: Sequence[str], shelf_id: str, children: Iterable[str]) -> bool:
    """May the shelf's own tile on Home be pressed? The mirror of the above.

    A parent who hand-lists one game (``gcompris.erase``) and not the shelf
    has still asked for that game -- and the only door to it is the shelf's
    tile. Denying the tile because the shelf's id is missing strands the very
    thing the list names behind "Ask a grown-up", asked about a thing the
    grown-up already gave. So the shelf tile is allowed when the list is
    empty, when the shelf's own id is in it, **or when any of its children
    is** -- the shelf is a door, and a door is allowed when anything behind
    it is.
    """
    if not allowed or shelf_id in allowed:
        return True
    return any(child in allowed for child in children)


# --- progressive disclosure (spec 7b, SYNTHESIS B2) ----------------------

#: How many tiles a brand-new machine shows, **including "All done"**. 09
#: section 3 splits the ceiling from the default: twelve is a geometry-and-
#: visual-search limit, not a working-memory one, but a first run should still
#: be a small screen. Six is the top of 09's "first-run default 5-6".
DEFAULT_INITIAL_TILES = 6
#: One more tile after every N completed sessions.
DEFAULT_REVEAL_EVERY_SESSIONS = 2
#: A tile is never *taken away*: the count only ever goes up, and the ceiling
#: is whatever the allow-list and availability already left on Home.
MIN_INITIAL_TILES = 2


@dataclass(frozen=True)
class HomeConfig:
    """``[home]`` in ``parent.toml``: how fast Home grows.

    Working-memory limits bind on *held* option sets, not on a visible,
    labelled, spatially stable grid (Pailian 2016; Schneider 2021), so the
    reason to start small is not capacity -- it is that a child meeting a
    computer for the first time should meet five things, learn them, and be
    handed a sixth once they are theirs. ``show_everything`` is the parent's
    override for a child who has been using it for a year.
    """

    initial_tiles: int = DEFAULT_INITIAL_TILES
    reveal_every_sessions: int = DEFAULT_REVEAL_EVERY_SESSIONS
    #: **True by default since 2026-08-23.** The argument for growing Home is a
    #: good one; it is not worth an unannounced new button every fortnight to a
    #: child who navigates by position and does not experience the schedule
    #: (forum #9, #26, #40). ``reveal_every_sessions`` now applies only when a
    #: parent has deliberately set ``show_everything = false``.
    show_everything: bool = True

    def tiles_visible(self, total: int, sessions_completed: int) -> int:
        """How many of ``total`` Home cells this child has earned.

        Total and floor are both honoured: a machine can never show more than
        Home actually has, and never fewer than "one activity plus All done".
        """
        if self.show_everything:
            return total
        every = max(1, self.reveal_every_sessions)
        start = max(MIN_INITIAL_TILES, self.initial_tiles)
        return max(0, min(total, start + max(0, sessions_completed) // every))


@dataclass
class KidState:
    """Kid-owned counters that outlive a day (``progress.toml``).

    One number today: how many sessions have been *completed* -- i.e. reached
    Goodbye. It is the clock for progressive disclosure and nothing else. It is
    not a streak, it is never shown to the child, and losing the file costs a
    child a couple of tiles, not their work.
    """

    sessions_completed: int = 0
    path: Path | None = None

    @classmethod
    def load(cls, path: Path) -> KidState:
        if not path.is_file():
            return cls(path=path)
        try:
            with path.open("rb") as handle:
                data = tomllib.load(handle)
            completed = int(data.get("sessions_completed", 0))
        except (OSError, ValueError, TypeError, tomllib.TOMLDecodeError) as exc:
            log.warning("kid state %s unreadable (%s); starting fresh", path, exc)
            return cls(path=path)
        return cls(sessions_completed=max(0, completed), path=path)

    def save(self, path: Path | None = None) -> None:
        target = path or self.path
        if target is None:
            return
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(f"sessions_completed = {self.sessions_completed}\n", encoding="utf-8")
        except OSError as exc:  # a full disk must never end a child's session
            log.warning("could not save kid state to %s (%s)", target, exc)
            return
        self.path = target

    def complete_session(self) -> int:
        """One more session reached Goodbye. Returns the new total."""
        self.sessions_completed += 1
        self.save()
        return self.sessions_completed


# --- parent config -------------------------------------------------------


@dataclass
class ParentConfig:
    """Everything the grown-up sheet can change."""

    pin_salt: str = ""
    pin_hash: str = ""
    default_session_minutes: int = 25
    #: **Empty or missing means "every installed activity is allowed".** A
    #: non-empty list restricts Home to those ids; the rest render outline-only
    #: and speak "Ask a grown-up for this one" (spec S2, SYNTHESIS G3).
    #:
    #: Empty-means-all is the deliberate reading: a parent panel that writes
    #: ``allowed_activity_ids = []`` while a parent unticks the last box must
    #: not hand a five-year-old a Home screen with nothing on it but "All
    #: done". Denying everything is not a setting anyone wants by accident.
    allowed_activity_ids: list[str] | None = None
    profiles: list[Profile] = field(default_factory=lambda: [DEFAULT_PROFILE])
    #: Spec 7b / SYNTHESIS B4: how long the pointer has to have *settled* on a
    #: control before read-aloud speaks it. 450 ms is extrapolated from adult
    #: gaze-dwell work (Paulus & Remijn 2021); there is no child evidence, and
    #: it is the first parameter to tune in child testing (protocol P5), which
    #: is exactly why it is a config key and not a constant.
    hover_dwell_ms: int = DEFAULT_HOVER_DWELL_MS
    #: ``[home]``: progressive disclosure.
    home: HomeConfig = field(default_factory=HomeConfig)
    #: ``[access]``: captions, calm mode, volume and mute
    #: (:mod:`kidnix_shell.access`). Its defaults are deliberate: a machine
    #: nobody configured is the one a SEND child is most likely to be handed.
    access: AccessConfig = field(default_factory=AccessConfig)
    #: ``[[next_after]]``: S1b's picture options.
    next_after: tuple[NextAfter, ...] = DEFAULT_NEXT_AFTER
    path: Path | None = None
    #: True when this came from a root-owned file (or from nowhere): the shell
    #: running as the child must not try to write it back.
    read_only: bool = False
    #: True when nothing was found and the dev PIN is in force.
    is_default: bool = False
    #: **Has a grown-up ever chosen the four numbers?** Set by
    #: :meth:`load` when the file carried a ``pin_hash``, and by
    #: :meth:`set_pin`. False is what makes the gate open the Set-PIN flow
    #: before anything else (:attr:`must_set_pin`), and it is the state a
    #: freshly installed machine is now in **by design**: the image ships
    #: ``parent.toml`` with no hash at all (panel ruling, spec 7d #11).
    pin_configured: bool = False

    def __post_init__(self) -> None:
        if not self.pin_hash:
            # A fallback, not a gate. Nothing child-facing reaches it any more:
            # `must_set_pin` sends the grown-up sheet straight to "choose a
            # PIN" and does not let anything else happen first. It exists so a
            # developer's shell, `--demo` and the tests still have a PIN to
            # check, and so a *programmatic* caller never meets an empty hash.
            self.pin_salt, self.pin_hash = hash_pin(DEFAULT_PIN)
        else:
            self.pin_configured = True
        if not self.profiles:
            self.profiles = [DEFAULT_PROFILE]

    # -- behaviour --

    def check_pin(self, pin: str) -> bool:
        return verify_pin(pin, self.pin_salt, self.pin_hash)

    def set_pin(self, pin: str) -> None:
        self.pin_salt, self.pin_hash = hash_pin(pin)
        self.pin_configured = True
        self.is_default = False

    @property
    def must_set_pin(self) -> bool:
        """Is the gate still unset, i.e. must it ask for a new PIN first?

        The image ships ``parent.toml`` **without** a ``pin_hash``, so on a
        stock machine this is true and the grown-up sheet opens on "Choose a
        grown-up PIN" rather than on a pad that would accept 1234. That is the
        panel's ruling (7d #11) and Mags's own sentence for it: *"please make
        it refuse to start until I have picked my own four numbers, and please
        let me pick them somewhere he is not looking."*

        It is the *only* condition on the flow. It goes false as soon as a PIN
        has been chosen, whether or not it could be written to disk -- see
        :meth:`kidnix_shell.screens.grownup.GrownupSheet._finish_setting_pin`,
        which never claims to have saved something it did not.
        """
        return not self.pin_configured

    @property
    def pin_is_starter(self) -> bool:
        """True while the gate is still the PIN the image shipped with.

        Compared against :data:`STARTER_PIN_HASH` -- a constant -- rather than
        inferred from a missing key, which is what made the warning invisible
        on exactly the machines that needed it (forum #44, #56). Also true when
        there is no parent config at all, because ``__post_init__`` then hashes
        the same 1234.
        """
        return self.is_default or self.pin_hash == STARTER_PIN_HASH

    @property
    def writable_path(self) -> Path | None:
        """The config file this process could actually rewrite, or ``None``.

        The shell runs as the child and ``/etc/kidnix/parent.toml`` is
        root-owned on purpose -- a child-writable PIN is not a PIN -- so on a
        real machine this is ``None`` and the sheet says which command to run
        instead of pretending it saved something.
        """
        target = self.path
        if target is None:
            return None
        if target.is_file():
            return target if os.access(target, os.W_OK) else None
        parent = target.parent
        return target if parent.is_dir() and os.access(parent, os.W_OK) else None

    def is_allowed(self, activity_id: str, profile_id: str = "") -> bool:
        """May this child open this activity? (parent-panel section 7.2)

        The child's own ``allowed_activity_ids`` when they have one, and the
        machine-wide list otherwise. Empty means all at **both** levels, so
        the three states are: this child's list, the machine's list, or
        everything -- and none of them is "nothing".

        The panel writes the machine list as the union of the active
        children's, so falling back to it is a widening and never a
        narrowing: an older sibling's extra activity was already reachable
        from this file before the shell learned to read the per-child key.
        The age band filters per child on top of this, and always has.

        ``profile_id`` defaults to ``""`` -- no profile -- which is what a
        caller with no child in hand (the validators, the manifest checker)
        gets, and it reads the machine list.
        """
        allowed = self.effective_allow_list(profile_id)
        if not allowed:
            return True
        return activity_id in allowed

    def effective_allow_list(self, profile_id: str = "") -> tuple[str, ...]:
        """The list that actually decides for this child. ``()`` means "all".

        The three states :meth:`is_allowed` documents, as data rather than as a
        verdict: this child's list if they have one, the machine's list
        otherwise, and ``()`` when neither is set. Split out because a *shelf*
        needs to ask more of the same list than "is this id in it" -- see
        :func:`shelf_child_allowed` -- and asking twice with two readings of
        empty is how the two disagree.
        """
        profile = self.profile(profile_id) if profile_id else None
        if profile is not None and profile.allowed_activity_ids:
            return tuple(profile.allowed_activity_ids)
        return tuple(self.allowed_activity_ids or ())

    def profile(self, profile_id: str) -> Profile | None:
        return next((p for p in self.profiles if p.id == profile_id), None)

    # -- persistence --

    @classmethod
    def discover(cls, explicit: Path | None = None) -> ParentConfig:
        """Load the parent config from a root-owned path, or warn and default.

        ``explicit`` is ``--config`` -- a developer naming a file, which is the
        only way a path outside :data:`CONFIG_SEARCH_PATH` is ever read.
        """
        path = explicit or first_system_config("parent.toml")
        if path is None:
            warn_no_parent_config()
            return cls(read_only=True, is_default=True)
        return cls.load(path)

    @classmethod
    def load(cls, path: Path) -> ParentConfig:
        read_only = is_system_path(path)
        if not path.is_file():
            log.info("no parent config at %s; using defaults (PIN %s)", path, DEFAULT_PIN)
            return cls(path=path, read_only=read_only, is_default=True)
        try:
            with path.open("rb") as handle:
                data = tomllib.load(handle)
        except (OSError, tomllib.TOMLDecodeError) as exc:
            log.warning("parent config %s is unreadable (%s); using defaults", path, exc)
            return cls(path=path, read_only=read_only, is_default=True)

        profiles: list[Profile] = []
        for raw in data.get("profiles", []) or []:
            if not isinstance(raw, dict) or "id" not in raw or "name" not in raw:
                log.warning("parent config %s: skipping malformed profile %r", path, raw)
                continue
            base = replace(DEFAULT_PROFILE, id=str(raw["id"]), name=str(raw["name"]))
            profiles.append(
                replace(
                    base,
                    colour_primary=str(raw.get("colour_primary", base.colour_primary)),
                    colour_secondary=str(raw.get("colour_secondary", base.colour_secondary)),
                    avatar=str(raw.get("avatar", base.avatar)),
                    badge=_badge(raw.get("badge"), len(profiles)),
                    age_band=str(raw.get("age_band", base.age_band)),
                    skip_next_choice=bool(raw.get("skip_next_choice", base.skip_next_choice)),
                    language=str(raw.get("language", base.language) or "").strip(),
                    allowed_activity_ids=_allow_list(raw.get("allowed_activity_ids")),
                )
            )

        allowed = data.get("allowed_activity_ids")
        allowed_list: list[str] | None = None
        if isinstance(allowed, list):
            allowed_list = [str(a) for a in allowed]

        length = data.get("default_session_minutes", 25)
        if not isinstance(length, int) or isinstance(length, bool):
            length = 25

        config = cls(
            pin_salt=str(data.get("pin_salt", "")),
            pin_hash=str(data.get("pin_hash", "")),
            default_session_minutes=length,
            allowed_activity_ids=allowed_list,
            profiles=profiles,
            hover_dwell_ms=_hover_dwell_ms(data.get("hover_dwell_ms"), path),
            access=parse_access(data.get("access"), str(path)),
            home=_home_config(data.get("home"), path),
            next_after=parse_next_after(data.get("next_after"), str(path)),
            path=path,
            read_only=read_only,
        )
        if not str(data.get("pin_hash", "")):
            # **The shipped state**, since the image stopped carrying a hash:
            # the gate is unconfigured, `must_set_pin` is true, and the sheet
            # opens on "choose a PIN". INFO rather than WARNING because it is
            # now the expected condition of a machine nobody has set up yet,
            # and the thing that acts on it is a screen, not a log line.
            config.is_default = True
            log.info("parent config %s has no PIN yet; the gate will ask for one", path)
        return config

    def save(self, path: Path | None = None) -> Path:
        target = path or self.path
        if target is None:
            raise ValueError("ParentConfig has no path to save to")
        if path is None and self.read_only:
            raise PermissionError(f"{target} is root-owned; the shell must not rewrite it")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(self.to_toml(), encoding="utf-8")
        # The child must never be able to rewrite their own PIN or allow-list.
        os.chmod(target, 0o644)
        self.path = target
        return target

    def to_toml(self) -> str:
        lines = [
            "# kidnix parent config. Written by the grown-up sheet.",
            "# The PIN is stored as a PBKDF2-SHA256 hash; it is not recoverable.",
        ]
        if self.pin_configured:
            lines += [
                f"pin_salt = {_toml_str(self.pin_salt)}",
                f"pin_hash = {_toml_str(self.pin_hash)}",
            ]
        else:
            # **Never write out the built-in default.** A file with a hash in
            # it is a file that says a grown-up chose a PIN, and `pin_hash` is
            # the only thing `must_set_pin` reads. Round-tripping the fallback
            # here would silently re-open the gate the ruling closed.
            lines.append("# no pin_hash: the grown-up gate will ask for a new PIN")
        lines += [
            f"default_session_minutes = {self.default_session_minutes}",
            f"hover_dwell_ms = {self.hover_dwell_ms}",
        ]
        if self.allowed_activity_ids is None:
            lines.append("# allowed_activity_ids omitted = every activity is allowed")
        else:  # an empty list round-trips, and still means "all"
            allowed = ", ".join(_toml_str(a) for a in self.allowed_activity_ids)
            lines.append(f"allowed_activity_ids = [{allowed}]")
        lines += [
            "",
            "[access]",
            f"captions = {str(self.access.captions).lower()}",
            f"calm = {str(self.access.calm).lower()}",
            f"sound_volume = {self.access.sound_volume}",
            f"mute = {str(self.access.mute).lower()}",
            f"speech_rate = {self.access.speech_rate}",
            f"language = {_toml_str(self.access.language)}",
            "",
            "[home]",
            f"initial_tiles = {self.home.initial_tiles}",
            f"reveal_every_sessions = {self.home.reveal_every_sessions}",
            f"show_everything = {str(self.home.show_everything).lower()}",
        ]
        for profile in self.profiles:
            lines += [
                "",
                "[[profiles]]",
                f"id = {_toml_str(profile.id)}",
                f"name = {_toml_str(profile.name)}",
                f"colour_primary = {_toml_str(profile.colour_primary)}",
                f"colour_secondary = {_toml_str(profile.colour_secondary)}",
                f"avatar = {_toml_str(profile.avatar)}",
                f"badge = {_toml_str(profile.badge)}",
                f"age_band = {_toml_str(profile.age_band)}",
                f"skip_next_choice = {str(profile.skip_next_choice).lower()}",
                f"language = {_toml_str(profile.language)}",
                "# This child's own allow-list. Empty falls back to the machine's above.",
                "allowed_activity_ids = ["
                + ", ".join(_toml_str(a) for a in profile.allowed_activity_ids)
                + "]",
            ]
        for option in self.next_after:
            lines += [
                "",
                "[[next_after]]",
                f"id = {_toml_str(option.id)}",
                f"label = {_toml_str(option.label)}",
                f"audio_label = {_toml_str(option.speak_text)}",
                f"icon = {_toml_str(option.icon)}",
            ]
        return "\n".join(lines) + "\n"


# --- setting the PIN in place --------------------------------------------
#
# ``ParentConfig.save`` rewrites the whole file from ``to_toml()``, which is
# right for a file the shell owns and wrong for ``/etc/kidnix/parent.toml``:
# that one is ninety lines of explanation a parent is meant to read, and a
# grown-up who changes their PIN should not lose it. So the PIN is edited **in
# place**, two lines of it, and everything else in the file is left alone.

PIN_KEYS = ("pin_salt", "pin_hash")


def rewrite_pin(path: Path, pin: str) -> Path:
    """Set ``pin`` in the TOML at ``path``, keeping every other line of it.

    Write-then-rename, so a power cut cannot leave a parent with a config that
    has half a PIN in it and a machine that will not let them in.
    """
    salt, digest = hash_pin(pin)
    values = {"pin_salt": salt, "pin_hash": digest}
    lines = path.read_text(encoding="utf-8").splitlines() if path.is_file() else []
    seen = set()
    for index, line in enumerate(lines):
        key = line.split("=", 1)[0].strip()
        if key in PIN_KEYS and key not in seen:
            lines[index] = f"{key} = {_toml_str(values[key])}"
            seen.add(key)
    missing = [key for key in PIN_KEYS if key not in seen]
    if missing:
        header = ["", "# Set by `kidnix-shell --set-pin`."] if lines else []
        lines = [*header, *(f"{key} = {_toml_str(values[key])}" for key in missing), *lines]
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text("\n".join(lines) + "\n", encoding="utf-8")
    os.chmod(temporary, 0o644)
    temporary.replace(path)
    log.info("wrote a new grown-up PIN to %s", path)
    return path


def _int_key(value: Any, fallback: int, low: int, high: int, key: str, path: Path) -> int:
    """A whole number out of TOML, clamped, with a log line on nonsense."""
    if isinstance(value, bool) or not isinstance(value, int):
        if value is not None:
            log.warning(
                "parent config %s: %s=%r is not a whole number; using %d",
                path,
                key,
                value,
                fallback,
            )
        return fallback
    if not low <= value <= high:
        clamped = max(low, min(high, value))
        log.warning(
            "parent config %s: %s=%d is outside %d-%d; using %d",
            path,
            key,
            value,
            low,
            high,
            clamped,
        )
        return clamped
    return value


def _hover_dwell_ms(value: Any, path: Path) -> int:
    return _int_key(
        value,
        DEFAULT_HOVER_DWELL_MS,
        MIN_HOVER_DWELL_MS,
        MAX_HOVER_DWELL_MS,
        "hover_dwell_ms",
        path,
    )


def _badge(value: Any, index: int) -> str:
    """The profile's shape token, defaulted by position and never invented.

    An unknown name falls back to the badge that position would have had:
    a config typo must not leave a child with no shape at all, which is the
    only carrier of identity that survives colour blindness.
    """
    fallback = PROFILE_BADGES[index % len(PROFILE_BADGES)]
    if value is None:
        return fallback
    name = str(value)
    if name not in PROFILE_BADGES:
        log.warning("parent config: badge %r is not one of %s", name, ", ".join(PROFILE_BADGES))
        return fallback
    return name


def _home_config(raw: Any, path: Path) -> HomeConfig:
    """``[home]``: progressive disclosure, or the defaults if it is missing."""
    if raw is None:
        return HomeConfig()
    if not isinstance(raw, dict):
        log.warning("parent config %s: [home] must be a table; using the defaults", path)
        return HomeConfig()
    show_everything = raw.get("show_everything", HomeConfig.show_everything)
    if not isinstance(show_everything, bool):
        log.warning("parent config %s: home.show_everything must be true or false", path)
        show_everything = HomeConfig.show_everything
    return HomeConfig(
        initial_tiles=_int_key(
            raw.get("initial_tiles"),
            DEFAULT_INITIAL_TILES,
            MIN_INITIAL_TILES,
            64,
            "home.initial_tiles",
            path,
        ),
        reveal_every_sessions=_int_key(
            raw.get("reveal_every_sessions"),
            DEFAULT_REVEAL_EVERY_SESSIONS,
            1,
            1000,
            "home.reveal_every_sessions",
            path,
        ),
        show_everything=show_everything,
    )


def warn_no_parent_config(stream: Any = None) -> None:
    """Say, loudly and once, that this machine has no parent config.

    A shell running on the dev PIN is a shell whose grown-up gate is 1234, and
    that has to be impossible to miss in the journal.
    """
    out = stream if stream is not None else sys.stderr
    looked = ", ".join(str(p) for p in system_config_candidates("parent.toml"))
    banner = (
        "\n"
        "**********************************************************************\n"
        "  kidnix: NO PARENT CONFIG FOUND. Running with built-in defaults:\n"
        f"    grown-up PIN {DEFAULT_PIN}, every activity allowed, 25 minutes.\n"
        f"  Looked in: {looked}\n"
        "  This is fine for development and NOT fine on a child's machine.\n"
        "**********************************************************************\n"
    )
    print(banner, file=out, flush=True)
    log.warning("no parent config in %s; using built-in defaults (PIN %s)", looked, DEFAULT_PIN)


def _toml_str(value: Any) -> str:
    """Quote a string for TOML. Our values are hex, ids and short names."""
    text = str(value).replace("\\", "\\\\").replace('"', '\\"')
    return f'"{text}"'
