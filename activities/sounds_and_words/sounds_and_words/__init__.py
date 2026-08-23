"""Sounds & Words -- the kidnix literacy activity.

Weeks 1-4 of the v1 plan (docs/plan/SUITE.md section 3, research 10 section
7.1): the corpus, the ceiling, the Reading Framework acceptance test, the
schedule, and three modules of the loop -- **Find it** (B), **Blend it** (C)
and **Read it** (E), the last of which brings twelve authored decodable texts
with it. Hear it (A) is week 6 if there is time.

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
from .clips import ClipPlayer, NullClipPlayer, make_player
from .corpus import Corpus, Gpc, TrickyWord, Word, load_corpus
from .distractors import CHOICE_CEILING, board_graphemes, choose_distractors, find_it_options
from .i18n import N_
from .keys import BoardKeys, Press, PressResult, keys_for
from .loop import MAX_ITEMS, Outcome, Plan, SessionRunner, plan_session
from .phonemes import Phoneme, Source, phoneme_for, say_label
from .pictures import PICTURE_WORDS, picture_for
from .reading import (
    SHELF_PER_PAGE,
    Page,
    ReadingText,
    WordSpan,
    illustration_for,
    load_texts,
    shelf_pages,
    text_by_slug,
    texts_for,
    word_spans,
)
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
from .settings import (
    Narration,
    ParentCeiling,
    Progress,
    load_narration,
    load_parent_ceiling,
    load_progress,
    save_progress,
)
from .summary import (
    ReadingSummary,
    Summary,
    SummaryCard,
    caption_for,
    meta_for,
    read_caption_for,
    read_meta_for,
)

#: The manifest id the shell launches this as, and the id every Journal entry
#: is filed under. It is a slug, and it is the identity everywhere that matters.
ACTIVITY_ID = "sounds-and-words"
#: The window title, and the fallback title of a Journal card. ``N_`` because
#: it is a module-level constant: it holds the msgid, and the *use site* --
#: :func:`sounds_and_words.activity.main` -- calls ``_()`` on it once a child's
#: language is known (docs/design/i18n.md, ADR-0012).
TITLE = N_("Sounds & words")

__all__ = [
    "ACTIVITY_ID",
    "BOX_INTERVALS",
    "CHOICE_CEILING",
    "MAX_ITEMS",
    "PICTURE_WORDS",
    "SHELF_PER_PAGE",
    "TITLE",
    "BlendState",
    "BlendWord",
    "BoardKeys",
    "Ceiling",
    "ClipPlayer",
    "Corpus",
    "Gpc",
    "GpcState",
    "History",
    "Item",
    "ItemKind",
    "Mark",
    "Narration",
    "NullClipPlayer",
    "Outcome",
    "Page",
    "ParentCeiling",
    "Phoneme",
    "Plan",
    "Press",
    "PressResult",
    "Progress",
    "ReadingSummary",
    "ReadingText",
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
    "WordSpan",
    "WordVerdict",
    "allowed_gpcs",
    "allowed_sentences",
    "allowed_texts",
    "allowed_words",
    "blend_word",
    "board_graphemes",
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
    "illustration_for",
    "intersect",
    "keys_for",
    "load_corpus",
    "load_narration",
    "load_parent_ceiling",
    "load_progress",
    "load_schemes",
    "load_texts",
    "make_player",
    "meta_for",
    "phoneme_for",
    "picture_for",
    "plan_session",
    "read_caption_for",
    "read_meta_for",
    "resolve_ceiling",
    "save_progress",
    "say_label",
    "segment",
    "shelf_pages",
    "text_by_slug",
    "texts_for",
    "tokenise",
    "word_spans",
]

__version__ = "0.1.0"
