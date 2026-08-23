"""The ceiling: the hard gate.

The one-line acceptance test for the whole activity lives here:
*a Reception child whose parent has said "they've done up to `ck`" can find a
grapheme, blend six words and read one four-sentence book, and never sees a
grapheme past `ck`.*
"""

from __future__ import annotations

import pytest

from sounds_and_words.ceiling import (
    Reason,
    allowed_gpcs,
    allowed_sentences,
    allowed_texts,
    allowed_words,
    ceiling_for_grapheme,
    ceiling_for_phase,
    ceiling_from_order,
    check_text,
    check_word,
    custom_ceiling,
    intersect,
    with_notes,
)


@pytest.fixture
def ck(corpus):
    return ceiling_for_grapheme(corpus, "ck")


@pytest.fixture
def end_of_phase_2(corpus):
    return ceiling_for_phase(corpus, 2)


@pytest.fixture
def end_of_phase_3(corpus):
    return ceiling_for_phase(corpus, 3)


# ------------------------------------------------------------------- building
def test_ceiling_for_grapheme_stops_at_that_grapheme(corpus, ck):
    assert "ck" in ck.graphemes
    assert "e" not in ck.graphemes
    assert ck.order == corpus.gpc_by_id["ck"].order


def test_ceiling_for_grapheme_records_what_the_parent_said(ck):
    assert ck.label == "up to 'ck'"
    assert ck.scheme == "letters_and_sounds"


def test_ceiling_for_phase_2_reaches_ss_and_no_further(corpus, end_of_phase_2):
    assert {"ss", "ll", "ff"} <= end_of_phase_2.graphemes
    assert "j" not in end_of_phase_2.graphemes
    assert end_of_phase_2.phase == 2


def test_ceiling_for_phase_3_reaches_er(corpus, end_of_phase_3):
    assert "er" in end_of_phase_3.graphemes
    assert "ay" not in end_of_phase_3.graphemes


def test_phase_4_ceiling_has_the_same_graphemes_as_phase_3(corpus, end_of_phase_3):
    p4 = ceiling_for_phase(corpus, 4)
    assert p4.graphemes == end_of_phase_3.graphemes
    assert p4.gpc_ids == end_of_phase_3.gpc_ids


def test_phase_4_ceiling_adds_tricky_words_but_no_graphemes(corpus, end_of_phase_3):
    p4 = ceiling_for_phase(corpus, 4)
    assert p4.tricky_words > end_of_phase_3.tricky_words
    assert {"said", "come", "little", "what"} <= p4.tricky_words


def test_a_zero_ceiling_permits_nothing(corpus):
    nothing = ceiling_from_order(corpus, 0)
    assert len(nothing) == 0
    assert nothing.tricky_words == frozenset()
    assert not check_word(corpus, "sat", nothing).allowed


def test_custom_ceiling_rejects_unknown_ids(corpus):
    with pytest.raises(KeyError):
        custom_ceiling(corpus, {"s", "not_a_gpc"})


def test_with_notes_appends(ck):
    assert with_notes(ck, "hello").notes == ("hello",)


# ------------------------------------------------------------ the word filter
def test_a_word_of_taught_graphemes_is_allowed(corpus, ck):
    v = check_word(corpus, "cat", ck)
    assert v.allowed
    assert v.reason is Reason.OK_DECODABLE
    assert v.graphemes == ("c", "a", "t")


def test_a_word_with_an_untaught_grapheme_is_refused(corpus, ck):
    v = check_word(corpus, "hat", ck)
    assert not v.allowed
    assert v.reason is Reason.UNTAUGHT_GPC
    assert v.blocked_by == ("h",)


def test_the_refusal_names_the_grapheme(corpus, ck):
    assert "not taught yet" in check_word(corpus, "hat", ck).explanation


def test_case_is_ignored(corpus, ck):
    assert check_word(corpus, "CAT", ck).allowed


def test_an_unknown_word_is_refused_in_strict_mode(corpus, ck):
    v = check_word(corpus, "zzzq", ck)
    assert not v.allowed
    assert v.reason is Reason.UNKNOWN_WORD


def test_strict_mode_refuses_a_word_it_could_have_guessed(corpus, end_of_phase_3):
    """'catnap' segments into taught graphemes but is not in the corpus.

    Refusing it is the point: guessing is how an untaught GPC reaches a child.
    """
    assert "catnap" not in corpus.segmentations
    assert not check_word(corpus, "catnap", end_of_phase_3).allowed
    assert check_word(corpus, "catnap", end_of_phase_3, strict=False).allowed


