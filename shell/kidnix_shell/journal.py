"""My Things -- the Journal (spec section 5).

Sugar's one great uncopied idea: everything the child makes is kept
automatically, in time order, and a card is *resumed* rather than opened.

On disk, deliberately boring so a parent can browse it in Files::

    $XDG_DATA_HOME/kidnix/journal/YYYY/MM/DD/<entry-id>/
        entry.json     id, activity_id, created, updated, title, source_path,
                       mime, starred, starred_at, versions[]
        v001.png       the imported file (open formats only, never renamed
                       into something proprietary)
        v002.png       ... a later save of the same source file
        thumb.png      256 px thumbnail, images only

Import is idempotent: re-importing a file whose bytes have not changed is a
no-op, and a changed file becomes a *new version* of the same entry rather than
a second entry. Nothing is ever deleted (SYNTHESIS C2).
"""

from __future__ import annotations

import hashlib
import json
import logging
import mimetypes
import shutil
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)

THUMB_NAME = "thumb.png"
ENTRY_FILE = "entry.json"
THUMB_SIZE = 256

#: SYNTHESIS F2: the favourites shelf is small and bounded on purpose. Starring
#: a ninth thing quietly unstars the oldest -- no dialogue, no error, and the
#: child can always re-star it.
MAX_FAVOURITES = 8

TODAY = "Today"
YESTERDAY = "Yesterday"
BEFORE = "Before"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 16), b""):
            digest.update(block)
    return digest.hexdigest()


@dataclass
class Version:
    """One save of the source file."""

    filename: str
    imported: str
    size: int
    sha256: str


@dataclass
class Entry:
    """One thing the child made."""

    id: str
    activity_id: str
    created: str
    updated: str
    title: str
    source_path: str
    mime: str
    starred: bool = False
    starred_at: str = ""
    versions: list[Version] = field(default_factory=list)
    #: not serialised -- where this entry lives
    directory: Path = field(default=Path("."), compare=False, repr=False)

    # -- derived --

    @property
    def created_at(self) -> datetime:
        return datetime.fromisoformat(self.created)

    @property
    def updated_at(self) -> datetime:
        return datetime.fromisoformat(self.updated)

    @property
    def latest_version(self) -> Version | None:
        return self.versions[-1] if self.versions else None

    @property
    def latest_path(self) -> Path | None:
        latest = self.latest_version
        return self.directory / latest.filename if latest else None

    @property
    def thumbnail(self) -> Path | None:
        candidate = self.directory / THUMB_NAME
        return candidate if candidate.is_file() else None

    @property
    def is_image(self) -> bool:
        return self.mime.startswith("image/")

    @property
    def speak_text(self) -> str:
        return self.title

    # -- persistence --

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data.pop("directory", None)
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any], directory: Path) -> Entry:
        versions = [Version(**v) for v in data.get("versions", [])]
        return cls(
            id=str(data["id"]),
            activity_id=str(data.get("activity_id", "")),
            created=str(data["created"]),
            updated=str(data.get("updated", data["created"])),
            title=str(data.get("title", "")),
            source_path=str(data.get("source_path", "")),
            mime=str(data.get("mime", "application/octet-stream")),
            starred=bool(data.get("starred", False)),
            starred_at=str(data.get("starred_at", "")),
            versions=versions,
            directory=directory,
        )

    def save(self) -> None:
        self.directory.mkdir(parents=True, exist_ok=True)
        target = self.directory / ENTRY_FILE
        # Write-then-rename: a half-written entry.json on a power cut would
        # lose the whole entry, and the child would have made it for nothing.
        temporary = target.with_suffix(".json.tmp")
        temporary.write_text(json.dumps(self.to_dict(), indent=2, sort_keys=True), encoding="utf-8")
        temporary.replace(target)


def make_thumbnail(source: Path, destination: Path, size: int = THUMB_SIZE) -> bool:
    """Scale an image into ``destination`` as PNG. False if not possible.

    GdkPixbuf handles PNG/JPEG/GIF/BMP/TIFF/SVG out of the box on the image, so
    Pillow is not a dependency. Non-images get no thumbnail and the UI falls
    back to the activity's icon (spec section 5).
    """
    try:
        import gi

        gi.require_version("GdkPixbuf", "2.0")
        from gi.repository import GdkPixbuf

        pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(
            str(source),
            size,
            size,
            True,  # preserve aspect ratio
        )
        destination.parent.mkdir(parents=True, exist_ok=True)
        pixbuf.savev(str(destination), "png", [], [])
        return True
    except Exception as exc:
        log.debug("no thumbnail for %s: %s", source, exc)
        return False


