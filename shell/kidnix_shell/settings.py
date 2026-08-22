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
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)

DEFAULT_PIN = "1234"  # spec S9: dev default, replaced by the parent
PBKDF2_ROUNDS = 200_000
SYSTEM_CONFIG_DIR = Path("/etc/kidnix")
#: The image's shipped defaults, used when /etc has nothing (bootc's 3-way
#: merge means /etc is the parent's copy, /usr/share is ours).
SYSTEM_DEFAULT_DIR = Path("/usr/share/kidnix")

#: 08 section 3.4 -- colour is *whose it is*, shape is *what it is*. Each
#: profile owns a two-colour identity used for its avatar, band tint, focus
#: rings and journal cards.
PROFILE_COLOURS: tuple[tuple[str, str], ...] = (
    ("#0f8a8a", "#f06292"),  # teal / pink
    ("#2e7d32", "#f9a825"),  # green / gold
    ("#4527a0", "#26c6da"),  # violet / cyan
    ("#bf360c", "#ffb300"),  # rust / amber
)

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


@dataclass(frozen=True)
class Paths:
    """Every directory the shell touches, resolved once and passed around.

    Built from the environment so tests can point the whole shell at a tmpdir.
    """

    home: Path
    data_home: Path
    config_home: Path
    cache_home: Path
    state_home: Path
    runtime_dir: Path | None = None

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

    @property
    def journal_root(self) -> Path:
        """Spec section 5: ``$XDG_DATA_HOME/kidnix/journal/``."""
        return self.data_home / "kidnix" / "journal"

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
        """Kid-owned: how much of today's budget has been spent."""
        return self.state_home / "kidnix" / "usage.toml"


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
    age_band: str = "4-5"

    @property
    def speak_text(self) -> str:
        return self.name


DEFAULT_PROFILE = Profile(id="child", name="Me")


# --- parent config -------------------------------------------------------


@dataclass
class ParentConfig:
    """Everything the grown-up sheet can change."""

    pin_salt: str = ""
    pin_hash: str = ""
    default_session_minutes: int = 25
    #: ``None`` means "every installed activity is allowed". A list restricts
    #: Home to those ids; the rest render outline-only (spec S2).
    allowed_activity_ids: list[str] | None = None
    profiles: list[Profile] = field(default_factory=lambda: [DEFAULT_PROFILE])
    path: Path | None = None
    #: True when this came from a root-owned file (or from nowhere): the shell
    #: running as the child must not try to write it back.
    read_only: bool = False
    #: True when nothing was found and the dev PIN is in force.
    is_default: bool = False

    def __post_init__(self) -> None:
        if not self.pin_hash:
            self.pin_salt, self.pin_hash = hash_pin(DEFAULT_PIN)
        if not self.profiles:
            self.profiles = [DEFAULT_PROFILE]

    # -- behaviour --

    def check_pin(self, pin: str) -> bool:
        return verify_pin(pin, self.pin_salt, self.pin_hash)

    def set_pin(self, pin: str) -> None:
        self.pin_salt, self.pin_hash = hash_pin(pin)

    def is_allowed(self, activity_id: str) -> bool:
        if self.allowed_activity_ids is None:
            return True
        return activity_id in self.allowed_activity_ids

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

        profiles = []
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
                    age_band=str(raw.get("age_band", base.age_band)),
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
            path=path,
            read_only=read_only,
        )
        if not str(data.get("pin_hash", "")):
            config.is_default = True
            log.warning("parent config %s has no PIN; the dev default is in force", path)
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
            f"pin_salt = {_toml_str(self.pin_salt)}",
            f"pin_hash = {_toml_str(self.pin_hash)}",
            f"default_session_minutes = {self.default_session_minutes}",
        ]
        if self.allowed_activity_ids is None:
            lines.append("# allowed_activity_ids omitted = every activity is allowed")
        else:
            allowed = ", ".join(_toml_str(a) for a in self.allowed_activity_ids)
            lines.append(f"allowed_activity_ids = [{allowed}]")
        for profile in self.profiles:
            lines += [
                "",
                "[[profiles]]",
                f"id = {_toml_str(profile.id)}",
                f"name = {_toml_str(profile.name)}",
                f"colour_primary = {_toml_str(profile.colour_primary)}",
                f"colour_secondary = {_toml_str(profile.colour_secondary)}",
                f"avatar = {_toml_str(profile.avatar)}",
                f"age_band = {_toml_str(profile.age_band)}",
            ]
        return "\n".join(lines) + "\n"


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
