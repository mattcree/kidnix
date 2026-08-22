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

Two things beyond parsing live here because they are the same question --
"should this be a tile?" -- asked at load time:

* **Order.** ``order`` (an int, small first) is what the Home grid sorts by, so
  the first thing a five-year-old sees is Draw and not whatever happens to sort
  first alphabetically. Manifests without one fall to the back, in filename
  order.
* **Availability.** A tile for a program that is not installed is a button that
  lies (`docs/spikes/e2e-scenario.md` section 3.1). :class:`Availability`
  resolves ``exec[0]`` on ``PATH`` and asks ``flatpak info`` about
  ``flatpak run <ref>`` execs, once per boot, and the unavailable ones are left
  off Home unless the manifest says ``show_when_unavailable = true``.
* **Age band.** 01 #35 / SYNTHESIS B8 ask for a *fine* band (4-5 vs 6-8), set
  by the parent on the profile. ``age_min``/``age_max`` (or the shorthand
  ``age_band = "6-8"``) are matched against it by :func:`in_age_band`, and an
  activity outside the band is simply **not there** -- not outlined, not
  spoken. ``tuxmath.toml``'s own comment says "the shell should not show this
  to a four-year-old", and until v0.1.3 the shell showed it.
* **Content.** An *installed* program with nothing to open is the same button
  telling the same lie through a different door: ``kiwix-serve`` is on ``PATH``
  on every image, and until a parent copies a ZIM onto the machine the Library
  tile opens an empty library (05 Lib-4, CCI audit section 3.2). A manifest
  therefore declares ``content_required = ["/path/*.glob", ...]``; if any one
  of those globs matches nothing, the activity is treated exactly as if its
  program were missing.
"""

from __future__ import annotations

import glob as globlib
import logging
import os
import re
import shutil
import subprocess
import tomllib
from collections.abc import Callable
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)

SYSTEM_ACTIVITY_DIR = Path("/usr/share/kidnix/activities")

#: Manifests without an explicit ``order`` sort after every manifest that has
#: one, among themselves by filename.
DEFAULT_ORDER = 1000

ID_RE = re.compile(r"^[a-z0-9][a-z0-9._-]*$")
CATEGORIES = frozenset({"make", "learn", "play"})
ICON_KINDS = frozenset({"icon-name", "path"})

#: ``"4-5"``, ``"6-8"``, or a bare ``"5"``. Used by both the profile
#: (kidnix_shell.settings.Profile.age_band) and the manifest shorthand.
AGE_BAND_RE = re.compile(r"^\s*(\d{1,2})\s*(?:[-\u2013]\s*(\d{1,2})\s*)?$")

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
        "age_band",
        "age_min",
        "age_max",
        "oars_rating",
        "network_required",
        "journal_watch",
        "journal_glob",
        "goal",
        "order",
        "show_when_unavailable",
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
    order: int | None = None
    show_when_unavailable: bool = False
    wayland_native: bool = True
    #: Path globs that must each match at least one file for this activity to
    #: have anything to open. Empty means "nothing to check".
    content_required: tuple[str, ...] = ()
    notes: str = ""
    package: str = ""
    #: Set by :func:`resolve_availability` at startup, not by the manifest.
    available: bool = True
    #: Set by :func:`resolve_availability` at startup: every glob in
    #: :attr:`content_required` matched something.
    has_content: bool = True

    @property
    def speak_text(self) -> str:
        """What the shell reads aloud on focus/hover (spec section 3)."""
        return self.audio_label or self.name

    @property
    def sort_key(self) -> tuple[int, str, str]:
        """Home's order: ``order`` first, then filename, then id."""
        return (
            DEFAULT_ORDER if self.order is None else self.order,
            self.source_path.name,
            self.id,
        )

    @property
    def usable(self) -> bool:
        """Can a tap on this actually produce something?

        Two ways to fail and they are the same failure to a five-year-old: the
        program is not installed, or it is installed with nothing to open.
        """
        return self.available and self.has_content

    @property
    def on_home(self) -> bool:
        """Should this be a tile at all?

        An activity that cannot work is not shown -- a tile that cannot work is
        worse than no tile -- unless the manifest asks for it, in which case
        Home renders it outline-only and says so (SYNTHESIS G3: never a silent
        denial, but also never a lie).
        """
        return self.usable or self.show_when_unavailable

    @property
    def flatpak_ref(self) -> str:
        """The ref behind a ``flatpak run <ref>`` exec, or ``""``."""
        argv = list(self.exec_argv)
        if len(argv) < 3 or Path(argv[0]).name != "flatpak" or argv[1] != "run":
            return ""
        return next((arg for arg in argv[2:] if not arg.startswith("-")), "")

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


