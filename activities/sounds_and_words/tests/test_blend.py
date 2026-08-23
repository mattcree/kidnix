"""Blend it: dots, bars, and the point where software stops.

Letters and Sounds p.70's convention is the one on every UK classroom
whiteboard, so it is the one a child arrives already able to read. Two dots
under `sh` would tell them the opposite of what their teacher told them, which
is why the mark is a tested property of the model and not a styling detail.
"""

from __future__ import annotations

import pytest

from sounds_and_words.blend import BlendState, Mark, Stage, blend_word, mark_for
from sounds_and_words.ceiling import ceiling_for_grapheme


@pytest.fixture
def set3(corpus):
    return ceiling_for_grapheme(corpus, "k")


@pytest.fixture
def phase3(corpus):
    return ceiling_for_grapheme(corpus, "ng")


# --- the dot and the bar ----------------------------------------------------


def test_a_single_letter_gets_a_dot(corpus):
    assert mark_for(corpus.gpc_by_id["s"]) is Mark.DOT


def test_a_digraph_gets_a_bar(corpus):
    assert mark_for(corpus.gpc_by_id["sh"]) is Mark.BAR


def test_a_trigraph_gets_a_bar(corpus):
    assert mark_for(corpus.gpc_by_id["igh"]) is Mark.BAR


def test_a_doubled_consonant_gets_a_bar(corpus):
    """L&S p.70: a doubled letter "represents one phoneme". One mark."""
    assert mark_for(corpus.gpc_by_id["ll"]) is Mark.BAR


def test_a_split_digraph_gets_its_own_mark(corpus):
    split = next((g for g in corpus.gpcs if g.split), None)
    assert split is not None
    assert mark_for(split) is Mark.SPLIT


def test_every_taught_gpc_has_exactly_one_mark(corpus, phase3):
    for gpc in corpus.gpcs:
        if gpc.id in phase3.gpc_ids:
            assert mark_for(gpc) in (Mark.DOT, Mark.BAR, Mark.SPLIT)


# --- a word becomes a row of buttons ---------------------------------------


def test_cat_is_three_buttons_and_three_dots(corpus, set3):
    word = blend_word(corpus, "cat", set3)
    assert [b.grapheme for b in word.buttons] == ["c", "a", "t"]
    assert {b.mark for b in word.buttons} == {Mark.DOT}
    assert len(word) == 3


def test_a_word_with_a_digraph_has_fewer_buttons_than_letters(corpus, phase3):
    word = blend_word(corpus, "ship", phase3)
    assert [b.grapheme for b in word.buttons] == ["sh", "i", "p"]
    assert len(word) == 3
    assert len(word.text) == 4
    assert word.has_multigraph


def test_the_bar_is_under_the_digraph_and_only_there(corpus, phase3):
    word = blend_word(corpus, "ship", phase3)
    assert [b.mark for b in word.buttons] == [Mark.BAR, Mark.DOT, Mark.DOT]


def test_the_buttons_say_sounds_not_letter_names(corpus, phase3):
    word = blend_word(corpus, "ship", phase3)
    assert word.phonemes[0] == "shh"
    assert "aitch" not in " ".join(word.phonemes)


def test_the_buttons_are_numbered_in_reading_order(corpus, set3):
    word = blend_word(corpus, "cat", set3)
    assert [b.index for b in word.buttons] == [0, 1, 2]


def test_the_word_carries_its_source(corpus, set3):
    assert blend_word(corpus, "cat", set3).source


# --- the gate is still the gate --------------------------------------------


def test_a_word_above_the_ceiling_is_refused_not_drawn(corpus, set3):
    with pytest.raises(ValueError):
        blend_word(corpus, "ship", set3)


def test_a_tricky_word_above_the_ceiling_is_refused(corpus, set3):
    with pytest.raises(ValueError):
        blend_word(corpus, "the", set3)


def test_a_word_that_is_not_in_the_corpus_is_refused(corpus, set3):
    """Strict mode: guessing a segmentation is how an untaught GPC reaches a
    child (docs/design/sounds-and-words.md 3.2)."""
    with pytest.raises(ValueError):
        blend_word(corpus, "catnap", set3)


def test_the_refusal_says_why(corpus, set3):
    with pytest.raises(ValueError, match="sh"):
        blend_word(corpus, "ship", set3)


# --- pictures ---------------------------------------------------------------


def test_a_concrete_noun_gets_a_picture(corpus, set3):
    assert blend_word(corpus, "cat", set3).picture is not None


def test_a_word_that_is_not_a_thing_gets_none(corpus, set3):
    assert blend_word(corpus, "sat", set3).picture is None


def test_every_picture_word_that_the_ceiling_allows_is_actually_drawn(corpus, phase3):
    from sounds_and_words.pictures import PICTURE_WORDS

    drawn = [
        word
        for word in PICTURE_WORDS
        if word in corpus.word_by_text and blend_word(corpus, word, phase3).picture is not None
    ]
    assert len(drawn) >= 10, drawn


# --- the three stages, and none of them is a gate --------------------------


def test_a_word_starts_on_the_sounds(corpus, set3):
    state = BlendState(blend_word(corpus, "cat", set3))
    assert state.stage is Stage.SOUNDS
    assert not state.all_sounded


def test_pressing_every_button_is_noticed_but_never_required(corpus, set3):
    state = BlendState(blend_word(corpus, "cat", set3))
    for index in range(3):
        assert state.sound(index) is not None
    assert state.all_sounded


def test_pressing_the_same_button_eleven_times_is_fine(corpus, set3):
    state = BlendState(blend_word(corpus, "cat", set3))
    for _ in range(11):
        state.sound(0)
    assert state.sounded == {0}


def test_a_button_that_does_not_exist_is_not_an_error(corpus, set3):
    state = BlendState(blend_word(corpus, "cat", set3))
    assert state.sound(9) is None
    assert state.sound(-1) is None


def test_the_arrow_works_before_any_sound_button_has_been_pressed(corpus, set3):
    """Research 10 open question 2: forcing every button first would answer
    "do sound buttons entrench sound-by-sound reading?" the wrong way, by
    construction."""
    state = BlendState(blend_word(corpus, "cat", set3))
    assert state.push() is Stage.PUSHED
    assert not state.all_sounded


def test_after_the_push_it_is_a_persons_turn(corpus, set3):
    state = BlendState(blend_word(corpus, "cat", set3))
    state.push()
    assert state.hand_over() is Stage.SAY_IT