def guess_mime(path: Path) -> str:
    mime, _ = mimetypes.guess_type(path.name)
    return mime or "application/octet-stream"


def friendly_title(path: Path, activity_name: str, when: datetime) -> str:
    """A title a six-year-old could read back. Never a file path."""
    stem = path.stem.replace("_", " ").replace("-", " ").strip()
    if stem and not stem.isdigit() and len(stem) <= 24:
        return stem.capitalize()
    return f"{activity_name} {when:%H:%M}"


class Journal:
    """The on-disk journal, loaded into memory once at start."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.entries: list[Entry] = []
        self._by_source: dict[str, Entry] = {}

    # -- loading --

    def load(self) -> None:
        self.entries = []
        self._by_source = {}
        if not self.root.is_dir():
            return
        for entry_file in sorted(self.root.glob("*/*/*/*/" + ENTRY_FILE)):
            try:
                data = json.loads(entry_file.read_text(encoding="utf-8"))
                entry = Entry.from_dict(data, entry_file.parent)
            except (OSError, ValueError, KeyError) as exc:
                log.warning("skipping unreadable journal entry %s: %s", entry_file, exc)
                continue
            self.entries.append(entry)
            if entry.source_path:
                self._by_source[entry.source_path] = entry
        self.entries.sort(key=lambda e: e.updated, reverse=True)
        log.info("journal loaded: %d entries from %s", len(self.entries), self.root)

    # -- import --

    def entry_for_source(self, source: Path) -> Entry | None:
        return self._by_source.get(str(source))

    def import_file(
        self,
        source: Path,
        activity_id: str,
        *,
        activity_name: str = "",
        now: datetime | None = None,
    ) -> Entry | None:
        """Copy ``source`` into the journal. Returns the entry if anything changed.

        Returns ``None`` when the file's bytes are identical to the version
        already stored -- activities rewrite their save files constantly and
        the child should not end up with forty copies of one drawing.
        """
        if not source.is_file():
            return None
        when = now or datetime.now()
        try:
            digest = sha256_file(source)
            size = source.stat().st_size
        except OSError as exc:
            log.warning("cannot read %s: %s", source, exc)
            return None

        entry = self.entry_for_source(source)
        if entry is not None:
            latest = entry.latest_version
            if latest is not None and latest.sha256 == digest:
                return None
            return self._add_version(entry, source, digest, size, when)

        return self._create_entry(source, activity_id, activity_name, digest, size, when)

    def _entry_directory(self, when: datetime, entry_id: str) -> Path:
        return self.root / f"{when:%Y}" / f"{when:%m}" / f"{when:%d}" / entry_id

    def _create_entry(
        self,
        source: Path,
        activity_id: str,
        activity_name: str,
        digest: str,
        size: int,
        when: datetime,
    ) -> Entry:
        base = f"{activity_id or 'thing'}-{when:%H%M%S}-{digest[:6]}"
        directory = self._entry_directory(when, base)
        suffix = 1
        while directory.exists():
            suffix += 1
            directory = self._entry_directory(when, f"{base}-{suffix}")

        entry = Entry(
            id=directory.name,
            activity_id=activity_id,
            created=when.isoformat(timespec="seconds"),
            updated=when.isoformat(timespec="seconds"),
            title=friendly_title(source, activity_name or activity_id, when),
            source_path=str(source),
            mime=guess_mime(source),
            directory=directory,
        )
        directory.mkdir(parents=True, exist_ok=True)
        self._store_version(entry, source, digest, size, when)
        entry.save()
        self.entries.insert(0, entry)
        self._by_source[entry.source_path] = entry
        log.info("journal kept %s from %s", entry.id, activity_id)
        return entry

    def _add_version(
        self, entry: Entry, source: Path, digest: str, size: int, when: datetime
    ) -> Entry:
        self._store_version(entry, source, digest, size, when)
        entry.updated = when.isoformat(timespec="seconds")
        entry.save()
        self.entries.sort(key=lambda e: e.updated, reverse=True)
        log.info("journal kept version %d of %s", len(entry.versions), entry.id)
        return entry

    def _store_version(
        self, entry: Entry, source: Path, digest: str, size: int, when: datetime
    ) -> None:
        number = len(entry.versions) + 1
        filename = f"v{number:03d}{source.suffix.lower()}"
        destination = entry.directory / filename
        entry.directory.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        entry.versions.append(
            Version(
                filename=filename,
                imported=when.isoformat(timespec="seconds"),
                size=size,
                sha256=digest,
            )
        )
        if entry.mime.startswith("image/"):
            make_thumbnail(destination, entry.directory / THUMB_NAME)

    # -- reading --

    def by_id(self, entry_id: str) -> Entry | None:
        return next((e for e in self.entries if e.id == entry_id), None)

    def for_activity(self, activity_id: str) -> list[Entry]:
        return [e for e in self.entries if e.activity_id == activity_id]

    def latest_for_activity(self, activity_id: str) -> Entry | None:
        """Drives the "recently used" thumbnail in a Home tile's corner."""
        return next((e for e in self.entries if e.activity_id == activity_id), None)

    def made_on(self, day: date) -> list[Entry]:
        return [e for e in self.entries if e.created_at.date() == day]

    def made_on_today(self, now: datetime | None = None) -> list[Entry]:
        """What the Goodbye screen counts (spec S7)."""
        return self.made_on((now or datetime.now()).date())

    def count_today(self, now: datetime | None = None) -> int:
        return len(self.made_on_today(now))

    def grouped(self, now: datetime | None = None) -> list[tuple[str, list[Entry]]]:
        """Today / Yesterday / Before (SYNTHESIS F1). Empty groups are dropped."""
        today = (now or datetime.now()).date()
        yesterday = today - timedelta(days=1)
        buckets: dict[str, list[Entry]] = {TODAY: [], YESTERDAY: [], BEFORE: []}
        for entry in sorted(self.entries, key=lambda e: e.updated, reverse=True):
            day = entry.updated_at.date()
            if day >= today:
                buckets[TODAY].append(entry)
            elif day == yesterday:
                buckets[YESTERDAY].append(entry)
            else:
                buckets[BEFORE].append(entry)
        return [(label, buckets[label]) for label in (TODAY, YESTERDAY, BEFORE) if buckets[label]]

    def favourites(self) -> list[Entry]:
        """The shelf: starred, most recently starred first, at most 8."""
        starred = [e for e in self.entries if e.starred]
        starred.sort(key=lambda e: e.starred_at or e.updated, reverse=True)
        return starred[:MAX_FAVOURITES]

    # -- writing --

    def set_starred(self, entry: Entry, starred: bool, now: datetime | None = None) -> None:
        when = now or datetime.now()
        entry.starred = starred
        entry.starred_at = when.isoformat(timespec="seconds") if starred else ""
        entry.save()
        if starred:
            self._trim_favourites(entry)

    def toggle_star(self, entry: Entry, now: datetime | None = None) -> bool:
        self.set_starred(entry, not entry.starred, now)
        return entry.starred

    def _trim_favourites(self, keep: Entry) -> None:
        starred = [e for e in self.entries if e.starred]
        if len(starred) <= MAX_FAVOURITES:
            return
        starred.sort(key=lambda e: e.starred_at or e.updated, reverse=True)
        for extra in starred[MAX_FAVOURITES:]:
            if extra is keep:
                continue
            extra.starred = False
            extra.starred_at = ""
            extra.save()
            log.info("favourites shelf full: quietly unstarred %s", extra.id)


