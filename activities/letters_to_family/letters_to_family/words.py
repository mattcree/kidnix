"""Every line this activity says out loud, in one place.

Pure strings and pure formatting: no GTK, no voice, no file. That is what lets
a headless test assert the rules the whole product is held to, on every line,
without a display:

* **No digits, ever** (01 #19, 03 #32). "About as long as one story", never
  "twelve minutes"; and here, "a grown-up will send it", never "in two days".
* **No promise about the reply.** 05 section 3 says the reply must come back --
  it does not say when, and nothing on this machine knows. A line that said
  "Grandad will write back soon" would be a promise made on somebody else's
  behalf to a five-year-old, which is the worst kind. So the posted line names
  the grown-up as the one who does the next thing, and stops.
* **No reward vocabulary** (SUITE section 5, SYNTHESIS E1). No "well done", no
  "brilliant", no star, no point, no level. The reward is the letter.
* **Two sentences, twelve words, imperative** (B5). The prompts here are one
  sentence each.
* **Nothing is audio-only** (B2). Every line here is put on a
  :class:`~kidnix_activity.widgets.Prompt` as well as spoken, and every prompt
  has a replay.

The one line with a name in it is the posted line, and it is the whole point of
the activity: *purpose and audience*. "Posted!" on its own is a receipt.
"Posted! A grown-up will send it to Grandad." is an audience.
"""

from __future__ import annotations

from .i18n import N_, _

__all__ = [
    "ASK_A_GROWNUP",
    "CHOOSE_PICTURE",
    "DRAW_ONE",
    "FROM_LINE",
    "GROWNUP_LABEL",
    "GROWNUP_NO_FAMILY_BODY",
    "GROWNUP_NO_FAMILY_TITLE",
    "GROWNUP_WRITE_BODY",
    "GROWNUP_WRITE_TITLE",
    "KEEP_LABEL",
    "KEEP_SPEAK",
    "LISTEN_LABEL",
    "LISTEN_SPEAK",
    "NOBODY_YET",
    "PICK_A_COLOUR",
    "POSTED_LINE",
    "POST_IT",
    "SAY_IT",
    "SHELF_EMPTY",
    "SHELF_TITLE",
    "TELL_THEM",
    "UNDO_LABEL",
    "UNDO_SPEAK",
    "WHO_FOR",
    "WRITE_IT",
    "WRITE_ONE",
    "WRITE_ONE_SPEAK",
    "YOUR_LETTER_FOR",
    "all_lines",
    "posted_line",
    "reply_line",
    "shelf_button",
    "your_letter_for",
]

# ADR-0012 / docs/design/i18n.md: `N_` marks a msgid at module level and the
# **use site** calls `_()` on it, once a child's language is known. Never `_()`
# here -- a module-level translation freezes whichever catalogue happened to be
# installed when Python first imported the file, which on a profile switch is
# the wrong one. The one name in these sentences is a *person's*, and it goes
# in a **named** placeholder so a translator may put it wherever their language
# puts it.

# -- screen one: who is it for? ---------------------------------------------

#: The prompt on the first screen. A question, because the answer is a person
#: and the child already knows who.
WHO_FOR = N_("Who is your letter for?")

#: Spoken when a grown-up has not added anybody yet. Said to the *child*, and
#: it says what to do next in the only currency a five-year-old has: fetch a
#: person. The card beside it is for the grown-up they fetch.
NOBODY_YET = N_("There is nobody to write to yet. Ask a grown-up.")

GROWNUP_NO_FAMILY_TITLE = N_("Your turn, grown-up")
GROWNUP_NO_FAMILY_BODY = N_(
    "Ask a grown-up to add someone in the parent panel. "
    "Parent Panel on the grown-up's account, then the Family tab: a name, a "
    "photo if you have one, and how they are related. Nothing is sent from "
    "this machine -- you take the finished letter out of the outbox yourself."
)

# -- screen two: the picture -------------------------------------------------

CHOOSE_PICTURE = N_("Choose a picture to send, or draw a new one.")
DRAW_ONE = N_("Draw one")
PICK_A_COLOUR = N_("Pick a colour, then draw.")

#: The two controls on the drawing screen. One short word under the picture and
#: the whole sentence in the ear (SYNTHESIS B4) -- two msgids per button, so a
#: translator can shorten the label without shortening what is said.
UNDO_LABEL = N_("Undo")
UNDO_SPEAK = N_("Take the last line off.")
KEEP_LABEL = N_("That's it")
KEEP_SPEAK = N_("That's my picture.")

# -- screen three: the words -------------------------------------------------

