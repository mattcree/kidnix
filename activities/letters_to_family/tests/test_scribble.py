"""The quick drawing: three colours, one undo, and nothing else.

Deliberately not a paint program -- Draw is a whole tile on Home and is better
than anything that would fit here. What is pinned is the small set of promises
the canvas makes to a four-year-old.
"""

from __future__ import annotations

from letters_to_family.scribble import COLOURS, Colour, Scribble, colour_for


def test_there_are_exactly_three_crayons():
    """Every extra item on a drawing surface costs a five-year-old touch
    accuracy (05 section 3, Couse & Chen)."""
    assert len(COLOURS) == 3
    assert [colour.key for colour in COLOURS] == ["teal", "pink", "black"]


def test_the_crayons_differ_in_lightness_as_well_as_hue():
    """B6: colour is never the sole carrier of meaning, and roughly 8% of boys
    are colour-blind. Black against teal against pink separates in greyscale."""
    lightness = sorted(sum(colour.rgb) for colour in COLOURS)
    assert lightness[-1] - lightness[0] > 0.5


def test_each_crayon_has_a_word_for_the_ear():
    for colour in COLOURS:
        assert colour.speak_text
        assert not any(character.isdigit() for character in colour.speak_text)


def test_a_colour_turns_into_the_numbers_cairo_wants():
    assert Colour(key="k", name="K", hex="#0f8a8a").rgb == (
        0x0F / 255,
        0x8A / 255,
        0x8A / 255,
    )


def test_an_unknown_colour_key_falls_back_rather_than_raising():
    assert colour_for("chartreuse") is COLOURS[0]


def test_a_press_and_a_drag_make_one_stroke():
    scribble = Scribble()
    scribble.start(0.1, 0.1)
    scribble.extend(0.2, 0.2)
    scribble.extend(0.3, 0.4)
    scribble.end()
    assert scribble.stroke_count == 1
    assert scribble.strokes[0].points == [(0.1, 0.1), (0.2, 0.2), (0.3, 0.4)]


def test_a_press_with_no_drag_is_a_dot_and_is_kept():
    """A single press *is* a mark a four-year-old meant to make."""
    scribble = Scribble()
    scribble.start(0.5, 0.5)
    scribble.end()
    assert scribble.stroke_count == 1
    assert scribble.is_empty is False


def test_a_finger_that_slides_off_the_canvas_leaves_a_line_to_the_edge():
    scribble = Scribble()
    scribble.start(0.9, 0.9)
    scribble.extend(1.4, -0.3)
    assert scribble.strokes[0].points[-1] == (1.0, 0.0)


def test_extending_with_nothing_open_does_nothing():
    scribble = Scribble()
    assert scribble.extend(0.5, 0.5) is False
    assert scribble.stroke_count == 0


def test_choosing_a_colour_ends_the_stroke_in_progress():
    """A line never changes colour halfway along."""
    scribble = Scribble()
    scribble.start(0.1, 0.1)
    scribble.choose("pink")
    assert scribble.drawing is False
    assert scribble.extend(0.2, 0.2) is False


def test_the_next_stroke_uses_the_colour_that_was_chosen():
    scribble = Scribble()
    scribble.choose("pink")
    scribble.start(0.1, 0.1)
    assert scribble.strokes[0].colour.key == "pink"


def test_undo_takes_the_whole_last_stroke_not_the_last_point():
    scribble = Scribble()
    scribble.start(0.1, 0.1)
    scribble.extend(0.2, 0.2)
    scribble.end()
    scribble.start(0.5, 0.5)
    scribble.extend(0.6, 0.6)
    scribble.end()
    assert scribble.undo() is True
    assert scribble.stroke_count == 1
    assert scribble.strokes[0].points[0] == (0.1, 0.1)


def test_undo_on_an_empty_page_is_safe_and_says_so():
    """A3: eight presses a second on an empty page produce nothing, not eight
    exceptions -- and that is exactly what a child does."""
    scribble = Scribble()
    for _ in range(8):
        assert scribble.undo() is False
    assert scribble.stroke_count == 0


def test_undo_ends_a_stroke_that_is_still_being_drawn():
    scribble = Scribble()
    scribble.start(0.1, 0.1)
    scribble.undo()
    assert scribble.drawing is False
    assert scribble.stroke_count == 0


def test_a_new_scribble_is_empty():
    assert Scribble().is_empty is True
    assert Scribble().stroke_count == 0
