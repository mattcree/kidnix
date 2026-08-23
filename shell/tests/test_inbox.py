"""Letters that came back: the inbox, and the card it becomes.

`docs/design/letters-to-family.md` section 7 is the contract these hold to --
where a reply lives, that it is imported once and only once, that nothing in a
grown-up's folder is touched, and that the child is told once, gently, at Home
(SYNTHESIS D6).
"""

from __future__ import annotations

import json
import os
import re
from datetime import datetime
from pathlib import Path

import pytest

from kidnix_shell.inbox import (
    ANNOUNCEMENT,
    CAPTION_NAME,
    KIND,
    META_NAME,
    Announcement,
    Imported,
    Reply,
    announcement,
    draw_envelope,
    import_replies,
    inbox_dir,
    read_replies,
    state_path,
)
from kidnix_shell.journal import THUMB_NAME, Journal
from kidnix_shell.voice import NOTE_NAME, has_note

from .conftest import NOW, write_png

LATER = datetime(2026, 8, 19, 9, 30, 0)


# -- a little inbox on disk --------------------------------------------------


def make_inbox(tmp_path: Path) -> Path:
    root = tmp_path / "var" / "lib" / "kidnix" / "inbox"
    root.mkdir(parents=True)
    return root


def reply_dir(root: Path, profile: str, name: str) -> Path:
    directory = root / profile / name
    directory.mkdir(parents=True)
    return directory


