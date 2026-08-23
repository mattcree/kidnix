"""The ceiling: the hard gate that stops kidnix showing an untaught grapheme.

Design constitution, research 05 section 2a: *"kidnix must not invent its own
phonics progression, and must never show a child a word containing a
grapheme-phoneme correspondence they may not have been taught."*

Two ideas that are deliberately kept apart (research 10, section 4.3):

* **the ceiling** -- what the parent says the school has taught. A hard gate.
  It is never inferred, never advanced by the child getting good at something.
* **the schedule** -- which of the already-permitted GPCs get rehearsed today.
  That lives in ``schedule.py`` and can only ever choose from what the ceiling
  already allows.

Why a lexicon and not just a segmenter
--------------------------------------
Longest-match segmentation over the taught graphemes is necessary but not
sufficient, because a grapheme can stand for a phoneme that has not been
taught. The DfE Reading Framework's own Appendix 7 turns on exactly this:

    'worn'  = w + or(/or/) + n           -- decodable at Phase 3
    'worms' = w + or(/ur/) + m + s       -- *not* decodable at Phase 3

Both segment cleanly into the same taught graphemes. Only the pronunciation
distinguishes them. So the corpus stores a GPC-id segmentation for every word
it ships, and that mapping is authoritative. Longest-match is the fallback, and
in strict mode (the default) an unknown word is *rejected*, not guessed at.
Under-permitting is harmless; over-permitting undermines the school.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, replace
from enum import StrEnum

from .corpus import Corpus, DecodableText, Sentence, Word

WORD_RE = re.compile(r"[a-z]+(?:['\u2019-][a-z]+)*")


class Reason(StrEnum):
    """Why a word was allowed or refused. Every refusal names a cause."""

    OK_DECODABLE = "ok_decodable"
    OK_TRICKY = "ok_tricky"
    UNTAUGHT_GPC = "untaught_gpc"
    TRICKY_NOT_TAUGHT = "tricky_not_taught"
    UNKNOWN_WORD = "unknown_word"
    NO_SEGMENTATION = "no_segmentation"


@dataclass(frozen=True)
class Ceiling:
    """The set of GPCs and tricky words a child may be shown, and nothing more."""

    scheme: str
    label: str
    order: int
    phase: int
    gpc_ids: frozenset[str]
    graphemes: frozenset[str]
    tricky_words: frozenset[str]
    conservative: bool = False
    notes: tuple[str, ...] = ()

    def allows_gpc(self, gpc_id: str) -> bool:
        return gpc_id in self.gpc_ids

    def allows_tricky(self, word: str) -> bool:
        return word in self.tricky_words

    def __len__(self) -> int:
        return len(self.gpc_ids)


@dataclass(frozen=True)
class WordVerdict:
    word: str
    allowed: bool
    reason: Reason
    graphemes: tuple[str, ...] = ()
    blocked_by: tuple[str, ...] = ()

    @property
    def explanation(self) -> str:
        if self.reason is Reason.OK_DECODABLE:
            return f"{self.word!r} is decodable: {' + '.join(self.graphemes)}"
        if self.reason is Reason.OK_TRICKY:
            return f"{self.word!r} is a tricky word the school has taught"
        if self.reason is Reason.UNTAUGHT_GPC:
            return f"{self.word!r} needs {', '.join(self.blocked_by)}, which is not taught yet"
        if self.reason is Reason.TRICKY_NOT_TAUGHT:
            return f"{self.word!r} is a tricky word, and it is above the ceiling"
        if self.reason is Reason.UNKNOWN_WORD:
            return f"{self.word!r} is not in the corpus, so we cannot prove it is decodable"
        return f"{self.word!r} does not segment into taught graphemes"


@dataclass(frozen=True)
class TextVerdict:
    text: str
    allowed: bool
    verdicts: tuple[WordVerdict, ...]

    @property
    def blocked(self) -> tuple[WordVerdict, ...]:
        return tuple(v for v in self.verdicts if not v.allowed)

    @property
    def blocked_words(self) -> tuple[str, ...]:
        return tuple(v.word for v in self.blocked)

    def report(self) -> str:
        if self.allowed:
            return f"accepted: {self.text!r}"
        return "rejected: " + "; ".join(v.explanation for v in self.blocked)


# --------------------------------------------------------------------------
# Building a ceiling
# --------------------------------------------------------------------------

def _tricky_at(corpus: Corpus, order: int, phase: int) -> frozenset[str]:
    """Tricky words are gated by the GPC order L&S pins them to where it does,
    and by phase where it does not."""
    out = set()
    for tw in corpus.tricky_words:
        if tw.after_order is not None:
            if tw.after_order <= order:
                out.add(tw.text)
        elif tw.phase <= phase:
            out.add(tw.text)
    return frozenset(out)


def _phase_for_order(corpus: Corpus, order: int) -> int:
    phases = [g.phase for g in corpus.gpcs if g.order <= order]
    return max(phases) if phases else 1


def ceiling_from_order(
    corpus: Corpus,
    order: int,
    *,
    scheme: str = "letters_and_sounds",
    phase: int | None = None,
    label: str | None = None,
    notes: tuple[str, ...] = (),
    conservative: bool = False,
) -> Ceiling:
    gpcs = corpus.gpcs_up_to(order)
    resolved_phase = phase if phase is not None else _phase_for_order(corpus, order)
    if label is None:
        label = f"up to {gpcs[-1].grapheme!r}" if gpcs else "nothing taught yet"
    return Ceiling(
        scheme=scheme,
        label=label,
        order=order,
        phase=resolved_phase,
        gpc_ids=frozenset(g.id for g in gpcs),
        graphemes=frozenset(g.grapheme for g in gpcs),
        tricky_words=_tricky_at(corpus, order, resolved_phase),
        conservative=conservative,
        notes=notes,
    )


def ceiling_for_grapheme(
    corpus: Corpus, last_grapheme: str, *, scheme: str = "letters_and_sounds"
) -> Ceiling:
    """The parent's answer -- "the last sound they brought home was 'ai'"."""
    order = corpus.order_of_last_grapheme(last_grapheme)
    return ceiling_from_order(
        corpus, order, scheme=scheme, label=f"up to {last_grapheme!r}"
    )