def test_non_strict_mode_still_refuses_what_will_not_segment(corpus, ck):
    v = check_word(corpus, "zqip", ck, strict=False)
    assert not v.allowed
    assert v.reason is Reason.NO_SEGMENTATION


# ------------------------------------------------------------- digraph safety
def test_a_digraph_is_one_grapheme_not_two(corpus):
    before = ceiling_for_grapheme(corpus, "k")
    assert not check_word(corpus, "kick", before).allowed
    after = ceiling_for_grapheme(corpus, "ck")
    assert check_word(corpus, "kick", after).allowed


def test_a_trigraph_is_one_grapheme(corpus):
    before = ceiling_for_grapheme(corpus, "ee")
    assert not check_word(corpus, "night", before).allowed
    after = ceiling_for_grapheme(corpus, "igh")
    assert check_word(corpus, "night", after).allowed


def test_a_doubled_consonant_is_one_grapheme(corpus):
    before = ceiling_for_grapheme(corpus, "l")
    assert not check_word(corpus, "bell", before).allowed
    after = ceiling_for_grapheme(corpus, "ll")
    assert check_word(corpus, "bell", after).allowed


def test_the_two_pronunciations_of_oo_are_separate_gpcs(corpus):
    long_only = ceiling_for_grapheme(corpus, "oo_long")
    assert check_word(corpus, "moon", long_only).allowed
    assert not check_word(corpus, "look", long_only).allowed
    both = ceiling_for_grapheme(corpus, "oo_short")
    assert check_word(corpus, "look", both).allowed


def test_a_split_digraph_word_needs_its_split_digraph(corpus, end_of_phase_3):
    assert not check_word(corpus, "make", end_of_phase_3).allowed
    p5 = ceiling_for_grapheme(corpus, "a-e")
    assert check_word(corpus, "make", p5).allowed


def test_both_pronunciations_of_th_are_taught_together(corpus):
    th = ceiling_for_grapheme(corpus, "th")
    assert check_word(corpus, "thin", th).allowed
    assert check_word(corpus, "that", th).allowed


# ---------------------------------------------------------------- tricky words
def test_tricky_words_arrive_at_the_point_ls_teaches_them(corpus):
    before = ceiling_for_grapheme(corpus, "k")
    assert "the" not in before.tricky_words
    after = ceiling_for_grapheme(corpus, "r")
    assert {"to", "the"} <= after.tricky_words
    assert "no" not in after.tricky_words


def test_no_go_i_arrive_at_the_end_of_set_5(corpus, end_of_phase_2):
    assert {"no", "go", "i", "to", "the"} <= end_of_phase_2.tricky_words
    assert len(end_of_phase_2.tricky_words) == 5


def test_phase_3_tricky_words_are_the_twelve_ls_names(corpus, end_of_phase_3):
    expected = {"he", "she", "we", "me", "be", "was", "my", "you", "her", "they", "all", "are"}
    assert expected <= end_of_phase_3.tricky_words


def test_a_tricky_word_above_the_ceiling_is_refused(corpus, ck):
    v = check_word(corpus, "the", ck)
    assert not v.allowed
    assert v.reason is Reason.TRICKY_NOT_TAUGHT


def test_a_permitted_tricky_word_is_allowed(corpus, end_of_phase_2):
    v = check_word(corpus, "the", end_of_phase_2)
    assert v.allowed
    assert v.reason is Reason.OK_TRICKY


def test_phase_5_tricky_words_never_leak_into_phase_3(corpus, end_of_phase_3):
    for w in ("people", "because", "thought", "their"):
        assert not check_word(corpus, w, end_of_phase_3).allowed


# --------------------------------------------------------------- text filter
def test_check_text_accepts_a_caption_it_should(corpus):
    c = ceiling_for_grapheme(corpus, "ss")
    assert check_text(corpus, "a cat in a hat", c).allowed


def test_check_text_reports_every_blocked_word(corpus, ck):
    v = check_text(corpus, "the night bus", ck)
    assert not v.allowed
    assert set(v.blocked_words) == {"the", "night", "bus"}


def test_check_text_report_is_readable(corpus, ck):
    assert check_text(corpus, "hat", ck).report().startswith("rejected:")
    assert check_text(corpus, "cat", ck).report().startswith("accepted:")


