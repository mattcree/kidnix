"""Every spoken line, held to the rules the whole product is held to.

No digits, no reward vocabulary, no promise about the reply, and short enough
for a five-year-old to hold. These assertions run over *all* the lines rather
than a chosen few, so a line added later is checked by existing tests.
"""

from __future__ import annotations

from letters_to_family import words

#: SUITE section 5 / SYNTHESIS E1. The reward is the letter.
REWARD_WORDS = (
    "well done",
    "brilliant",
    "amazing",
    "star",
    "point",
    "score",
    "level",
    "streak",
    "badge",
    "coin",
    "prize",
    "winner",
)

#: 05 section 3 says the reply must come back; nothing on this machine knows
#: *when*, so nothing on this machine may say when. Checked on the lines that
#: are *about the letter going and coming back* -- "today" is legitimate in
#: "tell them one thing that happened today", which is about the child's day.
TIMING_WORDS = ("soon", "tomorrow", "tonight", "in a minute", "shortly", "right away", "next week")


def test_no_line_contains_a_digit():
    """01 #19 / 03 #32: no digits where a child can see or hear them."""
    for line in words.all_lines():
        assert not any(character.isdigit() for character in line), line


def test_no_line_uses_reward_vocabulary():
    for line in words.all_lines():
        lowered = line.lower()
        for banned in REWARD_WORDS:
            assert banned not in lowered, f"{banned!r} in {line!r}"


def test_nothing_promises_when_a_reply_will_come():
    about_the_post = [
        words.posted_line("Grandad"),
        words.reply_line("Grandad"),
        words.SHELF_TITLE,
        words.SHELF_EMPTY,
        words.GROWNUP_NO_FAMILY_BODY,
    ]
    for line in about_the_post:
        lowered = line.lower()
        for banned in TIMING_WORDS:
            assert banned not in lowered, f"{banned!r} in {line!r}"


def test_no_line_anywhere_promises_a_reply_is_coming_soon():
    for line in words.all_lines():
        assert "soon" not in line.lower(), line
        assert "tomorrow" not in line.lower(), line


def test_the_posted_line_names_the_audience_and_the_grown_up():
    line = words.posted_line("Grandad")
    assert "Grandad" in line
    assert "grown-up" in line
    assert line.startswith("Posted!")


def test_the_posted_line_does_not_claim_anything_was_sent():
    """SYNTHESIS H1: nothing leaves the machine by itself, so nothing says it
    has. "will send" is a future a grown-up controls; "sent" would be a lie."""
    line = words.posted_line("Grandad").lower()
    assert " sent" not in line
    assert "will send" in line


def test_the_child_facing_prompts_are_one_short_sentence():
    """B5: audio-first, at most two sentences, at most about twelve words."""
    for line in (words.WHO_FOR, words.TELL_THEM, words.CHOOSE_PICTURE, words.PICK_A_COLOUR):
        assert line.count(".") + line.count("?") <= 1
        assert len(line.split()) <= 12, line


def test_the_scaffold_is_the_one_the_evidence_names():
    """05 section 3, word for word: "tell them one thing that happened today"."""
    assert words.TELL_THEM == "Tell them one thing that happened today."


def test_the_scaffold_is_a_prompt_and_not_a_template():
    """Nothing is filled in for the child: no sentence starter, no blank to
    complete, no "Dear ______"."""
    assert "Dear" not in words.TELL_THEM
    assert "_" not in words.TELL_THEM
    assert "..." not in words.TELL_THEM


def test_the_no_family_card_tells_a_grown_up_exactly_where_to_go():
    body = words.GROWNUP_NO_FAMILY_BODY
    assert "parent panel" in body.lower()
    assert "Family tab" in body


def test_the_no_family_line_for_the_child_says_what_to_do_next():
    assert "grown-up" in words.NOBODY_YET
    assert words.NOBODY_YET.endswith("Ask a grown-up.")


def test_the_grown_up_writing_card_forbids_tidying_the_spelling():
    body = words.GROWNUP_WRITE_BODY.lower()
    assert "do not tidy the spelling" in body
    assert "invented spelling" in body


def test_the_shelf_button_never_counts_the_letters():
    """A count is a digit on a pre-reader's screen and the shape of a
    notification badge, which D6 says this product does not have."""
    assert words.shelf_button(1) == words.shelf_button(9) == words.SHELF_TITLE
    assert words.shelf_button(0) == words.SHELF_EMPTY
    for count in (0, 1, 40):
        assert not any(c.isdigit() for c in words.shelf_button(count))


def test_every_screen_after_the_first_names_the_recipient():
    assert "Grandad" in words.your_letter_for("Grandad")
    assert "Grandad" in words.posted_line("Grandad")
    assert "Grandad" in words.reply_line("Grandad")


def test_nothing_asks_the_child_a_question_they_have_to_read():
    """C2/D6: no modal confirmations, no "are you sure?", no exit friction."""
    for line in words.all_lines():
        lowered = line.lower()
        assert "are you sure" not in lowered
        assert "do you want to" not in lowered
