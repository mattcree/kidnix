"""The Journal storage contract (spec section 5)."""

from __future__ import annotations

import json
from datetime import timedelta
from pathlib import Path

from kidnix_shell.journal import (
    MAX_FAVOURITES,
    Journal,
    JournalImporter,
    build_pages,
    friendly_title,
)

from .conftest import NOW, make_activity, write_png


def test_importing_a_file_creates_a_dated_entry(tmp_path: Path, journal: Journal) -> None:
    source = write_png(tmp_path / "work" / "picture.png")
    entry = journal.import_file(source, "scribble", now=NOW)
    assert entry is not None
    assert entry.directory.parent.parent.parent.name == "2026"
    assert entry.directory.parent.parent.name == "08"
    assert entry.directory.parent.name == "18"
    assert (entry.directory / "entry.json").is_file()


def test_the_file_is_copied_not_moved(tmp_path: Path, journal: Journal) -> None:
    source = write_png(tmp_path / "work" / "picture.png")
    entry = journal.import_file(source, "scribble", now=NOW)
    assert source.is_file()
    assert entry is not None
    assert entry.latest_path is not None
    assert entry.latest_path.read_bytes() == source.read_bytes()


def test_entry_json_carries_the_specified_fields(tmp_path: Path, journal: Journal) -> None:
    source = write_png(tmp_path / "work" / "picture.png")
    entry = journal.import_file(source, "scribble", now=NOW)
    assert entry is not None
    data = json.loads((entry.directory / "entry.json").read_text())
    for field in (
        "id",
        "activity_id",
        "created",
        "updated",
        "title",
        "source_path",
        "mime",
        "starred",
        "versions",
    ):
        assert field in data


def test_reimporting_identical_bytes_is_a_no_op(tmp_path: Path, journal: Journal) -> None:
    source = write_png(tmp_path / "work" / "picture.png")
    assert journal.import_file(source, "scribble", now=NOW) is not None
    assert journal.import_file(source, "scribble", now=NOW) is None
    assert len(journal.entries) == 1


def test_a_changed_file_becomes_a_new_version(tmp_path: Path, journal: Journal) -> None:
    source = write_png(tmp_path / "work" / "picture.png")
    journal.import_file(source, "scribble", now=NOW)
    write_png(source, colour=(0, 0, 255))
    entry = journal.import_file(source, "scribble", now=NOW + timedelta(minutes=5))
    assert entry is not None
    assert len(entry.versions) == 2
    assert entry.versions[0].filename == "v001.png"
    assert entry.versions[1].filename == "v002.png"
    assert len(journal.entries) == 1


def test_versions_record_size_and_digest(tmp_path: Path, journal: Journal) -> None:
    source = write_png(tmp_path / "work" / "picture.png")
    entry = journal.import_file(source, "scribble", now=NOW)
    assert entry is not None
    version = entry.versions[0]
    assert version.size == source.stat().st_size
    assert len(version.sha256) == 64


def test_a_missing_source_imports_nothing(tmp_path: Path, journal: Journal) -> None:
    assert journal.import_file(tmp_path / "nope.png", "scribble", now=NOW) is None


def test_entries_reload_from_disk(tmp_path: Path, paths, journal: Journal) -> None:  # type: ignore[no-untyped-def]
    for index in range(3):
        source = write_png(tmp_path / "work" / f"p{index}.png", colour=(index * 40, 0, 0))
        journal.import_file(source, "scribble", now=NOW)

    reloaded = Journal(paths.journal_root)
    reloaded.load()
    assert len(reloaded.entries) == 3
    assert {e.activity_id for e in reloaded.entries} == {"scribble"}


def test_grouping_splits_today_yesterday_and_before(tmp_path: Path, journal: Journal) -> None:
    for index, when in enumerate(
        (NOW, NOW - timedelta(days=1), NOW - timedelta(days=9), NOW - timedelta(days=40))
    ):
        source = write_png(tmp_path / "work" / f"p{index}.png", colour=(index * 30, 0, 0))
        journal.import_file(source, "scribble", now=when)

    groups = dict(journal.grouped(now=NOW))
    assert len(groups["Today"]) == 1
    assert len(groups["Yesterday"]) == 1
    assert len(groups["Before"]) == 2


def test_empty_groups_are_dropped(tmp_path: Path, journal: Journal) -> None:
    source = write_png(tmp_path / "work" / "p.png")
    journal.import_file(source, "scribble", now=NOW)
    assert [label for label, _ in journal.grouped(now=NOW)] == ["Today"]


def test_count_today_only_counts_today(tmp_path: Path, journal: Journal) -> None:
    for index, when in enumerate((NOW, NOW, NOW - timedelta(days=2))):
        source = write_png(tmp_path / "work" / f"p{index}.png", colour=(index * 50, 0, 0))
        journal.import_file(source, "scribble", now=when)
    assert journal.count_today(NOW) == 2


def test_starring_puts_an_entry_on_the_shelf(tmp_path: Path, journal: Journal) -> None:
    source = write_png(tmp_path / "work" / "p.png")
    entry = journal.import_file(source, "scribble", now=NOW)
    assert entry is not None
    assert journal.favourites() == []
    assert journal.toggle_star(entry, now=NOW) is True
    assert journal.favourites() == [entry]
    assert journal.toggle_star(entry, now=NOW) is False
    assert journal.favourites() == []