def ceiling_for_phase(corpus: Corpus, phase: int, *, scheme: str = "letters_and_sounds") -> Ceiling:
    """A whole phase. Phase 4 adds no new GPCs -- it is adjacent consonants and
    a new set of tricky words -- so its ceiling is Phase 3's graphemes."""
    orders = [g.order for g in corpus.gpcs if g.phase <= phase]
    order = max(orders) if orders else 0
    return ceiling_from_order(
        corpus, order, scheme=scheme, phase=phase, label=f"phase {phase}"
    )


def custom_ceiling(
    corpus: Corpus,
    gpc_ids: set[str] | frozenset[str],
    *,
    scheme: str = "custom",
    label: str = "custom",
    tricky_words: set[str] | frozenset[str] | None = None,
    notes: tuple[str, ...] = (),
) -> Ceiling:
    """An explicit GPC set. Used by the Reading Framework fixtures, which state a
    grapheme list rather than a phase."""
    by_id = corpus.gpc_by_id
    unknown = sorted(g for g in gpc_ids if g not in by_id)
    if unknown:
        raise KeyError(f"unknown GPC ids: {unknown}")
    chosen = [by_id[g] for g in gpc_ids]
    order = max((g.order for g in chosen), default=0)
    phase = max((g.phase for g in chosen), default=1)
    return Ceiling(
        scheme=scheme,
        label=label,
        order=order,
        phase=phase,
        gpc_ids=frozenset(gpc_ids),
        graphemes=frozenset(g.grapheme for g in chosen),
        tricky_words=frozenset(tricky_words or ()),
        notes=notes,
    )


def intersect(a: Ceiling, b: Ceiling, *, label: str | None = None) -> Ceiling:
    """The conservative intersection of two ceilings.

    Used when a school's scheme orders GPCs differently from Letters and Sounds:
    permit only what *both* orderings have taught by this point (research 10,
    section 4.5). Under-permitting is harmless.
    """
    return Ceiling(
        scheme=f"{a.scheme}+{b.scheme}",
        label=label or f"{a.label} (conservative)",
        order=min(a.order, b.order),
        phase=min(a.phase, b.phase),
        gpc_ids=a.gpc_ids & b.gpc_ids,
        graphemes=a.graphemes & b.graphemes,
        tricky_words=a.tricky_words & b.tricky_words,
        conservative=True,
        notes=tuple(dict.fromkeys(a.notes + b.notes)),
    )


def with_notes(ceiling: Ceiling, *notes: str) -> Ceiling:
    return replace(ceiling, notes=ceiling.notes + tuple(notes))


# --------------------------------------------------------------------------
# Segmentation
# --------------------------------------------------------------------------

