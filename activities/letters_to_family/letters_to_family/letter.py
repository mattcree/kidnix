"""What a letter *is*, and the one rule the whole activity exists to keep.

    **No spelling correction** -- invented spelling *is* the Year 1 curriculum.
    -- docs/research/05-learning-science.md section 3

So :attr:`Letter.caption` is a string this module receives and never touches.
It is not stripped, not title-cased, not spell-checked, not normalised, not
collapsed. ``i sor a dog at the parc`` goes into ``caption.txt``, into the
rendered card and into the outbox exactly as the child typed it, byte for byte,
and :mod:`letters_to_family.tests.test_letter` asserts that on a caption with
four misspellings and a double space in it. The GTK side matches: the entry has
no completion, no input-purpose spellcheck and no red squiggle.

The rest of the shape follows 05 section 3's sentence about what a
five-year-old's letter legitimately is -- "a drawing, three words, and a
recorded 'I love you Grandad'":

============ ==============================================================
picture      **required.** A Journal drawing the child chose, or a scribble
             they made here. A letter with no picture is a text message.
caption      optional. The child's own words, or a grown-up's, or none.
voice        optional. Twenty seconds, the shell's own recorder.
recipient    **required**, and from the parent-approved list only.
============ ==============================================================

:data:`STATUS_WAITING` is the other load-bearing constant. Every letter this
activity writes is marked *waiting for a grown-up to send*, in the Journal and
in the outbox, because SYNTHESIS H1 means the letter never leaves the machine by
itself and a status of "sent" would be a lie told by a program that has no
network. Nothing in the child session ever changes it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path

from .i18n import N_, _
from .recipients import Recipient, slugify

__all__ = [
    "CAPTION_NAME",
    "CARD_NAME",
    "KIND",
    "LETTER_FOR",
    "META_NAME",
    "PICTURE_NAME",
    "SOMEONE",
    "STATUS_UNPOSTED",
    "STATUS_WAITING",
    "VOICE_NAME",
    "CaptionSource",
    "Letter",
    "PictureSource",
    "Step",
    "letter_title",
    "outbox_name",
]

#: The Journal ``kind`` and the word a card in My Things is filed under.
KIND = "letter"

#: **The only status this activity can write.** The child session has no egress
#: (SYNTHESIS H1); a grown-up takes the letter out of the outbox and sends it,
#: and until they do this is what is true. Written into the Journal meta and
#: into the outbox manifest so that both say the same thing to whoever reads
#: them next.
STATUS_WAITING = "waiting for a grown-up to send"

#: What is true of a letter the child made but never pressed **Post it** on --
#: put away when the session ended, with the picture and the words safe in the
#: Journal and **no outbox copy**. A grown-up who was never asked to send
#: something must not find it in the folder they send things out of.
STATUS_UNPOSTED = "not posted -- Post it was never pressed"

#: TRANSLATORS: the Journal card's title when the child wrote no words.
#: {name} is a person -- "A letter for Grandad".
LETTER_FOR = N_("A letter for {name}")
#: Who a letter is for when we somehow do not know. Said out loud, so it is a
#: word rather than a blank.
SOMEONE = N_("someone")

#: Filenames inside an outbox directory. Boring, conventional and open (F4): a
#: parent opens the folder in Files and sees a picture, a card and a recording.
PICTURE_NAME = "picture.png"
CARD_NAME = "letter.png"
VOICE_NAME = "note.ogg"
CAPTION_NAME = "caption.txt"
META_NAME = "letter.json"


class Step(Enum):
    """The one predictable flow. Forward only, and short.

    There is no branching and no menu: a child who has pressed Grandad is on
    the picture screen, and a child who has chosen a picture is on the words
    screen. :data:`Step.SHELF` is off to one side -- reading is not making, and
    it does not sit in the middle of writing a letter.
    """

    WHO = "who"
    PICTURE = "picture"
    WORDS = "words"
    POSTED = "posted"
    SHELF = "shelf"
    #: A grown-up has not added anybody. One card, one line, and out.
    NOBODY = "nobody"


class PictureSource(Enum):
    """Where the picture came from. Recorded for the grown-up, not scored."""

    JOURNAL = "journal"
    DRAWING = "drawing"


class CaptionSource(Enum):
    """Whose words these are, which is the one thing a reader must not guess.

    A grown-up reading ``i luv u grandad`` should know it is the child's own
    spelling and not a typo of theirs; a grown-up reading a tidy sentence
    should know a grown-up wrote it down. Recorded in the meta and printed on
    the card in different type. It is **not** a judgement of either.
    """

    #: The child typed it themselves. Untouched, always.
    CHILD = "child"
    #: A grown-up wrote down what the child said (the co-use route).
    GROWNUP = "grown-up"
    #: There are no written words -- a picture, or a picture and a voice.
    NONE = "none"


def letter_title(recipient: Recipient | None) -> str:
    """The card's title in My Things when there are no written words.

    "A letter for Grandad" -- so a pre-reader looking at the shelf is told who
    it was for, which is the fact the whole activity is about. When the child
    *has* written something, the SDK's ``title_for`` uses their words instead,
    and that is the better answer: the card then says what they said.
    """
    name = recipient.name if recipient is not None else _(SOMEONE)
    return _(LETTER_FOR).format(name=name)


def outbox_name(recipient: Recipient, when: datetime) -> str:
    """``20260823-153200-grandad`` -- the outbox directory's name.

    A timestamp and a name, in that order, so a grown-up's file manager sorts
    the folder chronologically without being asked. The digits are in a
    directory name a **grown-up** reads in Files; 01 #19 is about what a child
    sees and hears, and no child sees this.
    """
    return f"{when.strftime('%Y%m%d-%H%M%S')}-{slugify(recipient.slug)}"


@dataclass
class Letter:
    """One letter, being made. Mutable, because it is being made.

    Everything about it is optional except the recipient and, by the time it is
    posted, the picture -- :meth:`can_post` is the whole of the gate, and it is
    deliberately not "is it good enough". There is no minimum number of words,
    no minimum number of strokes and no check on either.
    """

    recipient: Recipient
    picture: Path | None = None
    picture_source: PictureSource | None = None
    #: **The child's own spelling. Never touched by anything in this package.**
    caption: str = ""
    caption_source: CaptionSource = CaptionSource.NONE
    voice: Path | None = None
    created: datetime = field(default_factory=datetime.now)

    # -- what is true about it --

    @property
    def has_words(self) -> bool:
        """Is there anything written? A caption of spaces is not words."""
        return bool(self.caption.strip())

    @property
    def has_voice(self) -> bool:
        try:
            return self.voice is not None and self.voice.is_file()
        except OSError:  # pragma: no cover - a disk that went away
            return False

    @property
    def has_picture(self) -> bool:
        try:
            return self.picture is not None and self.picture.is_file()
        except OSError:  # pragma: no cover
            return False

    def can_post(self) -> bool:
        """A picture is the floor, and it is the only floor.

        05 section 3: "a 5-year-old's letter is legitimately a drawing, three
        words, and a recorded 'I love you Grandad'" -- the drawing is the part
        that is always there. Requiring words as well would make this a writing
        test, and a child who cannot yet write would be locked out of the one
        activity in the suite that is *about* having an audience.
        """
        return self.has_picture

    # -- what it says about itself --

    def set_caption(self, text: str, source: CaptionSource) -> None:
        """Take the words as given. **The only writer of ``caption``.**

        There is no ``.strip()`` here and there is not going to be one. A
        trailing space is not a mistake worth correcting in a five-year-old's
        first letter, and the moment this method starts tidying is the moment
        somebody adds a spell-checker underneath it.
        """
        self.caption = text
        self.caption_source = source if text else CaptionSource.NONE

    def title(self) -> str:
        return letter_title(self.recipient)

    def meta(self, status: str = STATUS_WAITING) -> dict:
        """What goes in ``meta.json`` beside the Journal entry, and in the
        outbox manifest. For a grown-up and for the panel; never for a score.

        ``status`` is one of exactly two strings and neither of them is "sent":
        :data:`STATUS_WAITING` for a letter the child posted, and
        :data:`STATUS_UNPOSTED` for one the session ended in the middle of.
        Nothing in the child session can send anything (SYNTHESIS H1), so
        nothing in the child session writes a third.
        """
        return {
            "recipient": {
                "id": self.recipient.id,
                "name": self.recipient.name,
                "relation": self.recipient.relation,
            },
            "status": status,
            "caption_source": self.caption_source.value,
            "picture_source": (
                self.picture_source.value if self.picture_source is not None else ""
            ),
            "has_voice": self.has_voice,
            "created": self.created.isoformat(timespec="seconds"),
        }

    def outbox_name(self) -> str:
        return outbox_name(self.recipient, self.created)
