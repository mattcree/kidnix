"""Loading and indexing the Letters and Sounds corpus.

The corpus is plain TOML under ``data/``. Nothing here is adaptive, learned or
generated: it is a transcription of an Open Government Licence document plus a
small, individually-marked set of kidnix additions. A parent can read it in a
text editor, which is the point.
"""

from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path


def data_dir() -> Path:
    """Where the TOML lives.

    ``KIDNIX_SOUNDS_AND_WORDS_DATA`` overrides, which is how the image build and
    the tests point at a different tree.
    """
    override = os.environ.get("KIDNIX_SOUNDS_AND_WORDS_DATA")
    if override:
        return Path(override)
    return Path(__file__).resolve().parent.parent / "data"


@dataclass(frozen=True)
class Gpc:
    """One grapheme-phoneme correspondence."""

    id: str
    grapheme: str
    order: int
    phase: int
    ipa: str
    spoken_label: str
    stretchable: bool
    kind: str
    example_words: tuple[str, ...]
    source: str
    set: int | None = None
    variant_of: str | None = None
    alternative_pronunciation: bool = False
    split: bool = False
    added_by: str | None = None
    note: str | None = None

    @property
    def is_multigraph(self) -> bool:
        return len(self.grapheme) > 1

    @property
    def from_letters_and_sounds(self) -> bool:
        return self.added_by is None


@dataclass(frozen=True)
class UntaughtGrapheme:
    """A pseudo-GPC that exists only so the corpus can say *why* a word is not
    decodable. It is never in any ceiling, at any phase."""

    id: str
    grapheme: str
    description: str
    example_words: tuple[str, ...]
    taught: bool = False


@dataclass(frozen=True)
class Word:
    text: str
    phase: int
    order: int
    graphemes: tuple[str, ...]
    groups: tuple[str, ...]
    source: str
    set: int | None = None
    target_gpc: str | None = None
    proper_noun: bool = False
    high_frequency: bool = False
    order_exceeds_group: bool = False
    added_by: str | None = None
    note: str | None = None


@dataclass(frozen=True)
class TrickyWord:
    text: str
    phase: int
    graphemes: tuple[str, ...]
    source: str
    after_order: int | None = None


@dataclass(frozen=True)
class Sentence:
    text: str
    text_lower: str
    tokens: tuple[str, ...]
    kind: str
    phase: int
    after_order: int
    group: str
    source: str


@dataclass(frozen=True)
class DecodableText:
    title: str
    phase: int
    after_order: int
    lines: tuple[str, ...]
    lines_lower: tuple[str, ...]
    tokens: tuple[str, ...]
    source: str


@dataclass(frozen=True)
class LexiconEntry:
    word: str
    graphemes: tuple[str, ...]
    source: str
    never_decodable: bool = False


def _tup(v):
    return tuple(v) if isinstance(v, list) else v


def _make(cls, row: dict):
    fields = {f for f in cls.__dataclass_fields__}
    return cls(**{k: _tup(v) for k, v in row.items() if k in fields})


def _load(path: Path) -> dict:
    with path.open("rb") as fh:
        return tomllib.load(fh)


@dataclass(frozen=True)
class Corpus:
    """Everything the activity knows about sounds and words."""

    gpcs: tuple[Gpc, ...]
    untaught: tuple[UntaughtGrapheme, ...]
    words: tuple[Word, ...]
    tricky_words: tuple[TrickyWord, ...]
    sentences: tuple[Sentence, ...]
    texts: tuple[DecodableText, ...]
    lexicon: tuple[LexiconEntry, ...]
    parent_text: dict = field(default_factory=dict)
    sources: dict = field(default_factory=dict)

    # ---------------------------------------------------------------- indices
    @property
    def gpc_by_id(self) -> dict[str, Gpc]:
        return {g.id: g for g in self.gpcs}

    @property
    def untaught_by_id(self) -> dict[str, UntaughtGrapheme]:
        return {u.id: u for u in self.untaught}

    @property
    def word_by_text(self) -> dict[str, Word]:
        return {w.text: w for w in self.words}

    @property
    def tricky_by_text(self) -> dict[str, TrickyWord]:
        return {t.text: t for t in self.tricky_words}

    @property
    def segmentations(self) -> dict[str, tuple[str, ...]]:
        """word -> GPC ids. The word banks first, then the hand-written lexicon.

        This mapping is *authoritative*: where a word is in it, no segmentation
        is guessed. See ``ceiling.segment`` for the fallback and why it is not
        trusted on its own.
        """
        out: dict[str, tuple[str, ...]] = {w.text: w.graphemes for w in self.words}
        for e in self.lexicon:
            out.setdefault(e.word, e.graphemes)
        return out

    def gpcs_for_grapheme(self, grapheme: str) -> list[Gpc]:
        return sorted((g for g in self.gpcs if g.grapheme == grapheme), key=lambda g: g.order)

    def gpcs_up_to(self, order: int) -> list[Gpc]:
        return [g for g in self.gpcs if g.order <= order]

    def max_order(self) -> int:
        return max(g.order for g in self.gpcs)

    def order_of_last_grapheme(self, last: str) -> int:
        """Translate a parent's answer ("they've done up to 'ck'") into an order.

        A bare grapheme resolves to its *first* teaching, never a later
        alternative pronunciation: under-permitting is harmless, over-permitting
        undermines the school (research 10, section 4.5).
        """
        by_id = self.gpc_by_id
        if last in by_id:
            return by_id[last].order
        candidates = self.gpcs_for_grapheme(last)
        if not candidates:
            raise KeyError(f"no GPC for grapheme or id {last!r}")
        return candidates[0].order


@lru_cache(maxsize=4)
def load_corpus(path: str | None = None) -> Corpus:
    root = Path(path) if path else data_dir()
    graphemes = _load(root / "graphemes.toml")
    words = _load(root / "words.toml")
    tricky = _load(root / "tricky_words.toml")
    sentences = _load(root / "sentences.toml")
    lexicon = _load(root / "lexicon.toml")
    parent_text = _load(root / "parent_text.toml")
    sources = _load(root / "sources.toml")
    return Corpus(
        gpcs=tuple(_make(Gpc, r) for r in graphemes.get("gpc", [])),
        untaught=tuple(_make(UntaughtGrapheme, r) for r in graphemes.get("untaught", [])),
        words=tuple(_make(Word, r) for r in words.get("word", [])),
        tricky_words=tuple(_make(TrickyWord, r) for r in tricky.get("tricky_word", [])),
        sentences=tuple(_make(Sentence, r) for r in sentences.get("sentence", [])),
        texts=tuple(_make(DecodableText, r) for r in sentences.get("text", [])),
        lexicon=tuple(_make(LexiconEntry, r) for r in lexicon.get("entry", [])),
        parent_text=parent_text,
        sources=sources,
    )
