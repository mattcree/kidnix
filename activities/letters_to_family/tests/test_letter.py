"""What a letter is -- and above all, that nothing touches the child's spelling.

    **No spelling correction** -- invented spelling *is* the Year 1 curriculum.
    -- docs/research/05-learning-science.md section 3

That is the rule this file exists to make impossible to break by accident. The
caption goes in and comes out byte for byte, through the model, through
``caption.txt``, through the outbox manifest and onto the rendered card.
"""

from __future__ import annotations

from datetime import datetime

from letters_to_family.letter import (
    STATUS_UNPOSTED,
    STATUS_WAITING,
    CaptionSource,
    Letter,
    PictureSource,
    Step,
    letter_title,
    outbox_name,
)
from letters_to_family.recipients import Recipient

GRANDAD = Recipient(id="grandad", name="Grandad", relation="Grandpa")

#: A real five-year-old's sentence: four inventions, a double space and no full
#: stop. Every one of those is something a tidying function would "fix".
INVENTED = "i sor a dinosor  at the parc wiv nanna"


def a_letter(tmp_path, **kwargs) -> Letter:
    picture = kwargs.pop("picture", None)
    if picture is None:
        picture = tmp_path / "picture.png"
        picture.write_bytes(b"\x89PNG\r\n\x1a\n")
    return Letter(recipient=GRANDAD, picture=picture, **kwargs)


# -- the spelling ------------------------------------------------------------


def test_the_caption_is_kept_exactly_as_it_was_typed(tmp_path):
    letter = a_letter(tmp_path)
    letter.set_caption(INVENTED, CaptionSource.CHILD)
    assert letter.caption == INVENTED


def test_nothing_strips_cases_or_collapses_the_child_s_words(tmp_path):
    """Not stripped, not title-cased, not de-double-spaced. All three are
    things a well-meaning `.strip().capitalize()` would do."""
    letter = a_letter(tmp_path)
    letter.set_caption("  i luv u  ", CaptionSource.CHILD)
    assert letter.caption == "  i luv u  "
    assert letter.caption != letter.caption.strip()
    assert not letter.caption.lstrip().startswith("I")


def test_a_caption_of_only_spaces_is_not_words_but_is_still_kept(tmp_path):
    letter = a_letter(tmp_path)
    letter.set_caption("   ", CaptionSource.CHILD)
    assert letter.has_words is False
    assert letter.caption == "   "


def test_setting_an_empty_caption_puts_the_source_back_to_none(tmp_path):
    letter = a_letter(tmp_path)
    letter.set_caption(INVENTED, CaptionSource.CHILD)
    letter.set_caption("", CaptionSource.CHILD)
    assert letter.caption_source is CaptionSource.NONE


def test_whose_words_they_are_is_recorded_and_is_not_a_judgement(tmp_path):
    letter = a_letter(tmp_path)
    letter.set_caption("We went to the park with Nanna.", CaptionSource.GROWNUP)
    assert letter.caption_source is CaptionSource.GROWNUP
    assert letter.meta()["caption_source"] == "grown-up"


# -- what makes a letter postable -------------------------------------------


def test_a_picture_is_the_only_thing_a_letter_needs(tmp_path):
    """05 section 3: a drawing, three words and a recording -- the drawing is
    the part that is always there. Requiring words would lock out a child who
    cannot yet write from the one activity that is *about* having an audience."""
    letter = a_letter(tmp_path)
    assert letter.has_words is False
    assert letter.has_voice is False
    assert letter.can_post() is True


def test_a_letter_with_no_picture_cannot_be_posted(tmp_path):
    letter = Letter(recipient=GRANDAD)
    letter.set_caption(INVENTED, CaptionSource.CHILD)
    assert letter.can_post() is False


def test_a_picture_path_that_is_not_on_disk_is_not_a_picture(tmp_path):
    letter = Letter(recipient=GRANDAD, picture=tmp_path / "gone.png")
    assert letter.has_picture is False
    assert letter.can_post() is False


def test_a_voice_note_counts_only_when_the_file_is_really_there(tmp_path):
    letter = a_letter(tmp_path, voice=tmp_path / "note.ogg")
    assert letter.has_voice is False
    (tmp_path / "note.ogg").write_bytes(b"OggS")
    assert letter.has_voice is True


# -- what it says about itself ----------------------------------------------


def test_the_meta_names_the_recipient_and_says_it_is_waiting(tmp_path):
    letter = a_letter(tmp_path, picture_source=PictureSource.JOURNAL)
    meta = letter.meta()
    assert meta["recipient"] == {"id": "grandad", "name": "Grandad", "relation": "Grandpa"}
    assert meta["status"] == STATUS_WAITING
    assert meta["picture_source"] == "journal"


def test_the_status_never_says_sent(tmp_path):
    """SYNTHESIS H1. A program with no network that reported "sent" would be
    lying, and the person it would be lying to is five."""
    for status in (STATUS_WAITING, STATUS_UNPOSTED):
        assert "sent" not in status.split() or "send" in status
    assert "waiting" in STATUS_WAITING
    assert STATUS_WAITING != STATUS_UNPOSTED


def test_the_unposted_status_is_available_for_put_away(tmp_path):
    letter = a_letter(tmp_path)
    assert letter.meta(STATUS_UNPOSTED)["status"] == STATUS_UNPOSTED


def test_the_meta_has_no_score_no_count_and_no_duration(tmp_path):
    """E1/F4: nothing in the child's record is a measurement of the child."""
    meta = a_letter(tmp_path).meta()
    for banned in ("score", "stars", "level", "streak", "attempts", "seconds", "words"):
        assert banned not in meta


def test_the_title_names_who_it_is_for_when_there_are_no_words():
    assert letter_title(GRANDAD) == "A letter for Grandad"
    assert letter_title(None) == "A letter for someone"


def test_the_outbox_directory_is_a_timestamp_then_the_recipient():
    when = datetime(2026, 8, 23, 15, 32, 0)
    assert outbox_name(GRANDAD, when) == "20260823-153200-grandad"


def test_the_outbox_directory_name_survives_an_awkward_name():
    when = datetime(2026, 8, 23, 15, 32, 0)
    who = Recipient(id="", name="Nanna Jean & Bill")
    assert outbox_name(who, when) == "20260823-153200-nanna-jean-bill"


def test_the_letter_carries_its_own_outbox_name(tmp_path):
    letter = a_letter(tmp_path, created=datetime(2026, 1, 2, 3, 4, 5))
    assert letter.outbox_name() == "20260102-030405-grandad"


def test_the_flow_is_short_and_forward_only():
    assert [step.value for step in Step] == [
        "who",
        "picture",
        "words",
        "posted",
        "shelf",
        "nobody",
    ]
