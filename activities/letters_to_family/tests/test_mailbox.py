"""The outbox and the inbox: where a letter goes, and what comes back.

Two ordinary directories and a contract, and the properties worth pinning are
the ones that protect a child from a machine problem: an unwritable outbox is
not an error the child hears, the inbox is never written to, and a folder full
of a grown-up's own files does not confuse either.
"""

from __future__ import annotations

import json
import os
import stat

import pytest

from letters_to_family.letter import (
    CAPTION_NAME,
    CARD_NAME,
    META_NAME,
    PICTURE_NAME,
    STATUS_WAITING,
    VOICE_NAME,
    CaptionSource,
    Letter,
)
from letters_to_family.mailbox import (
    INBOX_ROOT,
    OUTBOX_ROOT,
    inbox_dir,
    inbox_replies,
    outbox_dir,
    post,
    profile_dir,
)
from letters_to_family.recipients import Recipient

GRANDAD = Recipient(id="grandad", name="Grandad", relation="Grandpa")
INVENTED = "i sor a dinosor  at the parc"


@pytest.fixture
def made(tmp_path):
    """One finished letter and its rendered card, on disk."""
    picture = tmp_path / "picture.png"
    picture.write_bytes(b"\x89PNG\r\n\x1a\npicture")
    card = tmp_path / "letter.png"
    card.write_bytes(b"\x89PNG\r\n\x1a\ncard")
    letter = Letter(recipient=GRANDAD, picture=picture)
    letter.set_caption(INVENTED, CaptionSource.CHILD)
    return letter, card


# -- where things go ---------------------------------------------------------


def test_the_roots_are_machine_local_and_per_profile():
    assert OUTBOX_ROOT.as_posix() == "/var/lib/kidnix/outbox"
    assert INBOX_ROOT.as_posix() == "/var/lib/kidnix/inbox"


def test_an_unset_profile_gets_a_folder_of_its_own_not_the_root(tmp_path):
    """Two children's letters must never share one folder the first time
    somebody adds a profile."""
    assert profile_dir(tmp_path, "") == tmp_path / "_"
    assert profile_dir(tmp_path, "sam") == tmp_path / "sam"


def test_the_outbox_path_is_root_profile_timestamp_recipient(tmp_path, made):
    letter, _card = made
    target = outbox_dir(letter, "sam", tmp_path)
    assert target.parent == tmp_path / "sam"
    assert target.name.endswith("-grandad")


def test_the_inbox_path_is_root_profile(tmp_path):
    assert inbox_dir("sam", tmp_path) == tmp_path / "sam"


# -- posting -----------------------------------------------------------------


def test_posting_writes_the_card_the_picture_and_the_manifest(tmp_path, made):
    letter, card = made
    target = post(letter, card, "sam", tmp_path)
    assert target is not None
    assert (target / CARD_NAME).read_bytes() == card.read_bytes()
    assert (target / PICTURE_NAME).read_bytes() == letter.picture.read_bytes()
    assert (target / META_NAME).is_file()


def test_the_outbox_caption_is_the_child_s_own_spelling_byte_for_byte(tmp_path, made):
    letter, card = made
    target = post(letter, card, "sam", tmp_path)
    assert (target / CAPTION_NAME).read_text(encoding="utf-8") == INVENTED
    # And nothing added a newline the child did not type.
    assert not (target / CAPTION_NAME).read_text().endswith("\n")


def test_the_manifest_says_who_it_is_for_and_that_it_is_waiting(tmp_path, made):
    letter, card = made
    target = post(letter, card, "sam", tmp_path, entry_id="abc123")
    document = json.loads((target / META_NAME).read_text())
    assert document["recipient"]["name"] == "Grandad"
    assert document["status"] == STATUS_WAITING
    assert document["profile"] == "sam"
    assert document["entry_id"] == "abc123"
    assert document["schema"] == 1
    assert CARD_NAME in document["files"]


def test_a_voice_note_is_copied_in_beside_the_letter(tmp_path, made):
    letter, card = made
    voice = tmp_path / "note.ogg"
    voice.write_bytes(b"OggS")
    letter.voice = voice
    target = post(letter, card, "sam", tmp_path)
    assert (target / VOICE_NAME).read_bytes() == b"OggS"


def test_a_letter_with_no_words_writes_no_caption_file(tmp_path, made):
    letter, card = made
    letter.set_caption("", CaptionSource.CHILD)
    target = post(letter, card, "sam", tmp_path)
    assert not (target / CAPTION_NAME).exists()


def test_an_unwritable_outbox_is_none_and_never_raises(tmp_path, made):
    """A permissions problem on a directory a child has never heard of must not
    become "your letter did not work". The Journal copy is already safe."""
    letter, card = made
    locked = tmp_path / "locked"
    locked.mkdir()
    locked.chmod(stat.S_IREAD | stat.S_IEXEC)
    try:
        assert post(letter, card, "sam", locked) is None
    finally:
        locked.chmod(0o755)


