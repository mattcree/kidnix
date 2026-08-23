"""One loop: twelve items, twelve minutes, two attempts, and no buzzer.

The bounds in research 10 section 4.1 and 4.3 are the ones that get quietly
relaxed the first time somebody wants "just one more round", so they are here
as assertions rather than as comments.
"""

from __future__ import annotations

import random

import pytest

from sounds_and_words.ceiling import ceiling_for_grapheme, ceiling_from_order
from sounds_and_words.loop import (
    MAX_ATTEMPTS,
    MAX_ITEMS,
    MAX_MINUTES,
    MIN_MINUTES,
    Outcome,
    SessionRunner,
    estimated_minutes,
    plan_session,
)
from sounds_and_words.schedule import History, ItemKind


@pytest.fixture
def set3(corpus):
    return ceiling_for_grapheme(corpus, "k")


@pytest.fixture
def plan(corpus, set3):
    return plan_session(corpus, set3, History(), 0, rng=random.Random(3))


# --- the two bounds ---------------------------------------------------------


def test_a_session_is_never_more_than_twelve_items(corpus, set3):
    for day in range(12):
        assert len(plan_session(corpus, set3, History(), day)) <= MAX_ITEMS


def test_a_session_is_never_more_than_twelve_minutes(corpus, set3):
    for day in range(12):
        assert plan_session(corpus, set3, History(), day).minutes <= MAX_MINUTES


def test_the_whole_loop_lands_in_the_eight_to_twelve_minute_band(plan):
    """Research 10 4.1's band is for A to G. Weeks 2-3 ship two of the four
    modules, so the *runnable* part is shorter by design -- what has to fit the
    band is the loop the plan describes, Read it included."""
    assert plan.minutes <= MAX_MINUTES
    whole = estimated_minutes([*plan.items, *plan.deferred])
    assert MIN_MINUTES <= whole <= MAX_MINUTES, whole


def test_a_lower_ceiling_lowers_the_bounds_too(corpus):
    """kidnix does not manufacture work. Fewer sounds is a shorter session."""
    tiny = plan_session(corpus, ceiling_for_grapheme(corpus, "t"), History(), 0)
    full = plan_session(corpus, ceiling_for_grapheme(corpus, "k"), History(), 0)
    assert len(tiny) < len(full)


def test_nothing_taught_is_an_empty_session_not_an_invented_one(corpus):
    nothing = ceiling_from_order(corpus, 0)
    assert len(plan_session(corpus, nothing, History(), 0)) == 0


def practice(plan):
    """The plan without its book. What the trim is allowed to cut."""
    return tuple(item for item in plan.items if item.kind is not ItemKind.READ_TEXT)


def test_a_tighter_budget_cuts_from_the_end(corpus, set3):
    short = plan_session(corpus, set3, History(), 0, max_minutes=3.0, rng=random.Random(3))
    long = plan_session(corpus, set3, History(), 0, rng=random.Random(3))
    assert practice(short) == practice(long)[: len(practice(short))]


def test_the_book_is_reserved_rather_than_trimmed(corpus, set3):
    """Four Find it, eight Blend it and a book is thirteen items. The bound is
    twelve, and the thing that must survive it is the book: it is the module
    with the meta-analysis behind it and the only connected language in the
    session. So the trim comes out of the practice tail, not out of Read it."""
    plan = plan_session(corpus, set3, History(), 0, rng=random.Random(3))
    assert plan.items[-1].kind is ItemKind.READ_TEXT
    assert len(plan.of_kind(ItemKind.READ_TEXT)) == 1
    assert len(plan) <= MAX_ITEMS

    squeezed = plan_session(corpus, set3, History(), 0, max_minutes=3.0, rng=random.Random(3))
    assert squeezed.items[-1].kind is ItemKind.READ_TEXT


def test_a_ceiling_with_no_book_in_it_gets_no_reserved_slot(corpus):
    """Reserving room for something that does not exist would be manufacturing
    work. Below the first text's order there is no book, and the session is
    twelve practice items and nothing else."""
    tiny = plan_session(corpus, ceiling_for_grapheme(corpus, "t"), History(), 0)
    assert not tiny.of_kind(ItemKind.READ_TEXT)


def test_the_book_the_schedule_picked_is_inside_the_ceiling(corpus):
    from sounds_and_words.ceiling import check_lines
    from sounds_and_words.reading import text_by_slug

    for grapheme in ("d", "k", "ss", "er"):
        ceiling = ceiling_for_grapheme(corpus, grapheme)
        for day in range(6):
            for item in plan_session(corpus, ceiling, History(), day).of_kind(ItemKind.READ_TEXT):
                book = text_by_slug(item.payload)
                assert book is not None, item.payload
                assert check_lines(corpus, book.all_lines, ceiling).allowed, (grapheme, book.slug)


def test_a_tighter_item_cap_cuts_from_the_end_too(corpus, set3):
    short = plan_session(corpus, set3, History(), 0, max_items=5, rng=random.Random(3))
    assert len(short) <= 5


def test_estimating_an_empty_plan_costs_nothing():
    assert estimated_minutes([]) == 0.0


