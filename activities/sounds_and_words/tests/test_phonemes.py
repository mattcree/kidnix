"""Saying a sound, and the fifteen drawings.

The schwa is the failure this whole module exists to avoid: /s/ said as "suh"
gives a child "suh-a-tuh", which is not "sat" and which a teacher then has to
un-teach. These tests hold the labels to the corpus's own blacklist and hold
the audio provenance to being *stated* rather than assumed.
"""

from __future__ import annotations

import xml.etree.ElementTree as ElementTree

import pytest

from sounds_and_words.ceiling import ceiling_for_grapheme
from sounds_and_words.phonemes import (
    CLIP_DIR,
    CLIP_LEDGER,
    GCOMPRIS_BUNDLE_DIR,
    Source,
    missing_recordings,
    phoneme_for,
    say_label,
    yes_line,
)
from sounds_and_words.pictures import PICTURE_DIR, PICTURE_WORDS, have_pictures, picture_for

#: The classic phonics error, in every spelling somebody might reach for.
SCHWA = ("suh", "tuh", "puh", "muh", "nuh", "duh", "guh", "buh", "kuh", "luh", "ruh")


# --- what to say ------------------------------------------------------------


def test_a_label_is_the_sound_not_the_letters_name(corpus):
    assert say_label(corpus.gpc_by_id["s"]) == "sss"


def test_the_aside_for_a_grown_up_is_not_said_to_a_child(corpus):
    """"oo (long, as in moon)" is written so an adult reading the corpus can
    tell two GPCs apart. Saying it would be saying a sentence."""
    assert say_label(corpus.gpc_by_id["oo_long"]) == "oo"
    assert say_label(corpus.gpc_by_id["th"]) == "th"


def test_two_gpcs_with_one_spelling_still_have_their_own_sound(corpus):
    assert say_label(corpus.gpc_by_id["s"]) != say_label(corpus.gpc_by_id["s_z"])


def test_no_label_is_ever_a_schwa(corpus):
    for gpc in corpus.gpcs:
        assert say_label(gpc).lower() not in SCHWA, gpc.id


def test_every_gpc_has_something_to_say(corpus):
    for gpc in corpus.gpcs:
        assert say_label(gpc).strip()


def test_the_yes_line_names_the_sound_and_not_the_child(corpus):
    """Informational, never controlling (research 05 2f). "yes, sss", not
    "well done"."""
    line = yes_line(corpus.gpc_by_id["s"])
    assert line == "yes, sss"
    assert "well done" not in line
    assert "good" not in line


# --- where the sound comes from --------------------------------------------


def test_a_gpc_with_no_clip_falls_back_to_the_label(corpus, tmp_path):
    sound = phoneme_for(corpus.gpc_by_id["s"], clip_dir=tmp_path)
    assert sound.source is Source.SPELLED
    assert sound.is_placeholder
    assert sound.clip is None
    assert sound.label == "sss"


def test_a_clip_on_disk_is_used_and_is_not_a_placeholder(corpus, tmp_path):
    (tmp_path / "s.ogg").write_bytes(b"OggS-not-really")
    sound = phoneme_for(corpus.gpc_by_id["s"], clip_dir=tmp_path)
    assert sound.source is Source.RECORDED
    assert not sound.is_placeholder
    assert sound.clip is not None


def test_clips_are_keyed_on_the_gpc_id_not_the_grapheme(corpus, tmp_path):
    """`oo` long and `oo` short are different sounds and must be different
    files -- which is the whole reason every GPC has an id."""
    (tmp_path / "oo_long.ogg").write_bytes(b"OggS")
    assert phoneme_for(corpus.gpc_by_id["oo_long"], clip_dir=tmp_path).source is Source.RECORDED
    assert phoneme_for(corpus.gpc_by_id["oo_short"], clip_dir=tmp_path).source is Source.SPELLED


def test_the_missing_list_is_honest_about_today(corpus, tmp_path):
    ceiling = ceiling_for_grapheme(corpus, "k")
    taught = [g for g in corpus.gpcs if g.id in ceiling.gpc_ids]
    assert missing_recordings(taught, clip_dir=tmp_path) == [g.id for g in taught]


def test_the_missing_list_shrinks_as_clips_land(corpus, tmp_path):
    (tmp_path / "s.ogg").write_bytes(b"OggS")
    taught = [corpus.gpc_by_id["s"], corpus.gpc_by_id["a"]]
    assert missing_recordings(taught, clip_dir=tmp_path) == ["a"]


def test_the_missing_list_is_in_teaching_order(corpus, tmp_path):
    taught = [corpus.gpc_by_id["t"], corpus.gpc_by_id["s"], corpus.gpc_by_id["a"]]
    assert missing_recordings(taught, clip_dir=tmp_path) == ["s", "a", "t"]


def test_the_two_paths_that_matter_are_named_in_the_code():
    """Both are follow-ups somebody has to find. A design note is not enough."""
    # The directory build_files/64-first-party-activities.sh creates, and the
    # one tests/image/test_first_party.sh asserts against the built image. It
    # is per language because a phoneme is.
    assert str(CLIP_DIR) == "/usr/share/kidnix/phonemes/en_GB"
    assert CLIP_LEDGER == CLIP_DIR / "phonemes.toml"
    assert "gcompris" in str(GCOMPRIS_BUNDLE_DIR)


# --- the pictures -----------------------------------------------------------


def test_all_fifteen_drawings_are_installed():
    assert have_pictures() == list(PICTURE_WORDS)


@pytest.mark.parametrize("word", PICTURE_WORDS)
def test_every_drawing_is_valid_svg(word):
    root = ElementTree.parse(PICTURE_DIR / f"{word}.svg").getroot()
    assert root.tag.endswith("svg")


@pytest.mark.parametrize("word", PICTURE_WORDS)
def test_every_drawing_says_what_it_is(word):
    """SYNTHESIS B4: a picture that carries meaning carries a name with it."""
    text = (PICTURE_DIR / f"{word}.svg").read_text(encoding="utf-8")
    assert "aria-label" in text
    assert "<title>" in text


@pytest.mark.parametrize("word", PICTURE_WORDS)
def test_no_drawing_contains_a_letter(word):
    """A picture beside a word must not spell the word: the child is reading
    the word, not matching it."""
    text = (PICTURE_DIR / f"{word}.svg").read_text(encoding="utf-8")
    assert "<text" not in text


def test_every_picture_word_has_a_segmentation_on_record(corpus):
    """Strict mode rejects a word kidnix cannot prove is decodable, so a
    drawing for a word with no segmentation is a drawing that can never
    appear. `fox` is the one that is in the hand-written lexicon rather than
    in the L&S banks -- the banks are word lists, not a dictionary of things a
    five-year-old can name."""
    segmentations = corpus.segmentations
    for word in PICTURE_WORDS:
        assert word in segmentations, word


def test_almost_every_picture_word_comes_from_the_licensed_banks(corpus):
    from_banks = [word for word in PICTURE_WORDS if word in corpus.word_by_text]
    assert len(from_banks) >= len(PICTURE_WORDS) - 1


def test_a_word_that_is_not_a_thing_has_no_picture():
    assert picture_for("sat") is None
    assert picture_for("the") is None
    assert picture_for("") is None


def test_a_named_picture_that_is_missing_from_disk_is_not_offered(tmp_path):
    assert picture_for("cat", directory=tmp_path) is None