#: The scaffold 05 section 3 names, word for word: "a few prompt scaffolds
#: ('tell them one thing that happened today') without templating the letter".
#: It is a prompt and not a template: there is no sentence starter on the
#: screen, nothing is filled in, and a child who writes about something else
#: has not got it wrong.
TELL_THEM = N_("Tell them one thing that happened today.")

WRITE_IT = N_("Write it")
SAY_IT = N_("Say it")
ASK_A_GROWNUP = N_("Ask a grown-up to write it")
#: The short word under the picture on that third button. What it *says* is
#: :data:`ASK_A_GROWNUP`, which is the whole sentence.
GROWNUP_LABEL = N_("Grown-up")

GROWNUP_WRITE_TITLE = N_("Your turn, grown-up")
GROWNUP_WRITE_BODY = N_(
    "Write down what they tell you, in their words. Do not tidy the spelling "
    "of anything they wrote themselves -- invented spelling is the Year One "
    "curriculum, and the person receiving this would rather have their words."
)

POST_IT = N_("Post it")

# -- the shelf ---------------------------------------------------------------

SHELF_TITLE = N_("Letters for you")
SHELF_EMPTY = N_("No letters yet. There will be one day.")

#: The way OFF the shelf, and back to the first screen. The shelf used to be a
#: dead end: every other screen leads forwards, the shelf led nowhere, and the
#: only way out of it was the shell's own Back, which leaves the activity
#: altogether. A child who went to look at Nanna's letter and then wanted to
#: write one had to leave Letters and come back into it.
#:
#: The label is what the button DOES rather than where it goes ("Write a
#: letter", not "Back"): B1 says a pre-reader navigates by picture and by
#: place, and "back" is a direction, not a thing.
WRITE_ONE = N_("Write a letter")
WRITE_ONE_SPEAK = N_("Write a letter to somebody.")
#: Playing back a reply that came with a voice note.
LISTEN_LABEL = N_("Listen")
LISTEN_SPEAK = N_("Hear it.")

#: TRANSLATORS: {name} is a person -- "Grandad", "Auntie Jo".
YOUR_LETTER_FOR = N_("Your letter for {name}.")
#: TRANSLATORS: what is said when the letter is posted. {name} is a person. It
#: says who does the next thing and deliberately not when.
POSTED_LINE = N_("Posted! A grown-up will send it to {name}.")
#: TRANSLATORS: a reply on the shelf. {name} is the person who sent it.
FROM_LINE = N_("A letter from {name}.")


def your_letter_for(name: str) -> str:
    """The prompt once a recipient has been chosen. Names them, every screen."""
    return _(YOUR_LETTER_FOR).format(name=name)


def posted_line(name: str) -> str:
    """What is said when the letter is posted. The audience, named.

    It says who does the next thing and it does not say when, because nothing
    on this machine knows when and a five-year-old would hold us to it.
    """
    return _(POSTED_LINE).format(name=name)


def reply_line(name: str) -> str:
    """A reply on the shelf. "A letter from Grandad." """
    return _(FROM_LINE).format(name=name)


def shelf_button(count: int) -> str:
    """The label on the way into the shelf. **Never a count.**

    The number of letters waiting is a digit on a screen a pre-reader is
    looking at, and it is also the shape of a notification badge -- the thing
    D6 says this product does not have. So one letter and nine letters get the
    same three words, and the child finds out how many by looking.
    """
    return _(SHELF_TITLE) if count else _(SHELF_EMPTY)


def all_lines() -> list[str]:
    """Every fixed line, for the tests that check the rules on all of them."""
    return [
        _(line)
        for line in (
            WHO_FOR,
            NOBODY_YET,
            GROWNUP_NO_FAMILY_TITLE,
            GROWNUP_NO_FAMILY_BODY,
            CHOOSE_PICTURE,
            DRAW_ONE,
            PICK_A_COLOUR,
            UNDO_LABEL,
            UNDO_SPEAK,
            KEEP_LABEL,
            KEEP_SPEAK,
            TELL_THEM,
            WRITE_IT,
            SAY_IT,
            ASK_A_GROWNUP,
            GROWNUP_LABEL,
            GROWNUP_WRITE_TITLE,
            GROWNUP_WRITE_BODY,
            POST_IT,
            SHELF_TITLE,
            SHELF_EMPTY,
            LISTEN_LABEL,
            LISTEN_SPEAK,
            WRITE_ONE,
            WRITE_ONE_SPEAK,
        )
    ] + [
        your_letter_for("Grandad"),
        posted_line("Grandad"),
        reply_line("Grandad"),
    ]
