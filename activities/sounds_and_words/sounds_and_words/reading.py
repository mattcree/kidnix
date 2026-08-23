"""Read it (module E): twelve books, one sentence to a page, and nothing to press.

Research 10 section 4.1 E, and its evidence anchor is the sharpest negative
finding in the whole of this literature. Takacs, Swart & Bus (2015), a
meta-analysis of 43 studies and 2,147 children, found that a narrated text with
**congruent illustration** beats a plain adult reading (g+ = 0.17 comprehension,
0.20 expressive vocabulary) and that **hotspots, tap-to-animate, embedded games
and tap-a-word dictionaries make it worse**. So this module is deliberately the
least interactive thing in the activity:

* one sentence per screen, set large, in the letterforms the child is taught in;
* one picture per sentence, showing what the sentence says;
* a *"read it to me"* button, optional narration with word-by-word
  highlighting, and nothing else that responds to a touch;
* **tapping a word does nothing at all.** Not a definition, not a sound, not a
  wobble. That is the finding, implemented.

What is here and what is next door
----------------------------------

This module is pure: the twelve texts, whether a ceiling admits one, how a text
paginates, which drawing goes with a line, and the arithmetic that decides
which word is lit when. None of it imports GTK, all of it is provable headless,
and that is the same split the rest of this package keeps
(``docs/design/activity-sdk.md`` section 2). The screen is in
:mod:`sounds_and_words.reader`.

Why the texts are ours
----------------------

There is no openly-licensed decodable set that follows a UK phonics
progression (research 10 section 5; the search is recorded there as an
absence). So they are written here, out of the Letters and Sounds word banks,
and every word of every one of them -- **titles included** -- is put through
:func:`sounds_and_words.ceiling.check_lines` in strict mode by
``tests/test_reading.py``. Strict mode refuses a word it has no segmentation
for rather than guessing at one, which is what stops an author reaching for a
word that merely *looks* decodable.

The shelf is a choice, and five is the bound
--------------------------------------------

ADR-0013: five is the ceiling on a choice the child has to *weigh*, as against
a labelled grid whose items are the task itself. A shelf of books is squarely a
choice -- the child is picking between alternatives on the strength of a
picture and a title -- so :data:`SHELF_PER_PAGE` is five and a longer shelf
pages rather than growing.
"""

from __future__ import annotations

import logging
import re
import tomllib
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from .ceiling import Ceiling, check_lines, tokenise
from .corpus import Corpus, data_dir
from .pictures import PICTURE_DIR

log = logging.getLogger(__name__)

__all__ = [
    "MAX_LINES",
    "MIN_LINES",
    "SCENE_DIR",
    "SHELF_PER_PAGE",
    "WORDS_PER_MINUTE",
    "Page",
    "ReadingText",
    "WordSpan",
    "illustration_for",
    "load_texts",
    "sentence_ms",
    "shelf_pages",
    "text_by_slug",
    "texts_for",
    "word_spans",
]

#: The eleven drawings that are scenes rather than single nouns. The fifteen
#: nouns in ``pictures/`` are reused wherever a line is about one of them --
#: a picture of a cat is already the best picture a line about a cat can have.
SCENE_DIR = Path(__file__).resolve().parent / "scenes"

#: The file the twelve texts live in. Hand-written, unlike the generated corpus
#: beside it, and it says so at the top.
TEXTS_NAME = "read_texts.toml"

#: Research 10 section 4.1 E: "a 4-8 sentence decodable text". Both ends are
#: asserted. Four is short enough to finish; eight is where a five-year-old
#: reading every word aloud starts to run out of session.
MIN_LINES = 4
MAX_LINES = 8

#: ADR-0013. A shelf is a choice, not a labelled grid, so five is the bound.
SHELF_PER_PAGE = 5

#: Words a minute, for an adult reading a decodable text to a five-year-old.
#: Slower than conversational (~150) because this is read-aloud, with the
#: pauses that go with it. It exists only to time a highlight, and a highlight
#: that is a beat out is a highlight, not a lie.
WORDS_PER_MINUTE = 120.0

#: What speech-dispatcher's ``rate`` means for our arithmetic. The scale is
#: -100 to +100 and negative is slower; this maps it to a duration multiplier
#: that is 1.0 at zero, 2.0 at -100 and 0.67 at +100. Approximate on purpose:
#: the SDK's voice does not report how long it will take, and the alternative
#: to approximating is not highlighting at all.
RATE_SPAN = 200.0

_PUNCTUATION = re.compile("[^\\w'\u2019-]+", re.UNICODE)


