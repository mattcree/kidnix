"""Which three wrong tiles, and the two rules that are not negotiable.

"Find the one that says /d/" is nearly free against ``s``, ``m`` and ``ai``,
and is the discrimination a Reception child's teacher is spending the term on
against ``b``, ``p`` and ``q``. These tests pin the tiering that makes the
board the second thing rather than the first -- and, harder, that it can never
reach for a grapheme the school has not taught in order to do it.
"""

from __future__ import annotations

import random

import pytest

from sounds_and_words.ceiling import ceiling_for_grapheme
from sounds_and_words.distractors import (
    BOARD_TILES,
    CHOICE_CEILING,
    board_graphemes,
    choose_distractors,
    confusability,
    find_it_options,
)


@pytest.fixture
def set3(corpus):
    """Phase 2 set 3: s a t p i n m d g o c k. The shipped default."""
    return ceiling_for_grapheme(corpus, "k")


@pytest.fixture
def phase3(corpus):
    """Far enough in to have digraphs to confuse with each other."""
    return ceiling_for_grapheme(corpus, "ng")


def graphemes(gpcs):
    return [g.grapheme for g in gpcs]


# --- the rules that are not negotiable -------------------------------------


def test_a_distractor_is_never_an_untaught_grapheme(corpus, set3):
    for target in [g for g in corpus.gpcs if g.id in set3.gpc_ids]:
        for wrong in choose_distractors(corpus, set3, target):
            assert wrong.id in set3.gpc_ids, f"{wrong.grapheme} is above the ceiling"


def test_the_board_is_never_two_tiles_with_the_same_letter(corpus, phase3):
    """`oo` is in the corpus twice and `s` is too. Both on one board is an
    unanswerable question that looks, to a child, like being told they are
    wrong when they are right."""
    for target in [g for g in corpus.gpcs if g.id in phase3.gpc_ids]:
        board = board_graphemes(find_it_options(corpus, phase3, target))
        assert len(board) == len(set(board)), board


def test_the_target_is_always_on_the_board(corpus, phase3):
    for target in [g for g in corpus.gpcs if g.id in phase3.gpc_ids]:
        assert target.grapheme in board_graphemes(find_it_options(corpus, phase3, target))


def test_the_target_is_never_also_a_distractor(corpus, set3):
    for target in [g for g in corpus.gpcs if g.id in set3.gpc_ids]:
        assert target.grapheme not in graphemes(choose_distractors(corpus, set3, target))


# --- tier 1: the reversals --------------------------------------------------


def test_d_is_offered_against_p(corpus, set3):
    """d/p is a mirror, and both are taught by set 3. It goes first."""
    d = corpus.gpc_by_id["d"]
    assert graphemes(choose_distractors(corpus, set3, d))[0] == "p"


def test_p_is_offered_against_d(corpus, set3):
    p = corpus.gpc_by_id["p"]
    assert graphemes(choose_distractors(corpus, set3, p))[0] == "d"


def test_b_and_d_beat_everything_else(corpus):
    ceiling = ceiling_for_grapheme(corpus, "ck")
    b = corpus.gpc_by_id["b"]
    assert graphemes(choose_distractors(corpus, ceiling, b))[0] in {"d", "p"}


def test_q_is_offered_against_p(corpus):
    ceiling = ceiling_for_grapheme(corpus, "qu")
    p = corpus.gpc_by_id["p"]
    first = graphemes(choose_distractors(corpus, ceiling, p, count=3))
    assert {"d", "b"} & set(first)


# --- tier 2: visually similar ----------------------------------------------


def test_m_is_offered_against_n(corpus, set3):
    m = corpus.gpc_by_id["m"]
    assert graphemes(choose_distractors(corpus, set3, m))[0] == "n"


def test_n_is_offered_against_m(corpus, set3):
    n = corpus.gpc_by_id["n"]
    assert "m" in graphemes(choose_distractors(corpus, set3, n))[:2]


def test_c_and_o_are_a_pair(corpus, set3):
    c = corpus.gpc_by_id["c"]
    assert "o" in graphemes(choose_distractors(corpus, set3, c))[:2]