def build_pages(
    groups: list[tuple[str, list[Entry]]], per_page: int
) -> list[list[tuple[str, object]]]:
    """Lay day-grouped entries out into fixed pages of cards.

    Returns pages of ``("heading", label)`` and ``("card", entry)`` items. A
    group that spans a page break repeats its heading at the top of the next
    page -- a five-year-old who paged forward and lost "Today" would have no
    idea what they were looking at.
    """
    if per_page <= 0:
        raise ValueError("per_page must be positive")
    pages: list[list[tuple[str, object]]] = []
    page: list[tuple[str, object]] = []
    cards = 0

    for label, entries in groups:
        if not entries:
            continue
        page.append(("heading", label))
        for entry in entries:
            if cards >= per_page:
                pages.append(page)
                page = [("heading", label)]
                cards = 0
            page.append(("card", entry))
            cards += 1

    if any(kind == "card" for kind, _ in page):
        pages.append(page)
    return pages or [[]]


class JournalImporter:
    """Sweeps activities' watch directories and imports what is new.

    Pure Python and synchronous so it is fully testable; :class:`JournalWatcher`
    is the GIO wrapper that decides *when* to call :meth:`sweep`.
    """

    def __init__(self, journal: Journal, activities: list[Any]) -> None:
        self.journal = journal
        self.activities = activities
        #: paths whose mtime+size we have already looked at
        self._seen: dict[Path, tuple[float, int]] = {}

    def watch_directories(self) -> list[Path]:
        directories: list[Path] = []
        for activity in self.activities:
            directories.extend(activity.journal_watch)
        return directories

    def prime(self) -> None:
        """Record what already exists without importing it.

        Called once at start so the shell does not re-import a child's entire
        back catalogue of Tux Paint saves on every boot.
        """
        for activity in self.activities:
            for path in self._candidates(activity):
                self._remember(path)

    def sweep(self, now: datetime | None = None) -> list[Entry]:
        """Import every new or changed file. Returns what was kept."""
        kept: list[Entry] = []
        for activity in self.activities:
            for path in self._candidates(activity):
                stamp = self._stat(path)
                if stamp is None or self._seen.get(path) == stamp:
                    continue
                self._seen[path] = stamp
                entry = self.journal.import_file(
                    path,
                    activity.id,
                    activity_name=getattr(activity, "name", ""),
                    now=now,
                )
                if entry is not None:
                    kept.append(entry)
        return kept

    def _candidates(self, activity: Any) -> list[Path]:
        pattern = getattr(activity, "journal_glob", "*") or "*"
        found: list[Path] = []
        for directory in activity.journal_watch:
            if not directory.is_dir():
                continue
            found.extend(p for p in sorted(directory.glob(pattern)) if p.is_file())
        return found

    @staticmethod
    def _stat(path: Path) -> tuple[float, int] | None:
        try:
            info = path.stat()
        except OSError:
            return None
        return (info.st_mtime, info.st_size)

    def _remember(self, path: Path) -> None:
        stamp = self._stat(path)
        if stamp is not None:
            self._seen[path] = stamp


