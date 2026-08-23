"""Everything the activity says, in one place, so that what it says can be read.

Two rules run through all of it, and both are tested rather than intended.

**No digits in anything spoken.** The voice says "four", never "4". This is
partly the SDK's rule (``docs/design/activity-sdk.md`` section 12 -- no digits
where a child can hear them) and partly speech-dispatcher's: a numeral is read
by whatever expansion the synthesiser happens to have, and "5" can come out as
"five" on one voice and something else on another. The numeral has exactly one
job in this activity -- it is **printed on the tile**, where the ELG wants a
child to meet it -- and :func:`numeral` is the one function that produces one.

**No score, ever, in any form.** Not a count of right answers, not "three out
of four", not "well done", not a star. SYNTHESIS E1: the reward is the artefact
and specific, descriptive, *informational* feedback. Kluger & DeNisi's 607
effect sizes are the reason to care -- feedback averaged d = .41 but **more
than a third of interventions made performance worse**, and the harmful ones
were the ones that pointed at the person rather than the task. So the entire
vocabulary of this activity is task information: *what the number was*, *how
you would find out*, *which two numbers make five*. "Yes, four" is a fact.
"Well done!" is a verdict on a child, and there is not one in here.

A wrong answer is never called wrong. It is answered with the thing that would
have produced the right one: the picture comes back, and the dots get counted.
Guidance beats discovery hardest for the youngest children (d = 0.5-0.7,
05 section 2f), and 05 section 4 #9 says in as many words not to design for
struggle at five.
"""

from __future__ import annotations

__all__ = [
    "MAX_NUMBER",
    "NUMBER_WORDS",
    "bond_ask_again",
    "bond_prompt",
    "bond_sentence",
    "card_caption",
    "count_aloud",
    "end_line",
    "grownup_body",
    "grownup_title",
    "how_many_prompt",
    "look_again",
    "number_word",
    "numeral",
    "tell_line",
    "tile_speech",
    "yes_line",
]

#: The largest number this activity has a word for. The ELG stops at ten and so
#: does everything here; there is no eleven to say because there is no eleven to
#: show.
MAX_NUMBER = 10

#: Index is the number. ``NUMBER_WORDS[0]`` exists because a frame can be empty,
#: not because zero is ever an answer -- see :mod:`numbers_activity.items`,
#: where a bond's two parts are both at least one.
NUMBER_WORDS: tuple[str, ...] = (
    "zero",
    "one",
    "two",
    "three",
    "four",
    "five",
    "six",
    "seven",
    "eight",
    "nine",
    "ten",
)


def number_word(number: int) -> str:
    """``4`` -> ``"four"``. The only way a number reaches the voice."""
    if not 0 <= number <= MAX_NUMBER:
        raise ValueError(f"no word for {number}")
    return NUMBER_WORDS[number]


def numeral(number: int) -> str:
    """``4`` -> ``"4"``. **Printed, never spoken.**

    The one place a digit is allowed. The EYFS Number ELG is about a child's
    "deep understanding of numbers to 10" meeting the written symbol, and
    symbolic comparison is the half of the literature that actually predicts
    later maths (r = .30 against .24 for non-symbolic; Schneider et al.). So the
    numeral is on the tile, at full size, with the quantity underneath it -- and
    it is not in any sentence, which is what the test asserts.
    """
    if not 0 <= number <= MAX_NUMBER:
        raise ValueError(f"no numeral for {number}")
    return str(number)


# -- how many? ---------------------------------------------------------------


def how_many_prompt() -> str:
    """The question. Two words, imperative, and the same two words every time.

    SYNTHESIS B5: instructions audio-first, at most two sentences and twelve
    words. This one is two words because a child who has heard it four times
    should not have to listen to it a fifth.
    """
    return "How many?"


def yes_line(number: int) -> str:
    """``4`` -> ``"Yes, four."`` Confirmation, and the number said out loud.

    "Yes" is information -- it answers the question the child just answered --
    and it is the whole of the celebration. There is deliberately no adjective.
    """
    return f"Yes, {number_word(number)}."


def look_again() -> str:
    """What is said instead of "no". The next thing to do, not a verdict."""
    return "Let's look again, and count them."