# --- tier 3: multigraphs that share a letter -------------------------------


def test_sh_is_offered_against_ch_and_th(corpus, phase3):
    sh = corpus.gpc_by_id["sh"]
    top = graphemes(choose_distractors(corpus, phase3, sh))
    assert {"ch", "th"} <= set(top[:3]), top


def test_a_digraph_gets_digraph_company_before_single_letters(corpus, phase3):
    ai = corpus.gpc_by_id["ai"]
    first = graphemes(choose_distractors(corpus, phase3, ai))[0]
    assert len(first) > 1 or first in {"a", "i"}


# --- the shape of the board -------------------------------------------------


def test_four_tiles_by_default(corpus, set3):
    assert len(find_it_options(corpus, set3, corpus.gpc_by_id["t"])) == 4


def test_a_tiny_ceiling_gives_a_smaller_board_and_never_borrows(corpus):
    """Three days into Phase 2 set 1 there are three tiles, not four."""
    ceiling = ceiling_for_grapheme(corpus, "t")
    board = find_it_options(corpus, ceiling, corpus.gpc_by_id["t"])
    assert board_graphemes(board) != []
    assert set(board_graphemes(board)) <= set("sat")
    assert len(board) <= 3


def test_the_very_first_sound_gets_a_board_of_one(corpus):
    ceiling = ceiling_for_grapheme(corpus, "s")
    board = find_it_options(corpus, ceiling, corpus.gpc_by_id["s"])
    assert board_graphemes(board) == ["s"]


def test_asking_for_no_distractors_gets_none(corpus, set3):
    assert choose_distractors(corpus, set3, corpus.gpc_by_id["t"], count=0) == []


# --- determinism ------------------------------------------------------------


def test_the_same_seed_gives_the_same_board(corpus, set3):
    target = corpus.gpc_by_id["t"]
    first = board_graphemes(find_it_options(corpus, set3, target, rng=random.Random(7)))
    second = board_graphemes(find_it_options(corpus, set3, target, rng=random.Random(7)))
    assert first == second


def test_the_answer_is_not_always_in_the_same_place(corpus, set3):
    """A correct answer that never moves is a position-memory task, and a
    five-year-old finds the pattern before an adult notices there is one."""
    target = corpus.gpc_by_id["t"]
    positions = {
        board_graphemes(find_it_options(corpus, set3, target, rng=random.Random(seed))).index("t")
        for seed in range(24)
    }
    assert len(positions) > 1


def test_confusability_is_a_sort_key_not_a_score(corpus):
    d, p, s = (corpus.gpc_by_id[i] for i in ("d", "p", "s"))
    assert confusability(d, p) < confusability(d, s)
    assert confusability(d, p)[0] == 0


# --- the five-choice ceiling (ADR-0013) -------------------------------------


def test_a_find_it_board_is_a_choice_set_and_stays_under_the_ceiling(corpus, phase3):
    """ADR-0013 draws the line the checkpoint-2 audit asked for: five is the
    bound on a choice the child has to *weigh*, not on a labelled grid whose
    items are the task itself. Four graphemes, one of which answers a sound
    they have just heard, is squarely a choice -- so the ceiling binds, and
    four sits inside it with a tile to spare."""
    for target in [g for g in corpus.gpcs if g.id in phase3.gpc_ids]:
        board = find_it_options(corpus, phase3, target, rng=random.Random(1))
        assert len(board) <= CHOICE_CEILING, (target.id, board_graphemes(board))


def test_the_default_board_is_four_tiles(corpus, set3):
    assert BOARD_TILES == 4
    assert len(find_it_options(corpus, set3, corpus.gpc_by_id["t"])) == BOARD_TILES


def test_asking_for_more_than_five_is_capped_rather_than_obeyed(corpus, phase3, caplog):
    """Refusing outright would turn a design mistake into a child staring at a
    screen that will not start. The cap is loud in the log instead."""
    with caplog.at_level("WARNING"):
        board = find_it_options(corpus, phase3, corpus.gpc_by_id["t"], count=9)
    assert len(board) == CHOICE_CEILING
    assert "ADR-0013" in caplog.text