class JournalWatcher:
    """Gio.FileMonitor on every watch directory, debounced (spec section 5).

    File monitors are unreliable across the filesystems an activity might save
    to (and Tux Paint writes a thumbnail *and* a PNG for every save), so this
    also sweeps periodically. Both paths funnel into one debounced sweep.
    """

    DEBOUNCE_MS = 2000
    SAFETY_SWEEP_MS = 15000

    def __init__(
        self,
        importer: JournalImporter,
        on_import: Any = None,
        debounce_ms: int = DEBOUNCE_MS,
    ) -> None:
        self.importer = importer
        self.on_import = on_import
        self.debounce_ms = debounce_ms
        self._monitors: list[Any] = []
        self._pending: int | None = None
        self._safety: int | None = None

    def start(self) -> None:
        import gi

        gi.require_version("Gio", "2.0")
        from gi.repository import Gio, GLib

        self.importer.prime()
        for directory in self.importer.watch_directories():
            try:
                directory.mkdir(parents=True, exist_ok=True)
                gfile = Gio.File.new_for_path(str(directory))
                monitor = gfile.monitor_directory(Gio.FileMonitorFlags.WATCH_MOVES, None)
                monitor.connect("changed", self._on_changed)
                self._monitors.append(monitor)
                log.info("watching %s for new work", directory)
            except (OSError, GLib.Error) as exc:
                log.warning("cannot watch %s: %s", directory, exc)

        self._safety = GLib.timeout_add(self.SAFETY_SWEEP_MS, self._safety_sweep)

    def _on_changed(self, _monitor: Any, _f: Any, _other: Any, _event: Any) -> None:
        from gi.repository import GLib

        if self._pending is not None:
            GLib.source_remove(self._pending)
        self._pending = GLib.timeout_add(self.debounce_ms, self._run_sweep)

    def _run_sweep(self) -> bool:
        self._pending = None
        self.sweep_now()
        return False  # GLib.SOURCE_REMOVE

    def _safety_sweep(self) -> bool:
        self.sweep_now()
        return True  # GLib.SOURCE_CONTINUE

    def sweep_now(self) -> list[Entry]:
        kept = self.importer.sweep()
        if kept and self.on_import is not None:
            self.on_import(kept)
        return kept

    def stop(self) -> None:
        from gi.repository import GLib

        for handle in (self._pending, self._safety):
            if handle is not None:
                GLib.source_remove(handle)
        self._pending = None
        self._safety = None
        for monitor in self._monitors:
            monitor.cancel()
        self._monitors = []