@dataclass(frozen=True)
class Page:
    """One screen: a sentence, a drawing, and where it sits in the book."""

    index: int
    sentence: str
    picture: str
    total: int

    @property
    def first(self) -> bool:
        return self.index == 0

    @property
    def last(self) -> bool:
        return self.index >= self.total - 1

    @property
    def words(self) -> tuple[str, ...]:
        """The words as they are **written**, punctuation and all.

        Not :func:`sounds_and_words.ceiling.tokenise`: what gets highlighted is
        what is on the glass, and on the glass ``"tap,"`` is one word with a
        comma on it. The tokeniser's answer is what the *ceiling* checks, which
        is a different question about the same sentence.
        """
        return tuple(self.sentence.split())


@dataclass(frozen=True)
class ReadingText:
    """One authored decodable text."""

    slug: str
    title: str
    phase: int
    after_order: int
    lines: tuple[str, ...]
    pictures: tuple[str, ...]
    cover: str
    set: int | None = None

    def __post_init__(self) -> None:
        if len(self.lines) != len(self.pictures):
            raise ValueError(f"{self.slug}: {len(self.lines)} lines and {len(self.pictures)} pictures")

    def __len__(self) -> int:
        return len(self.lines)

    @property
    def pages(self) -> tuple[Page, ...]:
        """One sentence per page, in order. The whole of the pagination.

        There is no reflow, no "fit two short ones on a page" and no page
        number anywhere: a child is reading one sentence, and the next thing
        that happens is that they press the arrow.
        """
        total = len(self.lines)
        return tuple(
            Page(index=index, sentence=line, picture=picture, total=total)
            for index, (line, picture) in enumerate(zip(self.lines, self.pictures, strict=True))
        )

    def page(self, index: int) -> Page | None:
        pages = self.pages
        if 0 <= index < len(pages):
            return pages[index]
        return None

    @property
    def words(self) -> tuple[str, ...]:
        """Every distinct word in the book, in the order it first appears.

        What goes in the Journal card's ``meta.json`` -- the list a grown-up
        can look at and recognise as the words their child has just read.
        """
        seen: list[str] = []
        for line in self.lines:
            for token in tokenise(line):
                if token not in seen:
                    seen.append(token)
        return tuple(seen)

    @property
    def all_lines(self) -> tuple[str, ...]:
        """The lines **and the title**, which is the thing the ceiling checks.

        The title is on the shelf and at the top of nothing else, but a child
        reads it, so it is held to exactly the same rule as a sentence.
        """
        return (self.title, *self.lines)


# -- loading ----------------------------------------------------------------


def _make(row: dict) -> ReadingText:
    return ReadingText(
        slug=str(row["slug"]),
        title=str(row["title"]),
        phase=int(row["phase"]),
        after_order=int(row["after_order"]),
        lines=tuple(str(line) for line in row["lines"]),
        pictures=tuple(str(name) for name in row["pictures"]),
        cover=str(row["cover"]),
        set=int(row["set"]) if row.get("set") is not None else None,
    )


@lru_cache(maxsize=4)
def load_texts(path: str | None = None) -> tuple[ReadingText, ...]:
    """The twelve, in teaching order. Cached, like the corpus."""
    root = Path(path) if path else data_dir()
    with (root / TEXTS_NAME).open("rb") as handle:
        doc = tomllib.load(handle)
    texts = tuple(_make(row) for row in doc.get("text", []))
    return tuple(sorted(texts, key=lambda text: (text.after_order, text.title)))


def text_by_slug(slug: str, *, texts: tuple[ReadingText, ...] | None = None) -> ReadingText | None:
    """One book by name, or ``None``. What a plan item's payload resolves to."""
    for text in texts if texts is not None else load_texts():
        if text.slug == slug:
            return text
    return None


# -- the shelf --------------------------------------------------------------


def texts_for(
    corpus: Corpus,
    ceiling: Ceiling,
    *,
    texts: tuple[ReadingText, ...] | None = None,
    strict: bool = True,
) -> list[ReadingText]:
    """The books this child may be shown, in teaching order.

    The gate is the same one everything else in this activity goes through, and
    it is applied to the **whole** text rather than to its declared
    ``after_order``: a mistyped number in the TOML must not be able to put a
    book on a shelf, and the only thing that decides is
    :func:`~sounds_and_words.ceiling.check_lines`.
    """
    pool = texts if texts is not None else load_texts()
    return [
        text for text in pool if check_lines(corpus, text.all_lines, ceiling, strict=strict).allowed
    ]


def shelf_pages(
    texts: list[ReadingText] | tuple[ReadingText, ...], *, per_page: int = SHELF_PER_PAGE
) -> tuple[tuple[ReadingText, ...], ...]:
    """Break the shelf into pages of at most :data:`SHELF_PER_PAGE`.

    A caller who asks for more is **capped and logged**, not refused: ADR-0013
    is a design decision, and turning a design mistake into a child staring at
    a screen that will not start is not how a design decision is enforced.
    """
    if per_page > SHELF_PER_PAGE:
        log.warning(
            "a shelf page of %d was asked for; ADR-0013 caps a choice at %d",
            per_page,
            SHELF_PER_PAGE,
        )
        per_page = SHELF_PER_PAGE
    per_page = max(1, per_page)
    books = tuple(texts)
    if not books:
        return ()
    return tuple(books[start : start + per_page] for start in range(0, len(books), per_page))


