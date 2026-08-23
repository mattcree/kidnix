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

__all__ = [
    "ASK_A_GROWNUP",
    "CHOOSE_PICTURE",
    "DRAW_ONE",
    "GROWNUP_NO_FAMILY_BODY",
    "GROWNUP_NO_FAMILY_TITLE",
    "GROWNUP_WRITE_BODY",
    "GROWNUP_WRITE_TITLE",
    "NOBODY_YET",
    "PICK_A_COLOUR",
    "POST_IT",
    "SAY_IT",
    "SHELF_EMPTY",
    "SHELF_TITLE",
    "TELL_THEM",
    "WHO_FOR",
    "WRITE_IT",
    "all_lines",
    "posted_line",
    "reply_line",
    "shelf_button",
    "your_letter_for",
]

# -- screen one: who is it for? ---------------------------------------------

#: The prompt on the first screen. A question, because the answer is a person
#: and the child already knows who.
WHO_FOR = "Who is your letter for?"

#: Spoken when a grown-up has not added anybody yet. Said to the *child*, and
#: it says what to do next in the only currency a five-year-old has: fetch a
#: person. The card beside it is for the grown-up they fetch.
NOBODY_YET = "There is nobody to write to yet. Ask a grown-up."

GROWNUP_NO_FAMILY_TITLE = "Your turn, grown-up"
GROWNUP_NO_FAMILY_BODY = (
    "Ask a grown-up to add someone in the parent panel. "
    "Parent Panel on the grown-up's account, then the Family tab: a name, a "
    "photo if you have one, and how they are related. Nothing is sent from "
    "this machine -- you take the finished letter out of the outbox yourself."
)

# -- screen two: the picture -------------------------------------------------

CHOOSE_PICTURE = "Choose a picture to send, or draw a new one."
DRAW_ONE = "Draw one"
PICK_A_COLOUR = "Pick a colour, then draw."

# -- screen three: the words -------------------------------------------------

#: The scaffold 05 section 3 names, word for word: "a few prompt scaffolds
#: ('tell them one thing that happened today') without templating the letter".
#: It is a prompt and not a template: there is no sentence starter on the
#: screen, nothing is filled in, and a child who writes about something else
#: has not got it wrong.
TELL_THEM = "Tell them one thing that happened today."

WRITE_IT = "Write it"
SAY_IT = "Say it"
ASK_A_GROWNUP = "Ask a grown-up to write it"

GROWNUP_WRITE_TITLE = "Your turn, grown-up"
GROWNUP_WRITE_BODY = (
    "Write down what they tell you, in their words. Do not tidy the spelling "
    "of anything they wrote themselves -- invented spelling is the Year One "
    "curriculum, and the person receiving this would rather have their words."
)

POST_IT = "Post it"

# -- the shelf ---------------------------------------------------------------

SHELF_TITLE = "Letters for you"
SHELF_EMPTY = "No letters yet. There will be one day."


def your_letter_for(name: str) -> str:
    """The prompt once a recipient has been chosen. Names them, every screen."""
    return f"Your letter for {name}."


def posted_line(name: str) -> str:
    """What is said when the letter is posted. The audience, named.

    It says who does the next thing and it does not say when, because nothing
    on this machine knows when and a five-year-old would hold us to it.
    """
    return f"Posted! A grown-up will send it to {name}."


def reply_line(name: str) -> str:
    """A reply on the shelf. "A letter from Grandad." """
    return f"A letter from {name}."


def shelf_button(count: int) -> str:
    """The label on the way into the shelf. **Never a count.**

    The number of letters waiting is a digit on a screen a pre-reader is
    looking at, and it is also the shape of a notification badge -- the thing
    D6 says this product does not have. So one letter and nine letters get the
    same three words, and the child finds out how many by looking.
    """
    return SHELF_TITLE if count else SHELF_EMPTY


def all_lines() -> list[str]:
    """Every fixed line, for the tests that check the rules on all of them."""
    return [
        WHO_FOR,
        NOBODY_YET,
        GROWNUP_NO_FAMILY_TITLE,
        GROWNUP_NO_FAMILY_BODY,
        CHOOSE_PICTURE,
        DRAW_ONE,
        PICK_A_COLOUR,
        TELL_THEM,
        WRITE_IT,
        SAY_IT,
        ASK_A_GROWNUP,
        GROWNUP_WRITE_TITLE,
        GROWNUP_WRITE_BODY,
        POST_IT,
        SHELF_TITLE,
        SHELF_EMPTY,
        your_letter_for("Grandad"),
        posted_line("Grandad"),
        reply_line("Grandad"),
    ]
