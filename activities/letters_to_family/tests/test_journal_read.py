"""Reading the child's own Journal, so a letter can send something they made.

The strongest version of "make a letter" is not "draw something now", it is
*send the dinosaur you were proud of on Tuesday*. The properties pinned here:
read-only, pictures only, newest first, and a broken entry is one fewer picture
rather than a traceback in front of a five-year-old.
"""

from __future__ import annotations

import json
import os

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


# --- the letters that came back (design note section 7 step 5) --------------
#
# Landed 2026-08-24: the shelf reads the Journal, where the shell put each
# reply exactly once, instead of the inbox, which has no idea what the child
# has already been given and so showed every letter forever.


def write_reply(
    root,
    entry_id: str,
    *,
    created: str,
    from_name: str = "Grandad",
    source: str = "",
    words: str = "",
    voice: bool = False,
    picture: bool = True,
    thumb: bool = True,
    kind: str = "letter-reply",
    meta=None,
):
    """One imported reply, in the layout ``kidnix_shell.inbox`` writes."""
    day = created[:10].replace("-", "/")
    directory = root / day / entry_id
    directory.mkdir(parents=True, exist_ok=True)
    filename = "v001.png" if picture else "v001.ogg"
    (directory / filename).write_bytes(b"data-" + entry_id.encode())
    if thumb:
        (directory / "thumb.png").write_bytes(b"\x89PNG\r\n\x1a\nthumb")
    if words:
        (directory / "caption.txt").write_text(words, encoding="utf-8")
    if voice:
        (directory / "note.ogg").write_bytes(b"OggS")
    (directory / "entry.json").write_text(
        json.dumps(
            {
                "id": entry_id,
                "activity_id": "letters",
                "created": created + "T10:00:00",
                "updated": created + "T10:00:00",
                "title": f"A letter from {from_name}",
                "source_path": source,
                "mime": "image/png" if picture else "audio/ogg",
                "versions": [
                    {"filename": filename, "imported": created, "size": 5, "sha256": "x"}
                ],
            }
        )
    )
    document = meta
    if document is None:
        document = {
            "schema": 1,
            "kind": kind,
            "from": from_name,
            "source": source or f"/var/lib/kidnix/inbox/sam/{entry_id}",
            "caption": words,
        }
    (directory / "meta.json").write_text(json.dumps(document))
    return directory


def an_inbox_reply(inbox, name: str, *, profile: str = "sam"):
    folder = inbox / profile / name
    folder.mkdir(parents=True)
    (folder / "photo.png").write_bytes(b"\x89PNG\r\n\x1a\nphoto")
    return folder


def test_an_imported_reply_is_read_back_off_the_shelf(tmp_path):
    from letters_to_family.journal_read import letter_replies

    directory = write_reply(
        tmp_path, "r1", created="2026-08-21", from_name="Nanna", words="Thank you!", voice=True
    )
    (reply,) = letter_replies(tmp_path)
    assert reply.path == directory
    assert reply.from_name == "Nanna"
    assert reply.words == "Thank you!"
    assert reply.has_picture and reply.picture.name == "v001.png"
    assert reply.has_voice and reply.voice.name == "note.ogg"
    assert reply.speak_text == "A letter from Nanna."


def test_a_thing_the_child_made_is_not_a_letter_that_came_back(tmp_path):
    """``meta.json``'s kind is the whole test: a drawing must never turn up
    on "Letters for you", and neither must a card we cannot identify."""
    from letters_to_family.journal_read import letter_replies

    write_entry(tmp_path, "mine", created="2026-08-20")  # no meta.json at all
    write_reply(tmp_path, "theirs", created="2026-08-19", kind="drawing")
    assert letter_replies(tmp_path) == []


def test_the_card_is_what_the_tile_shows_so_a_voice_letter_is_not_a_blank(tmp_path):
    """A reply that is only a voice has no picture -- it has the envelope the
    shell drew, which is the difference between six letters and six
    placeholders."""
    from letters_to_family.journal_read import letter_replies

    write_reply(tmp_path, "r1", created="2026-08-21", picture=False, voice=True)
    (reply,) = letter_replies(tmp_path)
    assert not reply.has_picture
    assert reply.tile_image is not None and reply.tile_image.name == "thumb.png"


def test_a_letter_with_no_card_at_all_falls_back_to_the_placeholder(tmp_path):
    from letters_to_family.journal_read import letter_replies

    write_reply(tmp_path, "r1", created="2026-08-21", picture=False, thumb=False)
    (reply,) = letter_replies(tmp_path)
    assert reply.tile_image is None