def write_ogg(path: Path) -> Path:
    """Enough of an Ogg container to be a file. Nothing here decodes it."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"OggS\x00\x02" + b"\x00" * 64)
    return path


def write_words(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def snapshot(directory: Path) -> dict[str, bytes]:
    """Every file under ``directory``, by relative path, with its bytes."""
    return {
        str(path.relative_to(directory)): path.read_bytes()
        for path in sorted(directory.rglob("*"))
        if path.is_file()
    }


class Drawer:
    """A stand-in for the envelope card, so the import can be asserted anywhere."""

    def __init__(self, works: bool = True) -> None:
        self.calls: list[tuple[Path, str]] = []
        self.works = works

    def __call__(self, destination: Path, words: str = "") -> bool:
        self.calls.append((destination, words))
        if self.works:
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(b"drawn")
        return self.works


@pytest.fixture
def inbox(tmp_path: Path) -> Path:
    return make_inbox(tmp_path)


@pytest.fixture
def state(tmp_path: Path) -> Path:
    return state_path(tmp_path / "state")


def sweep(
    journal: Journal,
    inbox: Path,
    state: Path,
    *,
    profile: str = "ada",
    now: datetime = NOW,
    envelope: Drawer | None = None,
) -> list[Imported]:
    return import_replies(
        journal,
        profile_id=profile,
        state=state,
        root=inbox,
        now=now,
        envelope=envelope or Drawer(),
    )


# -- reading the inbox -------------------------------------------------------


def test_a_folder_with_a_picture_is_one_reply(inbox: Path) -> None:
    write_png(reply_dir(inbox, "ada", "grandad") / "beach.png")
    replies = read_replies("ada", inbox)
    assert len(replies) == 1
    assert replies[0].kind == "image"
    assert replies[0].from_name == "Grandad"


def test_a_loose_file_is_also_one_reply(inbox: Path) -> None:
    (inbox / "ada").mkdir()
    write_png(inbox / "ada" / "nanna.png")
    replies = read_replies("ada", inbox)
    assert [(r.kind, r.from_name) for r in replies] == [("image", "Nanna")]


def test_the_sender_comes_from_from_txt(inbox: Path) -> None:
    folder = reply_dir(inbox, "ada", "reply-one")
    write_png(folder / "photo.png")
    write_words(folder / "from.txt", "Grandad Bill\nsecond line ignored\n")
    assert read_replies("ada", inbox)[0].from_name == "Grandad Bill"


def test_the_folder_name_loses_its_digits(inbox: Path) -> None:
    write_png(reply_dir(inbox, "ada", "2026-08-23-grandad") / "photo.png")
    # 01 #19: that string is spoken to the child, and a child never hears a number.
    assert read_replies("ada", inbox)[0].from_name == "Grandad"


def test_dot_directories_are_ignored(inbox: Path) -> None:
    write_png(reply_dir(inbox, "ada", ".imported") / "old.png")
    assert read_replies("ada", inbox) == []


def test_a_file_that_is_not_a_picture_a_sound_or_words_is_ignored(inbox: Path) -> None:
    (inbox / "ada").mkdir()
    (inbox / "ada" / "letter.pdf").write_bytes(b"%PDF-1.7")
    assert read_replies("ada", inbox) == []


def test_replies_come_back_newest_first(inbox: Path) -> None:
    older = write_png(reply_dir(inbox, "ada", "nanna") / "a.png")
    newer = write_png(reply_dir(inbox, "ada", "grandad") / "b.png")
    os.utime(older.parent, (1_000_000, 1_000_000))
    os.utime(newer.parent, (2_000_000, 2_000_000))
    assert [r.from_name for r in read_replies("ada", inbox)] == ["Grandad", "Nanna"]


def test_a_missing_inbox_is_not_an_error(inbox: Path) -> None:
    assert read_replies("nobody", inbox) == []


def test_an_unset_profile_gets_its_own_folder(inbox: Path) -> None:
    # Never the root itself: two children's letters must not share one folder
    # the day somebody adds a second profile.
    assert inbox_dir("", inbox) == inbox / "_"
    assert inbox_dir("  ", inbox) == inbox / "_"


# -- the card ----------------------------------------------------------------


def test_a_picture_becomes_a_journal_card(journal: Journal, inbox: Path, state: Path) -> None:
    write_png(reply_dir(inbox, "ada", "grandad") / "beach.png")
    kept = sweep(journal, inbox, state)
    assert len(kept) == 1
    entry = kept[0].entry
    assert (entry.directory / "v001.png").is_file()
    assert (entry.directory / THUMB_NAME).is_file()  # the picture thumbnails itself
    assert entry.activity_id == "letters"


def test_the_card_is_named_for_the_sender(journal: Journal, inbox: Path, state: Path) -> None:
    write_png(reply_dir(inbox, "ada", "grandad") / "beach.png")
    assert sweep(journal, inbox, state)[0].entry.title == "A letter from Grandad"


def test_meta_json_records_the_kind_and_the_sender(
    journal: Journal, inbox: Path, state: Path
) -> None:
    folder = reply_dir(inbox, "ada", "grandad")
    write_png(folder / "beach.png")
    entry = sweep(journal, inbox, state)[0].entry
    meta = json.loads((entry.directory / META_NAME).read_text(encoding="utf-8"))
    assert meta["kind"] == KIND == "letter-reply"
    assert meta["from"] == "Grandad"
    assert meta["source"] == str(folder)
    assert meta["files"] == ["v001.png"]


def test_a_voice_reply_is_playable_in_showing_mode(
    journal: Journal, inbox: Path, state: Path
) -> None:
    write_ogg(reply_dir(inbox, "ada", "grandad") / "hello.ogg")
    entry = sweep(journal, inbox, state)[0].entry
    # `note.ogg` is the name kidnix_shell.voice looks for: it is what puts the
    # ear badge on the card and what plays when the child taps it in S7.
    assert (entry.directory / NOTE_NAME).is_file()
    assert has_note(entry.directory)


def test_a_voice_reply_gets_a_drawn_envelope(journal: Journal, inbox: Path, state: Path) -> None:
    write_ogg(reply_dir(inbox, "ada", "grandad") / "hello.ogg")
    drawer = Drawer()
    entry = sweep(journal, inbox, state, envelope=drawer)[0].entry
    assert [call[0] for call in drawer.calls] == [entry.directory / THUMB_NAME]
    assert (entry.directory / THUMB_NAME).is_file()


def test_a_picture_is_never_redrawn_as_an_envelope(
    journal: Journal, inbox: Path, state: Path
) -> None:
    write_png(reply_dir(inbox, "ada", "grandad") / "beach.png")
    drawer = Drawer()
    sweep(journal, inbox, state, envelope=drawer)
    assert drawer.calls == []


def test_the_words_are_kept_verbatim(journal: Journal, inbox: Path, state: Path) -> None:
    written = "i luv you ada. we saw a big dinosor at the musem!"
    write_words(reply_dir(inbox, "ada", "grandad") / "words.txt", written)
    entry = sweep(journal, inbox, state)[0].entry
    # Not corrected, not re-cased, not tidied -- a grown-up's spelling is left
    # alone on the way in for the same reason a child's is (05 section 3).
    assert (entry.directory / CAPTION_NAME).read_text(encoding="utf-8") == written


def test_the_words_are_drawn_on_the_card(journal: Journal, inbox: Path, state: Path) -> None:
    write_words(reply_dir(inbox, "ada", "grandad") / "words.txt", "hello ada")
    drawer = Drawer()
    sweep(journal, inbox, state, envelope=drawer)
    assert drawer.calls[0][1] == "hello ada"


def test_a_card_survives_a_machine_that_cannot_draw(
    journal: Journal, inbox: Path, state: Path
) -> None:
    write_ogg(reply_dir(inbox, "ada", "grandad") / "hello.ogg")
    entry = sweep(journal, inbox, state, envelope=Drawer(works=False))[0].entry
    # No thumbnail is a card that falls back to the Letters icon, not a failure.
    assert not (entry.directory / THUMB_NAME).exists()
    assert entry.title == "A letter from Grandad"


def test_the_entry_is_dated_when_it_arrived_not_when_it_was_sent(
    journal: Journal, inbox: Path, state: Path
) -> None:
    folder = reply_dir(inbox, "ada", "grandad")
    write_png(folder / "beach.png")
    (folder / "reply.json").write_text(
        json.dumps({"from": "Grandad", "kind": "image", "sent_at": "2026-01-02T09:00:00"}),
        encoding="utf-8",
    )
    entry = sweep(journal, inbox, state)[0].entry
    assert entry.created_at.date() == NOW.date()
    meta = json.loads((entry.directory / META_NAME).read_text(encoding="utf-8"))
    assert meta["sent_at"] == "2026-01-02T09:00:00"


def test_reply_json_names_the_sender_and_the_file(
    journal: Journal, inbox: Path, state: Path
) -> None:
    folder = reply_dir(inbox, "ada", "2026-08-23-01")
    write_png(folder / "one.png")
    write_words(folder / "notes.txt", "not the words")
    (folder / "reply.json").write_text(
        json.dumps({"from": "Auntie Jo", "kind": "image", "files": ["one.png"]}),
        encoding="utf-8",
    )
    kept = sweep(journal, inbox, state)
    assert kept[0].entry.title == "A letter from Auntie Jo"
    # `files` named one thing, so the stray text file is not this reply's words.
    assert not (kept[0].entry.directory / CAPTION_NAME).exists()


def test_a_broken_reply_json_is_ignored_and_the_letter_still_arrives(
    journal: Journal, inbox: Path, state: Path
) -> None:
    folder = reply_dir(inbox, "ada", "grandad")
    write_png(folder / "beach.png")
    (folder / "reply.json").write_text("{not json at all", encoding="utf-8")
    kept = sweep(journal, inbox, state)
    assert len(kept) == 1
    assert kept[0].entry.title == "A letter from Grandad"


def test_a_reply_json_that_is_not_an_object_is_ignored(
    journal: Journal, inbox: Path, state: Path
) -> None:
    folder = reply_dir(inbox, "ada", "grandad")
    write_png(folder / "beach.png")
    (folder / "reply.json").write_text("[1, 2, 3]", encoding="utf-8")
    assert len(sweep(journal, inbox, state)) == 1


def test_a_folder_with_nothing_but_a_broken_reply_json_imports_nothing(
    journal: Journal, inbox: Path, state: Path
) -> None:
    (reply_dir(inbox, "ada", "grandad") / "reply.json").write_text("{", encoding="utf-8")
    assert sweep(journal, inbox, state) == []
    assert journal.entries == []


def test_reply_json_cannot_name_a_file_outside_its_own_folder(
    journal: Journal, inbox: Path, state: Path, tmp_path: Path
) -> None:
    secret = write_png(tmp_path / "elsewhere" / "secret.png")
    folder = reply_dir(inbox, "ada", "grandad")
    write_png(folder / "beach.png")
    (folder / "reply.json").write_text(
        json.dumps({"files": ["../../elsewhere/secret.png", str(secret)]}), encoding="utf-8"
    )
    entry = sweep(journal, inbox, state)[0].entry
    assert entry.latest_path is not None
    assert entry.latest_path.read_bytes() == (folder / "beach.png").read_bytes()


# -- once and only once ------------------------------------------------------


def test_a_second_sweep_imports_nothing(journal: Journal, inbox: Path, state: Path) -> None:
    write_png(reply_dir(inbox, "ada", "grandad") / "beach.png")
    assert len(sweep(journal, inbox, state)) == 1
    assert sweep(journal, inbox, state, now=LATER) == []
    assert len(journal.entries) == 1


def test_the_journal_is_the_backstop_when_the_state_file_is_lost(
    journal: Journal, inbox: Path, state: Path
) -> None:
    write_png(reply_dir(inbox, "ada", "grandad") / "beach.png")
    sweep(journal, inbox, state)
    state.unlink()
    fresh = Journal(journal.root)
    fresh.load()
    assert sweep(fresh, inbox, state, now=LATER) == []
    assert len(fresh.entries) == 1


def test_the_state_file_records_the_path_mtime_and_size(
    journal: Journal, inbox: Path, state: Path
) -> None:
    folder = reply_dir(inbox, "ada", "grandad")
    write_png(folder / "beach.png")
    sweep(journal, inbox, state)
    data = json.loads(state.read_text(encoding="utf-8"))
    assert data["schema"] == 1
    recorded = data["imported"][str(folder)]
    assert set(recorded) == {"mtime", "size", "imported"}


def test_a_reply_that_gains_a_file_later_is_not_a_second_letter(
    journal: Journal, inbox: Path, state: Path
) -> None:
    folder = reply_dir(inbox, "ada", "grandad")
    write_png(folder / "beach.png")
    sweep(journal, inbox, state)
    write_ogg(folder / "hello.ogg")  # the same letter, with the voice added after
    assert sweep(journal, inbox, state, now=LATER) == []
    assert len(journal.entries) == 1


def test_nothing_in_the_inbox_is_ever_touched(journal: Journal, inbox: Path, state: Path) -> None:
    folder = reply_dir(inbox, "ada", "grandad")
    write_png(folder / "beach.png")
    write_words(folder / "words.txt", "hello ada")
    write_ogg(folder / "hello.ogg")
    before = snapshot(inbox)
    sweep(journal, inbox, state)
    sweep(journal, inbox, state, now=LATER)
    # 0750 parent:kid -- the child's session can read this folder and nothing
    # else, and the import is written entirely on our own side of the fence.
    assert snapshot(inbox) == before


def test_one_childs_letters_are_not_another_childs(
    journal: Journal, inbox: Path, state: Path
) -> None:
    write_png(reply_dir(inbox, "ada", "grandad") / "beach.png")
    write_png(reply_dir(inbox, "bram", "nanna") / "cake.png")
    kept = sweep(journal, inbox, state, profile="ada")
    assert [letter.reply.from_name for letter in kept] == ["Grandad"]
    assert len(journal.entries) == 1


def test_an_empty_inbox_keeps_nothing_and_writes_nothing(
    journal: Journal, inbox: Path, state: Path
) -> None:
    (inbox / "ada").mkdir()
    assert sweep(journal, inbox, state) == []
    assert journal.entries == []
    assert not state.exists()


def test_no_inbox_at_all_is_the_normal_developer_case(
    journal: Journal, tmp_path: Path, state: Path
) -> None:
    assert sweep(journal, tmp_path / "nowhere", state) == []
    assert not state.exists()


def test_the_newest_letter_is_first_in_my_things(
    journal: Journal, inbox: Path, state: Path
) -> None:
    older = write_png(reply_dir(inbox, "ada", "nanna") / "a.png", colour=(0, 255, 0))
    newer = write_png(reply_dir(inbox, "ada", "grandad") / "b.png", colour=(0, 0, 255))
    os.utime(older.parent, (1_000_000, 1_000_000))
    os.utime(newer.parent, (2_000_000, 2_000_000))
    sweep(journal, inbox, state)
    assert [entry.title for entry in journal.entries] == [
        "A letter from Grandad",
        "A letter from Nanna",
    ]


# -- the one gentle line -----------------------------------------------------


def test_the_line_names_the_sender(journal: Journal, inbox: Path, state: Path) -> None:
    write_png(reply_dir(inbox, "ada", "grandad") / "beach.png")
    kept = sweep(journal, inbox, state)
    assert announcement(kept) == "There's a letter for you from Grandad. It's in My Things."


def test_nothing_arrived_is_said_with_silence() -> None:
    assert announcement([]) == ""
    held = Announcement()
    assert held.offer([]) == ""
    assert held.pending is False
    assert held.take() == ""


def test_the_line_is_said_once_and_never_again(journal: Journal, inbox: Path, state: Path) -> None:
    write_png(reply_dir(inbox, "ada", "grandad") / "beach.png")
    held = Announcement()
    held.offer(sweep(journal, inbox, state))
    assert held.pending is True
    assert held.take() == "There's a letter for you from Grandad. It's in My Things."
    # D6: no badge, no pulse, no second telling. Home is entered many times in
    # a sitting and the child hears this on the first one only.
    assert held.take() == ""
    assert held.pending is False


def test_several_letters_are_still_one_line_and_no_count(
    journal: Journal, inbox: Path, state: Path
) -> None:
    older = write_png(reply_dir(inbox, "ada", "nanna") / "a.png", colour=(0, 255, 0))
    newer = write_png(reply_dir(inbox, "ada", "grandad") / "b.png", colour=(0, 0, 255))
    os.utime(older.parent, (1_000_000, 1_000_000))
    os.utime(newer.parent, (2_000_000, 2_000_000))
    line = announcement(sweep(journal, inbox, state))
    assert line == "There's a letter for you from Grandad. It's in My Things."
    assert "Nanna" not in line
    assert not re.search(r"\d|two|both", line, re.IGNORECASE)


def test_the_line_is_one_sentence_a_child_could_answer_with_nothing() -> None:
    # Not a demand, not a question, no "come and see": nothing in this product
    # summons a child back to it (SYNTHESIS D6).
    line = ANNOUNCEMENT
    assert "?" not in line
    assert "!" not in line
    for word in ("now", "quick", "come", "check"):
        assert word not in line.lower()


def test_the_announcement_can_be_dropped_without_being_said(
    journal: Journal, inbox: Path, state: Path
) -> None:
    write_png(reply_dir(inbox, "ada", "grandad") / "beach.png")
    held = Announcement()
    kept = sweep(journal, inbox, state)
    assert isinstance(kept[0], Imported)
    assert isinstance(kept[0].reply, Reply)
    held.offer(kept)
    # A sitting that never reached Home (a refusal at "Who's here?") drops the
    # line rather than saving it up for next time: it is not news any more.
    held.clear()
    assert held.pending is False


# -- the drawn card, for real ------------------------------------------------


def test_the_envelope_card_is_a_real_png(tmp_path: Path) -> None:
    pytest.importorskip("cairo")
    pytest.importorskip("gi")
    destination = tmp_path / "thumb.png"
    if not draw_envelope(destination, "hello ada", size=128):  # pragma: no cover
        pytest.skip("no cairo/pango on this machine")
    assert destination.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")


def test_the_envelope_card_is_drawn_with_no_words_too(tmp_path: Path) -> None:
    pytest.importorskip("cairo")
    pytest.importorskip("gi")
    destination = tmp_path / "thumb.png"
    if not draw_envelope(destination, "", size=128):  # pragma: no cover
        pytest.skip("no cairo/pango on this machine")
    assert destination.stat().st_size > 0


def test_a_card_that_cannot_be_written_is_not_an_exception(tmp_path: Path) -> None:
    # A directory where the file should be: every failure here is a missing
    # thumbnail, never a child's session ending.
    destination = tmp_path / "thumb.png"
    destination.mkdir()
    assert draw_envelope(destination, "hello") is False
