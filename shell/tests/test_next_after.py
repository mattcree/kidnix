"""S1b's option set (spec 7b, SYNTHESIS D4).

Coco's Videos derived its nine categories by clustering 381 diary entries of
what children actually did after screen time. Ours are somebody else's
household, which is why they are parent-configurable -- and why a mistyped
option costs one tile, never the screen.
"""

from __future__ import annotations

import tomllib

import pytest

from kidnix_shell.next_after import (
    DEFAULT_NEXT_AFTER,
    MAX_OPTIONS,
    MIN_OPTIONS,
    NextAfter,
    find,
    parse_next_after,
)


def test_the_shipped_set_is_between_six_and_nine() -> None:
    """09 section 6: "6-9 picture options"."""
    assert MIN_OPTIONS <= len(DEFAULT_NEXT_AFTER) <= MAX_OPTIONS


def test_every_default_has_an_id_a_label_an_audio_label_and_a_picture() -> None:
    for option in DEFAULT_NEXT_AFTER:
        assert option.id and option.label and option.speak_text and option.icon


def test_the_default_ids_are_unique() -> None:
    ids = [option.id for option in DEFAULT_NEXT_AFTER]
    assert len(set(ids)) == len(ids)


def test_every_default_reads_as_a_sentence_at_goodbye() -> None:
    """S7 says "Ready to [thing]?", and a tile label is a noun as often as a
    verb -- "Ready to a book?" is exactly what ``phrase`` exists to prevent.

    The skip option is exempt because it never reaches S7: choosing it clears
    ``ctx.next_after`` and Goodbye falls back to the generated line.
    """
    for option in DEFAULT_NEXT_AFTER:
        if option.skips:
            continue
        line = option.ready_line
        assert line.startswith("Ready to ")
        assert line.endswith("?")
        assert line[9].islower()
        verb = option.phrase.split()[0]
        assert verb in {"go", "read", "build", "draw", "have", "help", "play"}, option.id


def test_a_default_icon_exists_in_the_bundled_set() -> None:
    from kidnix_shell.widgets import bundled_icon

    for option in DEFAULT_NEXT_AFTER:
        assert bundled_icon(option.icon) is not None, option.icon


def test_no_default_asks_the_child_to_come_back() -> None:
    """SYNTHESIS D6: the system has no interest in whether the child returns."""
    for option in DEFAULT_NEXT_AFTER:
        text = f"{option.label} {option.speak_text}".lower()
        for banned in ("again", "tomorrow", "next time", "computer", "screen"):
            assert banned not in text, option.id


# --- parsing --------------------------------------------------------------


def test_a_missing_key_falls_back_to_the_defaults() -> None:
    assert parse_next_after(None) == DEFAULT_NEXT_AFTER


def test_both_toml_spellings_parse_the_same_way() -> None:
    """A parent should not have to know which array syntax we meant."""
    inline = tomllib.loads(
        'next_after = [{ id = "outside", label = "Go outside", icon = "kidnix-next-outside" }]'
    )
    tables = tomllib.loads(
        '[[next_after]]\nid = "outside"\nlabel = "Go outside"\nicon = "kidnix-next-outside"\n'
    )
    assert parse_next_after(inline["next_after"]) == parse_next_after(tables["next_after"])


def test_the_audio_label_defaults_to_the_label() -> None:
    options = parse_next_after([{"id": "outside", "label": "Go outside"}])
    assert options[0].speak_text == "Go outside"


def test_a_malformed_entry_costs_one_tile_not_the_screen() -> None:
    options = parse_next_after(
        [
            {"id": "outside", "label": "Go outside"},
            {"label": "No id at all"},
            "not a table",
            {"id": "book", "label": "Read a book"},
        ]
    )
    assert [option.id for option in options] == ["outside", "book"]


def test_a_duplicate_id_keeps_the_first() -> None:
    options = parse_next_after(
        [{"id": "outside", "label": "Go outside"}, {"id": "outside", "label": "Outdoors"}]
    )
    assert [option.label for option in options] == ["Go outside"]


def test_an_empty_or_unusable_list_falls_back_rather_than_showing_nothing() -> None:
    """An empty S1b would be a screen a child cannot get off."""
    assert parse_next_after([]) == DEFAULT_NEXT_AFTER
    assert parse_next_after([{"nonsense": 1}]) == DEFAULT_NEXT_AFTER
    assert parse_next_after("go outside") == DEFAULT_NEXT_AFTER


def test_too_many_options_are_truncated_to_nine() -> None:
    many = [{"id": f"o{index}", "label": f"Thing {index}"} for index in range(20)]
    assert len(parse_next_after(many)) == MAX_OPTIONS


def test_fewer_than_six_is_allowed_because_a_household_may_have_four() -> None:
    few = [{"id": f"o{index}", "label": f"Thing {index}"} for index in range(4)]
    assert len(parse_next_after(few)) == 4


def test_finding_an_option_by_id() -> None:
    assert find(DEFAULT_NEXT_AFTER, "outside") is not None
    assert find(DEFAULT_NEXT_AFTER, "nope") is None


def test_an_option_lays_out_like_an_activity_tile() -> None:
    """S1b reuses Home's tile, so the option has to quack like an Activity."""
    option = NextAfter("outside", "Go outside", icon="kidnix-next-outside")
    assert option.name == "Go outside"
    assert option.icon_kind == "icon-name"
    assert option.category
    assert option.speak_text == "Go outside"


def test_an_empty_label_does_not_produce_a_broken_sentence() -> None:
    assert NextAfter("x", "").phrase == ""


def test_a_parent_can_give_an_option_its_own_sentence() -> None:
    options = parse_next_after([{"id": "swing", "label": "The swing", "phrase": "go on the swing"}])
    assert options[0].ready_line == "Ready to go on the swing?"


@pytest.mark.parametrize("option", DEFAULT_NEXT_AFTER, ids=lambda o: o.id)
def test_no_default_label_is_longer_than_a_tile_can_hold(option: NextAfter) -> None:
    """S1b uses Home's tile, whose label box is two lines at the 18 pt floor.

    A third line makes the tile taller than the grid budgeted for, so the
    labels are short and the *audio* label carries the longer wording.
    """
    assert len(option.label) <= 12
    assert len(option.label.split()) <= 2, option.id
    assert max(len(word) for word in option.label.split()) <= 8