def parse_age_band(text: str) -> tuple[int, int] | None:
    """``"4-5"`` -> ``(4, 5)``; ``"5"`` -> ``(5, 5)``; nonsense -> ``None``.

    One parser for both spellings of the same idea: the profile's band (set by
    the parent) and a manifest's ``age_band`` shorthand.
    """
    match = AGE_BAND_RE.match(text or "")
    if match is None:
        return None
    low = int(match.group(1))
    high = int(match.group(2)) if match.group(2) else low
    return (low, high) if high >= low else (high, low)


def in_age_band(activity: Activity, band: tuple[int, int] | None) -> bool:
    """Is ``activity`` pitched at a child in ``band``?

    Overlap, not containment: a Library banded 5-12 is right for a five-year-old
    even though most of its range is not, and Tux Paint (no bounds at all) is
    right for everybody. An activity is out only when its whole range sits
    above or below the child's -- which is exactly ``tuxmath`` (6-10) against a
    4-5 profile, the case 01 #35 names.

    ``band`` of ``None`` (a profile with no band set) means "do not filter":
    a parent who has not answered the question is not answered *for*.
    """
    if band is None:
        return True
    low, high = band
    if activity.age_max is not None and activity.age_max < low:
        return False
    return not (activity.age_min is not None and activity.age_min > high)


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

    content_raw = data.get("content_required", [])
    if isinstance(content_raw, bool):
        # v0.1.1 accepted a bare `true` and nothing ever checked it, which is
        # how the Library shipped as a tile that opened an empty library.
        raise ManifestError(
            path,
            "'content_required' must be a list of path globs, e.g. "
            '["/var/lib/kidnix/library/*.zim"] -- a bare true says nothing '
            "the shell can check",
        )
    if not isinstance(content_raw, list) or not all(isinstance(c, str) for c in content_raw):
        raise ManifestError(path, "'content_required' must be a list of path globs")
    content_required = tuple(str(_expand(c, home)) for c in content_raw if c.strip())

    order = data.get("order")
    if order is not None and (isinstance(order, bool) or not isinstance(order, int)):
        raise ManifestError(path, "'order' must be a whole number")

    age_min = _opt_int(data, "age_min", path)
    age_max = _opt_int(data, "age_max", path)
    band_text = _opt_str(data, "age_band", path)
    if band_text:
        # A shorthand for the pair, so a manifest can say `age_band = "6-8"`
        # in the same spelling the profile uses. Explicit bounds win.
        band = parse_age_band(band_text)
        if band is None:
            raise ManifestError(path, f"age_band {band_text!r} must look like '4-5' or '6-8'")
        age_min = band[0] if age_min is None else age_min
        age_max = band[1] if age_max is None else age_max
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
        order=order,
        show_when_unavailable=_opt_bool(data, "show_when_unavailable", path, False),
        wayland_native=_opt_bool(data, "wayland_native", path, True),
        content_required=content_required,
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
    combined.activities = sorted(by_id.values(), key=lambda a: a.sort_key)
    return combined


def default_activity_dirs(data_home: Path | None = None) -> list[Path]:
    """System directory first, user/dev directory second (so dev wins)."""
    dirs = [SYSTEM_ACTIVITY_DIR]
    if data_home is not None:
        dirs.append(data_home / "kidnix" / "activities")
    return dirs


# --- is the program actually there? --------------------------------------

