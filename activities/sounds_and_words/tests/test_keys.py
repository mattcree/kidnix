"""The keyboard: lowercase, no Shift, and a digraph that is two keys.

Research 10 section 6. "Press the key that makes /s/" is a Letters and Sounds
Phase 2 success criterion, not typing practice -- so the tests here are about
whether a five-year-old's key press means what they meant, and not one of them
is about speed.
"""

from __future__ import annotations

import pytest

from sounds_and_words.keys import KEYCAPS, BoardKeys, Press, key_hint, keys_for, printable

# --- what counts as a key ---------------------------------------------------


@pytest.mark.parametrize("key", list("abcxyz"))
def test_every_letter_is_a_keycap(key):
    assert printable(key) == key


def test_uppercase_is_folded_rather_than_refused():
    """Caps Lock is on, or the keycaps say S. Neither is the child being wrong."""
    assert printable("S") == "s"


@pytest.mark.parametrize("key", ["1", " ", "", "ab", "!", "\n", "é"])
def test_nothing_else_is_a_keycap(key):
    assert printable(key) == ""


def test_there_are_twenty_six_of_them():
    assert len(KEYCAPS) == 26
    assert KEYCAPS.lower() == KEYCAPS


# --- one grapheme to its keys ----------------------------------------------


def test_a_single_letter_is_one_key():
    assert keys_for("s") == ("s",)


def test_a_digraph_is_two_keys_in_order():
    assert keys_for("sh") == ("s", "h")


def test_a_trigraph_is_three():
    assert keys_for("igh") == ("i", "g", "h")


def test_a_split_digraph_has_no_key_sequence():
    """`a-e` is discontinuous with a word in the middle. That is a real limit
    of the keyboard route and one reason the tiles exist."""
    assert keys_for("a-e") == ()


def test_the_hint_is_for_a_grown_up_not_a_child():
    assert key_hint("sh") == "press s then h"
    assert key_hint("s") == "press s"


# --- one press --------------------------------------------------------------


def test_pressing_the_letter_chooses_it():
    board = BoardKeys(["s", "a", "t", "p"])
    result = board.press("s")
    assert result.press is Press.CHOSE
    assert result.chosen == "s"


def test_pressing_a_capital_chooses_the_same_thing():
    board = BoardKeys(["s", "a", "t", "p"])
    assert board.press("A").chosen == "a"


def test_a_key_that_is_not_on_the_board_is_not_a_wrong_answer():
    board = BoardKeys(["s", "a", "t", "p"])
    result = board.press("z")
    assert result.press is Press.UNKNOWN
    assert result.chosen is None


def test_a_modifier_or_an_arrow_is_simply_ignored():
    board = BoardKeys(["s", "a", "t", "p"])
    assert board.press("").press is Press.IGNORED
    assert board.press("\t").press is Press.IGNORED


# --- a digraph is two keys that become one tile -----------------------------


def test_the_first_letter_of_a_digraph_is_pending_not_wrong():
    """The whole point. Scoring `s` as a wrong answer on the way to `sh` is
    the failure research 10 section 6 warns about by name."""
    board = BoardKeys(["sh", "ch", "th", "ng"])
    first = board.press("s")
    assert first.press is Press.PENDING
    assert first.pending == "s"


def test_the_second_letter_completes_it():
    board = BoardKeys(["sh", "ch", "th", "ng"])
    board.press("s")
    assert board.press("h").chosen == "sh"


def test_a_trigraph_takes_three():
    board = BoardKeys(["igh", "ai", "ee", "oa"])
    assert board.press("i").press is Press.PENDING
    assert board.press("g").press is Press.PENDING
    assert board.press("h").chosen == "igh"


def test_a_digraph_that_goes_wrong_halfway_is_unknown_and_resets():
    board = BoardKeys(["sh", "ch", "th"])
    board.press("s")
    result = board.press("x")
    assert result.press is Press.UNKNOWN
    assert board.typed == ""


def test_the_wrong_digraph_is_still_a_choice():
    """Pressing c-h on a board that has `ch` chooses `ch`. Being wrong is
    allowed; being unheard is not."""
    board = BoardKeys(["sh", "ch", "th"])
    board.press("c")
    assert board.press("h").chosen == "ch"


def test_reset_forgets_a_half_typed_grapheme():
    board = BoardKeys(["sh", "ch"])
    board.press("s")
    board.reset()
    assert board.typed == ""


# --- the prefix problem, and why there is no timer --------------------------


def test_a_letter_that_is_also_the_start_of_a_digraph_is_held():
    board = BoardKeys(["a", "ai", "s", "t"])
    assert "a" in board.ambiguous
    result = board.press("a")
    assert result.press is Press.PENDING
    assert result.pending == "a"


def test_the_next_key_resolves_the_hold_upwards():
    board = BoardKeys(["a", "ai", "s", "t"])
    board.press("a")
    assert board.press("i").chosen == "ai"


def test_a_key_that_does_not_extend_commits_the_shorter_answer():
    """a then t on a board of {a, ai, t} chose `a`, not nothing."""
    board = BoardKeys(["a", "ai", "t"])
    board.press("a")
    result = board.press("t")
    assert result.chosen == "a"


def test_settling_commits_a_held_answer():
    board = BoardKeys(["a", "ai", "s"])
    board.press("a")
    assert board.settle().chosen == "a"


def test_settling_twice_does_not_choose_twice():
    board = BoardKeys(["a", "ai", "s"])
    board.press("a")
    board.settle()
    assert board.settle().press is Press.IGNORED


def test_settling_a_half_typed_digraph_chooses_nothing():
    board = BoardKeys(["sh", "ch"])
    board.press("s")
    assert board.settle().press is Press.IGNORED


def test_nothing_is_ambiguous_on_an_ordinary_board():
    assert BoardKeys(["s", "a", "t", "p"]).ambiguous == frozenset()


# --- construction -----------------------------------------------------------


def test_a_board_drops_graphemes_that_cannot_be_typed():
    board = BoardKeys(["a-e", "ai", "s"])
    assert board.graphemes == ("ai", "s")


def test_a_board_does_not_repeat_itself():
    assert BoardKeys(["s", "s", "a"]).graphemes == ("s", "a")
