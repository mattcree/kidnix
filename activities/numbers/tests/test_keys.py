"""The keyboard. One table, and the keys this activity is careful not to take.

SYNTHESIS A6 is that the keyboard is never *required* -- every answer here can
be given by pressing a tile -- and SDK section 3.4 is that **Escape belongs to
the shell**. Both are assertions here rather than intentions, because "we did
not handle Escape" is exactly the kind of claim that stops being true the week
somebody adds a second key handler.
"""

from __future__ import annotations

import pytest

from numbers_activity.keys import KEY_NAMES, TEN_KEY, number_for


@pytest.mark.parametrize("digit", list(range(1, 10)))
def test_a_digit_key_is_that_number(digit: int) -> None:
    assert number_for(str(digit)) == digit


@pytest.mark.parametrize("digit", list(range(1, 10)))
def test_the_keypad_says_the_same_thing(digit: int) -> None:
    assert number_for(f"KP_{digit}") == digit


def test_zero_means_ten() -> None:
    # There is no zero to answer -- both parts of a bond are at least one, and
    # you cannot subitise nothing -- so the key is free, and it is where a hand
    # already is.
    assert number_for("0") == TEN_KEY == 10
    assert number_for("KP_0") == 10


def test_escape_is_not_ours() -> None:
    assert number_for("Escape") is None


def test_backspace_is_not_ours() -> None:
    assert number_for("BackSpace") is None


@pytest.mark.parametrize(
    "name", ["Tab", "ISO_Left_Tab", "Left", "Right", "Up", "Down", "Return", "space", "a", ""]
)
def test_everything_the_focus_ring_needs_falls_through(name: str) -> None:
    assert number_for(name) is None


def test_the_table_is_the_digits_and_only_the_digits() -> None:
    assert len(KEY_NAMES) == 20
    assert set(KEY_NAMES) == {str(d) for d in range(10)} | {f"KP_{d}" for d in range(10)}


def test_every_listed_name_maps_to_a_number() -> None:
    for name in KEY_NAMES:
        assert number_for(name) in set(range(1, 11))
