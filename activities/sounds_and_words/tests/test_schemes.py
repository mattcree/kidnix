"""Co-existing with school: turning "which programme?" into a ceiling.

Research 10, section 4.5. The rule under test throughout: **under-permitting is
harmless; over-permitting undermines the school.**
"""

from __future__ import annotations

import pytest

from sounds_and_words.ceiling import allowed_words, ceiling_for_grapheme, check_word
from sounds_and_words.schemes import (
    DEFAULT_SCHEME,
    Scheme,
    load_schemes,
    resolve_ceiling,
    scheme_ceiling,
)


@pytest.fixture(scope="module")
def schemes():
    return load_schemes()


def test_letters_and_sounds_is_the_one_we_ship(schemes):
    ls = schemes[DEFAULT_SCHEME]
    assert ls.status == "shipped"
    assert ls.has_own_order
    assert len(ls.order) == 114


def test_the_shipped_order_matches_the_corpus(corpus, schemes):
    ls = schemes[DEFAULT_SCHEME]
    assert list(ls.order) == [g.id for g in corpus.gpcs]


def test_the_other_schemes_are_stubs(schemes):
    others = {k: v for k, v in schemes.items() if k != DEFAULT_SCHEME}
    assert len(others) >= 4
    for s in others.values():
        assert s.status == "stub"
        assert not s.has_own_order
        assert s.note, f"{s.id} must explain itself to a parent"


def test_every_stub_note_promises_never_to_go_ahead(schemes):
    for s in schemes.values():
        if s.status == "stub":
            assert "never go ahead of them" in s.note


def test_resolve_for_letters_and_sounds_is_the_plain_ceiling(corpus):
    got = resolve_ceiling(corpus, DEFAULT_SCHEME, "ck")
    assert got.gpc_ids == ceiling_for_grapheme(corpus, "ck").gpc_ids
    assert not got.conservative


def test_resolve_for_a_stub_falls_back_and_says_so(corpus):
    got = resolve_ceiling(corpus, "read_write_inc", "ck")
    assert got.gpc_ids == ceiling_for_grapheme(corpus, "ck").gpc_ids
    assert got.conservative
    assert got.notes and "never go ahead" in got.notes[0]


def test_resolve_with_no_scheme_starts_at_the_very_beginning(corpus):
    got = resolve_ceiling(corpus, None, None)
    assert got.scheme == "unknown"
    assert got.conservative
    assert got.graphemes == {"s"}
    assert check_word(corpus, "sat", got).allowed is False
    assert got.notes


def test_i_dont_know_defaults_to_set_1(corpus):
    got = resolve_ceiling(corpus, "unknown", None)
    assert got.order == corpus.gpc_by_id["s"].order
    assert "ask the teacher" in got.notes[0].lower()


def test_i_dont_know_with_a_grapheme_still_honours_the_grapheme(corpus):
    got = resolve_ceiling(corpus, "unknown", "ck")
    assert got.gpc_ids == ceiling_for_grapheme(corpus, "ck").gpc_ids
    assert got.conservative


def test_an_unrecognised_scheme_is_an_error_not_a_guess(corpus):
    with pytest.raises(KeyError):
        resolve_ceiling(corpus, "phonics_r_us", "ck")


# ------------------------------------------------- the conservative intersection
@pytest.fixture
def divergent_scheme():
    """A scheme that teaches 'sh' very early and 'p' very late.

    Stands in for Read Write Inc. / Sounds-Write, whose orders diverge
    substantially from Letters and Sounds.
    """
    return Scheme(
        id="divergent",
        name="A Divergent Programme",
        status="shipped",
        source="synthetic, for tests only",
        order=("s", "a", "t", "sh", "i", "n", "m", "d", "p"),
    )


def test_a_scheme_with_its_own_order_uses_it(corpus, divergent_scheme):
    own = scheme_ceiling(corpus, divergent_scheme, "sh")
    assert own is not None
    assert own.gpc_ids == {"s", "a", "t", "sh"}


def test_the_intersection_drops_what_only_one_side_taught(corpus, divergent_scheme):
    table = {"divergent": divergent_scheme}
    got = resolve_ceiling(corpus, "divergent", "sh", schemes=table)
    # 'p' is a Letters and Sounds set 1 letter, but this school teaches it last,
    # so it is dropped: kidnix will not show a letter the school has not reached.
    assert "p" not in got.gpc_ids
    # everything else L&S taught before 'sh' and the school has not -> dropped.
    assert got.gpc_ids == {"s", "a", "t", "sh"}
    assert got.conservative


def test_the_intersection_never_permits_more_than_either_side(corpus, divergent_scheme):
    table = {"divergent": divergent_scheme}
    got = resolve_ceiling(corpus, "divergent", "sh", schemes=table)
    own = scheme_ceiling(corpus, divergent_scheme, "sh")
    ls = ceiling_for_grapheme(corpus, "sh")
    assert got.gpc_ids <= own.gpc_ids
    assert got.gpc_ids <= ls.gpc_ids


def test_the_intersection_costs_something_and_we_can_measure_it(corpus, divergent_scheme):
    """Research 10, open question 6: what does under-permitting cost?

    Not a research answer -- but the number is available, which is the first
    step to asking a child.
    """
    table = {"divergent": divergent_scheme}
    conservative = resolve_ceiling(corpus, "divergent", "sh", schemes=table)
    optimistic = ceiling_for_grapheme(corpus, "sh")
    lost = len(allowed_words(corpus, optimistic)) - len(allowed_words(corpus, conservative))
    assert lost > 0


def test_a_grapheme_the_scheme_has_not_taught_is_an_error(corpus, divergent_scheme):
    with pytest.raises(KeyError):
        scheme_ceiling(corpus, divergent_scheme, "igh")


def test_scheme_ceiling_returns_none_for_a_stub(corpus, schemes):
    assert scheme_ceiling(corpus, schemes["sounds_write"], "ck") is None