def segment(word: str, graphemes: frozenset[str] | set[str]) -> tuple[str, ...] | None:
    """Longest-match segmentation of ``word`` over ``graphemes``.

    Longest-first is what makes digraphs and trigraphs work: with ``igh``
    taught, ``night`` is n-igh-t and not n-i-g-h-t. Returns ``None`` when the
    word does not segment cleanly, which is a rejection, not a fallback.

    Split digraphs (``a-e``) are discontinuous and cannot be found this way;
    they are skipped here and must come from the corpus segmentations instead.
    """
    contiguous = sorted((g for g in graphemes if "-" not in g and g), key=len, reverse=True)
    cleaned = word.replace("-", "").replace("'", "").replace("\u2019", "")
    out: list[str] = []
    i = 0
    while i < len(cleaned):
        for g in contiguous:
            if cleaned.startswith(g, i):
                out.append(g)
                i += len(g)
                break
        else:
            return None
    return tuple(out) or None


def tokenise(text: str) -> list[str]:
    """Words of a caption or sentence, lowercased, punctuation dropped.

    The typographic apostrophe is folded to the typewriter one, because the
    source PDFs use the former and the corpus keys use the latter.
    """
    return WORD_RE.findall(text.lower().replace("\u2019", "'"))


# --------------------------------------------------------------------------
# The filter
# --------------------------------------------------------------------------

def check_word(
    corpus: Corpus, word: str, ceiling: Ceiling, *, strict: bool = True
) -> WordVerdict:
    """Is this word safe to show at this ceiling?

    ``strict`` (the default) means: if we do not have a segmentation on record,
    refuse. Guessing would be exactly the failure the design constitution
    forbids.
    """
    w = word.lower().strip().replace("\u2019", "'")
    tricky = corpus.tricky_by_text
    if w in tricky:
        if ceiling.allows_tricky(w):
            return WordVerdict(w, True, Reason.OK_TRICKY, tricky[w].graphemes)
        return WordVerdict(w, False, Reason.TRICKY_NOT_TAUGHT, tricky[w].graphemes, (w,))

    seg = corpus.segmentations.get(w)
    if seg is not None:
        blocked = tuple(g for g in seg if g not in ceiling.gpc_ids)
        if blocked:
            return WordVerdict(w, False, Reason.UNTAUGHT_GPC, seg, blocked)
        return WordVerdict(w, True, Reason.OK_DECODABLE, seg)

    if strict:
        return WordVerdict(w, False, Reason.UNKNOWN_WORD, (), (w,))

    guessed = segment(w, ceiling.graphemes)
    if guessed is None:
        return WordVerdict(w, False, Reason.NO_SEGMENTATION, (), (w,))
    return WordVerdict(w, True, Reason.OK_DECODABLE, guessed)


def check_text(
    corpus: Corpus, text: str, ceiling: Ceiling, *, strict: bool = True
) -> TextVerdict:
    verdicts = tuple(
        check_word(corpus, tok, ceiling, strict=strict) for tok in tokenise(text)
    )
    return TextVerdict(text, all(v.allowed for v in verdicts), verdicts)


def check_lines(
    corpus: Corpus, lines: list[str] | tuple[str, ...], ceiling: Ceiling, *, strict: bool = True
) -> TextVerdict:
    joined = " ".join(lines)
    return check_text(corpus, joined, ceiling, strict=strict)


def allowed_words(
    corpus: Corpus,
    ceiling: Ceiling,
    *,
    include_proper_nouns: bool = False,
    target_gpc: str | None = None,
) -> list[Word]:
    """Every corpus word the child may be shown. A filter, not a model."""
    out = []
    for w in corpus.words:
        if not include_proper_nouns and w.proper_noun:
            continue
        if target_gpc is not None and target_gpc not in w.graphemes:
            continue
        if all(g in ceiling.gpc_ids for g in w.graphemes):
            out.append(w)
    return out


def allowed_sentences(corpus: Corpus, ceiling: Ceiling, *, kind: str | None = None) -> list[Sentence]:
    out = []
    for s in corpus.sentences:
        if kind is not None and s.kind != kind:
            continue
        if check_text(corpus, s.text, ceiling).allowed:
            out.append(s)
    return out


def allowed_texts(corpus: Corpus, ceiling: Ceiling) -> list[DecodableText]:
    return [t for t in corpus.texts if check_lines(corpus, t.lines, ceiling).allowed]


def allowed_gpcs(corpus: Corpus, ceiling: Ceiling):
    return [g for g in corpus.gpcs if g.id in ceiling.gpc_ids]
