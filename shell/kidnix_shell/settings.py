"""XDG paths, child profiles and the parent-owned config (PIN, allow-list).

Two config files, deliberately different in ownership:

* ``/etc/kidnix/session.toml`` -- session policy, root-owned, read-only to the
  child. Read by :mod:`kidnix_shell.session`.
* ``<config>/kidnix/parent.toml`` -- PIN hash, default session length, the
  activity allow-list and the child profiles. On the image this lives in a
  parent-owned directory the child cannot write; in a dev checkout it is under
  ``$XDG_CONFIG_HOME``. The shell reads it every time it needs it and writes it
  only from the grown-up sheet.

TOML both ways. ``tomllib`` cannot write, so there is a small dumper here for
the flat schema we actually use rather than a third-party dependency.
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import os
import secrets
import tomllib
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)

DEFAULT_PIN = "1234"  # spec S9: dev default, replaced by the parent
PBKDF2_ROUNDS = 200_000
SYSTEM_CONFIG_DIR = Path("/etc/kidnix")

#: 08 section 3.4 -- colour is *whose it is*, shape is *what it is*. Each
#: profile owns a two-colour identity used for its avatar, band tint, focus
#: rings and journal cards.
PROFILE_COLOURS: tuple[tuple[str, str], ...] = (
    ("#0f8a8a", "#f06292"),  # teal / pink
    ("#2e7d32", "#f9a825"),  # green / gold
    ("#4527a0", "#26c6da"),  # violet / cyan
    ("#bf360c", "#ffb300"),  # rust / amber
)


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
    def parent_config(self) -> Path:
        system = SYSTEM_CONFIG_DIR / "parent.toml"
        if system.is_file():
            return system
        return self.config_home / "kidnix" / "parent.toml"

    @property
    def session_config(self) -> Path:
        system = SYSTEM_CONFIG_DIR / "session.toml"
        if system.is_file():
            return system
        return self.config_home / "kidnix" / "session.toml"

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
    def load(cls, path: Path) -> ParentConfig:
        if not path.is_file():
            log.info("no parent config at %s; using defaults (PIN %s)", path, DEFAULT_PIN)
            return cls(path=path)
        try:
            with path.open("rb") as handle:
                data = tomllib.load(handle)
        except (OSError, tomllib.TOMLDecodeError) as exc:
            log.warning("parent config %s is unreadable (%s); using defaults", path, exc)
            return cls(path=path)

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

        return cls(
            pin_salt=str(data.get("pin_salt", "")),
            pin_hash=str(data.get("pin_hash", "")),
            default_session_minutes=length,
            allowed_activity_ids=allowed_list,
            profiles=profiles,
            path=path,
        )

    def save(self, path: Path | None = None) -> Path:
        target = path or self.path
        if target is None:
            raise ValueError("ParentConfig has no path to save to")
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


def _toml_str(value: Any) -> str:
    """Quote a string for TOML. Our values are hex, ids and short names."""
    text = str(value).replace("\\", "\\\\").replace('"', '\\"')
    return f'"{text}"'
