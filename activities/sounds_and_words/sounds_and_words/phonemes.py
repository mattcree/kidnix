"""Saying a *sound* out loud, which is not the same as saying a word.

The single most common error in phonics software is the schwa: /s/ said as
"suh", /t/ as "tuh". A child who blends "suh-a-tuh" does not get "sat", and a
teacher then has to un-teach it. Every general-purpose TTS engine does this,
Piper included, because it is synthesising an *utterance* and an isolated
consonant is not one. Hence the rule in ``docs/design/sounds-and-words.md``
section 9: **never synthesise a phoneme.**

So there are two routes to a sound, and this module is the one place that knows
which one a given GPC is on:

``RECORDED``
    A real recording of an adult saying the phoneme, played as audio. The a-z
    clips exist already: GCompris ships ``voices-en_GB``, CC-BY-SA-4.0, and it
    is in the image (``docs/LICENSES.md``). See :data:`GCOMPRIS_BUNDLE_DIR` for
    why they are not readable *yet*.

``SPELLED``
    A **placeholder**, and marked as one everywhere it is used. The phoneme's
    kidnix-safe label -- "sss", "shh", "ay" -- spoken through the ordinary
    voice. These are spelled so that an en-GB engine says something close to
    the sound rather than the letter's name, and they are the strings the
    corpus already blacklist-checks for schwa spellings
    (``tests/test_corpus.py``). It is honest for "sss" and thin for "ck"; it is
    what week 2 can ship without a microphone, and §11 of the design note
    carries the row that says so.

Nothing here decides *whether* to speak. That is the activity's business, and
in calm mode or with the voice muted the caption still carries the line.

The two things a reader should not have to find out the hard way
---------------------------------------------------------------

1. **The GCompris clips are inside a Qt ``.rcc`` bundle, not on disk.**
   ``/usr/share/gcompris-qt/rcc/data3/voices-ogg/voices-en_GB-*.rcc`` is a Qt
   resource archive; ``build_files/55-gcompris.sh`` already reads its name table
   to assert ``alphabet/U0061.ogg`` .. ``U007A.ogg`` are present. Getting them
   out is a build-stage job (unpack once into :data:`CLIP_DIR`), it belongs in
   ``build_files/``, and this activity does not own that directory. Until that
   lands every GPC resolves to ``SPELLED``, which is why the fallback had to be
   good enough to ship on its own.

2. **A digraph clip does not exist anywhere yet.** Research 10 section 5 and
   open question 8: ~20 clips, one adult, one morning, and they become kidnix's
   own CC-BY-SA asset. Nothing in this module pretends otherwise --
   :func:`missing_recordings` is what the design note's licensing table is
   generated from.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from .corpus import Gpc

__all__ = [
    "CLIP_DIR",
    "GCOMPRIS_BUNDLE_DIR",
    "Phoneme",
    "Source",
    "missing_recordings",
    "phoneme_for",
    "say_label",
    "yes_line",
]

#: Where an unpacked phoneme clip would live, one ``.ogg`` per **GPC id** --
#: ``oo_long.ogg`` and ``oo_short.ogg`` are different sounds and must be
#: different files, which is the whole reason the corpus gives every GPC an id
#: rather than keying on the grapheme.
CLIP_DIR = Path("/usr/share/kidnix/sounds-and-words/phonemes")

#: The GCompris bundles the a-z recordings are currently locked inside. Named
#: here so that the follow-up is findable from the code that needs it, not only
#: from a design note. See the module docstring.
GCOMPRIS_BUNDLE_DIR = Path("/usr/share/gcompris-qt/rcc/data3/voices-ogg")

#: "oo (long, as in moon)" -> "oo". The parenthetical in ``spoken_label`` is
#: written for a **grown-up reading the corpus**, so they can tell two GPCs with
#: the same grapheme apart. Saying it to a child would be saying a sentence
#: where a sound belongs.
_ASIDE = re.compile(r"\s*\(.*\)\s*$")


class Source(StrEnum):
    """Where the sound a child hears actually comes from."""

    #: A recording of a person. What this should always be.
    RECORDED = "recorded"
    #: The kidnix-safe spelling, spoken by the ordinary voice. A placeholder.
    SPELLED = "spelled"


@dataclass(frozen=True)
class Phoneme:
    """One GPC's sound, and the honest provenance of it."""

    gpc_id: str
    grapheme: str
    label: str
    source: Source
    clip: Path | None = None

    @property
    def is_placeholder(self) -> bool:
        """Should a reviewer be told this is not a recording? Usually yes."""
        return self.source is Source.SPELLED


def say_label(gpc: Gpc) -> str:
    """What to *say* for this GPC. Never the letter's name, never a sentence.

    The corpus's ``spoken_label`` minus the disambiguating aside. Empty labels
    cannot happen -- the generator asserts every GPC has one -- but an empty
    string here would be a silent control, so the grapheme stands in.
    """
    label = _ASIDE.sub("", (gpc.spoken_label or "").strip())
    return label or gpc.grapheme


def phoneme_for(gpc: Gpc, *, clip_dir: Path | None = None) -> Phoneme:
    """Resolve one GPC to a clip if there is one, and to its label if not."""
    root = CLIP_DIR if clip_dir is None else clip_dir
    clip = root / f"{gpc.id}.ogg"
    if clip.is_file():
        return Phoneme(gpc.id, gpc.grapheme, say_label(gpc), Source.RECORDED, clip)
    return Phoneme(gpc.id, gpc.grapheme, say_label(gpc), Source.SPELLED, None)


def missing_recordings(gpcs: Iterable[Gpc], *, clip_dir: Path | None = None) -> list[str]:
    """Every GPC id with no recording, in teaching order.

    The list that has to reach zero before the design note may stop calling the
    audio a placeholder. It is a function rather than a constant because the
    answer depends on what is installed on *this* machine.
    """
    return [
        gpc.id
        for gpc in sorted(gpcs, key=lambda g: g.order)
        if phoneme_for(gpc, clip_dir=clip_dir).source is Source.SPELLED
    ]


def yes_line(gpc: Gpc) -> str:
    """What the child hears when they got it: "yes, sss".

    Informational, not evaluative (research 05 section 2f). It names the sound
    they just found, which is the useful half; "well done" names them, which is
    the half the evidence says to leave out.
    """
    return f"yes, {say_label(gpc)}"
