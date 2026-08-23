"""Everything the activity says, checked against the two rules it is held to.

**No digit ever reaches the ear.** The voice says "four". The tile prints "4".
:func:`~numbers_activity.words.numeral` is the only function allowed to produce
a digit and it is the only one exempted here.

**Nothing that could be read as a score, a mark or a verdict on a child.**
SYNTHESIS E1 and 05 section 4 #3: no points, stars, badges, streaks or levels,
and no praise adjective either. Kluger & DeNisi's 607 effect sizes are why --
feedback that points at the person rather than the task made performance *worse*
in more than a third of interventions. The ban list below is checked against
every sentence this activity can produce, and against the literal strings in the
window module as well, because a "Well done!" added to a button label would be
just as much of one.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

from numbers_activity import words

#: Words and phrases that must not appear in anything a child hears or reads.
#: Some of these are obvious; ``correct`` and ``wrong`` are here because a
#: program that says either has started marking, and this one does not mark.
BANNED = (
    "well done",
    "good boy",
    "good girl",
    "clever",
    "score",
    "scored",
    "point",
    "points",
    "star",
    "stars",
    "streak",
    "badge",
    "level",
    "prize",
    "reward",
    "winner",
    "win",
    "lost",
    "wrong",
    "correct",
    "incorrect",
    "out of",
    "%",
    "oops",
    "try harder",
)


def _every_spoken_line() -> list[str]:
    """Every sentence the activity can say, over the whole domain of numbers."""
    lines = [
        words.how_many_prompt(),
        words.look_again(),
        words.end_line(),
        words.grownup_title(),
    ]
    for number in range(1, words.MAX_NUMBER + 1):
        lines.append(words.yes_line(number))
        lines.append(words.count_aloud(number))
        lines.append(words.tell_line(number))
        lines.append(words.tile_speech(number))
        lines.append(words.number_word(number))
    for total in (5, 10):
        lines.append(words.bond_ask_again(total))
        for shown in range(1, total):
            lines.append(words.bond_prompt(shown, total))
            lines.append(words.bond_sentence(shown, total - shown, total))
    return lines


def _contains_banned(line: str) -> list[str]:
    lowered = line.lower()
    return [
        banned
        for banned in BANNED
        if re.search(rf"(?<![a-z]){re.escape(banned)}(?![a-z])", lowered)
    ]


# -- the numbers themselves --------------------------------------------------


@pytest.mark.parametrize("number", list(range(0, 11)))
def test_every_number_to_ten_has_a_word(number: int) -> None:
    assert words.number_word(number).isalpha()


def test_there_is_no_word_for_eleven() -> None:
    with pytest.raises(ValueError):
        words.number_word(11)


def test_the_numeral_is_the_digit() -> None:
    assert words.numeral(4) == "4"
    assert words.numeral(10) == "10"


# -- no digits in the ear ----------------------------------------------------


def test_nothing_spoken_contains_a_digit() -> None:
    for line in _every_spoken_line():
        assert not re.search(r"\d", line), f"a digit reached the voice: {line!r}"


def test_the_grown_ups_card_has_no_digits_either() -> None:
    # It is not read aloud, but it is read by a person, and a card that says
    # "show 4 fingers" while the voice says "four" is two conventions.
    assert not re.search(r"\d", words.grownup_body(4, 5))


# -- no scores, no marks, no verdicts ----------------------------------------


def test_nothing_spoken_could_be_read_as_a_score() -> None:
    for line in _every_spoken_line():
        assert _contains_banned(line) == [], f"{line!r} reads as a mark"


def test_the_grown_ups_card_carries_no_marking_language() -> None:
    assert _contains_banned(words.grownup_body(4, 5)) == []


def test_nothing_spoken_says_no_or_wrong() -> None:
    for line in _every_spoken_line():
        assert not re.match(r"^(no|nope)\b", line.lower())


def test_the_reply_to_a_wrong_answer_is_a_method_not_a_verdict() -> None:
    assert words.look_again() == "Let's look again, and count them."
    assert "count" in words.bond_ask_again(5).lower()


# -- the actual sentences ----------------------------------------------------


def test_yes_says_the_number_back() -> None:
    assert words.yes_line(4) == "Yes, four."


def test_counting_aloud_ends_on_the_cardinal() -> None:
    assert words.count_aloud(4) == "One, two, three, four. Four."
    assert words.count_aloud(1) == "One. One."


def test_counting_nothing_is_not_a_thing() -> None:
    with pytest.raises(ValueError):
        words.count_aloud(0)


def test_the_bond_sentence_is_the_sentence() -> None:
    assert words.bond_sentence(3, 2, 5) == "Three and two make five."
    assert words.bond_sentence(5, 5, 10) == "Five and five make ten."


def test_the_bond_prompt_says_what_is_there_and_what_is_wanted() -> None:
    assert words.bond_prompt(3, 5) == "Here are three. How many more make five?"


def test_the_prompts_are_short_enough_to_hear() -> None:
    # SYNTHESIS B5: at most two sentences and twelve words.
    for line in (words.how_many_prompt(), words.bond_prompt(3, 5), words.bond_prompt(9, 10)):
        assert len(line.split()) <= 12
        assert line.count(".") + line.count("?") <= 2


# -- the Journal caption -----------------------------------------------------


def test_the_caption_names_the_bond() -> None:
    assert words.card_caption([(3, 2, 5)]) == "Today: three and two make five"


def test_the_caption_counts_the_others_in_words() -> None:
    caption = words.card_caption([(3, 2, 5), (1, 4, 5), (5, 5, 10)])
    assert caption == "Today: three and two make five, and two more"
    assert not re.search(r"\d", caption)


def test_a_session_with_no_bonds_still_has_a_caption() -> None:
    assert words.card_caption([]) == "Today: seeing how many."


def test_no_caption_could_be_read_as_a_mark() -> None:
    for bonds in ([], [(1, 4, 5)], [(1, 4, 5), (2, 3, 5)], [(5, 5, 10)] * 4):
        assert _contains_banned(words.card_caption(bonds)) == []


# -- and the same rules over the window module -------------------------------


def _window_strings() -> list[str]:
    """Child-facing literals in ``activity.py``: labels, and everything spoken.

    Read out of the syntax tree rather than by grepping the file, so that a
    docstring explaining *why there is no score* does not trip a test looking
    for the word "score" -- and so that a new ``speak_text=`` on a new control
    is caught the day it is added, with no list to remember to update.
    """
    source = Path(words.__file__).with_name("activity.py").read_text()
    tree = ast.parse(source)
    found: list[str] = []
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.keyword)
            and node.arg in {"speak_text", "label", "title"}
            and isinstance(node.value, ast.Constant)
            and isinstance(node.value.value, str)
        ):
            found.append(node.value.value)
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if (
                    isinstance(target, ast.Name)
                    and target.id.endswith(("_LINE", "_LABEL"))
                    and isinstance(node.value, ast.Constant)
                    and isinstance(node.value.value, str)
                ):
                    found.append(node.value.value)
    return found


def test_the_window_has_child_facing_strings_to_check() -> None:
    # If this ever finds nothing, the test below is passing vacuously.
    assert len(_window_strings()) >= 5


def test_no_label_or_spoken_string_in_the_window_reads_as_a_reward() -> None:
    for line in _window_strings():
        assert _contains_banned(line) == [], f"{line!r} reads as a reward"


def test_no_label_or_spoken_string_in_the_window_contains_a_digit() -> None:
    for line in _window_strings():
        assert not re.search(r"\d", line), f"a digit reached a control: {line!r}"
