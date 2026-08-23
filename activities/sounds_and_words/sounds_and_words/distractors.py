"""Choosing the three wrong tiles in Find it, and why they are those three.

"Find the one that says /d/" is a different task depending on what sits next to
the ``d``. Against ``s``, ``m`` and ``ai`` it is nearly free. Against ``b``,
``p`` and ``q`` it is the discrimination a Reception child actually has to make,
and the one their teacher is spending the term on: ``b``/``d`` reversals are the
single most common confusion in early English literacy, and ``p``/``q`` is the
same mirror on a different axis.

So distractors are **chosen, not sampled**, in four tiers:

1. **Reversals and rotations** -- ``b d p q``, ``n u``, ``m w``. The pairs that
   are the *same shape* under a flip. If one is taught, it is the first tile on
   the board.
2. **Visually similar** -- ``m``/``n``, ``c``/``o``/``e``, ``i``/``l``/``j``,
   ``h``/``n``, ``v``/``w``, ``f``/``t``, ``s``/``z``: different shapes that a
   five-year-old reading at 20 mm confuses anyway.
3. **Shares a letter, in the same place** -- for a multigraph. ``sh`` against
   ``ch`` and ``th``; ``ai`` against ``ar``. This is where digraph practice
   actually lives, because a child who has learned "s-then-h is one sound" has
   to learn that "c-then-h" is a *different* one sound.
4. **Nearest in teaching order** -- anything else the school has taught, closest
   first. Not padding: the sounds either side of the target in the progression
   are the ones a child has most recently had to hold apart.

Two hard rules underneath all of it, both asserted by tests:

* **Never an untaught grapheme.** Every candidate comes from ``ceiling.gpc_ids``
  and nothing else. A distractor is still a grapheme kidnix put on a screen, and
  the design constitution does not have an exception for wrong answers.
* **Never two tiles with the same grapheme.** ``oo`` is in the corpus twice
  (/uː/ and /ʊ/) and so is ``s`` (/s/ and /z/). Putting both on the board asks a
  child to pick between two identical tiles, one of which is arbitrarily wrong
  -- an unanswerable question that would look, to them, exactly like being told
  they are wrong when they are right.

Deterministic for a given ``rng``, so a screenshot and a test see the same
board. The *tiers* are the design; the shuffle inside a tier only decides which
of several equally good distractors gets used.
"""

from __future__ import annotations

import logging
import random
from collections.abc import Iterable, Sequence

from .ceiling import Ceiling
from .corpus import Corpus, Gpc

log = logging.getLogger(__name__)

__all__ = [
    "BOARD_TILES",
    "CHOICE_CEILING",
    "REVERSALS",
    "SIMILAR",
    "board_graphemes",
    "choose_distractors",
    "confusability",
    "find_it_options",
]

#: **The five-choice ceiling, applied here** (ADR-0013, SYNTHESIS B2).
#:
#: ADR-0013 draws the line the checkpoint-2 audit asked for: five is the bound
#: on a choice the child has to *weigh*, and not on a labelled grid whose items
#: are the task itself (a number line, a clock face, a keyboard). A Find it
#: board is squarely on the **choice** side of that line -- four graphemes, one
#: of which answers a sound the child has just heard and three of which are
#: there to be discriminated against -- so the ceiling binds, and four is
#: inside it with a tile to spare.
#:
#: It is a constant rather than a comment because the tempting change is
#: "one more distractor makes it harder", and the answer to that is an ADR.
CHOICE_CEILING = 5

#: How many tiles a full board carries. One target and three distractors: the
#: three tiers below have something to say at three, and a fourth distractor
#: would be tier 4 padding bought at the cost of a fifth thing to hold.
BOARD_TILES = 4

#: Tier 1: the same shape under a flip or a turn. Written as unordered pairs;
#: :func:`_partners` expands them both ways.
REVERSALS: tuple[frozenset[str], ...] = (
    frozenset({"b", "d"}),
    frozenset({"p", "q"}),
    frozenset({"b", "p"}),
    frozenset({"d", "q"}),
    frozenset({"n", "u"}),
    frozenset({"m", "w"}),
    frozenset({"b", "q"}),
    frozenset({"d", "p"}),
)

#: Tier 2: not mirror images, but confusable at a child's reading distance and
#: at the sizes ADR-0011 puts on the screen.
SIMILAR: tuple[frozenset[str], ...] = (
    frozenset({"m", "n"}),
    frozenset({"c", "o"}),
    frozenset({"c", "e"}),
    frozenset({"o", "e"}),
    frozenset({"a", "o"}),
    frozenset({"i", "l"}),
    frozenset({"i", "j"}),
    frozenset({"h", "n"}),
    frozenset({"h", "b"}),
    frozenset({"v", "w"}),
    frozenset({"v", "y"}),
    frozenset({"f", "t"}),
    frozenset({"s", "z"}),
    frozenset({"g", "q"}),
    frozenset({"g", "y"}),
    frozenset({"k", "x"}),
    frozenset({"r", "n"}),
)

