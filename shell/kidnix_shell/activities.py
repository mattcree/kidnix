"""Activity manifests -- the shell's input contract (spec section 4).

TOML files in ``/usr/share/kidnix/activities/*.toml`` (system) and
``$XDG_DATA_HOME/kidnix/activities/`` (dev override, wins on id collision).

The schema is owned jointly with the activities implementer; the manifests in
``system_files/usr/share/kidnix/activities/`` are the reference. This loader is
deliberately permissive about *optional* fields -- a manifest that omits
``goal`` or ``age_max`` still loads -- and strict about the three things the
shell cannot work without: ``id``, ``name`` and a non-empty ``exec``.

Invalid files are skipped with a log line. ``kidnix-shell --validate-manifests``
exits non-zero if any file in a directory is invalid, so CI can gate on it.
"""

from __future__ import annotations

import logging
import os
import re
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)

SYSTEM_ACTIVITY_DIR = Path("/usr/share/kidnix/activities")

ID_RE = re.compile(r"^[a-z0-9][a-z0-9._-]*$")
CATEGORIES = frozenset({"make", "learn", "play"})
ICON_KINDS = frozenset({"icon-name", "path"})

#: Fields the shell knows about. Anything else in a manifest is ignored (with a
#: debug line) rather than rejected, so the activities implementer can add
#: fields ahead of the shell.
KNOWN_KEYS = frozenset(
    {
        "schema",
        "id",
        "name",
        "audio_label",
        "icon",
        "icon_kind",
        "exec",
        "exec_resume",
        "category",
        "age_min",
        "age_max",
        "oars_rating",
        "network_required",
        "journal_watch",
        "journal_glob",
        "goal",
        "wayland_native",
        "content_required",
        "notes",
        "source",
        "package",
        "licence",
        "license",
    }
)

SUPPORTED_SCHEMA = 1


class ManifestError(Exception):
    """A manifest could not be loaded. Carries the path for the log line."""

    def __init__(self, path: Path, message: str) -> None:
        super().__init__(f"{path}: {message}")
        self.path = path
        self.message = message


@dataclass(frozen=True)
class Activity:
    """One tile on Home."""

    id: str
    name: str
    exec_argv: tuple[str, ...]
    source_path: Path
    audio_label: str = ""
    icon: str = ""
    icon_kind: str = "icon-name"
    exec_resume: tuple[str, ...] = ()
    category: str = "play"
    age_min: int | None = None
    age_max: int | None = None
    oars_rating: str = "none"
    network_required: bool = False
    journal_watch: tuple[Path, ...] = ()
    journal_glob: str = "*"
    goal: str = ""
    wayland_native: bool = True
    content_required: bool = False
    notes: str = ""
    package: str = ""

    @property
    def speak_text(self) -> str:
        """What the shell reads aloud on focus/hover (spec section 3)."""
        return self.audio_label or self.name

    @property
    def supports_resume(self) -> bool:
        return bool(self.exec_resume)

    def resume_argv(self, path: Path) -> list[str]:
        """argv for re-opening ``path``.

        ``exec_resume`` may contain the token ``{file}``; if it does not, the
        path is appended. Without ``exec_resume`` this is a plain launch --
        spec section 5, "else plain launch".
        """
        if not self.exec_resume:
            return list(self.exec_argv)
        argv = [arg.replace("{file}", str(path)) for arg in self.exec_resume]
        if not any("{file}" in arg for arg in self.exec_resume):
            argv.append(str(path))
        return argv


@dataclass
class LoadResult:
    """What a directory scan produced. Errors are reported, never raised."""

    activities: list[Activity] = field(default_factory=list)
    errors: list[ManifestError] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors


def _expand(raw: str, home: Path | None = None) -> Path:
    """Expand ``~`` and ``$VAR`` against a (possibly fake) home."""
    text = os.path.expandvars(raw)
    if text.startswith("~"):
        base = home if home is not None else Path.home()
        text = str(base) + text[1:]
    return Path(text)


def _require_str(data: dict[str, Any], key: str, path: Path) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ManifestError(path, f"missing or empty required field {key!r}")
    return value.strip()


def _opt_str(data: dict[str, Any], key: str, path: Path, default: str = "") -> str:
    value = data.get(key, default)
    if value is None:
        return default
    if not isinstance(value, str):
        raise ManifestError(path, f"{key!r} must be a string, got {type(value).__name__}")
    return value.strip()


def _opt_bool(data: dict[str, Any], key: str, path: Path, default: bool) -> bool:
    value = data.get(key, default)
    if not isinstance(value, bool):
        raise ManifestError(path, f"{key!r} must be true or false")
    return value


def _opt_int(data: dict[str, Any], key: str, path: Path) -> int | None:
    value = data.get(key)
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int):
        raise ManifestError(path, f"{key!r} must be a whole number")
    if value < 0:
        raise ManifestError(path, f"{key!r} must not be negative")
    return value


