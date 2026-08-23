"""The schedule: Leitner boxes, the two-day mastery rule, and one session plan.

Research 10, section 4.3. The thing these tests protect above all others: the
schedule can never widen the ceiling. Every session, at every ceiling, contains
only what the parent has already permitted.
"""

from __future__ import annotations

import random

import pytest

from sounds_and_words.ceiling import (
    ceiling_for_grapheme,
    ceiling_for_phase,
    check_word,
    tokenise,
)
from sounds_and_words.schedule import (
    BOX_INTERVALS,
    MASTERY_BOX,
    MASTERY_DISTINCT_DAYS,
    MASTERY_STREAK,
    GpcState,
    History,
    ItemKind,
    Role,
    compose_session,
    select_gpcs,
)


@pytest.fixture
def ck(corpus):
    return ceiling_for_grapheme(corpus, "ck")


@pytest.fixture
def phase3(corpus):
    return ceiling_for_phase(corpus, 3)


# ------------------------------------------------------------- Leitner boxes
def test_the_intervals_are_the_ones_in_the_research_note():
    assert BOX_INTERVALS == (0, 1, 2, 4, 8, 16)


def test_a_fresh_gpc_is_in_box_zero_and_due():
    s = GpcState("s")
    assert s.box == 0
    assert s.due_on(0)
    assert not s.seen


def test_a_correct_first_attempt_promotes():
    h = History()
    assert h.record("s", 0, correct=True).box == 1
    assert h.record("s", 1, correct=True).box == 2


def test_the_box_caps_at_five():
    h = History()
    for day in range(20):
        h.record("s", day, correct=True)
    assert h.state("s").box == len(BOX_INTERVALS) - 1


def test_an_error_demotes_to_box_one_never_to_zero():
    h = History()
    for day in range(4):
        h.record("s", day, correct=True)
    assert h.state("s").box == 4
    s = h.record("s", 5, correct=False)
    assert s.box == 1, "a demotion to zero re-teaches, and that is the school's job"
    assert s.streak == 0
    assert s.streak_days == ()


def test_an_error_keeps_the_history_of_correct_days():
    h = History()
    h.record("s", 0, correct=True)
    h.record("s", 1, correct=False)
    assert h.state("s").correct_days == (0,)
    assert h.state("s").attempts == 2


def test_due_follows_the_box_interval():
    h = History()
    h.record("s", 0, correct=True)      # box 1, interval 1 day
    assert not h.state("s").due_on(0)
    assert h.state("s").due_on(1)
    h.record("s", 1, correct=True)      # box 2, interval 2 days
    assert not h.state("s").due_on(2)
    assert h.state("s").due_on(3)


# ---------------------------------------------------- the two-day mastery rule
def test_three_correct_on_one_day_is_not_mastery():
    h = History()
    for _ in range(6):
        h.record("s", 0, correct=True)
    assert h.state("s").box >= MASTERY_BOX
    assert h.state("s").streak >= MASTERY_STREAK
    assert not h.state("s").mastered, "same-session repetition must not fake mastery"


def test_three_correct_across_two_days_is_mastery():
    h = History()
    for _ in range(3):
        h.record("s", 0, correct=True)
    h.record("s", 1, correct=True)
    assert h.state("s").mastered


def test_mastery_needs_the_box_as_well_as_the_streak():
    h = History()
    h.record("s", 0, correct=True)
    h.record("s", 1, correct=True)
    h.record("s", 2, correct=True)
    s = h.state("s")
    assert s.streak == MASTERY_STREAK
    assert len(set(s.streak_days)) >= MASTERY_DISTINCT_DAYS
    assert s.box == 3 < MASTERY_BOX
    assert not s.mastered


def test_an_error_un_masters():
    h = History()
    for day in range(5):
        h.record("s", day, correct=True)
    assert h.state("s").mastered
    h.record("s", 5, correct=False)
    assert not h.state("s").mastered


def test_mastered_ids_lists_only_mastered():
    h = History()
    for day in range(5):
        h.record("s", day, correct=True)
    h.record("a", 0, correct=True)
    assert h.mastered_ids() == ["s"]


# -------------------------------------------------- the parent-pane three states
def test_the_three_parent_states():
    h = History()
    assert h.state("s").parent_state() == "not tried"
    h.record("s", 0, correct=False)
    assert h.state("s").parent_state() == "tried"
    h.record("s", 1, correct=True)
    h.record("s", 2, correct=True)
    assert h.state("s").parent_state() == "tried"
    h.record("s", 3, correct=True)
    assert h.state("s").parent_state() == "read correctly on 3 different days"


def test_three_corrects_on_one_day_is_still_only_tried():
    h = History()
    for _ in range(3):
        h.record("s", 0, correct=True)
    assert h.state("s").parent_state() == "tried"


# ---------------------------------------------------------------- persistence
def test_history_round_trips():
    h = History()
    h.record("s", 0, correct=True)
    h.record("a", 1, correct=False)
    again = History.from_dict(h.to_dict())
    assert again.states == h.states


def test_history_serialises_to_something_a_parent_could_read():
    h = History()
    h.record("s", 0, correct=True)
    doc = h.to_dict()
    assert doc["s"]["box"] == 1
    assert set(doc["s"]) == {
        "box", "streak", "streak_days", "correct_days", "last_seen_day",
        "attempts", "first_attempt_correct",
    }


# ------------------------------------------------------------------ selection
def test_selection_never_goes_above_the_ceiling(corpus, ck):
    picks = select_gpcs(corpus, ck, History(), 0, size=10)
    assert {gid for gid, _ in picks} <= ck.gpc_ids


def test_selection_is_empty_at_a_zero_ceiling(corpus):
    from sounds_and_words.ceiling import ceiling_from_order

    assert select_gpcs(corpus, ceiling_from_order(corpus, 0), History(), 0) == []


