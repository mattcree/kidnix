"""Sounds & Words -- the kidnix literacy activity.

Weeks 1-3 of the v1 plan (docs/plan/SUITE.md section 3, research 10 section
7.1): the corpus, the ceiling, the Reading Framework acceptance test, the
schedule, and the first two modules of the loop -- **Find it** (B) and **Blend
it** (C). Read it (E) is week 4 and Hear it (A) is week 6 if there is time.

**Importing this package imports no GTK.** The half that carries the guarantee
-- which grapheme comes next, what the ceiling is, whether a word is decodable
-- is here and is provable headless; the window lives in
``sounds_and_words.activity`` and is imported only by the entry point. That
split is the shape ``docs/design/activity-sdk.md`` section 2 asks every
activity to copy, and this is the activity it was asked for.

The one-line acceptance test for the whole activity: *a Reception child whose
parent has said "they've done up to `ck`" can find a grapheme, blend six words
and read one four-sentence book, and never sees a grapheme past `ck`.*
"""

from .blend import BlendState, BlendWord, Mark, SoundButton, Stage, blend_word
from .ceiling import (
    Ceiling,
    Reason,
    TextVerdict,
    WordVerdict,
    allowed_gpcs,
    allowed_sentences,
    allowed_texts,
    allowed_words,
    ceiling_for_grapheme,
    ceiling_for_phase,
    ceiling_from_order,
    check_lines,
    check_text,
    check_word,
    custom_ceiling,
    intersect,
    segment,
    tokenise,
)
from .corpus import Corpus, Gpc, TrickyWord, Word, load_corpus
from .distractors import choose_distractors, find_it_options
from .keys import BoardKeys, Press, PressResult, keys_for
from .loop import MAX_ITEMS, Outcome, Plan, SessionRunner, plan_session
from .phonemes import Phoneme, Source, phoneme_for, say_label
from .pictures import PICTURE_WORDS, picture_for
from .schedule import (
    BOX_INTERVALS,
    GpcState,
    History,
    Item,
    ItemKind,
    Role,
    Session,
    compose_session,
)
from .schemes import Scheme, load_schemes, resolve_ceiling
from .settings import ParentCeiling, Progress, load_parent_ceiling, load_progress, save_progress
from .summary import Summary, SummaryCard, caption_for, meta_for

#: The manifest id the shell launches this as, and the id every Journal entry
#: is filed under. It is a slug, and it is the identity everywhere that matters.
ACTIVITY_ID = "sounds-and-words"
#: The window title, and the fallback title of a Journal card.
TITLE = "Sounds & words"

__all__ = [
    "ACTIVITY_ID",
    "BOX_INTERVALS",
    "MAX_ITEMS",
    "PICTURE_WORDS",
    "TITLE",
    "BlendState",
    "BlendWord",
    "BoardKeys",
    "Ceiling",
    "Corpus",
    "Gpc",
    "GpcState",
    "History",
    "Item",
    "ItemKind",
    "Mark",
    "Outcome",
    "ParentCeiling",
    "Phoneme",
    "Plan",
    "Press",
    "PressResult",
    "Progress",
    "Reason",
    "Role",
    "Scheme",
    "Session",
    "SessionRunner",
    "SoundButton",
    "Source",
    "Stage",
    "Summary",
    "SummaryCard",
    "TextVerdict",
    "TrickyWord",
    "Word",
    "WordVerdict",
    "allowed_gpcs",
    "allowed_sentences",
    "allowed_texts",
    "allowed_words",
    "blend_word",
    "caption_for",
    "ceiling_for_grapheme",
    "ceiling_for_phase",
    "ceiling_from_order",
    "check_lines",
    "check_text",
    "check_word",
    "choose_distractors",
    "compose_session",
    "custom_ceiling",
    "find_it_options",
    "intersect",
    "keys_for",
    "load_corpus",
    "load_parent_ceiling",
    "load_progress",
    "load_schemes",
    "meta_for",
    "phoneme_for",
    "picture_for",
    "plan_session",
    "resolve_ceiling",
    "save_progress",
    "say_label",
    "segment",
    "tokenise",
]

__version__ = "0.1.0"
