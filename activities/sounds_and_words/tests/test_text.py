"""The prompt must not print the answer.

The checkpoint-2 audit's first defect against this activity
(``docs/design/cci-compliance-audit-2026-08-23-checkpoint-2.md`` section 3):
``activity.py`` drew *"Find the one that says k."* over four tiles, one of
which was ``k``. The task is to match a **sound** to a grapheme; a prompt that
prints the grapheme has answered it.

These are the tests for the rule rather than for the sentence -- a rewrite of
the copy, a translation, or a grown-up editing ``parent_text.toml`` all have to
get past them. The corresponding on-screen assertions are in
``tests/test_gtk_screens.py``; these ones are headless, which is where a
guarantee belongs.
"""

from __future__ import annotations

from sounds_and_words.text import (
    BLEND_IT,
    FIND_IT,
    SCREEN_PROMPTS,
    names_a_grapheme,
    tokens,
)

# --- the rule ---------------------------------------------------------------


def test_the_line_the_audit_found_is_caught():
    assert names_a_grapheme("Find the one that says k.", ["k"]) == "k"


def test_a_digraph_is_caught_the_same_way():
    assert names_a_grapheme("Find the one that says sh.", ["sh", "ch"]) == "sh"


def test_a_letter_inside_an_ordinary_word_is_not_naming_it():
    """Every English sentence contains most of the alphabet. A rule that
    banned that would ban speaking."""
    assert names_a_grapheme("Find the one that says…", ["s", "a", "t", "i", "n", "d"]) is None


def test_the_trailing_full_stop_does_not_hide_a_grapheme():
    assert names_a_grapheme("Find the one that says a", ["a"]) == "a"
    assert names_a_grapheme("Find the one that says a.", ["a"]) == "a"
    assert names_a_grapheme("Find the one that says 'a'!", ["a"]) == "a"


def test_case_does_not_hide_one_either():
    assert names_a_grapheme("Find the one that says K.", ["k"]) == "k"


def test_an_apostrophe_stays_inside_its_word():
    assert tokens("That's the lot for today.") == ["that's", "the", "lot", "for", "today"]


def test_an_empty_line_names_nothing():
    assert names_a_grapheme("", ["a"]) is None
    assert names_a_grapheme("Find it", []) is None


# --- the strings this activity actually ships -------------------------------


def test_the_find_it_prompt_names_no_grapheme_in_the_corpus(corpus):
    """Every GPC, not only the taught ones: the ceiling can move and the
    prompt cannot."""
    assert names_a_grapheme(FIND_IT, [gpc.grapheme for gpc in corpus.gpcs]) is None


def test_no_prompt_shown_beside_graphemes_names_one(corpus):
    graphemes = [gpc.grapheme for gpc in corpus.gpcs]
    for prompt in SCREEN_PROMPTS:
        assert names_a_grapheme(prompt, graphemes) is None, prompt


def test_the_blend_it_prompt_says_what_to_do_and_not_what_it_says(corpus):
    """"Say the sounds, then push them together." is fine: the word is on the
    screen because reading it *is* the task."""
    assert names_a_grapheme(BLEND_IT, [gpc.grapheme for gpc in corpus.gpcs]) is None
    assert "push them together" in BLEND_IT


def test_the_prompt_has_nowhere_to_put_a_grapheme():
    """The old line was an f-string with the grapheme in it. A msgid with no
    placeholder cannot be handed one by accident or by a translator."""
    assert "{" not in FIND_IT
    assert "%" not in FIND_IT


def test_the_prompt_ends_where_the_sound_begins():
    """The ellipsis is the whole design: the sentence stops, and the sound is
    a separate utterance."""
    assert FIND_IT.endswith("…")
