"""The pictures. Cairo only, so the Journal card is proved with no display.

The card that lands in My Things is the activity's whole output -- SYNTHESIS E1
is that *the reward is the artefact* -- so "does it actually write a PNG, for
every session a child could have had" is not a decorative test.
"""

from __future__ import annotations

from pathlib import Path

import cairo
import pytest

from numbers_activity.arrange import dice, ten_frame
from numbers_activity.draw import (
    CARD_HEIGHT,
    CARD_WIDTH,
    draw_arrangement,
    draw_bond_frame,
    draw_paper,
    draw_pattern,
    frame_geometry,
    render_card,
)
from numbers_activity.settings import FIVE_FRAME, TEN_FRAME

PNG_MAGIC = b"\x89PNG\r\n\x1a\n"


def _context(width: int = 300, height: int = 200):
    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, width, height)
    return cairo.Context(surface), surface


def _has_ink(surface: cairo.ImageSurface) -> bool:
    """Did anything at all get drawn? A blank card is the failure that matters."""
    data = bytes(surface.get_data())
    return len(set(data)) > 1


# -- the pieces --------------------------------------------------------------


def test_paper_is_drawn() -> None:
    ctx, surface = _context()
    draw_paper(ctx, 300, 200)
    surface.flush()
    assert _has_ink(surface)


@pytest.mark.parametrize("count", list(range(1, 7)))
def test_a_dice_face_draws(count: int) -> None:
    ctx, surface = _context()
    draw_paper(ctx, 300, 200)
    draw_arrangement(ctx, 300, 200, dice(count))
    surface.flush()
    assert _has_ink(surface)


@pytest.mark.parametrize("count", list(range(1, 11)))
def test_a_ten_frame_draws(count: int) -> None:
    ctx, surface = _context()
    draw_arrangement(ctx, 300, 200, ten_frame(count))
    surface.flush()
    assert _has_ink(surface)


def test_revealing_none_of_a_scatter_draws_nothing() -> None:
    ctx, surface = _context()
    draw_arrangement(ctx, 300, 200, dice(4), revealed=0)
    surface.flush()
    assert not _has_ink(surface), "the counting reveal starts empty"


def test_revealing_is_bounded_by_how_many_there_are() -> None:
    ctx, _ = _context()
    # Asking for more dots than exist must not raise; it draws what there is.
    draw_arrangement(ctx, 300, 200, dice(3), revealed=99)


@pytest.mark.parametrize("number", list(range(1, 11)))
def test_the_pattern_under_a_numeral_draws_at_tile_size(number: int) -> None:
    ctx, surface = _context(48, 48)
    draw_pattern(ctx, 48, 48, number)
    surface.flush()
    assert _has_ink(surface)


# -- the frame, and the boxes the window puts targets on ---------------------


def test_the_frame_reports_one_box_per_cell() -> None:
    ctx, _ = _context(500, 220)
    boxes = draw_bond_frame(ctx, 500, 220, TEN_FRAME, shown=3, usable=10)
    assert len(boxes) == 10


def test_the_boxes_are_square_and_in_reading_order() -> None:
    ctx, _ = _context(500, 220)
    boxes = draw_bond_frame(ctx, 500, 220, TEN_FRAME, shown=3, usable=10)
    sizes = {round(size, 6) for _, _, size in boxes}
    assert len(sizes) == 1, "every box is the same size"
    top = boxes[:5]
    assert [x for x, _, _ in top] == sorted(x for x, _, _ in top)
    assert boxes[5][1] > boxes[0][1], "the second row is below the first"


def test_the_boxes_agree_with_the_geometry_the_window_places_targets_from() -> None:
    ctx, _ = _context(500, 220)
    boxes = draw_bond_frame(ctx, 500, 220, TEN_FRAME, shown=0, usable=10)
    x, y, cell = frame_geometry(500, 220, TEN_FRAME)
    assert boxes[0] == pytest.approx((x, y, cell))


def test_a_five_frame_is_one_row_of_boxes() -> None:
    ctx, _ = _context(400, 140)
    boxes = draw_bond_frame(ctx, 400, 140, FIVE_FRAME, shown=2, usable=5)
    assert len(boxes) == 5
    assert len({round(y, 6) for _, y, _ in boxes}) == 1


def test_the_childs_counters_go_where_the_finger_went() -> None:
    # `placed` is a set of box indices, not a count: a counter in the last box
    # of a ten-frame stays in the last box.
    ctx, surface = _context(500, 220)
    draw_bond_frame(ctx, 500, 220, TEN_FRAME, shown=3, placed={9}, usable=10)
    surface.flush()
    assert _has_ink(surface)


def test_drawing_a_frame_never_raises_for_any_bond() -> None:
    for total, frame in ((5, FIVE_FRAME), (5, TEN_FRAME), (10, TEN_FRAME)):
        for shown in range(1, total):
            ctx, _ = _context(500, 220)
            draw_bond_frame(
                ctx,
                500,
                220,
                frame,
                shown=shown,
                placed=set(range(shown, total)),
                usable=total,
            )


# -- the card that goes in the Journal ---------------------------------------


def test_the_card_is_a_png(tmp_path: Path) -> None:
    path = render_card(tmp_path / "card.png", [(3, 2, 5)])
    assert path.exists()
    assert path.read_bytes()[:8] == PNG_MAGIC


def test_the_card_is_the_size_it_says_it_is(tmp_path: Path) -> None:
    path = render_card(tmp_path / "card.png", [(3, 2, 5)])
    surface = cairo.ImageSurface.create_from_png(str(path))
    assert (surface.get_width(), surface.get_height()) == (CARD_WIDTH, CARD_HEIGHT)


def test_the_card_has_something_on_it(tmp_path: Path) -> None:
    path = render_card(tmp_path / "card.png", [(3, 2, 5), (1, 4, 5)])
    surface = cairo.ImageSurface.create_from_png(str(path))
    surface.flush()
    assert _has_ink(surface)


def test_a_card_of_four_bonds_draws(tmp_path: Path) -> None:
    bonds = [(1, 4, 5), (2, 3, 5), (5, 5, 10), (9, 1, 10)]
    path = render_card(tmp_path / "card.png", bonds)
    assert path.read_bytes()[:8] == PNG_MAGIC


def test_more_than_four_bonds_do_not_overflow_the_card(tmp_path: Path) -> None:
    bonds = [(1, 4, 5), (2, 3, 5), (3, 2, 5), (4, 1, 5), (5, 5, 10), (8, 2, 10)]
    path = render_card(tmp_path / "card.png", bonds)
    assert path.read_bytes()[:8] == PNG_MAGIC


def test_a_session_with_no_bonds_still_gets_a_card(tmp_path: Path) -> None:
    # "We did the how-many one today" is still a true and useful thing for a
    # card to say, and a child who ran out of time mid-loop still made something.
    path = render_card(tmp_path / "card.png", [], [2, 4, 5])
    assert path.read_bytes()[:8] == PNG_MAGIC


def test_a_card_with_nothing_at_all_still_writes(tmp_path: Path) -> None:
    path = render_card(tmp_path / "card.png", [], [])
    assert path.read_bytes()[:8] == PNG_MAGIC


def test_the_card_directory_is_made_if_it_is_missing(tmp_path: Path) -> None:
    path = render_card(tmp_path / "deep" / "down" / "card.png", [(2, 3, 5)])
    assert path.is_file()