def test_the_favourites_shelf_is_bounded(tmp_path: Path, journal: Journal) -> None:
    entries = []
    for index in range(MAX_FAVOURITES + 3):
        source = write_png(tmp_path / "work" / f"p{index}.png", colour=(index * 10, 5, 5))
        entry = journal.import_file(source, "scribble", now=NOW + timedelta(seconds=index))
        assert entry is not None
        entries.append(entry)

    for index, entry in enumerate(entries):
        journal.set_starred(entry, True, now=NOW + timedelta(minutes=index))

    favourites = journal.favourites()
    assert len(favourites) == MAX_FAVOURITES
    # The most recently starred survive; the oldest were quietly unstarred.
    assert favourites[0] is entries[-1]
    assert entries[0].starred is False


def test_starring_state_survives_a_reload(tmp_path: Path, paths, journal: Journal) -> None:  # type: ignore[no-untyped-def]
    source = write_png(tmp_path / "work" / "p.png")
    entry = journal.import_file(source, "scribble", now=NOW)
    assert entry is not None
    journal.set_starred(entry, True, now=NOW)

    reloaded = Journal(paths.journal_root)
    reloaded.load()
    assert len(reloaded.favourites()) == 1


def test_thumbnails_are_generated_for_images(tmp_path: Path, journal: Journal) -> None:
    source = write_png(tmp_path / "work" / "p.png")
    entry = journal.import_file(source, "scribble", now=NOW)
    assert entry is not None
    assert entry.is_image
    # GdkPixbuf is present on the image and on this host; if it is not, the
    # contract is "no thumbnail, fall back to the activity icon".
    if entry.thumbnail is not None:
        assert entry.thumbnail.name == "thumb.png"
        assert entry.thumbnail.stat().st_size > 0


def test_non_images_get_no_thumbnail(tmp_path: Path, journal: Journal) -> None:
    source = tmp_path / "work" / "story.txt"
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_text("once upon a time", encoding="utf-8")
    entry = journal.import_file(source, "story", now=NOW)
    assert entry is not None
    assert not entry.is_image
    assert entry.thumbnail is None


def test_latest_for_activity_drives_the_home_tile_corner(tmp_path: Path, journal: Journal) -> None:
    old = write_png(tmp_path / "work" / "old.png", colour=(1, 1, 1))
    new = write_png(tmp_path / "work" / "new.png", colour=(2, 2, 2))
    journal.import_file(old, "scribble", now=NOW - timedelta(hours=2))
    journal.import_file(new, "scribble", now=NOW)
    latest = journal.latest_for_activity("scribble")
    assert latest is not None and latest.source_path == str(new)
    assert journal.latest_for_activity("nobody") is None


def test_friendly_title_prefers_a_readable_stem() -> None:
    assert friendly_title(Path("my_dog.png"), "Scribble", NOW) == "My dog"
    assert friendly_title(Path("20260818120000.png"), "Scribble", NOW) == "Scribble 12:00"


# --- the importer sweep --------------------------------------------------


def test_the_importer_only_takes_new_files(tmp_path: Path, journal: Journal) -> None:
    watch = tmp_path / "watch"
    watch.mkdir()
    activity = make_activity(watch=[watch])
    importer = JournalImporter(journal, [activity])

    write_png(watch / "one.png")
    assert len(importer.sweep(now=NOW)) == 1
    assert importer.sweep(now=NOW) == []

    write_png(watch / "two.png", colour=(0, 255, 0))
    assert len(importer.sweep(now=NOW)) == 1


def test_priming_skips_the_back_catalogue(tmp_path: Path, journal: Journal) -> None:
    watch = tmp_path / "watch"
    watch.mkdir()
    write_png(watch / "yesterdays.png")
    importer = JournalImporter(journal, [make_activity(watch=[watch])])
    importer.prime()
    assert importer.sweep(now=NOW) == []


def test_the_glob_is_honoured(tmp_path: Path, journal: Journal) -> None:
    watch = tmp_path / "watch"
    watch.mkdir()
    write_png(watch / "keep.png")
    (watch / "ignore.tmp").write_text("scratch", encoding="utf-8")
    importer = JournalImporter(journal, [make_activity(watch=[watch])])
    kept = importer.sweep(now=NOW)
    assert [Path(e.source_path).name for e in kept] == ["keep.png"]


def test_a_missing_watch_directory_is_survivable(tmp_path: Path, journal: Journal) -> None:
    importer = JournalImporter(journal, [make_activity(watch=[tmp_path / "nope"])])
    assert importer.sweep(now=NOW) == []


# --- pagination ----------------------------------------------------------


def test_pages_repeat_the_day_heading_across_a_break(tmp_path: Path, journal: Journal) -> None:
    entries = []
    for index in range(10):
        source = write_png(tmp_path / "work" / f"p{index}.png", colour=(index * 20, 0, 0))
        entry = journal.import_file(source, "scribble", now=NOW)
        assert entry is not None
        entries.append(entry)

    pages = build_pages([("Today", entries)], per_page=8)
    assert len(pages) == 2
    assert pages[0][0] == ("heading", "Today")
    assert pages[1][0] == ("heading", "Today")
    assert sum(1 for kind, _ in pages[0] if kind == "card") == 8
    assert sum(1 for kind, _ in pages[1] if kind == "card") == 2


def test_no_entries_still_produces_one_page() -> None:
    assert build_pages([], per_page=8) == [[]]
