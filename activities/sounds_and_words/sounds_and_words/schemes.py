"""Translating "which programme does his school use?" into a ceiling.

kidnix ships one full ordering -- Letters and Sounds (2007), because it is the
only complete English SSP progression with an open licence and published word
banks. Schools mostly use something else. Research 10, section 4.5 sets the
policy this module implements:

* the mapping exists **only** to turn a parent's answer into a ceiling. It is
  never presented to the child, and kidnix never uses a scheme's own vocabulary;
* where a scheme's order genuinely differs, take the **intersection**: permit
  only the GPCs taught by *both* orderings up to that point;
* "I don't know" starts at Letters and Sounds Phase 2 Set 1, with a nudge to ask
  the teacher. Starting too low costs nothing;
* there is no silent auto-advance. Ever.

Other schemes ship as *stubs* in ``data/schemes/other_schemes.toml``: named,
with their status recorded, and with no ordering claimed. A stub resolves to the
Letters and Sounds prefix and is marked conservative, so the parent pane can say
so honestly. Filling one in means transcribing that scheme's published order,
which is a licensing question per scheme, not a coding one.
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from .ceiling import Ceiling, ceiling_from_order, intersect
from .corpus import Corpus, data_dir

DEFAULT_SCHEME = "letters_and_sounds"
UNKNOWN_SCHEME_NOTE = (
    "We do not know which programme this school uses, so kidnix is starting at "
    "the very beginning. Ask the teacher which sounds they have taught."
)


@dataclass(frozen=True)
class Scheme:
    id: str
    name: str
    status: str
    source: str
    order: tuple[str, ...] = ()
    note: str = ""

    @property
    def has_own_order(self) -> bool:
        return bool(self.order)


@lru_cache(maxsize=4)
def load_schemes(path: str | None = None) -> dict[str, Scheme]:
    root = (Path(path) if path else data_dir()) / "schemes"
    schemes: dict[str, Scheme] = {}
    for file in sorted(root.glob("*.toml")):
        with file.open("rb") as fh:
            doc = tomllib.load(fh)
        for row in doc.get("scheme", []):
            schemes[row["id"]] = Scheme(
                id=row["id"],
                name=row["name"],
                status=row["status"],
                source=row.get("source", ""),
                order=tuple(row.get("order", ())),
                note=row.get("note", ""),
            )
    return schemes


def scheme_ceiling(
    corpus: Corpus, scheme: Scheme, last_grapheme: str
) -> Ceiling | None:
    """The prefix of a scheme's *own* order, as a ceiling. ``None`` for a stub."""
    if not scheme.has_own_order:
        return None
    by_id = corpus.gpc_by_id
    ids = list(scheme.order)
    target = last_grapheme
    if target not in ids:
        matches = [i for i in ids if i in by_id and by_id[i].grapheme == last_grapheme]
        if not matches:
            raise KeyError(f"{last_grapheme!r} is not in scheme {scheme.id!r}")
        target = matches[0]
    known = [i for i in ids[: ids.index(target) + 1] if i in by_id]
    order = max((by_id[i].order for i in known), default=0)
    return Ceiling(
        scheme=scheme.id,
        label=f"{scheme.name}: up to {last_grapheme!r}",
        order=order,
        phase=max((by_id[i].phase for i in known), default=1),
        gpc_ids=frozenset(known),
        graphemes=frozenset(by_id[i].grapheme for i in known),
        tricky_words=ceiling_from_order(corpus, order, scheme=scheme.id).tricky_words,
        conservative=False,
    )


def resolve_ceiling(
    corpus: Corpus,
    scheme_id: str | None,
    last_grapheme: str | None,
    *,
    schemes: dict[str, Scheme] | None = None,
) -> Ceiling:
    """The one entry point the parent panel calls.

    ``scheme_id`` of ``None`` or ``"unknown"`` and ``last_grapheme`` of ``None``
    both mean "start at the beginning".
    """
    table = schemes if schemes is not None else load_schemes()
    ls = ceiling_from_order(
        corpus,
        corpus.order_of_last_grapheme(last_grapheme) if last_grapheme else 0,
        label=f"up to {last_grapheme!r}" if last_grapheme else "nothing taught yet",
    )

    if scheme_id in (None, "", "unknown"):
        first = min(corpus.gpcs, key=lambda g: g.order)
        base = ceiling_from_order(
            corpus,
            corpus.order_of_last_grapheme(last_grapheme) if last_grapheme else first.order,
            label=f"up to {last_grapheme!r}" if last_grapheme else "the very first sounds",
        )
        return Ceiling(
            scheme="unknown",
            label=base.label,
            order=base.order,
            phase=base.phase,
            gpc_ids=base.gpc_ids,
            graphemes=base.graphemes,
            tricky_words=base.tricky_words,
            conservative=True,
            notes=(UNKNOWN_SCHEME_NOTE,),
        )

    if scheme_id not in table:
        raise KeyError(f"unknown scheme {scheme_id!r}")
    scheme = table[scheme_id]

    if scheme.id == DEFAULT_SCHEME:
        return ls

    own = scheme_ceiling(corpus, scheme, last_grapheme) if last_grapheme else None
    if own is None:
        note = scheme.note or (
            f"kidnix does not ship {scheme.name}'s own order of sounds, so it is using the "
            "Letters and Sounds order instead. That may mean it holds back a sound the "
            "school has already taught. It will never go ahead of them."
        )
        return Ceiling(
            scheme=scheme.id,
            label=f"{scheme.name}: {ls.label}",
            order=ls.order,
            phase=ls.phase,
            gpc_ids=ls.gpc_ids,
            graphemes=ls.graphemes,
            tricky_words=ls.tricky_words,
            conservative=True,
            notes=(note,),
        )

    return intersect(own, ls, label=f"{scheme.name}: up to {last_grapheme!r}")