# -- the drawings -----------------------------------------------------------


def illustration_for(name: str, *, scenes: Path | None = None, pictures: Path | None = None) -> Path | None:
    """The drawing called ``name``: a scene first, then one of the fifteen nouns.

    Returns ``None`` when the file is not really there rather than trusting the
    name, for the same reason :func:`sounds_and_words.pictures.picture_for`
    does: a picture named in data and missing on disk is an empty frame beside
    a sentence, and an empty frame is worse than no frame.
    """
    key = (name or "").strip().lower()
    if not key:
        return None
    for directory in (scenes or SCENE_DIR, pictures or PICTURE_DIR):
        candidate = directory / f"{key}.svg"
        if candidate.is_file():
            return candidate
    return None


def missing_illustrations(*, texts: tuple[ReadingText, ...] | None = None) -> list[str]:
    """Every drawing the texts name and the package does not have. A test's list."""
    wanted: list[str] = []
    for text in texts if texts is not None else load_texts():
        for name in (text.cover, *text.pictures):
            if name not in wanted and illustration_for(name) is None:
                wanted.append(name)
    return wanted


# -- the highlight ----------------------------------------------------------


@dataclass(frozen=True)
class WordSpan:
    """When one written word is lit, in milliseconds from the start of the line."""

    index: int
    word: str
    start_ms: int
    duration_ms: int

    @property
    def end_ms(self) -> int:
        return self.start_ms + self.duration_ms


def rate_factor(rate: int = -20) -> float:
    """Turn speech-dispatcher's ``rate`` into a duration multiplier.

    ``[access] speech_rate`` is clamped to -100..100 and negative is slower
    (``kidnix_shell.access``), so a child whose parent has slowed the voice
    down gets a highlight that slows down with it. Calm mode arrives here the
    same way, through ``effective_speech_rate``, because calm takes the slower
    of the two rather than a fixed number of its own.
    """
    return max(0.4, 1.0 - (max(-100, min(100, int(rate))) / RATE_SPAN))


def sentence_ms(sentence: str, *, rate: int = -20, wpm: float = WORDS_PER_MINUTE) -> int:
    """Roughly how long saying ``sentence`` out loud will take.

    An estimate, and it is allowed to be: the SDK's voice reports that a line
    was handed to speech-dispatcher, not how long speech-dispatcher will spend
    on it, and there is no callback anywhere in the stack that would say. The
    alternative to estimating is no highlighting, and Takacs et al.'s finding is
    about narration *with* word-level highlighting.
    """
    words = sentence.split()
    if not words:
        return 0
    minutes = len(words) / max(1.0, wpm)
    return max(1, round(minutes * 60_000 * rate_factor(rate)))


def _weight(word: str) -> int:
    """How long this word gets, relative to its neighbours.

    Letters plus one, so that ``a`` is not given the same beat as
    ``farmyard`` -- which is what dividing the sentence into equal shares would
    do, and it is visibly wrong on any line with a one-letter word in it.
    """
    return max(1, len(_PUNCTUATION.sub("", word))) + 1


def word_spans(
    sentence: str,
    *,
    rate: int = -20,
    wpm: float = WORDS_PER_MINUTE,
    total_ms: int | None = None,
) -> tuple[WordSpan, ...]:
    """When to light each written word of ``sentence``.

    Contiguous and gapless: the first span starts at zero, each one begins
    where the last ended, and the last ends exactly at the total. A gap would
    mean a moment with no word lit at all, which reads as a stutter rather than
    as a pause.
    """
    words = sentence.split()
    if not words:
        return ()
    total = total_ms if total_ms is not None else sentence_ms(sentence, rate=rate, wpm=wpm)
    total = max(len(words), int(total))
    weights = [_weight(word) for word in words]
    whole = sum(weights)

    spans: list[WordSpan] = []
    start = 0
    running = 0
    for index, (word, weight) in enumerate(zip(words, weights, strict=True)):
        running += weight
        # The *boundary* is rounded, not the duration: rounding each duration
        # separately lets the errors accumulate and leaves the last word ending
        # somewhere near the total instead of on it.
        end = total if index == len(words) - 1 else round(total * running / whole)
        end = max(end, start + 1)
        spans.append(WordSpan(index=index, word=word, start_ms=start, duration_ms=end - start))
        start = end
    return tuple(spans)


def span_at(spans: tuple[WordSpan, ...], elapsed_ms: int) -> WordSpan | None:
    """Which word is lit at ``elapsed_ms``, or ``None`` once the line is done."""
    for span in spans:
        if span.start_ms <= elapsed_ms < span.end_ms:
            return span
    return None