# --- the order --------------------------------------------------------------


def test_find_it_comes_before_blend_it(plan):
    kinds = [item.kind for item in plan.items]
    assert kinds == sorted(kinds, key=lambda k: 0 if k is ItemKind.FIND_IT else 1)


def test_the_plan_only_contains_modules_that_exist(plan):
    assert {item.kind for item in plan.items} <= {
        ItemKind.FIND_IT,
        ItemKind.BLEND_IT,
        ItemKind.READ_TEXT,
    }


def test_read_it_is_planned_and_deferred_rather_than_silently_dropped(plan):
    """Week 4. The log should be able to say what is coming, not just shrink."""
    assert all(item.kind is ItemKind.READ_IT for item in plan.deferred)


def test_a_missing_module_is_skipped_not_stubbed(plan):
    """No "coming soon" tile. A child would press it every session."""
    assert not any(item.kind is ItemKind.READ_IT for item in plan.items)


def test_every_word_in_the_plan_is_under_the_ceiling(corpus, set3):
    from sounds_and_words.ceiling import check_word

    for day in range(8):
        for item in plan_session(corpus, set3, History(), day).items:
            if item.kind is ItemKind.BLEND_IT:
                assert check_word(corpus, item.payload, set3).allowed, item.payload


def test_every_grapheme_in_the_plan_is_under_the_ceiling(corpus, set3):
    for day in range(8):
        for item in plan_session(corpus, set3, History(), day).items:
            if item.gpc_id:
                assert item.gpc_id in set3.gpc_ids


def test_the_plan_describes_itself_without_saying_a_number_to_a_child(plan):
    described = plan.describe()
    assert "find_it" in described
    assert "min" in described


# --- two attempts, and then it moves on ------------------------------------


def runner(plan):
    return SessionRunner(plan, History())


def test_right_first_time_is_correct(plan):
    session = runner(plan)
    assert session.attempt(correct=True) is Outcome.CORRECT


def test_wrong_once_means_try_again(plan):
    session = runner(plan)
    assert session.attempt(correct=False) is Outcome.AGAIN


def test_wrong_twice_moves_on(plan):
    session = runner(plan)
    session.attempt(correct=False)
    assert session.attempt(correct=False) is Outcome.MOVE_ON


def test_there_are_exactly_two_attempts():
    assert MAX_ATTEMPTS == 2


def test_the_box_is_written_from_the_first_attempt_only(plan):
    """Getting it on the third go is not the same event as getting it first
    time, and treating them alike is how mastery bars come to mean nothing."""
    session = runner(plan)
    item = session.current
    session.attempt(correct=False)
    session.attempt(correct=True)
    state = session.history.state(item.gpc_id)
    assert state.attempts == 1
    assert state.first_attempt_correct == 0
    assert state.box == 1


def test_a_correct_first_attempt_promotes_the_box(plan):
    session = runner(plan)
    item = session.current
    session.attempt(correct=True)
    assert session.history.state(item.gpc_id).box == 1
    assert session.history.state(item.gpc_id).first_attempt_correct == 1


def test_an_error_never_demotes_to_zero(plan):
    """A demotion to zero re-teaches, and re-teaching is the school's job."""
    session = runner(plan)
    item = session.current
    session.history.record(item.gpc_id, 0, correct=True)
    session.history.record(item.gpc_id, 1, correct=True)
    session.attempt(correct=False)
    assert session.history.state(item.gpc_id).box == 1


def test_answering_after_the_end_does_nothing(plan):
    session = runner(plan)
    for _ in range(len(plan) + 2):
        session.advance()
    assert session.attempt(correct=True) is Outcome.MOVE_ON


def test_attempts_reset_on_the_next_item(plan):
    session = runner(plan)
    session.attempt(correct=False)
    session.advance()
    assert session.attempts == 0


# --- what the session produced ---------------------------------------------


def test_the_runner_starts_at_the_beginning_and_ends_at_the_end(plan):
    session = runner(plan)
    assert not session.done
    assert session.remaining == len(plan)
    for _ in range(len(plan)):
        session.advance()
    assert session.done
    assert session.current is None


def test_words_read_are_the_words_that_were_actually_reached(plan):
    session = runner(plan)
    session.blend("cat")
    session.blend("sat")
    assert session.words_read() == ("cat", "sat")


def test_a_word_is_not_counted_twice(plan):
    session = runner(plan)
    session.blend("cat")
    session.blend("Cat")
    assert session.words_read() == ("cat",)


def test_an_empty_word_is_not_a_word(plan):
    session = runner(plan)
    session.blend("  ")
    assert session.words_read() == ()


def test_gpcs_practised_counts_what_reached_the_screen_not_what_was_planned(plan):
    session = runner(plan)
    assert session.gpcs_practised() == ()
    session.advance()
    assert len(session.gpcs_practised()) == 1


def test_a_session_nobody_finished_still_has_a_truthful_list(plan):
    session = runner(plan)
    session.advance()
    session.advance()
    assert len(session.gpcs_practised()) <= 2
