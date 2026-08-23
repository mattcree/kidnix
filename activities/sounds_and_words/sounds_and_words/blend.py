"""Blend it: a word, its sound buttons, and the moment they are pushed together.

Letters and Sounds p.70's convention, which is the one on every UK classroom
whiteboard and therefore the one a child arrives already able to read:

* a **dot** under a grapheme that is one letter -- ``c`` ``a`` ``t``
* a **bar** under a grapheme that is two or more -- ``sh`` ``igh`` ``ck``, and
  the doubled consonants, because L&S p.70 says in as many words that a doubled
  letter "represents one phoneme"

The bar is not decoration. It is the entire visual claim that ``sh`` is *one
sound*, and a child who has been taught with bars and is then shown two dots
under ``sh`` has been told the opposite of what their teacher told them.

Split digraphs get a third mark, :attr:`Mark.SPLIT` -- two dots joined by a
line under ``a`` and ``e`` with the consonant between them. It is the classroom
convention and it is also the honest one: the two letters really are one sound
and really are not adjacent. Nothing in the v1 ceiling reaches Phase 5, so this
is a shape the widget layer draws and nothing exercises yet; it is here because
a model that could not express it would have to be rewritten rather than
extended.

**The push-together is never a gate.** A child who already knows the word can
press the arrow immediately; a child who wants to hear ``c`` eleven times can.
There is no order to get right, nothing is locked, and pressing the arrow first
is not a mistake -- research 10 open question 2 is whether sound buttons help or
entrench sound-by-sound reading, and an activity that *forced* every button
before the word could be heard would have answered that question the wrong way
by construction.

**And then it stops being software's job.** After the word is blended the loop
hands over: "say it to someone". kidnix never listens to a child read and never
grades it (research 10 section 4.6 #6). The grown-up card is the mechanism, and
the McTigue moderator -- g = -0.02 without an adult, 0.48 with one -- is the
reason it is in the loop rather than in a settings screen.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path

from .ceiling import Ceiling, check_word
from .corpus import Corpus, Gpc, Word
from .phonemes import say_label
from .pictures import picture_for

__all__ = [
    "BlendState",
    "BlendWord",
    "Mark",
    "SoundButton",
    "Stage",
    "blend_word",
    "mark_for",
]


class Mark(StrEnum):
    """What is drawn under one grapheme."""

    #: One letter, one sound: a dot.
    DOT = "dot"
    #: Two or more adjacent letters, one sound: a bar.
    BAR = "bar"
    #: A split digraph: two dots joined under the letters either side.
    SPLIT = "split"


class Stage(StrEnum):
    """Where one word has got to. Three steps, and no way to fail any of them."""

    #: The tiles are apart and the sound buttons are live.
    SOUNDS = "sounds"
    #: The arrow was pressed: the tiles have slid together and the word was said.
    PUSHED = "pushed"
    #: "Say it to someone" -- the grown-up's turn. Software has stopped judging.
    SAY_IT = "say_it"


def mark_for(gpc: Gpc) -> Mark:
    """Dot, bar or split, from the corpus's own ``kind`` field."""
    if gpc.split:
        return Mark.SPLIT
    return Mark.DOT if len(gpc.grapheme) == 1 else Mark.BAR


@dataclass(frozen=True)
class SoundButton:
    """One grapheme in the word, and the button under it."""

    index: int
    gpc_id: str
    grapheme: str
    label: str
    mark: Mark

    @property
    def is_multigraph(self) -> bool:
        return self.mark is not Mark.DOT


@dataclass(frozen=True)
class BlendWord:
    """A decodable word, ready to be put on a screen.

    Built only through :func:`blend_word`, which will not build one for a word
    the ceiling refuses. That is deliberate: this dataclass is the last place a
    word could reach a child, and a constructor that accepted anything would be
    a way round the gate.
    """

    text: str
    buttons: tuple[SoundButton, ...]
    picture: Path | None = None
    source: str = ""

    @property
    def phonemes(self) -> tuple[str, ...]:
        """What the buttons say, in order. ``("c", "a", "t")``."""
        return tuple(button.label for button in self.buttons)

    @property
    def has_multigraph(self) -> bool:
        """Does this word carry a bar? The words worth choosing usually do."""
        return any(button.is_multigraph for button in self.buttons)

    def __len__(self) -> int:
        """How many *sounds*, which is never how many letters."""
        return len(self.buttons)


def blend_word(
    corpus: Corpus,
    word: Word | str,
    ceiling: Ceiling,
    *,
    picture_dir: Path | None = None,
) -> BlendWord:
    """Build the screen model for one word, or refuse to.

    Raises :class:`ValueError` when the word is above the ceiling or has no
    segmentation on record. The caller is always the schedule, which chose the
    word from ``allowed_words()`` in the first place, so a raise here means a
    bug upstream -- and a bug upstream is exactly the thing that must not
    degrade into showing the word anyway.
    """
    text = word.text if isinstance(word, Word) else str(word).strip().lower()
    verdict = check_word(corpus, text, ceiling)
    if not verdict.allowed:
        raise ValueError(verdict.explanation)
    if not verdict.graphemes:
        raise ValueError(f"{text!r} has no segmentation to put buttons under")

    by_id = corpus.gpc_by_id
    buttons: list[SoundButton] = []
    for index, gpc_id in enumerate(verdict.graphemes):
        gpc = by_id.get(gpc_id)
        if gpc is None:  # pragma: no cover - a corrupt corpus, not a bad word
            raise ValueError(f"{text!r} refers to unknown GPC {gpc_id!r}")
        buttons.append(
            SoundButton(
                index=index,
                gpc_id=gpc.id,
                grapheme=gpc.grapheme,
                label=say_label(gpc),
                mark=mark_for(gpc),
            )
        )

    known = word if isinstance(word, Word) else corpus.word_by_text.get(text)
    return BlendWord(
        text=text,
        buttons=tuple(buttons),
        picture=picture_for(text, directory=picture_dir),
        source=known.source if known is not None else "",
    )


@dataclass
class BlendState:
    """What has happened to one word on the screen so far.

    Instrumentation, not scoring (research 10 section 4.4). Nothing here is
    shown to the child as a number, nothing gates anything, and the only thing
    it is used for is deciding which sentence to say next.
    """

    word: BlendWord
    stage: Stage = Stage.SOUNDS
    #: Indices of the buttons that have been pressed at least once.
    sounded: set[int] = field(default_factory=set)

    @property
    def all_sounded(self) -> bool:
        """Has every sound been heard? A prompt hint, never a lock."""
        return len(self.sounded) >= len(self.word.buttons)

    def sound(self, index: int) -> SoundButton | None:
        """Press one sound button. Returns it, or ``None`` if there is no such button."""
        if not 0 <= index < len(self.word.buttons):
            return None
        self.sounded.add(index)
        return self.word.buttons[index]

    def push(self) -> Stage:
        """Press the arrow: the tiles slide together and the word is said."""
        self.stage = Stage.PUSHED
        return self.stage

    def hand_over(self) -> Stage:
        """Move to the grown-up's turn. The last thing software does with this word."""
        self.stage = Stage.SAY_IT
        return self.stage