#: The tiers, as scores. Lower is closer, and the sort is stable, so a tie
#: inside a tier is broken by teaching distance and then by the shuffle.
_TIER_REVERSAL = 0
_TIER_SIMILAR = 1
_TIER_SHARED = 2
_TIER_ORDER = 3


def _partners(pairs: Iterable[frozenset[str]], grapheme: str) -> set[str]:
    """The other half of every pair ``grapheme`` is in."""
    out: set[str] = set()
    for pair in pairs:
        if grapheme in pair:
            out |= pair - {grapheme}
    return out


def _shares_a_letter(target: str, other: str) -> bool:
    """Do two multigraphs overlap where it matters -- first or last letter?

    ``sh``/``ch`` share the ``h``; ``ai``/``ar`` share the ``a``. Two graphemes
    that merely contain the same letter somewhere (``igh``/``air``) are not the
    confusion this tier is for, so the test is positional.
    """
    if len(target) < 2 or len(other) < 2:
        return False
    return target[0] == other[0] or target[-1] == other[-1]


def confusability(target: Gpc, other: Gpc) -> tuple[int, int]:
    """How good a distractor ``other`` is for ``target``. Lower is better.

    Returns ``(tier, teaching distance)`` -- a sort key rather than a score,
    because there is no meaningful unit here and inventing one would invite
    somebody to average it.
    """
    a, b = target.grapheme, other.grapheme
    distance = abs(target.order - other.order)
    if b in _partners(REVERSALS, a):
        return (_TIER_REVERSAL, distance)
    if b in _partners(SIMILAR, a):
        return (_TIER_SIMILAR, distance)
    if _shares_a_letter(a, b):
        return (_TIER_SHARED, distance)
    return (_TIER_ORDER, distance)


def _candidates(corpus: Corpus, ceiling: Ceiling, target: Gpc) -> list[Gpc]:
    """Every taught GPC that could legitimately be a wrong tile.

    One per *grapheme*: where the ceiling permits two GPCs spelled the same way
    (``oo`` long and short), the earlier-taught one stands for both, because the
    tile a child sees is the spelling and they cannot be asked to choose between
    two of them.
    """
    seen: dict[str, Gpc] = {}
    for gpc in sorted(corpus.gpcs, key=lambda g: g.order):
        if gpc.id not in ceiling.gpc_ids:
            continue
        if gpc.grapheme == target.grapheme:
            continue
        seen.setdefault(gpc.grapheme, gpc)
    return list(seen.values())


def choose_distractors(
    corpus: Corpus,
    ceiling: Ceiling,
    target: Gpc,
    *,
    count: int = 3,
    rng: random.Random | None = None,
) -> list[Gpc]:
    """The wrong tiles, most confusable first.

    Returns **fewer than ``count``** when the ceiling does not hold enough
    graphemes -- a child three days into Phase 2 set 1 gets a board of three
    tiles, not four, and never a fourth tile borrowed from next term. Padding
    the board is exactly the failure mode this module exists to prevent.
    """
    rng = rng or random.Random(target.order)
    pool = _candidates(corpus, ceiling, target)
    # Shuffle first, then sort: the sort is stable, so the shuffle decides only
    # between candidates the design considers equally good.
    rng.shuffle(pool)
    pool.sort(key=lambda gpc: confusability(target, gpc))
    return pool[: max(0, count)]


def find_it_options(
    corpus: Corpus,
    ceiling: Ceiling,
    target: Gpc,
    *,
    count: int = BOARD_TILES,
    rng: random.Random | None = None,
) -> list[Gpc]:
    """The whole board: the target plus its distractors, in tile order.

    Shuffled, because a correct answer that is always in the same place is a
    position-memory task rather than a grapheme task -- and a five-year-old will
    find the pattern before an adult notices there is one.

    ``count`` is held to :data:`CHOICE_CEILING` (ADR-0013). A caller asking for
    more is asking for a decision a five-year-old has to hold more of than they
    can, and the honest thing to do with it is to say so in the log and give
    them five -- refusing outright would turn a design mistake into a child
    staring at a screen that will not start.
    """
    if count > CHOICE_CEILING:
        log.warning(
            "a Find it board of %d was asked for; ADR-0013 caps a choice set at %d",
            count,
            CHOICE_CEILING,
        )
        count = CHOICE_CEILING
    rng = rng or random.Random(target.order)
    board: list[Gpc] = [target, *choose_distractors(corpus, ceiling, target, count=count - 1, rng=rng)]
    rng.shuffle(board)
    return board


def board_graphemes(board: Sequence[Gpc]) -> list[str]:
    """What the child actually sees. Used by tests and by the log line."""
    return [gpc.grapheme for gpc in board]