#: ``flatpak info`` on a machine with a cold system installation can take a
#: moment; nothing child-facing waits on this, but the shell's startup does.
FLATPAK_TIMEOUT_SECONDS = 5.0


def _flatpak_installed(ref: str) -> bool:
    """``flatpak info <ref>`` -- cheap, offline, and exits non-zero if absent."""
    if shutil.which("flatpak") is None:
        return False
    try:
        completed = subprocess.run(  # fixed argv, no shell
            ["flatpak", "info", ref],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=FLATPAK_TIMEOUT_SECONDS,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        log.warning("could not ask flatpak about %s (%s); treating it as missing", ref, exc)
        return False
    return completed.returncode == 0


def _glob_matches(pattern: str) -> bool:
    """Does ``pattern`` match at least one path? Never raises."""
    try:
        return bool(next(iter(globlib.iglob(pattern)), None))
    except (OSError, ValueError) as exc:  # pragma: no cover - a broken pattern
        log.warning("content glob %r could not be evaluated (%s)", pattern, exc)
        return False


class Availability:
    """Which activities can actually run. Answers are cached for the boot.

    All three probes are injectable so the tests never touch ``PATH``, spawn
    ``flatpak`` or read the real filesystem.
    """

    def __init__(
        self,
        which: Callable[[str], str | None] | None = None,
        flatpak: Callable[[str], bool] | None = None,
        globber: Callable[[str], bool] | None = None,
    ) -> None:
        self._which = which or shutil.which
        self._flatpak = flatpak or _flatpak_installed
        self._globber = globber or _glob_matches
        self._cache: dict[str, bool] = {}
        self._content_cache: dict[str, bool] = {}

    def check(self, activity: Activity) -> bool:
        if not activity.exec_argv:
            return False
        ref = activity.flatpak_ref
        key = f"flatpak:{ref}" if ref else f"exec:{activity.exec_argv[0]}"
        cached = self._cache.get(key)
        if cached is None:
            cached = self._resolve(activity.exec_argv[0], ref)
            self._cache[key] = cached
        return cached

    def _resolve(self, program: str, ref: str) -> bool:
        if self._which(program) is None:
            return False
        return self._flatpak(ref) if ref else True

    def has_content(self, activity: Activity) -> bool:
        """Every glob in ``content_required`` matches at least one file.

        A manifest with no ``content_required`` has nothing to check and is
        content-complete by definition -- most activities carry their own.
        """
        for pattern in activity.content_required:
            matched = self._content_cache.get(pattern)
            if matched is None:
                matched = self._globber(pattern)
                self._content_cache[pattern] = matched
            if not matched:
                return False
        return True

    def missing_content(self, activity: Activity) -> list[str]:
        """Which globs found nothing -- for the log line the parent reads."""
        return [p for p in activity.content_required if not self._content_cache.get(p, False)]


def resolve_availability(
    activities: list[Activity], availability: Availability | None = None
) -> list[Activity]:
    """Stamp ``available`` and ``has_content``, logging what is missing.

    The unusable ones stay in the list -- the Journal still has to be able to
    name the activity an old entry came from -- and it is Home that decides
    whether to draw a tile (:attr:`Activity.on_home`).
    """
    checker = availability or Availability()
    resolved = []
    for activity in activities:
        available = checker.check(activity)
        has_content = checker.has_content(activity) if available else True
        fate = "showing it outline-only" if activity.show_when_unavailable else "hiding its tile"
        if not available:
            log.warning(
                "activity %r is not installed (%s); %s",
                activity.id,
                " ".join(activity.exec_argv),
                fate,
            )
        elif not has_content:
            # 05 Lib-4: kiwix-serve is installed on every image and there is no
            # ZIM until a parent copies one on. A tile that opens an empty
            # library is the same lie as a tile that opens nothing.
            log.warning(
                "activity %r is installed but has no content yet (nothing matches %s); %s",
                activity.id,
                ", ".join(checker.missing_content(activity)) or "its content globs",
                fate,
            )
        resolved.append(replace(activity, available=available, has_content=has_content))
    return resolved
