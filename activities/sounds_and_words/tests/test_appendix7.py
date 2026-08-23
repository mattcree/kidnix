"""The acceptance test: the DfE Reading Framework's own four exemplar books.

Research 10, section 4.2: *"If kidnix's generator produces the latter for that
phase, it is broken."* Books 1 and 2 must be rejected at the stated ceiling;
Books 3 and 4 must be accepted. Nothing else in this repository is allowed to
make these four assertions fail.
"""

from __future__ import annotations

import pytest

from sounds_and_words.ceiling import Reason, check_lines, check_word


def books(appendix7):
    return {b["number"]: b for b in appendix7["book"]}


# -------------------------------------------------------------- the four books
@pytest.mark.parametrize("number", [1, 2])
def test_books_1_and_2_are_rejected(corpus, appendix7, appendix7_ceiling, number):
    book = books(appendix7)[number]
    verdict = check_lines(corpus, book["lines"], appendix7_ceiling)
    assert not verdict.allowed, f"Book {number} ({book['title']!r}) must be rejected"
    assert verdict.blocked


@pytest.mark.parametrize("number", [3, 4])
def test_books_3_and_4_are_accepted(corpus, appendix7, appendix7_ceiling, number):
    book = books(appendix7)[number]
    verdict = check_lines(corpus, book["lines"], appendix7_ceiling)
    assert verdict.allowed, (
        f"Book {number} ({book['title']!r}) must be accepted; blocked: {verdict.report()}"
    )


def test_every_book_declares_its_expectation(appendix7):
    for book in appendix7["book"]:
        assert book["expected"] in {"accept", "reject"}


def test_the_fixture_is_marked_verbatim(appendix7):
    assert appendix7["fixture"]["verbatim"] is True
    assert appendix7["fixture"]["source"] == "reading_framework_2023"
    assert appendix7["fixture"]["pages"] == "144-145"


# ------------------------------------------ every named undecodable word blocks
@pytest.mark.parametrize("number", [1, 2])
def test_named_undecodable_words_all_block(corpus, appendix7, appendix7_ceiling, number):
    book = books(appendix7)[number]
    for word in book["must_block"]:
        v = check_word(corpus, word, appendix7_ceiling)
        assert not v.allowed, f"{word!r} should not be decodable at the Appendix 7 ceiling"


def test_every_word_of_books_3_and_4_is_individually_allowed(
    corpus, appendix7, appendix7_ceiling
):
    from sounds_and_words.ceiling import tokenise

    for number in (3, 4):
        book = books(appendix7)[number]
        for line in book["lines"]:
            for token in tokenise(line):
                v = check_word(corpus, token, appendix7_ceiling)
                assert v.allowed, f"Book {number}: {v.explanation}"


# ------------------------------------------------- the pair the whole test rests on
def test_worn_is_decodable_but_worms_is_not(corpus, appendix7_ceiling):
    """The distinction the framework's example turns on.

    Both segment into the same taught graphemes. Only the phoneme 'or' stands
    for separates them, which is why coverage-only filtering is not enough.
    """
    assert check_word(corpus, "worn", appendix7_ceiling).allowed
    worms = check_word(corpus, "worms", appendix7_ceiling)
    assert not worms.allowed
    assert worms.reason is Reason.UNTAUGHT_GPC
    assert "or_er" in worms.blocked_by


def test_puddle_looks_segmentable_but_is_refused(corpus, appendix7_ceiling):
    """'puddle' is p+u+d+d+l+e under longest match -- all taught graphemes.

    It is /p-u-dd-le/, and 'le' is a syllable Letters and Sounds never teaches
    as a GPC. The lexicon is what stops it, which is the reason it exists.
    """
    from sounds_and_words.ceiling import segment

    assert segment("puddle", appendix7_ceiling.graphemes) is not None
    v = check_word(corpus, "puddle", appendix7_ceiling)
    assert not v.allowed
    assert v.reason is Reason.UNTAUGHT_GPC
    assert "le" in v.blocked_by


def test_their_segments_cleanly_and_is_still_refused(corpus, appendix7_ceiling):
    """'their' is th + e + i + r under longest match -- all taught graphemes.

    It is refused as a tricky word above the ceiling, which is the other of the
    two mechanisms. Either way it never reaches the child.
    """
    from sounds_and_words.ceiling import segment

    assert segment("their", appendix7_ceiling.graphemes) is not None
    v = check_word(corpus, "their", appendix7_ceiling)
    assert not v.allowed
    assert v.reason is Reason.TRICKY_NOT_TAUGHT
    assert corpus.tricky_by_text["their"].graphemes == ("th_voiced", "ei", "r")


def test_exception_words_are_the_only_tricky_words_allowed(appendix7, appendix7_ceiling):
    assert appendix7_ceiling.tricky_words == set(appendix7["fixture"]["exception_words"])


def test_he_is_refused_because_it_is_not_one_of_the_three(corpus, appendix7_ceiling):
    v = check_word(corpus, "he", appendix7_ceiling)
    assert not v.allowed
    assert v.reason is Reason.TRICKY_NOT_TAUGHT


def test_we_is_allowed_because_it_is_one_of_the_three(corpus, appendix7_ceiling):
    v = check_word(corpus, "we", appendix7_ceiling)
    assert v.allowed
    assert v.reason is Reason.OK_TRICKY


def test_off_needs_the_doubled_consonant_the_framework_did_not_name(corpus, appendix7):
    """Book 3 contains 'off'. The framework's grapheme list does not contain 'ff'.

    The fixture adds it and says so; this test pins that the addition is load-
    bearing rather than decorative.
    """
    from sounds_and_words.ceiling import custom_ceiling

    f = appendix7["fixture"]
    without_doublets = custom_ceiling(
        corpus,
        set(f["alphabet_gpcs"]) | set(f["named_gpcs"]) | set(f["footnote_variant_gpcs"]),
        label="Appendix 7 without the doubled consonants",
        tricky_words=set(f["exception_words"]),
    )
    assert not check_word(corpus, "off", without_doublets).allowed