# ----------------------------------------------------- the whole-corpus filters
def test_allowed_words_never_leak_an_untaught_gpc(corpus):
    for grapheme in ("t", "d", "k", "r", "ss", "x", "qu", "ng", "oa", "oi", "er"):
        c = ceiling_for_grapheme(corpus, grapheme)
        for w in allowed_words(corpus, c):
            assert set(w.graphemes) <= c.gpc_ids, (grapheme, w.text)


def test_allowed_words_hides_proper_nouns_by_default(corpus, end_of_phase_2):
    plain = {w.text for w in allowed_words(corpus, end_of_phase_2)}
    with_names = {w.text for w in allowed_words(corpus, end_of_phase_2, include_proper_nouns=True)}
    assert "sam" in with_names
    assert "sam" not in plain


def test_allowed_words_can_target_one_gpc(corpus, end_of_phase_2):
    for w in allowed_words(corpus, end_of_phase_2, target_gpc="ck"):
        assert "ck" in w.graphemes


def test_allowed_words_grows_monotonically_with_the_ceiling(corpus):
    previous: set[str] = set()
    for order in range(1, corpus.max_order() + 1):
        c = ceiling_from_order(corpus, order)
        now = {w.text for w in allowed_words(corpus, c, include_proper_nouns=True)}
        assert previous <= now, order
        previous = now


def test_allowed_sentences_never_leak(corpus):
    for phase in (2, 3, 4, 5):
        c = ceiling_for_phase(corpus, phase)
        for s in allowed_sentences(corpus, c):
            assert check_text(corpus, s.text, c).allowed


def test_allowed_texts_never_leak(corpus):
    c = ceiling_for_phase(corpus, 3)
    for t in allowed_texts(corpus, c):
        for line in t.lines:
            assert check_text(corpus, line, c).allowed


def test_allowed_gpcs_matches_the_ceiling(corpus, end_of_phase_2):
    assert {g.id for g in allowed_gpcs(corpus, end_of_phase_2)} == end_of_phase_2.gpc_ids


# ------------------------------------------------------------------ intersect
def test_intersect_takes_the_smaller_of_everything(corpus):
    a = ceiling_for_grapheme(corpus, "ck")
    b = ceiling_for_phase(corpus, 3)
    both = intersect(a, b)
    assert both.gpc_ids == a.gpc_ids & b.gpc_ids
    assert both.order == min(a.order, b.order)
    assert both.conservative


def test_intersect_is_never_wider_than_either_side(corpus):
    a = ceiling_for_phase(corpus, 2)
    b = ceiling_for_grapheme(corpus, "ai")
    both = intersect(a, b)
    assert both.gpc_ids <= a.gpc_ids
    assert both.gpc_ids <= b.gpc_ids
    assert both.tricky_words <= a.tricky_words


# ------------------------------------------- the one-line v1 acceptance test
def test_a_child_at_ck_can_do_a_session_and_sees_nothing_past_ck(corpus, ck):
    """SUITE.md section 3 / research 10 section 7.1, in one test."""
    graphemes = allowed_gpcs(corpus, ck)
    words = allowed_words(corpus, ck)
    assert len(graphemes) >= 13, "there must be something to find"
    assert len(words) >= 6, "there must be six words to blend"
    for g in graphemes:
        assert g.order <= corpus.gpc_by_id["ck"].order
    for w in words:
        assert set(w.graphemes) <= ck.gpc_ids
    assert not check_word(corpus, "get", ck).allowed, "'e' is past ck"
    assert not check_word(corpus, "run", ck).allowed, "'u' and 'r' are past ck"


def test_a_child_at_ss_can_read_a_four_line_book(corpus):
    """The 'read one four-sentence book' half of the same acceptance test."""
    c = ceiling_for_phase(corpus, 2)
    captions = allowed_sentences(corpus, c, kind="caption")
    assert len(captions) >= 4
    for cap in captions[:4]:
        assert check_text(corpus, cap.text, c).allowed


def test_a_typographic_apostrophe_is_folded(corpus):
    """The source PDFs use the curly apostrophe; the corpus keys use the straight
    one. A word must not be refused over a punctuation mark."""
    from sounds_and_words.ceiling import tokenise

    c = ceiling_for_phase(corpus, 2)
    assert tokenise("Let\u2019s go") == ["let's", "go"]
    assert check_word(corpus, "let\u2019s", c).allowed
    assert check_word(corpus, "let's", c).allowed
