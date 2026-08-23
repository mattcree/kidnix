"""The session: what is asked, in what order, and what happens to an answer.

Three things are pinned here that are easy to break and expensive to break:

* the loop is **always eight items in the same order** -- four *how many?* then
  four bonds -- because the DfE's own early-years guidance asks for content that
  is "slow-paced, repetitive and predictable" and because there is no adaptive
  ladder in this product (05 section 4 #8);
* **both parts of every bond are at least one**, so "five and zero make five"
  never reaches a child;
* nothing anywhere accumulates a score. :func:`respond` is total, has no memory
  and returns one of three *actions*.
"""

from __future__ import annotations

import random

import pytest

from numbers_activity.arrange import MAX_SCATTER, Shape
from numbers_activity.items import (
    BOND_ITEMS,
    HOW_MANY_ITEMS,
    MAX_ATTEMPTS,
    SESSION_ITEMS,
    HowMany,
    MakeBond,
    Practised,
    Response,
    bond_items,
    grownup_numbers,
    how_many_items,
    respond,
    session,
)
from numbers_activity.settings import (
    FIVE_FRAME,
    TEN_FRAME,
    FrameStyle,
    NumberRange,
    ParentSettings,
)

FIVE = ParentSettings()
TEN = ParentSettings(range=NumberRange.TEN)

SEEDS = list(range(40))


def _session(settings: ParentSettings, seed: int):
    return session(settings, random.Random(seed))


# -- the shape of a session --------------------------------------------------


@pytest.mark.parametrize("seed", SEEDS)
def test_a_session_is_always_eight_items(seed: int) -> None:
    assert len(_session(FIVE, seed)) == SESSION_ITEMS == 8


@pytest.mark.parametrize("seed", SEEDS[:10])
def test_the_how_many_items_all_come_first(seed: int) -> None:
    for settings in (FIVE, TEN):
        items = _session(settings, seed)
        kinds = [type(item) for item in items]
        assert kinds[:HOW_MANY_ITEMS] == [HowMany] * HOW_MANY_ITEMS
        assert kinds[HOW_MANY_ITEMS:] == [MakeBond] * BOND_ITEMS


@pytest.mark.parametrize("seed", SEEDS[:10])
def test_the_same_seed_gives_the_same_session(seed: int) -> None:
    first = _session(FIVE, seed)
    second = _session(FIVE, seed)
    assert [item.answer for item in first] == [item.answer for item in second]


# -- how many? ---------------------------------------------------------------


@pytest.mark.parametrize("seed", SEEDS)
def test_five_range_never_shows_more_than_five(seed: int) -> None:
    for item in how_many_items(FIVE, random.Random(seed)):
        assert 1 <= item.count <= 5


@pytest.mark.parametrize("seed", SEEDS)
def test_ten_range_shows_both_halves(seed: int) -> None:
    counts = [item.count for item in how_many_items(TEN, random.Random(seed))]
    assert any(count <= 5 for count in counts)
    assert any(count >= 6 for count in counts), "six to ten is the point of the ten range"
    assert all(1 <= count <= 10 for count in counts)


@pytest.mark.parametrize("seed", SEEDS)
def test_no_quantity_is_asked_twice_in_a_session(seed: int) -> None:
    for settings in (FIVE, TEN):
        counts = [item.count for item in how_many_items(settings, random.Random(seed))]
        assert len(set(counts)) == len(counts)


@pytest.mark.parametrize("seed", SEEDS)
def test_the_smallest_quantity_goes_first(seed: int) -> None:
    # A four-year-old's first question of the session is one they cannot get
    # wrong. A program that opens with its hardest item has said something about
    # the child in the first ten seconds.
    counts = [item.count for item in how_many_items(FIVE, random.Random(seed))]
    assert counts[0] == min(counts)


