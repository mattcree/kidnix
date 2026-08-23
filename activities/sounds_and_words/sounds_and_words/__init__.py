"""Sounds & Words -- the kidnix literacy activity.

Week 1 of the v1 plan (docs/plan/SUITE.md section 3, research 10 section 7.1):
the corpus, the ceiling, the Reading Framework acceptance test and the schedule
skeleton. Data and pure logic only -- no GTK, no audio, no window.

The one-line acceptance test for the whole activity: *a Reception child whose
parent has said "they've done up to `ck`" can find a grapheme, blend six words
and read one four-sentence book, and never sees a grapheme past `ck`.*
"""

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

__all__ = [
    "BOX_INTERVALS",
    "Ceiling",
    "Corpus",
    "Gpc",
    "GpcState",
    "History",
    "Item",
    "ItemKind",
    "Reason",
    "Role",
    "Scheme",
    "Session",
    "TextVerdict",
    "TrickyWord",
    "Word",
    "WordVerdict",
    "allowed_gpcs",
    "allowed_sentences",
    "allowed_texts",
    "allowed_words",
    "ceiling_for_grapheme",
    "ceiling_for_phase",
    "ceiling_from_order",
    "check_lines",
    "check_text",
    "check_word",
    "compose_session",
    "custom_ceiling",
    "intersect",
    "load_corpus",
    "load_schemes",
    "resolve_ceiling",
    "segment",
    "tokenise",
]

__version__ = "0.1.0"