@pytest.mark.skipif(os.geteuid() == 0, reason="root can write anywhere")
def test_the_default_root_is_not_written_to_in_a_test(tmp_path, made):
    """/var/lib/kidnix does not exist on a developer's machine, and the correct
    answer there is None with a log line, not a traceback."""
    letter, card = made
    assert post(letter, card, "nobody-at-all") is None or not OUTBOX_ROOT.exists()


# -- the inbox ---------------------------------------------------------------


def test_a_missing_inbox_is_no_letters_and_no_error(tmp_path):
    assert inbox_replies("sam", tmp_path / "nothing") == []


def test_an_empty_inbox_is_no_letters(tmp_path):
    (tmp_path / "sam").mkdir(parents=True)
    assert inbox_replies("sam", tmp_path) == []


def test_a_reply_folder_with_a_picture_a_voice_and_words(tmp_path):
    folder = tmp_path / "sam" / "2026-08-23-grandad"
    folder.mkdir(parents=True)
    (folder / "photo.jpg").write_bytes(b"jpeg")
    (folder / "voice.ogg").write_bytes(b"OggS")
    (folder / "words.txt").write_text("Thank you for the dinosaur!\n")

    reply = inbox_replies("sam", tmp_path)[0]
    assert reply.from_name == "Grandad"
    assert reply.picture.name == "photo.jpg"
    assert reply.voice.name == "voice.ogg"
    assert reply.words == "Thank you for the dinosaur!"
    assert reply.speak_text == "A letter from Grandad."


def test_a_from_txt_names_the_sender_when_the_folder_does_not(tmp_path):
    folder = tmp_path / "sam" / "reply-001"
    folder.mkdir(parents=True)
    (folder / "from.txt").write_text("Nanna Jean\nand Bill\n")
    (folder / "photo.png").write_bytes(b"png")
    assert inbox_replies("sam", tmp_path)[0].from_name == "Nanna Jean"


def test_a_folder_name_with_a_date_in_it_does_not_put_digits_in_a_child_s_ear(tmp_path):
    """01 #19: no digits where a child can see or hear them."""
    folder = tmp_path / "sam" / "2026-08-23-nanna"
    folder.mkdir(parents=True)
    (folder / "a.png").write_bytes(b"png")
    reply = inbox_replies("sam", tmp_path)[0]
    assert reply.from_name == "Nanna"
    assert not any(character.isdigit() for character in reply.speak_text)


def test_one_loose_file_in_the_inbox_is_a_reply_on_its_own(tmp_path):
    (tmp_path / "sam").mkdir(parents=True)
    (tmp_path / "sam" / "grandad.png").write_bytes(b"png")
    reply = inbox_replies("sam", tmp_path)[0]
    assert reply.from_name == "Grandad"
    assert reply.has_picture is True
    assert reply.has_voice is False


def test_a_loose_audio_file_is_a_voice_reply(tmp_path):
    (tmp_path / "sam").mkdir(parents=True)
    (tmp_path / "sam" / "nanna.ogg").write_bytes(b"OggS")
    reply = inbox_replies("sam", tmp_path)[0]
    assert reply.has_voice is True
    assert reply.has_picture is False


def test_a_file_that_is_not_a_picture_a_sound_or_words_is_not_a_reply(tmp_path):
    (tmp_path / "sam").mkdir(parents=True)
    (tmp_path / "sam" / "notes.pdf").write_bytes(b"%PDF")
    (tmp_path / "sam" / ".hidden.png").write_bytes(b"png")
    assert inbox_replies("sam", tmp_path) == []


def test_replies_come_back_newest_first(tmp_path):
    inbox = tmp_path / "sam"
    inbox.mkdir(parents=True)
    for index, name in enumerate(("old.png", "middle.png", "new.png")):
        path = inbox / name
        path.write_bytes(b"png")
        os.utime(path, (1_700_000_000 + index * 100, 1_700_000_000 + index * 100))
    assert [r.path.name for r in inbox_replies("sam", tmp_path)] == [
        "new.png",
        "middle.png",
        "old.png",
    ]


def test_the_shelf_is_bounded(tmp_path):
    inbox = tmp_path / "sam"
    inbox.mkdir(parents=True)
    for index in range(12):
        (inbox / f"reply{index}.png").write_bytes(b"png")
    assert len(inbox_replies("sam", tmp_path)) == 8
    assert len(inbox_replies("sam", tmp_path, limit=3)) == 3


def test_reading_the_inbox_changes_nothing_in_it(tmp_path):
    """Read-only, always: the inbox is a grown-up's folder, and marking a reply
    read or moving it is theirs to do."""
    inbox = tmp_path / "sam" / "grandad"
    inbox.mkdir(parents=True)
    (inbox / "photo.png").write_bytes(b"png")
    before = {p.name: p.stat().st_size for p in (tmp_path / "sam").rglob("*")}
    inbox_replies("sam", tmp_path)
    after = {p.name: p.stat().st_size for p in (tmp_path / "sam").rglob("*")}
    assert before == after


def test_an_empty_reply_folder_is_not_a_reply(tmp_path):
    (tmp_path / "sam" / "empty").mkdir(parents=True)
    assert inbox_replies("sam", tmp_path) == []