def count_aloud(number: int) -> str:
    """``4`` -> ``"One, two, three, four. Four."``

    One-to-one counting, and then the *cardinal* -- the last number said is how
    many there are. That final repetition is not padding: the cardinality
    principle is the thing a four-year-old is still assembling, and a count that
    stops at "four" without saying "four" is the count of an adult who already
    knows.
    """
    if number < 1:
        raise ValueError("there is nothing to count")
    counted = ", ".join(number_word(n) for n in range(1, number + 1))
    return f"{counted.capitalize()}. {number_word(number).capitalize()}."


def tell_line(number: int) -> str:
    """After the second try: the answer, plainly, and then we move on.

    Nobody is asked a third time. Two goes and then being told is the shape of
    a grown-up sitting next to you; a fourth attempt is the shape of a test.
    """
    return f"There are {number_word(number)}."


def tile_speech(number: int) -> str:
    """What an answer tile says when it is hovered, focused or pressed.

    Just the word. B4 wants icon + label + audio on every control, and for this
    control the icon is the dot pattern, the label is the numeral, and the audio
    is the name of the number -- which is also, for a child learning the
    numerals, the entire lesson the tile is teaching.
    """
    return number_word(number).capitalize()


# -- make five, make ten -----------------------------------------------------


def bond_prompt(shown: int, total: int) -> str:
    """``(3, 5)`` -> ``"Here are three. How many more make five?"``"""
    return f"Here are {number_word(shown)}. How many more make {number_word(total)}?"


def bond_ask_again(total: int) -> str:
    """The second go at a bond. Again: the method, not a verdict."""
    return f"Count the empty boxes. How many more make {number_word(total)}?"


def bond_sentence(shown: int, missing: int, total: int) -> str:
    """``(3, 2, 5)`` -> ``"Three and two make five."``

    The sentence the whole second half of the activity exists to produce, said
    out loud every time a bond is completed and printed on the Journal card.
    "Make" rather than "equals" and rather than "is": the ELG's word for this is
    *composition*, and five-year-olds meet it as two amounts being put together
    long before they meet an equals sign.
    """
    return (
        f"{number_word(shown).capitalize()} and {number_word(missing)} "
        f"make {number_word(total)}."
    )


# -- the ends ----------------------------------------------------------------


def end_line() -> str:
    """The end of the loop. Not a congratulation and not a cliffhanger."""
    return "That is all of them. There is a card of it to show a grown-up."


def grownup_title() -> str:
    """The only part of the grown-up card that is read aloud (SDK section 7).

    The child is told whose turn it is. What the adult is being asked to do is
    on the card, for the adult, and is not read to a five-year-old.
    """
    return "Your turn, grown-up"


def grownup_body(number: int, total: int) -> str:
    """The co-use card. Written for an adult, in an adult's register.

    Why there is one at all: the single clearest moderator in this literature is
    whether an adult is involved. GraphoGame's meta-analysis is g = -0.02
    overall and **0.48** with high adult interaction; the EEF's onebillion trial
    found pupils did better where the supervising adult saw their role as
    teaching rather than supervising. And Bedtime Math's real finding -- once
    the subgroup arithmetic is set aside -- is that *a structured maths
    conversation between a parent and a child* moved the outcome. This card is
    that prompt, and it asks for the thing a screen cannot do: fingers.
    """
    return (
        f"Show {number_word(number)} fingers and ask how many -- quickly, before "
        f"they can count. Then hide a couple behind your back and ask how many "
        f"more would make {number_word(total)}. Fingers beat a screen for this, "
        f"and doing it away from the computer is what makes it stick."
    )


def card_caption(bonds: tuple[tuple[int, int, int], ...] | list[tuple[int, int, int]]) -> str:
    """The one line on the Journal card. ``(3, 2, 5)`` -> ``"Today: three and two make five"``.

    Written for the grown-up reading My Things over the child's shoulder, which
    is why it names what was practised rather than how it went. There is no
    "got four right" here and there is no version of this function that could
    produce one -- it never sees an outcome.
    """
    bonds = list(bonds)
    if not bonds:
        return "Today: seeing how many."
    first = bond_sentence(*bonds[0])
    lowered = first[0].lower() + first[1:]
    rest = len(bonds) - 1
    if rest == 0:
        return f"Today: {lowered[:-1]}"
    return f"Today: {lowered[:-1]}, and {number_word(rest)} more"
