"""Posting: Journal first, outbox second, and never the other way round.

The SDK's ``save_entry`` is injected, so the whole of what is kept -- the kind,
the files, the caption, the voice, the meta -- is asserted with no display, no
``kidnix_shell`` and no real Journal.
"""

from __future__ import annotations

import inspect
import json
from dataclasses import dataclass, field
from pathlib import Path

import pytest

from conftest import HAVE_SDK
from letters_to_family.assemble import post_letter
from letters_to_family.letter import (
    CAPTION_NAME,
    CARD_NAME,
    META_NAME,
    STATUS_UNPOSTED,
    STATUS_WAITING,
    CaptionSource,
    Letter,
    PictureSource,
)
from letters_to_family.recipients import Recipient

GRANDAD = Recipient(id="grandad", name="Grandad", relation="Grandpa")
INVENTED = "i sor a dinosor  at the parc"


@dataclass
class FakeEntry:
    id: str = "entry-1"


@dataclass
class FakeJournal:
    """As much of ``kidnix_activity.journal.save_entry`` as this module uses."""

    calls: list[dict] = field(default_factory=list)

    def __call__(
        self,
        kind: str,
        files: list[Path],
        caption: str | None = None,
        voice: Path | None = None,
        meta: dict | None = None,
        *,
        activity_name: str = "",
    ) -> FakeEntry:
        """**No ``**kwargs``, on purpose.**

        A double that swallowed anything would be wider than every real callee,
        and a protocol nothing can fail is not a protocol. This one has exactly
        the parameters :class:`letters_to_family.assemble.SaveEntry` declares,
        so a keyword `post_letter` starts passing that the SDK does not accept
        breaks these tests first rather than breaking **Post it** on a machine.
        """
        self.calls.append(
            {
                "kind": kind,
                "files": list(files),
                "caption": caption,
                "voice": voice,
                "meta": meta,
                "activity_name": activity_name,
            }
        )
        return FakeEntry()

    @property
    def only(self) -> dict:
        assert len(self.calls) == 1
        return self.calls[0]


def a_letter(tmp_path, *, caption: str = INVENTED, voice: bool = False) -> Letter:
    picture = tmp_path / "picture.png"
    picture.write_bytes(b"\x89PNG\r\n\x1a\npicture")
    letter = Letter(
        recipient=GRANDAD, picture=picture, picture_source=PictureSource.DRAWING
    )
    if caption:
        letter.set_caption(caption, CaptionSource.CHILD)
    if voice:
        note = tmp_path / "note.ogg"
        note.write_bytes(b"OggS")
        letter.voice = note
    return letter


def test_the_fake_is_exactly_as_narrow_as_the_protocol():
    """The double may not be wider than what `post_letter` is allowed to call.

    This is the regression for the checkpoint-2 finding: `post_letter` passed
    `activity_name=` to a callee that had no such parameter, every headless test
    passed because the double took `**kwargs`, and the first press of Post it
    raised TypeError.
    """
    from letters_to_family.assemble import SaveEntry

    fake = set(inspect.signature(FakeJournal.__call__).parameters) - {"self"}
    protocol = set(inspect.signature(SaveEntry.__call__).parameters) - {"self"}
    assert fake == protocol
    assert not any(
        parameter.kind is inspect.Parameter.VAR_KEYWORD
        for parameter in inspect.signature(FakeJournal.__call__).parameters.values()
    )


@pytest.mark.skipif(not HAVE_SDK, reason="kidnix_activity is not importable here")
def test_the_sdk_s_own_writer_satisfies_the_protocol():
    from kidnix_activity.journal import save_entry as sdk_save_entry

    from letters_to_family.assemble import SaveEntry

    real = inspect.signature(sdk_save_entry).parameters
    for name in set(inspect.signature(SaveEntry.__call__).parameters) - {"self"}:
        assert name in real, name


@pytest.mark.skipif(not HAVE_SDK, reason="kidnix_activity is not importable here")
def test_the_application_wrapper_does_not_satisfy_it_and_is_never_passed():
    """`ActivityApplication.save_entry` pins `activity_name` to the window title
    and takes no such argument. It is the wrong callee here, and the activity
    passes its own thin wrapper round the SDK's writer instead."""
    from kidnix_activity.app import ActivityApplication

    assert "activity_name" not in inspect.signature(ActivityApplication.save_entry).parameters
    source = Path(
        __import__("letters_to_family.activity", fromlist=["x"]).__file__
    ).read_text(encoding="utf-8")
    assert "self.app.save_entry" not in source
    assert "self.save_entry," in source


def test_the_journal_entry_is_a_letter_not_a_picture(tmp_path):
    journal = FakeJournal()
    post_letter(a_letter(tmp_path), journal, tmp_path / "s", "sam", outbox_root=tmp_path / "out")
    assert journal.only["kind"] == "letter"


def test_the_card_is_kept_first_and_the_bare_drawing_behind_it(tmp_path):
    """Version order is what the shell thumbnails and what resume opens, so the
    card -- the letter, with the words on it -- is what the shelf shows."""
    journal = FakeJournal()
    letter = a_letter(tmp_path)
    post_letter(letter, journal, tmp_path / "s", "sam", outbox_root=tmp_path / "out")
    files = journal.only["files"]
    assert files[0].name == CARD_NAME
    assert files[1] == letter.picture


