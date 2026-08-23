"""Where the dots go, and where they are never allowed to go.

The load-bearing assertions here are the two negatives: **nothing above four is
ever scattered**, and **six to ten are always a full row of five and some
more**. Both come straight out of 05 section 2c -- the first because scattering
five turns subitising into counting, the second because "dot cloud" training is
the approximate-number-system intervention that failed to replicate (Szkudlarek
et al., N = 318) and that the synthesis says in as many words not to build.
"""

from __future__ import annotations

import random

import pytest

from numbers_activity.arrange import (
    DICE_PATTERNS,
    MAX_SCATTER,
    SCATTER_MIN_DISTANCE,
    Arrangement,
    Shape,
    arrangement_for,
    dice,
    frame_cells,
    scatter,
    ten_frame,
)


def _distance(a, b) -> float:
    return ((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2) ** 0.5


@pytest.mark.parametrize("count", [1, 2, 3, 4, 5, 6])
def test_a_dice_face_has_that_many_pips(count: int) -> None:
    arrangement = dice(count)
    assert arrangement.count == count
    assert len(arrangement.points) == count
    assert arrangement.shape is Shape.DICE


def test_dice_pips_are_inside_the_square_and_distinct() -> None:
    for count, points in DICE_PATTERNS.items():
        assert len(set(points)) == count, f"{count} has a repeated pip"
        for x, y in points:
            assert 0.0 < x < 1.0 and 0.0 < y < 1.0


def test_the_dice_five_is_the_dice_five() -> None:
    # The four corners and the middle. If this ever changes, a child who knows
    # a dice has been told their dice is wrong.
    assert dice(5).points == (
        (0.25, 0.25),
        (0.75, 0.25),
        (0.50, 0.50),
        (0.25, 0.75),
        (0.75, 0.75),
    )


def test_there_is_no_dice_face_above_six() -> None:
    with pytest.raises(ValueError):
        dice(7)


def test_a_frame_reads_left_to_right_then_down() -> None:
    cells = frame_cells(5, 2)
    assert len(cells) == 10
    top = cells[:5]
    bottom = cells[5:]
    assert [x for x, _ in top] == sorted(x for x, _ in top)
    assert all(y < bottom[0][1] for _, y in top)


@pytest.mark.parametrize("count", [6, 7, 8, 9, 10])
def test_six_to_ten_are_a_full_five_and_some_more(count: int) -> None:
    arrangement = ten_frame(count)
    top_row = [point for point in arrangement.points if point[1] < 0.5]
    bottom_row = [point for point in arrangement.points if point[1] > 0.5]
    assert len(top_row) == 5, "the top row must be full before the bottom starts"
    assert len(bottom_row) == count - 5


def test_a_five_frame_is_one_row() -> None:
    arrangement = ten_frame(4, rows=1)
    assert arrangement.rows == 1
    assert all(abs(y - 0.5) < 1e-9 for _, y in arrangement.points)


def test_a_frame_arrangement_knows_it_has_a_frame() -> None:
    assert ten_frame(3).framed is True
    assert dice(3).framed is False


def test_a_frame_refuses_more_than_it_holds() -> None:
    with pytest.raises(ValueError):
        ten_frame(11)


@pytest.mark.parametrize("count", [1, 2, 3, 4])
def test_scattered_dots_are_never_touching(count: int) -> None:
    for seed in range(60):
        arrangement = scatter(count, random.Random(seed))
        points = arrangement.points
        assert len(points) == count
        for index, first in enumerate(points):
            for second in points[index + 1 :]:
                assert _distance(first, second) >= SCATTER_MIN_DISTANCE


def test_scattered_dots_stay_on_the_card() -> None:
    for seed in range(40):
        for x, y in scatter(4, random.Random(seed)).points:
            assert 0.0 < x < 1.0 and 0.0 < y < 1.0


def test_scatter_varies_between_seeds() -> None:
    # A "random" arrangement that is the same every time is a picture again.
    first = scatter(3, random.Random(1)).points
    second = scatter(3, random.Random(2)).points
    assert first != second


def test_nothing_above_four_is_ever_scattered() -> None:
    with pytest.raises(ValueError):
        scatter(MAX_SCATTER + 1, random.Random(0))


def test_asking_to_scatter_five_gets_a_dice_face_instead() -> None:
    # The guard rail under items.py: a shape that cannot honestly show this many
    # is corrected rather than refused, because a blank card in front of a
    # five-year-old is worse than a familiar five.
    arrangement = arrangement_for(5, shape=Shape.SCATTER, rng=random.Random(0))
    assert arrangement.shape is Shape.DICE


def test_asking_for_a_dice_face_of_nine_gets_a_ten_frame() -> None:
    arrangement = arrangement_for(9, shape=Shape.DICE)
    assert arrangement.shape is Shape.TEN_FRAME
    assert arrangement.count == 9


def test_every_count_to_ten_can_be_arranged() -> None:
    for count in range(1, 11):
        for shape in Shape:
            arrangement = arrangement_for(count, shape=shape, rng=random.Random(count))
            assert arrangement.count == count
            assert len(arrangement.points) == count


def test_an_arrangement_cannot_lie_about_how_many_it_shows() -> None:
    with pytest.raises(ValueError):
        Arrangement(count=3, shape=Shape.DICE, points=((0.5, 0.5),))


def test_nothing_is_arranged_below_one() -> None:
    with pytest.raises(ValueError):
        arrangement_for(0)