def test_selection_starts_with_the_newest_permitted_gpc(corpus, ck):
    picks = select_gpcs(corpus, ck, History(), 0, size=3)
    assert picks
    assert all(role is Role.NEW for _, role in picks)
    assert picks[0][0] == "ck", "the sound the school taught most recently comes first"


def test_selection_prefers_what_is_due(corpus, ck):
    h = History()
    for gid in ("s", "a", "t"):
        h.record(gid, 0, correct=True)
    picks = select_gpcs(corpus, ck, h, day=5, size=5)
    review = [gid for gid, role in picks if role is Role.REVIEW]
    assert set(review) == {"s", "a", "t"}, "60% of five is three, and three are due"


def test_nothing_due_and_nothing_new_gives_a_shorter_session(corpus):
    """kidnix does not manufacture work."""
    from sounds_and_words.ceiling import ceiling_from_order

    tiny = ceiling_from_order(corpus, 1)          # 's' and 's_z' only
    h = History()
    h.record("s", 0, correct=True)
    h.record("s_z", 0, correct=True)
    picks = select_gpcs(corpus, tiny, h, day=0, size=5)
    assert picks == []


def test_mastered_gpcs_come_back_as_interleaving(corpus, ck):
    h = History()
    for day in range(5):
        h.record("s", day, correct=True)
    for gid in ("a", "t", "p", "i", "n", "m", "d", "g", "o", "c", "k", "ck"):
        h.record(gid, 0, correct=True)
    picks = select_gpcs(corpus, ck, h, day=1, size=5)
    assert any(role is Role.INTERLEAVE for _, role in picks)


def test_selection_never_repeats_a_gpc(corpus, phase3):
    picks = select_gpcs(corpus, phase3, History(), 0, size=8)
    ids = [gid for gid, _ in picks]
    assert len(ids) == len(set(ids))


# ------------------------------------------------------------ compose_session
def test_a_session_is_find_then_blend_then_read(corpus, ck):
    s = compose_session(corpus, ck, History(), day=0)
    kinds = [i.kind for i in s.items]
    assert ItemKind.FIND_IT in kinds
    assert ItemKind.BLEND_IT in kinds
    first_blend = kinds.index(ItemKind.BLEND_IT)
    assert all(k is ItemKind.FIND_IT for k in kinds[:first_blend])


def test_a_session_never_contains_an_untaught_gpc(corpus):
    """The test the whole activity rests on. Every ceiling, every day."""
    for grapheme in ("t", "d", "ck", "r", "ss", "x", "qu", "ng", "igh", "oi", "er"):
        c = ceiling_for_grapheme(corpus, grapheme)
        h = History()
        for day in range(6):
            session = compose_session(corpus, c, h, day=day, rng=random.Random(day))
            for item in session.items:
                if item.gpc_id:
                    assert item.gpc_id in c.gpc_ids, (grapheme, item)
                if item.kind is ItemKind.BLEND_IT:
                    assert set(item.graphemes) <= c.gpc_ids, (grapheme, item)
                    for token in tokenise(item.payload):
                        assert check_word(corpus, token, c).allowed, (grapheme, item)
            for gid in session.gpc_ids():
                h.record(gid, day, correct=True)


def test_every_read_it_item_is_fully_decodable(corpus):
    from sounds_and_words.ceiling import check_lines, check_text

    for grapheme in ("ss", "ng", "er"):
        c = ceiling_for_grapheme(corpus, grapheme)
        session = compose_session(corpus, c, History(), day=0)
        for item in session.of_kind(ItemKind.READ_IT):
            if item.graphemes:
                assert check_lines(corpus, list(item.graphemes), c).allowed
            else:
                assert check_text(corpus, item.payload, c).allowed


def test_a_session_lands_in_real_language(corpus):
    """Never a pure isolated-grapheme drill loop: phonics *and* meaning."""
    c = ceiling_for_grapheme(corpus, "ss")
    s = compose_session(corpus, c, History(), day=0)
    assert s.of_kind(ItemKind.READ_IT)


def test_a_session_is_deterministic_for_a_given_day(corpus, ck):
    a = compose_session(corpus, ck, History(), day=3)
    b = compose_session(corpus, ck, History(), day=3)
    assert a == b


def test_a_session_at_a_zero_ceiling_is_empty(corpus):
    from sounds_and_words.ceiling import ceiling_from_order

    s = compose_session(corpus, ceiling_from_order(corpus, 0), History(), day=0)
    assert len(s) == 0


def test_a_session_carries_the_ceiling_label(corpus, ck):
    assert compose_session(corpus, ck, History(), day=0).ceiling_label == "up to 'ck'"


def test_blend_it_words_are_short_first(corpus, phase3):
    s = compose_session(corpus, phase3, History(), day=0, words_per_gpc=2)
    blends = s.of_kind(ItemKind.BLEND_IT)
    assert blends
    assert all(len(i.graphemes) <= 6 for i in blends)


def test_the_child_at_ck_can_blend_six_words(corpus, ck):
    """The v1 acceptance test, from the schedule's side."""
    s = compose_session(corpus, ck, History(), day=0, size=5, words_per_gpc=2)
    assert len(s.of_kind(ItemKind.BLEND_IT)) >= 6


def test_every_item_cites_its_source(corpus, ck):
    for item in compose_session(corpus, ck, History(), day=0).items:
        assert item.source


def test_a_session_after_a_wrong_answer_reschedules_that_gpc(corpus, ck):
    h = History()
    for day in range(4):
        h.record("s", day, correct=True)
    h.record("s", 4, correct=False)
    picks = select_gpcs(corpus, ck, h, day=5, size=5)
    assert "s" in {gid for gid, _ in picks}
