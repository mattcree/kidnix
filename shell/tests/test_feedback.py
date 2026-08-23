"""E1's one line of descriptive feedback (panel ruling, 2026-08-23; forum #30, #52).

"You made three things today" is a count. "You drew two pictures and used five
colours" is the machine having noticed. The rules the line follows are in
:mod:`kidnix_shell.feedback`; this holds them.
"""

from __future__ import annotations

from kidnix_shell.feedback import (
    MANY_ABOVE,
    MadeSummary,
    count_phrase,
    descriptive_line,
    number_word,
    words_for,
)


def test_nothing_made_says_nothing() -> None:
    """No consolation prize, and no sentence about a thing that did not happen."""
    assert descriptive_line(MadeSummary(count=0)) == ""


def test_the_line_names_what_was_done_and_how_many() -> None:
    line = descriptive_line(
        MadeSummary(count=2, verb="drew", singular="picture", plural="pictures")
    )
    assert line == "You drew two pictures."


def test_one_of_something_is_singular() -> None:
    line = descriptive_line(
        MadeSummary(count=1, verb="drew", singular="picture", plural="pictures")
    )
    assert line == "You drew one picture."


def test_the_colours_are_the_specific_half() -> None:
    """SYNTHESIS E1's own example sentence, at last."""
    line = descriptive_line(
        MadeSummary(count=2, verb="drew", singular="picture", plural="pictures", colours=5)
    )
    assert line == "You drew two pictures and used five colours."


def test_an_awkward_number_becomes_lots() -> None:
    """No digits, and no "eleven colours" either (01 #19, 03 #32)."""
    line = descriptive_line(
        MadeSummary(count=2, verb="drew", singular="picture", plural="pictures", colours=11)
    )
    assert line == "You drew two pictures and used lots of colours."
    assert number_word(MANY_ABOVE + 1) == "lots of"


def test_one_colour_is_not_worth_saying() -> None:
    line = descriptive_line(
        MadeSummary(count=1, verb="drew", singular="picture", plural="pictures", colours=1)
    )
    assert line == "You drew one picture."


def test_no_colours_counted_drops_the_clause_rather_than_guessing() -> None:
    line = descriptive_line(
        MadeSummary(count=3, verb="made", singular="thing", plural="things", colours=None)
    )
    assert line == "You made three things."


def test_the_line_never_evaluates() -> None:
    """Descriptive, not evaluative -- that is the whole of why it is here."""
    line = descriptive_line(
        MadeSummary(count=3, verb="drew", singular="picture", plural="pictures", colours=4)
    )
    for praise in ("well done", "great", "good", "brilliant", "best", "!"):
        assert praise not in line.lower()


def test_there_are_no_digits_in_any_of_it() -> None:
    for count in range(1, 6):
        line = descriptive_line(
            MadeSummary(count=count, verb="made", singular="thing", plural="things", colours=count)
        )
        assert not any(character.isdigit() for character in line)


# --- which words -------------------------------------------------------


def test_one_activity_gets_its_own_verb() -> None:
    assert words_for(["tuxpaint"], ["make"]) == ("drew", "picture", "pictures")


def test_one_category_gets_the_category_verb() -> None:
    assert words_for(["a", "b"], ["learn", "learn"])[0] == "found out about"


def test_a_mixed_session_is_described_as_a_mixed_session() -> None:
    """Half the sitting described as if it were all of it would not be true."""
    assert words_for(["tuxpaint", "blinken"], ["make", "play"]) == ("made", "thing", "things")


def test_the_count_phrase_has_no_numerals_under_six() -> None:
    assert count_phrase(0) == "nothing"
    assert count_phrase(1) == "one thing"
    assert count_phrase(3) == "three things"
    assert count_phrase(12) == "12 things"
