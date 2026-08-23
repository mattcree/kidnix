"""Every word a child hears or reads in this activity, and one rule about them.

Two reasons this is its own module rather than a block at the top of
:mod:`sounds_and_words.activity`:

1. **``activity.py`` imports GTK.** The strings are the part of the interface a
   test should be able to check with no display, and the rule below is a
   *guarantee*, not a detail -- so it lives with the corpus and the ceiling, in
   the half that is provable headless (``docs/design/activity-sdk.md`` §2).
2. **``xgettext`` reads source, not imports.** Marking the msgids here puts them
   in one file a translator can read top to bottom, instead of scattered
   through 800 lines of widget wiring.

The rule
--------

**The Find it prompt never contains the grapheme it is asking for.** The task
is *match a sound to a letter*; a prompt that prints the letter is the answer
key set above the question, which is exactly what the checkpoint-2 audit found
on screen (``docs/design/cci-compliance-audit-2026-08-23-checkpoint-2.md`` §3,
"the visible prompt prints the answer" -- *"Find the one that says k."* over a
board with ``k`` on it). So the sentence stops at an ellipsis and the sound
arrives as its **own utterance** a beat later: a recording where one exists
(:mod:`sounds_and_words.clips`), the spelled label where one does not.

What the caption strip then shows is the instruction without the answer, and
then the sound's label on its own -- which is the deaf child's accommodation
rather than everybody's answer key. :func:`names_a_grapheme` is the rule as
code: :meth:`sounds_and_words.activity.SoundsAndWords.find_it_line` runs the
prompt through it before showing it, because ``data/parent_text.toml`` is copy
a grown-up may edit and a translator will certainly rewrite, and neither of
them should be able to put the answer back.

Where the words actually come from
----------------------------------

``data/parent_text.toml`` ``[child]``, at runtime, because
``tests/test_parent_text.py`` greps the whole corpus against the no-score
blacklist and a line written only in Python would be outside that net.
:data:`CHILD_LINES` holds the same words as msgids so the extractor can see
them, and ``tests/test_i18n.py`` fails if the two ever drift apart.
"""

from __future__ import annotations

import re
from collections.abc import Iterable

from .i18n import N_

__all__ = [
    "BLEND_IT",
    "CHILD_LINES",
    "DONE",
    "FIND_IT",
    "GROWN_UP_INVITE",
    "GROWN_UP_PROMPT",
    "GROWN_UP_READ",
    "GROWN_UP_TITLE",
    "LISTEN_LABEL",
    "LISTEN_SPEAK",
    "NEXT_LABEL",
    "NEXT_SPEAK",
    "NOTHING_DUE",
    "NO_CORRECTION",
    "PAGE_BACK_LABEL",
    "PAGE_BACK_SPEAK",
    "PAGE_NEXT_LABEL",
    "PAGE_NEXT_SPEAK",
    "PICK_A_BOOK",
    "PUSH_LABEL",
    "PUSH_SPEAK",
    "READ_IT",
    "SAY_IT_ALOUD",
    "SCREEN_PROMPTS",
    "SHELF_BACK_SPEAK",
    "SHELF_NEXT_SPEAK",
    "SHELF_TILE_SPEAK",
    "names_a_grapheme",
    "tokens",
]

# ADR-0012 / docs/design/i18n.md: `N_` marks a msgid at module level and the
# *use site* calls `_()` on it, once a child's language is known. Never `_()`
# here -- a module-level translation freezes whichever language happened to be
# installed when Python first imported the file.

#: **The Find it instruction, and it does not name the grapheme.** The ellipsis
#: is what stands where the answer used to be, on screen and in the caption.
FIND_IT = N_("Find the one that says…")
#: Blend it. Says what to do with the word, and does not say the word.
BLEND_IT = N_("Say the sounds, then push them together.")
SAY_IT_ALOUD = N_("Now say it out loud.")
DONE = N_("That's the lot for today.")
NOTHING_DUE = N_("Nothing to practise today. Go and find a book.")
NO_CORRECTION = N_("Have another go.")
#: The end of a book. Not "well done" and not a count of anything: what happens
#: next is a person, which is the only part of this with an effect size on it
#: (McTigue: 0.48 with an adult, -0.02 without).
READ_IT = N_("Read it to someone!")
#: The shelf. It says what to do and names no book, because the books are on
#: the screen with their pictures and a prompt that named one would be choosing
#: for the child.
PICK_A_BOOK = N_("Pick a book.")