def test_the_newest_letter_is_first(tmp_path):
    from letters_to_family.journal_read import letter_replies

    write_reply(tmp_path, "old", created="2026-08-01", from_name="Nanna")
    write_reply(tmp_path, "new", created="2026-08-21", from_name="Grandad")
    assert [r.from_name for r in letter_replies(tmp_path)] == ["Grandad", "Nanna"]


def test_only_a_few_letters_are_shown(tmp_path):
    from letters_to_family.journal_read import SHELF_LIMIT, letter_replies

    for index in range(SHELF_LIMIT + 4):
        write_reply(tmp_path, f"r{index:02d}", created=f"2026-08-{index + 1:02d}")
    assert len(letter_replies(tmp_path)) == SHELF_LIMIT


def test_a_letter_whose_meta_is_broken_is_simply_not_a_letter(tmp_path):
    from letters_to_family.journal_read import letter_replies

    directory = write_reply(tmp_path, "r1", created="2026-08-21")
    (directory / "meta.json").write_text("{ not json")
    assert letter_replies(tmp_path) == []


def test_a_nameless_sender_is_never_a_blank_tile(tmp_path):
    from letters_to_family.journal_read import letter_replies

    write_reply(tmp_path, "r1", created="2026-08-21", meta={"kind": "letter-reply"})
    (reply,) = letter_replies(tmp_path)
    assert reply.from_name == "someone"


def test_reading_the_letters_writes_nothing_into_the_journal(tmp_path):
    from letters_to_family.journal_read import letter_replies

    write_reply(tmp_path, "r1", created="2026-08-21", words="hello", voice=True)
    before = sorted(p.relative_to(tmp_path).as_posix() for p in tmp_path.rglob("*"))
    letter_replies(tmp_path)
    after = sorted(p.relative_to(tmp_path).as_posix() for p in tmp_path.rglob("*"))
    assert before == after


# --- the shelf: the Journal, plus anything not swept yet --------------------


def test_an_imported_reply_is_one_tile_and_not_two(tmp_path):
    """The bug this closes: the letter was in My Things *and* still on the
    shelf, because the inbox is a grown-up's folder and nothing in it is ever
    marked read."""
    from letters_to_family.journal_read import shelf_replies

    inbox = tmp_path / "inbox"
    folder = an_inbox_reply(inbox, "grandad")
    write_reply(tmp_path / "journal", "r1", created="2026-08-21", source=str(folder))

    found = shelf_replies(tmp_path / "journal", "sam", inbox)
    assert len(found) == 1
    assert found[0].path.name == "r1"  # the Journal's copy, with the card on it


def test_a_reply_that_arrived_since_the_last_sweep_still_shows(tmp_path):
    """The shell sweeps once a sitting. A folder dropped in while the child is
    at the machine must not be invisible until the next login."""
    from letters_to_family.journal_read import shelf_replies

    inbox = tmp_path / "inbox"
    an_inbox_reply(inbox, "nanna")
    found = shelf_replies(tmp_path / "journal", "sam", inbox)
    assert [r.from_name for r in found] == ["Nanna"]


def test_the_two_sources_are_shown_newest_first_together(tmp_path):
    from letters_to_family.journal_read import shelf_replies

    inbox = tmp_path / "inbox"
    fresh = an_inbox_reply(inbox, "nanna")
    os.utime(fresh, (1_800_000_000, 1_800_000_000))
    write_reply(tmp_path / "journal", "r1", created="2026-08-01", from_name="Grandad")

    found = shelf_replies(tmp_path / "journal", "sam", inbox)
    assert [r.from_name for r in found] == ["Nanna", "Grandad"]


def test_a_shelf_with_nothing_anywhere_is_empty_and_quiet(tmp_path):
    from letters_to_family.journal_read import shelf_replies

    assert shelf_replies(tmp_path / "journal", "sam", tmp_path / "inbox") == []


def test_the_shelf_reads_this_childs_journal_and_no_other(tmp_path):
    """``journal_root`` is already one child's -- that is what keeps a sibling's
    letters off this shelf without this module knowing about profiles."""
    from letters_to_family.journal_read import shelf_replies

    sam = tmp_path / "profiles" / "sam" / "journal"
    rose = tmp_path / "profiles" / "rose" / "journal"
    write_reply(sam, "r1", created="2026-08-21", from_name="Grandad")
    write_reply(rose, "r2", created="2026-08-21", from_name="Auntie")

    assert [r.from_name for r in shelf_replies(sam, "sam", tmp_path / "inbox")] == ["Grandad"]
