"""Reading the child's own Journal, so a letter can send something they made.

The strongest version of "make a letter" is not "draw something now", it is
*send the dinosaur you were proud of on Tuesday*. The properties pinned here:
read-only, pictures only, newest first, and a broken entry is one fewer picture
rather than a traceback in front of a five-year-old.
"""

from __future__ import annotations

import json

from letters_to_family.journal_read import (
    DEFAULT_LIMIT,
    JournalPicture,
    read_entry,
    recent_pictures,
)


def write_entry(
    root,
    entry_id: str,
    *,
    created: str,
    title: str = "A dinosaur",
    mime: str = "image/png",
    filename: str = "v001.png",
    thumb: bool = True,
    make_file: bool = True,
    body=None,
):
    day = created[:10].replace("-", "/")
    directory = root / day / entry_id
    directory.mkdir(parents=True, exist_ok=True)
    if make_file:
        (directory / filename).write_bytes(b"\x89PNG\r\n\x1a\n" + entry_id.encode())
    if thumb:
        (directory / "thumb.png").write_bytes(b"\x89PNG\r\n\x1a\nthumb")
    document = body
    if document is None:
        document = {
            "id": entry_id,
            "activity_id": "hello-draw",
            "created": created + "T10:00:00",
            "updated": created + "T10:00:00",
            "title": title,
            "source_path": "",
            "mime": mime,
            "versions": [
                {"filename": filename, "imported": created, "size": 8, "sha256": "x"}
            ],
        }
    (directory / "entry.json").write_text(json.dumps(document))
    return directory


def test_a_picture_entry_is_offered(tmp_path):
    write_entry(tmp_path, "aaa", created="2026-08-20")
    found = recent_pictures(tmp_path)
    assert len(found) == 1
    assert isinstance(found[0], JournalPicture)
    assert found[0].title == "A dinosaur"
    assert found[0].picture.name == "v001.png"


def test_the_thumbnail_is_what_the_tile_shows_when_there_is_one(tmp_path):
    write_entry(tmp_path, "aaa", created="2026-08-20")
    picture = recent_pictures(tmp_path)[0]
    assert picture.thumb is not None
    assert picture.tile_image == picture.thumb


def test_without_a_thumbnail_the_tile_shows_the_picture_itself(tmp_path):
    write_entry(tmp_path, "aaa", created="2026-08-20", thumb=False)
    picture = recent_pictures(tmp_path)[0]
    assert picture.thumb is None
    assert picture.tile_image == picture.picture


def test_the_tile_says_what_the_child_called_it_and_never_a_date(tmp_path):
    write_entry(tmp_path, "aaa", created="2026-08-20", title="My dinosaur")
    picture = recent_pictures(tmp_path)[0]
    assert picture.speak_text == "My dinosaur"
    assert not any(character.isdigit() for character in picture.speak_text)


def test_an_untitled_entry_still_has_something_to_say(tmp_path):
    write_entry(tmp_path, "aaa", created="2026-08-20", title="")
    assert recent_pictures(tmp_path)[0].speak_text == "A thing I made"


def test_a_sound_entry_is_not_offered_because_a_letter_cannot_send_a_tune(tmp_path):
    write_entry(tmp_path, "aaa", created="2026-08-20", mime="audio/ogg", filename="v001.ogg")
    assert recent_pictures(tmp_path) == []


def test_the_latest_version_is_the_one_that_is_sent(tmp_path):
    directory = write_entry(tmp_path, "aaa", created="2026-08-20")
    (directory / "v002.png").write_bytes(b"\x89PNG\r\n\x1a\nnewer")
    document = json.loads((directory / "entry.json").read_text())
    document["versions"].append(
        {"filename": "v002.png", "imported": "2026-08-21", "size": 9, "sha256": "y"}
    )
    (directory / "entry.json").write_text(json.dumps(document))
    assert recent_pictures(tmp_path)[0].picture.name == "v002.png"


def test_newest_first(tmp_path):
    write_entry(tmp_path, "old", created="2026-08-18")
    write_entry(tmp_path, "new", created="2026-08-22")
    write_entry(tmp_path, "mid", created="2026-08-20")
    assert [p.entry_id for p in recent_pictures(tmp_path)] == ["new", "mid", "old"]


def test_only_a_few_are_offered_because_a_choice_screen_is_capped(tmp_path):
    """B2: dialogs and choice screens are five choices, and the fifth control
    on that row is "draw a new one"."""
    for index in range(9):
        write_entry(tmp_path, f"e{index}", created="2026-08-2" [:9] + str(index % 9 + 1))
    assert len(recent_pictures(tmp_path)) == DEFAULT_LIMIT
    assert DEFAULT_LIMIT == 4


def test_a_missing_journal_is_no_pictures_and_no_error(tmp_path):
    assert recent_pictures(tmp_path / "never-existed") == []


def test_a_broken_entry_json_is_skipped_not_raised(tmp_path):
    directory = tmp_path / "2026/08/20/broken"
    directory.mkdir(parents=True)
    (directory / "entry.json").write_text("{not json at all")
    write_entry(tmp_path, "ok", created="2026-08-21")
    assert [p.entry_id for p in recent_pictures(tmp_path)] == ["ok"]


def test_an_entry_whose_file_is_gone_is_skipped(tmp_path):
    write_entry(tmp_path, "aaa", created="2026-08-20", make_file=False)
    assert recent_pictures(tmp_path) == []


def test_an_entry_with_no_versions_is_skipped(tmp_path):
    write_entry(
        tmp_path,
        "aaa",
        created="2026-08-20",
        body={"id": "aaa", "created": "2026-08-20T10:00:00", "mime": "image/png", "versions": []},
    )
    assert recent_pictures(tmp_path) == []


def test_a_version_filename_that_tries_to_escape_the_entry_is_refused(tmp_path):
    """A filename is a name, not a path. Nothing in the Journal writes one with
    a slash in it, and if something ever did it would not be followed."""
    directory = write_entry(tmp_path, "aaa", created="2026-08-20")
    document = json.loads((directory / "entry.json").read_text())
    document["versions"] = [
        {"filename": "../../../etc/passwd", "imported": "x", "size": 1, "sha256": "y"}
    ]
    (directory / "entry.json").write_text(json.dumps(document))
    assert read_entry(directory / "entry.json") is None


def test_reading_the_journal_writes_nothing_into_it(tmp_path):
    write_entry(tmp_path, "aaa", created="2026-08-20")
    before = sorted(p.relative_to(tmp_path).as_posix() for p in tmp_path.rglob("*"))
    recent_pictures(tmp_path)
    after = sorted(p.relative_to(tmp_path).as_posix() for p in tmp_path.rglob("*"))
    assert before == after
