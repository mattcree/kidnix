"""Numbers -- how many, without counting; and which two numbers make five.

Built to one statutory paragraph rather than to a genre. The [EYFS Number
ELG](https://www.gov.uk/government/publications/early-years-foundation-stage-framework--2)
asks that a child at the end of Reception can::

    have a deep understanding of number to 10, including the composition of
    each number; subitise (recognise quantities without counting) up to 5;
    automatically recall (without reference to rhymes, counting or other aids)
    number bonds up to 5 (including subtraction facts) and some number bonds to
    10, including double facts.

The 2021 reform *dropped* shape, space and measure and *added* subitising, and
`docs/research/05-learning-science.md` section 2c notes that it is "a target
almost no consumer app addresses". This is the activity that addresses it. It
does two things and nothing else:

**How many?** A picture flashes and goes; the child says how many by pressing a
numeral. One to five in the arrangements a child already knows -- the dice
faces -- and, where a grown-up has set the range to ten, six to ten as a full
row of five and some more on a ten-frame. Later in the loop the small numbers
come up scattered, so that what is being recognised is four things and not the
picture of a four.

**Make five, make ten.** Some counters are in a frame; the child fills the empty
boxes or presses the number that is missing, and the pair is said out loud --
"three and two make five". At the five range that is all four bonds to five,
every session. At the ten range it is two of those and then two to ten, of which
one is always the double.

And then **a grown-up's turn**, because the adult is the active ingredient in
every trial in this literature that found anything at all, and because fingers
beat a screen for this.

**What it is not.** There is no score, no star, no streak, no level, no "well
done", no timer, no leaderboard and no dashboard of the child. A wrong answer is
never called wrong: the picture comes back and the dots get counted, twice at
most, and then the child is simply told. Difficulty never moves on its own --
the range is a line in a root-owned file that a grown-up writes, because that
line is a claim about what a school has taught.

**Importing this package imports no GTK.** Everything the activity knows -- where
the dots go, which items make a session, what is said, what a key press means,
what a grown-up chose -- is in the pure modules here and is tested headless.
:mod:`numbers_activity.draw` imports ``cairo``, which is also displayless, so
even the pictures are exercised without a window. The window lives in
:mod:`numbers_activity.activity` and is imported only by the entry point.

The one-line acceptance test: *a Reception child can see four dots flash, press
the 4, hear "yes, four", fill two boxes to make five, hear "three and two make
five", and find a card of what they made in My Things.*
"""

from .arrange import Arrangement, Shape, arrangement_for, dice, scatter, ten_frame
from .draw import draw_arrangement, draw_bond_frame, draw_pattern, render_card
from .i18n import N_
from .items import (
    HowMany,
    Item,
    ItemKind,
    MakeBond,
    Practised,
    Response,
    respond,
    session,
)
from .keys import number_for, number_for_keyval
from .settings import (
    FIVE_FRAME,
    TEN_FRAME,
    Frame,
    FrameStyle,
    NumberRange,
    ParentSettings,
    load_settings,
    settings_from_document,
)
from .words import (
    bond_prompt,
    bond_sentence,
    card_caption,
    count_aloud,
    how_many_prompt,
    number_word,
    numeral,
    yes_line,
)

#: The manifest id the shell launches this as, and the id every Journal entry
#: is filed under. A slug, and the identity everywhere that matters.
ACTIVITY_ID = "numbers"
#: The window title, and the fallback title of a Journal card. A msgid: the
#: use site calls ``_()`` on it once a child's language is known (ADR-0012).
TITLE = N_("Numbers")

__all__ = [
    "ACTIVITY_ID",
    "FIVE_FRAME",
    "TEN_FRAME",
    "TITLE",
    "Arrangement",
    "Frame",
    "FrameStyle",
    "HowMany",
    "Item",
    "ItemKind",
    "MakeBond",
    "NumberRange",
    "ParentSettings",
    "Practised",
    "Response",
    "Shape",
    "arrangement_for",
    "bond_prompt",
    "bond_sentence",
    "card_caption",
    "count_aloud",
    "dice",
    "draw_arrangement",
    "draw_bond_frame",
    "draw_pattern",
    "how_many_prompt",
    "load_settings",
    "number_for",
    "number_for_keyval",
    "number_word",
    "numeral",
    "render_card",
    "respond",
    "scatter",
    "session",
    "settings_from_document",
    "ten_frame",
    "yes_line",
]

__version__ = "0.1.0"