@pytest.mark.parametrize("seed", SEEDS)
def test_the_first_two_pictures_are_canonical(seed: int) -> None:
    for settings in (FIVE, TEN):
        items = how_many_items(settings, random.Random(seed))
        for item in items[: HOW_MANY_ITEMS // 2]:
            assert item.arrangement.shape is not Shape.SCATTER


@pytest.mark.parametrize("seed", SEEDS)
def test_nothing_above_four_is_ever_scattered(seed: int) -> None:
    for settings in (FIVE, TEN):
        for item in how_many_items(settings, random.Random(seed)):
            if item.arrangement.shape is Shape.SCATTER:
                assert item.count <= MAX_SCATTER


@pytest.mark.parametrize("seed", SEEDS)
def test_six_to_ten_always_arrive_on_a_ten_frame(seed: int) -> None:
    for item in how_many_items(TEN, random.Random(seed)):
        if item.count >= 6:
            assert item.arrangement.shape is Shape.TEN_FRAME
            assert item.arrangement.rows == 2


@pytest.mark.parametrize("seed", SEEDS[:10])
def test_a_how_many_item_knows_its_own_answer(seed: int) -> None:
    for item in how_many_items(FIVE, random.Random(seed)):
        assert item.is_answer(item.count)
        assert not item.is_answer(item.count + 1)


def test_an_item_cannot_disagree_with_its_own_picture() -> None:
    from numbers_activity.arrange import dice

    with pytest.raises(ValueError):
        HowMany(count=3, arrangement=dice(4))


# -- the bonds ---------------------------------------------------------------


@pytest.mark.parametrize("seed", SEEDS)
def test_every_bond_adds_up(seed: int) -> None:
    for settings in (FIVE, TEN):
        for item in bond_items(settings, random.Random(seed)):
            assert item.shown + item.missing == item.total


@pytest.mark.parametrize("seed", SEEDS)
def test_neither_part_of_a_bond_is_ever_zero(seed: int) -> None:
    for settings in (FIVE, TEN):
        for item in bond_items(settings, random.Random(seed)):
            assert item.shown >= 1
            assert item.missing >= 1


@pytest.mark.parametrize("seed", SEEDS)
def test_the_five_range_does_every_bond_to_five(seed: int) -> None:
    # One and four, two and three, three and two, four and one -- the whole ELG
    # requirement, once a session, in a shuffled order.
    items = bond_items(FIVE, random.Random(seed))
    assert sorted(item.shown for item in items) == [1, 2, 3, 4]
    assert all(item.total == 5 for item in items)


@pytest.mark.parametrize("seed", SEEDS)
def test_the_ten_range_does_fives_before_tens(seed: int) -> None:
    totals = [item.total for item in bond_items(TEN, random.Random(seed))]
    assert totals == [5, 5, 10, 10]


@pytest.mark.parametrize("seed", SEEDS)
def test_the_ten_range_always_includes_the_double(seed: int) -> None:
    # "some number bonds to 10, **including double facts**" -- a double that
    # turns up sometimes is not included.
    bonds = [item.bond for item in bond_items(TEN, random.Random(seed))]
    assert (5, 5, 10) in bonds


@pytest.mark.parametrize("seed", SEEDS)
def test_no_bond_is_repeated_in_a_session(seed: int) -> None:
    for settings in (FIVE, TEN):
        bonds = [item.bond for item in bond_items(settings, random.Random(seed))]
        assert len(set(bonds)) == len(bonds)


@pytest.mark.parametrize("seed", SEEDS[:10])
def test_a_bond_to_five_gets_a_five_frame_by_default(seed: int) -> None:
    for item in bond_items(FIVE, random.Random(seed)):
        assert item.frame is FIVE_FRAME


@pytest.mark.parametrize("seed", SEEDS[:10])
def test_a_bond_to_ten_always_gets_a_ten_frame(seed: int) -> None:
    for item in bond_items(TEN, random.Random(seed)):
        if item.total == 10:
            assert item.frame is TEN_FRAME


def test_a_ten_frame_setting_puts_the_bonds_to_five_in_a_ten_frame() -> None:
    settings = ParentSettings(frames=FrameStyle.TEN)
    for item in bond_items(settings, random.Random(3)):
        assert item.frame is TEN_FRAME


def test_a_bond_refuses_to_be_impossible() -> None:
    with pytest.raises(ValueError):
        MakeBond(shown=5, total=5, frame=FIVE_FRAME)
    with pytest.raises(ValueError):
        MakeBond(shown=0, total=5, frame=FIVE_FRAME)
    with pytest.raises(ValueError):
        MakeBond(shown=3, total=10, frame=FIVE_FRAME)


def test_a_bond_knows_what_is_missing() -> None:
    item = MakeBond(shown=3, total=5, frame=FIVE_FRAME)
    assert item.missing == 2
    assert item.bond == (3, 2, 5)
    assert item.is_answer(2)
    assert not item.is_answer(3)


# -- answering ---------------------------------------------------------------


def test_the_right_number_is_right_however_many_goes_it_took() -> None:
    item = MakeBond(shown=3, total=5, frame=FIVE_FRAME)
    for attempts in range(4):
        assert respond(item, 2, attempts) is Response.RIGHT


def test_the_first_wrong_answer_gets_another_go() -> None:
    item = MakeBond(shown=3, total=5, frame=FIVE_FRAME)
    assert respond(item, 4, 0) is Response.TRY_AGAIN


def test_the_second_wrong_answer_is_told_rather_than_asked_again() -> None:
    item = MakeBond(shown=3, total=5, frame=FIVE_FRAME)
    assert respond(item, 4, 1) is Response.TOLD


def test_nobody_is_asked_a_third_time() -> None:
    item = MakeBond(shown=3, total=5, frame=FIVE_FRAME)
    assert MAX_ATTEMPTS == 2
    for attempts in range(2, 6):
        assert respond(item, 1, attempts) is Response.TOLD


# -- the grown-up's card -----------------------------------------------------


@pytest.mark.parametrize("seed", SEEDS[:10])
def test_the_grown_up_is_asked_about_numbers_the_child_just_did(seed: int) -> None:
    items = _session(TEN, seed)
    number, total = grownup_numbers(items)
    assert number in {item.count for item in items if isinstance(item, HowMany)}
    assert total in {item.total for item in items if isinstance(item, MakeBond)}
    assert number < total, "asking for more fingers than the total makes no sense"


def test_the_grown_up_card_has_numbers_even_with_no_items() -> None:
    assert grownup_numbers([]) == (4, 5)


# -- what goes on the Journal card -------------------------------------------


def test_practised_records_what_was_done_not_how_it_went() -> None:
    practised = Practised()
    assert practised.empty
    practised.add_bond((3, 2, 5))
    practised.add_count(4)
    assert not practised.empty
    assert practised.bonds == [(3, 2, 5)]
    assert practised.counts == [4]


def test_practised_does_not_record_the_same_thing_twice() -> None:
    practised = Practised()
    practised.add_bond((3, 2, 5))
    practised.add_bond((3, 2, 5))
    practised.add_count(4)
    practised.add_count(4)
    assert practised.bonds == [(3, 2, 5)]
    assert practised.counts == [4]


def test_practised_caption_names_the_bond() -> None:
    practised = Practised()
    practised.add_bond((3, 2, 5))
    assert practised.caption() == "Today: three and two make five"


def test_clearing_practised_is_what_a_second_save_starts_from() -> None:
    practised = Practised()
    practised.add_bond((1, 4, 5))
    practised.clear()
    assert practised.empty


def test_practised_has_no_score_shaped_attributes() -> None:
    # A structural assertion, not a wording one: there is nowhere in this object
    # to put a mark, and this test is what stops one appearing.
    names = set(vars(Practised()))
    assert names == {"bonds", "counts"}
