"""Numbers and times of day, as words a five-year-old owns (i18n foundation).

**The child never sees a digit** (01 #19, 03 #32) and never hears a clock, so
every count and every time in the shell is a *word*. Once those words have to
exist in more than one language, three things stop being free:

* ``str(count)`` is not a word in any language, and ``WORDS[count]`` is a
  lookup into a table that has to be translatable;
* ``f"{word} things"`` is English grammar wearing an f-string. Welsh has
  **six** plural forms and Polish has three; the noun after "two" is not the
  noun after "five" in either. Counted nouns therefore go through
  :func:`kidnix_shell.i18n.ngettext`, which asks the catalogue's own
  ``Plural-Forms`` rule and not our assumptions;
* concatenation fixes word order. Every sentence built here uses **named**
  placeholders (``"{count} {noun}"``), so a translator may reorder them.

Pure, tiny, and the msgids are the en_GB strings, so with no catalogue
installed every function returns exactly what the shell said before this module
existed.
"""

from __future__ import annotations

from .i18n import N_, _

#: 0 to 20, as words. Zero is "nothing" rather than "zero": the shell only ever
#: counts things a child made, and "you made zero things" is not a sentence
#: anybody says to a five-year-old.
#:
#: Marked with :func:`~kidnix_shell.i18n.N_` (extract now, translate later)
#: because this is module level: the catalogue in force at *import* time is not
#: the one in force when a child is sitting down.
NUMBER_WORDS: tuple[str, ...] = (
    N_("nothing"),
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
    N_("eleven"),
    N_("twelve"),
    N_("thirteen"),
    N_("fourteen"),
    N_("fifteen"),
    N_("sixteen"),
    N_("seventeen"),
    N_("eighteen"),
    N_("nineteen"),
    N_("twenty"),
)

#: Past the point where a number is useful to a child. "Eleven colours" is a
#: fact nobody needs; "lots of colours" is what an adult would have said.
MANY_WORD = N_("lots of")

#: The largest number this module will say out loud unless a caller raises it.
MAX_NUMBER = len(NUMBER_WORDS) - 1


def number_word(count: int, *, many_above: int | None = None) -> str:
    """``2`` -> ``"two"``; past ``many_above`` (or 20) -> ``"lots of"``.

    Total: any integer, including a negative one from arithmetic that went
    wrong, lands on a word rather than on a digit or an exception.
    """
    ceiling = MAX_NUMBER if many_above is None else many_above
    if count < 0 or count > ceiling or count > MAX_NUMBER:
        return _(MANY_WORD)
    return _(NUMBER_WORDS[count])


def counted(count: int, singular: str, plural: str, *, many_above: int | None = None) -> str:
    """``2, "picture", "pictures"`` -> ``"two pictures"``.

    ``singular`` and ``plural`` are **msgids** (mark them with
    :func:`~kidnix_shell.i18n.N_` where they are declared). The form actually
    used is chosen by the catalogue's plural rule, so a Welsh catalogue may
    pick one of six and a Polish one of three; the number word in front of it
    comes from :func:`number_word`.
    """
    noun = _ngettext(singular, plural, count)
    return _("{count} {noun}").format(count=number_word(count, many_above=many_above), noun=noun)


def _ngettext(singular: str, plural: str, n: int) -> str:
    # Imported through a thin wrapper rather than at module scope so that a
    # test which reinstalls the catalogue does not have to reimport this
    # module. (`_` and `N_` are safe at module scope: `_` resolves the
    # catalogue at call time and `N_` never resolves one at all.)
    from .i18n import ngettext

    return ngettext(singular, plural, n)


# --- times of day ---------------------------------------------------------
#
# The Journal's vocabulary (:mod:`kidnix_shell.journal`), kept here because it
# is the other half of "no digits, ever": a card says *when* in the same four
# words the day headings use, and a translator wants all of them on one page.

MORNING, AFTERNOON, EVENING, NIGHT = "morning", "afternoon", "evening", "night"

#: Today. ``NIGHT`` is "tonight" and not "this night", because it is not.
THIS_DAY_PART: dict[str, str] = {
    MORNING: N_("this morning"),
    AFTERNOON: N_("this afternoon"),
    EVENING: N_("this evening"),
    NIGHT: N_("tonight"),
}

#: The day before.
YESTERDAY_DAY_PART: dict[str, str] = {
    MORNING: N_("yesterday morning"),
    AFTERNOON: N_("yesterday afternoon"),
    EVENING: N_("yesterday evening"),
    NIGHT: N_("last night"),
}

#: Anything older. The same word the Journal's own day heading uses.
LONG_AGO = N_("before")


def this_day_part(part: str) -> str:
    """``"morning"`` -> ``"this morning"``, translated."""
    return _(THIS_DAY_PART.get(part, THIS_DAY_PART[MORNING]))


def yesterday_day_part(part: str) -> str:
    """``"morning"`` -> ``"yesterday morning"``, translated."""
    return _(YESTERDAY_DAY_PART.get(part, YESTERDAY_DAY_PART[MORNING]))


def long_ago() -> str:
    """``"before"``, translated."""
    return _(LONG_AGO)
