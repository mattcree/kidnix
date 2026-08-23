"""The card at the end: the words, and nothing that counts them.

Research 10 section 4.4 -- *to the child, nothing numeric, ever* -- is the rule
these tests exist to keep, and the way it gets broken is always the same: a
"3 words today" that somebody thought was encouragement.
"""

from __future__ import annotations

import json
from datetime import date

import pytest

from sounds_and_words.summary import (
    SummaryCard,
    caption_for,
    font_is_andika,
    layout,
    meta_for,
    render_card,
)

#: The words a five-year-old must never be shown, in any form, by this activity.
FORBIDDEN = (
    "score",
    "level",
    "star",
    "streak",
    "badge",
    "well done",
    "points",
    "percent",
    "%",
    "correct",
    "wrong",
)


# --- the caption ------------------------------------------------------------


def test_the_caption_lists_the_words_in_order():
    assert caption_for(["cat", "sat", "pin"]) == "Read today: cat, sat, pin"


def test_the_caption_is_lowercase_like_everything_else_child_facing():
    assert caption_for(["Cat", "SAT"]) == "Read today: cat, sat"


def test_the_caption_never_counts_anything():
    caption = caption_for(["cat", "sat", "pin"])
    assert not any(character.isdigit() for character in caption)


def test_a_session_with_no_words_still_gets_an_honest_caption():
    assert caption_for([]) == "Some sounds today"


def test_blank_words_are_dropped():
    assert caption_for(["cat", "", "  "]) == "Read today: cat"


@pytest.mark.parametrize("word", FORBIDDEN)
def test_the_caption_can_never_contain_a_reward_word(word):
    assert word not in caption_for(["cat", "sat"]).lower()


# --- the layout -------------------------------------------------------------


def test_words_are_laid_out_three_to_a_line():
    assert layout(["cat", "sat", "pin", "map"]) == (("cat", "sat", "pin"), ("map",))


def test_one_word_is_one_line():
    assert layout(["cat"]) == (("cat",),)


def test_no_words_is_no_lines():
    assert layout([]) == ()


def test_the_line_length_is_adjustable_but_never_zero():
    assert layout(["a", "b", "c"], per_line=0) == (("a",), ("b",), ("c",))


# --- the meta, which is for the grown-up ------------------------------------


def test_meta_carries_what_the_parent_pane_will_need():
    card = SummaryCard(("cat", "sat"), ("c", "a", "t"), date(2026, 8, 23), "up to 'k'")
    meta = meta_for(card)
    assert meta["words"] == ["cat", "sat"]
    assert meta["gpcs_practised"] == ["c", "a", "t"]
    assert meta["date"] == "2026-08-23"
    assert meta["ceiling"] == "up to 'k'"


def test_meta_is_json_serialisable_before_anything_is_copied():
    """save_entry checks this before it copies the PNG; a failure here would
    be a card the child lost."""
    card = SummaryCard(("cat",), ("c",), date(2026, 8, 23))
    assert json.loads(json.dumps(meta_for(card)))["words"] == ["cat"]


def test_meta_has_no_score_of_any_kind():
    meta = meta_for(SummaryCard(("cat", "sat"), ("c", "a"), date(2026, 8, 23)))
    assert set(meta) == {"gpcs_practised", "words", "date", "ceiling"}


def test_an_empty_card_knows_it_is_empty():
    assert SummaryCard().empty
    assert not SummaryCard(("cat",)).empty


# --- the drawing ------------------------------------------------------------

gi = pytest.importorskip("gi", reason="no PyGObject: the card cannot be drawn")


def test_a_card_is_written_and_is_a_real_png(tmp_path):
    card = SummaryCard(("cat", "sat", "pin"), ("c", "a", "t"), date(2026, 8, 23))
    path = render_card(card, tmp_path / "card.png")
    assert path.is_file()
    assert path.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"
    assert path.stat().st_size > 1000


def test_a_card_with_many_words_still_renders(tmp_path):
    words = tuple(f"w{index}" for index in range(9))
    path = render_card(SummaryCard(words, (), date(2026, 8, 23)), tmp_path / "many.png")
    assert path.is_file()


def test_an_empty_card_still_renders(tmp_path):
    """A session where nothing was blended is still a session that happened."""
    path = render_card(SummaryCard(), tmp_path / "empty.png")
    assert path.is_file()


def test_the_card_directory_is_created(tmp_path):
    path = render_card(SummaryCard(("cat",)), tmp_path / "deep" / "card.png")
    assert path.is_file()


def test_whether_andika_was_used_is_a_fact_we_can_state():
    """Not an assertion that it *is* installed -- a dev container has no fonts
    -- but the answer must be a boolean somebody can put in a log line."""
    assert isinstance(font_is_andika(), bool)