#: The keys of ``[child]`` in ``parent_text.toml``, and the msgid each one is.
CHILD_LINES: dict[str, str] = {
    "find_it": FIND_IT,
    "blend_it": BLEND_IT,
    "say_it_aloud": SAY_IT_ALOUD,
    "done": DONE,
    "nothing_due": NOTHING_DUE,
    "no_correction": NO_CORRECTION,
    "read_it": READ_IT,
    "pick_a_book": PICK_A_BOOK,
}

#: The lines that are on screen **while graphemes are**, which is the set the
#: rule at the top of this module binds on. ``nothing_due`` is not among them:
#: it is shown on an empty session with no board, and it contains the word "a",
#: which is also a grapheme -- a rule that could not tell those two apart would
#: be a rule about spelling rather than about answer keys.
SCREEN_PROMPTS: tuple[str, ...] = (FIND_IT, BLEND_IT, SAY_IT_ALOUD)

#: The two controls that carry a drawing. One short word under the picture and
#: the whole sentence in the ear (SYNTHESIS B4) -- two msgids per button, so a
#: translator can shorten the label without shortening what is said.
PUSH_LABEL = N_("push")
PUSH_SPEAK = N_("Push the sounds together.")
NEXT_LABEL = N_("next")
NEXT_SPEAK = N_("Next one.")

#: Read it's three controls. The two page arrows are separate msgids from
#: ``NEXT_*`` on purpose: "next one" is the next *item in the session* and
#: "the next page" is the next page of this book, and a translator handed one
#: string for both would have to guess which.
PAGE_BACK_LABEL = N_("back")
PAGE_BACK_SPEAK = N_("The page before.")
PAGE_NEXT_LABEL = N_("next")
PAGE_NEXT_SPEAK = N_("The next page.")
#: The narration control. **It is never a gate**: a child can read the whole
#: book without pressing it, and press it on every page if they want to.
LISTEN_LABEL = N_("read it")
LISTEN_SPEAK = N_("Read it to me.")

#: How a book announces itself on the shelf, and how it opens. `{title}` is the
#: book's own name, which is corpus content and is never translated -- an
#: en-GB phonics text is not a sentence with a French version.
SHELF_TILE_SPEAK = N_("{title}. A book to read.")
SHELF_BACK_SPEAK = N_("More books, the other way.")
SHELF_NEXT_SPEAK = N_("More books.")

#: The grown-up card, when the corpus has nothing to say.
GROWN_UP_TITLE = N_("Your turn")
GROWN_UP_INVITE = N_("Sit with him for this bit.")
GROWN_UP_PROMPT = N_("Ask him to say the word out loud to you.")
#: The grown-up card at the end of a book. The second half is the part that
#: matters: an adult who knows the book is inside the ceiling can let a child
#: struggle with a word instead of taking it off them, because there is no word
#: in it their school has not already taught.
GROWN_UP_READ = N_(
    "Ask him to read it to you — the words are all sounds he has been taught."
)

#: What separates one written word from the next. Not ``\W``: an apostrophe is
#: inside a word ("That's") and a hyphen may be, and neither of them is a
#: grapheme boundary. Kept explicit so the rule below is about *words a reader
#: sees* rather than about a regex's idea of one.
_SEPARATORS = re.compile("[^\\w'\u2019-]+", re.UNICODE)


def tokens(text: str) -> list[str]:
    """The written words in ``text``, lowercased, without their punctuation.

    Deliberately **not** a substring search. "Find the one that says…" contains
    the letters ``s``, ``a``, ``t`` and ``i`` -- every English sentence
    contains most of the alphabet, and a rule that banned that would ban
    speaking. What a child reads as *the answer* is a grapheme standing on its
    own as a word, which is what this splits on.
    """
    # Stripped at the edges as well as split on: "says 'a'!" is a prompt that
    # names `a`, and quoting the answer is exactly the sort of helpful edit
    # somebody makes.
    stripped = (word.strip("'\u2019-") for word in _SEPARATORS.split((text or "").lower()))
    return [word for word in stripped if word]


def names_a_grapheme(text: str, graphemes: Iterable[str]) -> str | None:
    """The first grapheme ``text`` prints as a word of its own, or ``None``.

    The rule at the top of this module, as something that can fail a test and
    a prompt at the same time. ``"Find the one that says k."`` -> ``"k"``;
    ``"Find the one that says…"`` -> ``None``.
    """
    words = set(tokens(text))
    for grapheme in graphemes:
        candidate = (grapheme or "").strip().lower()
        if candidate and candidate in words:
            return candidate
    return None
