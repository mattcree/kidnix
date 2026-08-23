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

from .i18n import N_, _

__all__ = [
    "AGAIN_LABEL",
    "AGAIN_SPEAK",
    "BOX_EMPTY_SPEAK",
    "BOX_FULL_SPEAK",
    "LOST_LINE",
    "MAX_NUMBER",
    "MORE_LABEL",
    "MORE_SPEAK",
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
#:
#: **A table, not a formatting rule** (ADR-0012). ``str(n)`` is not a word in
#: any language and no language builds its number words the way another does,
#: so the eleven words are eleven msgids and every sentence below is composed
#: from them with *named* placeholders a translator may reorder. They are
#: marked with :func:`~numbers_activity.i18n.N_` because this is module level:
#: the catalogue in force at import time is not the one in force when a child
#: is sitting down.
NUMBER_WORDS: tuple[str, ...] = (
    N_("zero"),
    N_("one"),
    N_("two"),
    N_("three"),
    N_("four"),
    N_("five"),
    N_("six"),
    N_("seven"),
    N_("eight"),
    N_("nine"),
    N_("ten"),
)


def number_word(number: int) -> str:
    """``4`` -> ``"four"``. The only way a number reaches the voice."""
    if not 0 <= number <= MAX_NUMBER:
        raise ValueError(f"no word for {number}")
    return _(NUMBER_WORDS[number])


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


# -- the msgids -------------------------------------------------------------
#
# Every sentence this activity can say, as a module-level constant marked with
# `N_` and translated by `_()` at the use site (ADR-0012, docs/design/i18n.md).
# Placeholders are **named**, never positional and never concatenation, so a
# translator may reorder them or fold a number into the word beside it.

#: TRANSLATORS: the question. Two words on purpose (SYNTHESIS B5).
HOW_MANY = N_("How many?")
#: TRANSLATORS: {number} is a number word -- "four", never a digit.
YES = N_("Yes, {number}.")
#: TRANSLATORS: what is said instead of "no". A method, not a verdict.
LOOK_AGAIN = N_("Let's look again, and count them.")
#: TRANSLATORS: {counted} is the count so far ("One, two, three"), {total} the
#: last number said again -- the cardinal, which is the whole point of it.
COUNTED = N_("{counted}. {total}.")
#: TRANSLATORS: {number} is a number word.
TELL = N_("There are {number}.")

#: TRANSLATORS: {shown} and {total} are number words.
BOND_PROMPT = N_("Here are {shown}. How many more make {total}?")
#: TRANSLATORS: {total} is a number word.
BOND_ASK_AGAIN = N_("Count the empty boxes. How many more make {total}?")
#: TRANSLATORS: the sentence the whole second half of the activity produces.
#: All three are number words: "Three and two make five."
BOND_SENTENCE = N_("{shown} and {missing} make {total}.")

END = N_("That is all of them. There is a card of it to show a grown-up.")
GROWNUP_TITLE = N_("Your turn, grown-up")
#: TRANSLATORS: the co-use card, written for an adult in an adult's register.
#: {number} and {total} are number words.
GROWNUP_BODY = N_(
    "Show {number} fingers and ask how many -- quickly, before they can "
    "count. Then hide a couple behind your back and ask how many more would "
    "make {total}. Fingers beat a screen for this, and doing it away from the "
    "computer is what makes it stick."
)

#: TRANSLATORS: the Journal card when nothing was put together.
CARD_NOTHING = N_("Today: seeing how many.")
#: TRANSLATORS: the Journal card. {sentence} is a bond sentence with its full
#: stop removed -- "three and two make five".
CARD_ONE = N_("Today: {sentence}")
#: TRANSLATORS: {count} is a number word: "Today: three and two make five, and
#: two more".
CARD_MORE = N_("Today: {sentence}, and {count} more")

# -- what the window's own controls say --------------------------------------
#
# They live here rather than in `activity.py` for the reason at the top of this
# module: a translator reads one file, and a headless test can check every word
# a child meets without a display.

#: What the child hears when the save failed (SYNTHESIS C3).
LOST_LINE = N_("I could not keep that one. Ask a grown-up.")
#: The button that brings the picture back. Not a hint and not a penalty: a
#: child who wants another look is doing the right thing.
AGAIN_LABEL = N_("Look")
AGAIN_SPEAK = N_("Show me the dots again.")
#: The button at the end of the loop. Pressed, never automatic (D6: no autoplay).
MORE_LABEL = N_("Some more")
MORE_SPEAK = N_("Some more numbers.")
#: The two faces of a ten-frame box, which is a control a child presses twice.
BOX_EMPTY_SPEAK = N_("Put a counter in.")
BOX_FULL_SPEAK = N_("Take it out again.")


# -- how many? ---------------------------------------------------------------


def how_many_prompt() -> str:
    """The question. Two words, imperative, and the same two words every time.

    SYNTHESIS B5: instructions audio-first, at most two sentences and twelve
    words. This one is two words because a child who has heard it four times
    should not have to listen to it a fifth.
    """
    return _(HOW_MANY)


def yes_line(number: int) -> str:
    """``4`` -> ``"Yes, four."`` Confirmation, and the number said out loud.

    "Yes" is information -- it answers the question the child just answered --
    and it is the whole of the celebration. There is deliberately no adjective.
    """
    return _(YES).format(number=number_word(number))


def look_again() -> str:
    """What is said instead of "no". The next thing to do, not a verdict."""
    return _(LOOK_AGAIN)


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
    # The comma is not in the catalogue: it is a list separator, and every
    # language this is likely to reach separates a spoken count the same way.
    # What *is* translatable is the sentence the two halves make (`COUNTED`).
    counted = ", ".join(number_word(n) for n in range(1, number + 1))
    return _(COUNTED).format(counted=counted.capitalize(), total=number_word(number).capitalize())


def tell_line(number: int) -> str:
    """After the second try: the answer, plainly, and then we move on.

    Nobody is asked a third time. Two goes and then being told is the shape of
    a grown-up sitting next to you; a fourth attempt is the shape of a test.
    """
    return _(TELL).format(number=number_word(number))


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
    return _(BOND_PROMPT).format(shown=number_word(shown), total=number_word(total))


def bond_ask_again(total: int) -> str:
    """The second go at a bond. Again: the method, not a verdict."""
    return _(BOND_ASK_AGAIN).format(total=number_word(total))


def bond_sentence(shown: int, missing: int, total: int) -> str:
    """``(3, 2, 5)`` -> ``"Three and two make five."``

    The sentence the whole second half of the activity exists to produce, said
    out loud every time a bond is completed and printed on the Journal card.
    "Make" rather than "equals" and rather than "is": the ELG's word for this is
    *composition*, and five-year-olds meet it as two amounts being put together
    long before they meet an equals sign.
    """
    return _(BOND_SENTENCE).format(
        shown=number_word(shown).capitalize(),
        missing=number_word(missing),
        total=number_word(total),
    )


# -- the ends ----------------------------------------------------------------


def end_line() -> str:
    """The end of the loop. Not a congratulation and not a cliffhanger."""
    return _(END)


def grownup_title() -> str:
    """The only part of the grown-up card that is read aloud (SDK section 7).

    The child is told whose turn it is. What the adult is being asked to do is
    on the card, for the adult, and is not read to a five-year-old.
    """
    return _(GROWNUP_TITLE)


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
    return _(GROWNUP_BODY).format(number=number_word(number), total=number_word(total))


def card_caption(bonds: tuple[tuple[int, int, int], ...] | list[tuple[int, int, int]]) -> str:
    """The one line on the Journal card. ``(3, 2, 5)`` -> ``"Today: three and two make five"``.

    Written for the grown-up reading My Things over the child's shoulder, which
    is why it names what was practised rather than how it went. There is no
    "got four right" here and there is no version of this function that could
    produce one -- it never sees an outcome.

    The known limitation of docs/design/i18n.md section 2.3 applies to the
    lower-casing below: it is English's rule for a sentence folded into a
    bigger one, and a language that capitalises nouns will want the whole line
    rewritten in the catalogue instead. ``CARD_ONE`` and ``CARD_MORE`` are two
    msgids so that a translator can do exactly that.
    """
    bonds = list(bonds)
    if not bonds:
        return _(CARD_NOTHING)
    first = bond_sentence(*bonds[0])
    lowered = first[0].lower() + first[1:]
    rest = len(bonds) - 1
    if rest == 0:
        return _(CARD_ONE).format(sentence=lowered[:-1])
    return _(CARD_MORE).format(sentence=lowered[:-1], count=number_word(rest))