def _argv(data: dict[str, Any], key: str, path: Path, *, required: bool) -> tuple[str, ...]:
    value = data.get(key)
    if value is None:
        if required:
            raise ManifestError(path, f"missing required field {key!r}")
        return ()
    if not isinstance(value, list) or not all(isinstance(a, str) for a in value):
        raise ManifestError(path, f"{key!r} must be a list of strings")
    if required and not value:
        raise ManifestError(path, f"{key!r} must not be empty")
    return tuple(value)


def parse_manifest(data: dict[str, Any], path: Path, home: Path | None = None) -> Activity:
    """Turn already-parsed TOML into an Activity, or raise ManifestError."""
    schema = data.get("schema", SUPPORTED_SCHEMA)
    if not isinstance(schema, int) or isinstance(schema, bool):
        raise ManifestError(path, "'schema' must be a whole number")
    if schema > SUPPORTED_SCHEMA:
        raise ManifestError(
            path, f"schema {schema} is newer than this shell understands ({SUPPORTED_SCHEMA})"
        )

    unknown = set(data) - KNOWN_KEYS
    if unknown:
        log.debug("%s: ignoring unknown fields %s", path, sorted(unknown))

    activity_id = _require_str(data, "id", path)
    if not ID_RE.match(activity_id):
        raise ManifestError(path, f"id {activity_id!r} must be lowercase [a-z0-9._-]")

    category = _opt_str(data, "category", path, "play") or "play"
    if category not in CATEGORIES:
        raise ManifestError(path, f"category {category!r} must be one of {sorted(CATEGORIES)}")

    icon_kind = _opt_str(data, "icon_kind", path, "icon-name") or "icon-name"
    if icon_kind not in ICON_KINDS:
        raise ManifestError(path, f"icon_kind {icon_kind!r} must be one of {sorted(ICON_KINDS)}")

    watch_raw = data.get("journal_watch", [])
    if not isinstance(watch_raw, list) or not all(isinstance(w, str) for w in watch_raw):
        raise ManifestError(path, "'journal_watch' must be a list of strings")

    age_min = _opt_int(data, "age_min", path)
    age_max = _opt_int(data, "age_max", path)
    if age_min is not None and age_max is not None and age_max < age_min:
        raise ManifestError(path, f"age_max ({age_max}) is below age_min ({age_min})")

    return Activity(
        id=activity_id,
        name=_require_str(data, "name", path),
        exec_argv=_argv(data, "exec", path, required=True),
        source_path=path,
        audio_label=_opt_str(data, "audio_label", path),
        icon=_opt_str(data, "icon", path),
        icon_kind=icon_kind,
        exec_resume=_argv(data, "exec_resume", path, required=False),
        category=category,
        age_min=age_min,
        age_max=age_max,
        oars_rating=_opt_str(data, "oars_rating", path, "none") or "none",
        network_required=_opt_bool(data, "network_required", path, False),
        journal_watch=tuple(_expand(w, home) for w in watch_raw),
        journal_glob=_opt_str(data, "journal_glob", path, "*") or "*",
        goal=_opt_str(data, "goal", path),
        wayland_native=_opt_bool(data, "wayland_native", path, True),
        content_required=_opt_bool(data, "content_required", path, False),
        notes=_opt_str(data, "notes", path),
        package=_opt_str(data, "package", path),
    )


def load_manifest(path: Path, home: Path | None = None) -> Activity:
    try:
        with path.open("rb") as handle:
            data = tomllib.load(handle)
    except tomllib.TOMLDecodeError as exc:
        raise ManifestError(path, f"not valid TOML: {exc}") from exc
    except OSError as exc:
        raise ManifestError(path, f"cannot be read: {exc}") from exc
    return parse_manifest(data, path, home)


def load_directory(directory: Path, home: Path | None = None) -> LoadResult:
    """Load every ``*.toml`` in one directory. Missing directory is not an error."""
    result = LoadResult()
    if not directory.is_dir():
        log.debug("activity directory %s does not exist", directory)
        return result
    for path in sorted(directory.glob("*.toml")):
        try:
            result.activities.append(load_manifest(path, home))
        except ManifestError as exc:
            log.warning("skipping activity manifest: %s", exc)
            result.errors.append(exc)
    return result


def load_activities(directories: list[Path], home: Path | None = None) -> LoadResult:
    """Load several directories in order; a later directory wins on id collision."""
    combined = LoadResult()
    by_id: dict[str, Activity] = {}
    for directory in directories:
        one = load_directory(directory, home)
        combined.errors.extend(one.errors)
        for activity in one.activities:
            if activity.id in by_id:
                log.info(
                    "activity %r from %s overrides %s",
                    activity.id,
                    activity.source_path,
                    by_id[activity.id].source_path,
                )
            by_id[activity.id] = activity
    combined.activities = sorted(by_id.values(), key=lambda a: (a.category, a.name.lower()))
    return combined


def default_activity_dirs(data_home: Path | None = None) -> list[Path]:
    """System directory first, user/dev directory second (so dev wins)."""
    dirs = [SYSTEM_ACTIVITY_DIR]
    if data_home is not None:
        dirs.append(data_home / "kidnix" / "activities")
    return dirs