def test_the_caption_reaches_the_journal_exactly_as_it_was_typed(tmp_path):
    journal = FakeJournal()
    post_letter(a_letter(tmp_path), journal, tmp_path / "s", "sam", outbox_root=tmp_path / "out")
    assert journal.only["caption"] == INVENTED


def test_a_letter_with_no_words_has_no_caption_and_gets_a_name_instead(tmp_path):
    journal = FakeJournal()
    post_letter(
        a_letter(tmp_path, caption=""),
        journal,
        tmp_path / "s",
        "sam",
        outbox_root=tmp_path / "out",
    )
    assert journal.only["caption"] is None
    assert journal.only["activity_name"] == "A letter for Grandad"


def test_a_voice_note_is_handed_to_the_journal_and_a_missing_one_is_not(tmp_path):
    journal = FakeJournal()
    post_letter(
        a_letter(tmp_path, voice=True), journal, tmp_path / "s", "sam", outbox_root=tmp_path / "o"
    )
    assert journal.calls[0]["voice"].name == "note.ogg"

    journal = FakeJournal()
    post_letter(a_letter(tmp_path), journal, tmp_path / "s2", "sam", outbox_root=tmp_path / "o")
    assert journal.only["voice"] is None


def test_the_meta_says_waiting_for_a_grown_up(tmp_path):
    journal = FakeJournal()
    post_letter(a_letter(tmp_path), journal, tmp_path / "s", "sam", outbox_root=tmp_path / "out")
    assert journal.only["meta"]["status"] == STATUS_WAITING
    assert journal.only["meta"]["recipient"]["name"] == "Grandad"


def test_the_outbox_copy_lands_beside_the_journal_entry(tmp_path):
    journal = FakeJournal()
    result = post_letter(
        a_letter(tmp_path), journal, tmp_path / "s", "sam", outbox_root=tmp_path / "out"
    )
    assert result.in_outbox is True
    assert (result.outbox / CARD_NAME).is_file()
    assert (result.outbox / CAPTION_NAME).read_text() == INVENTED
    document = json.loads((result.outbox / META_NAME).read_text())
    assert document["entry_id"] == "entry-1"


def test_an_unwritable_outbox_still_keeps_the_letter_in_the_journal(tmp_path):
    """The order is the design: the child's copy is written first, so a broken
    /var/lib/kidnix costs a convenience for the grown-up and nothing else."""
    journal = FakeJournal()
    blocker = tmp_path / "out"
    blocker.write_text("this is a file, not a directory")
    result = post_letter(a_letter(tmp_path), journal, tmp_path / "s", "sam", outbox_root=blocker)
    assert result.in_outbox is False
    assert result.outbox is None
    assert len(journal.calls) == 1


def test_put_away_keeps_the_work_and_writes_nothing_to_the_outbox(tmp_path):
    """A grown-up must not find something in the folder they send things out of
    that nobody asked them to send."""
    journal = FakeJournal()
    result = post_letter(
        a_letter(tmp_path),
        journal,
        tmp_path / "s",
        "sam",
        status=STATUS_UNPOSTED,
        to_outbox=False,
        outbox_root=tmp_path / "out",
    )
    assert result.outbox is None
    assert not (tmp_path / "out").exists()
    assert journal.only["meta"]["status"] == STATUS_UNPOSTED


def test_a_card_that_will_not_render_does_not_stop_the_letter(tmp_path):
    """Cairo on a broken machine. The picture and the words are still kept."""

    def explode(*_args, **_kwargs):
        raise RuntimeError("no cairo today")

    journal = FakeJournal()
    letter = a_letter(tmp_path)
    result = post_letter(
        letter, journal, tmp_path / "s", "sam", outbox_root=tmp_path / "out", render=explode
    )
    assert journal.only["files"] == [letter.picture]
    assert result.entry_id == "entry-1"


def test_the_grown_up_s_words_are_rendered_in_the_grown_up_s_hand(tmp_path):
    seen: dict = {}

    def spy(path, picture, caption, name, *, child_hand=True):
        seen.update(caption=caption, name=name, child_hand=child_hand)
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).write_bytes(b"\x89PNG\r\n\x1a\n")

    letter = a_letter(tmp_path, caption="")
    letter.set_caption("We went to the park.", CaptionSource.GROWNUP)
    post_letter(
        letter, FakeJournal(), tmp_path / "s", "sam", outbox_root=tmp_path / "o", render=spy
    )
    assert seen["child_hand"] is False
    assert seen["caption"] == "We went to the park."
    assert seen["name"] == "Grandad"


def test_the_child_s_own_words_are_rendered_in_the_child_s_hand(tmp_path):
    seen: dict = {}

    def spy(path, picture, caption, name, *, child_hand=True):
        seen["child_hand"] = child_hand
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).write_bytes(b"\x89PNG\r\n\x1a\n")

    post_letter(
        a_letter(tmp_path), FakeJournal(), tmp_path / "s", "sam", outbox_root=tmp_path / "o",
        render=spy,
    )
    assert seen["child_hand"] is True
