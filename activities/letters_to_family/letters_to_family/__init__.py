"""Letters -- a picture, a few words and your voice, for somebody real.

`docs/research/05-learning-science.md` section 3 calls this, on balance, **the
strongest activity in the kidnix list**, and it says why in one line: *purpose
and audience are the EEF's named mechanism*. A five-year-old writes because
somebody they love is going to read it, not because a program asked them to.
Everything here follows from that sentence and from the four bullets under it:

* **A real, named recipient** from the parent-approved ``[[family]]`` list. The
  child sees a photo and a name, never an address -- there is no address
  anywhere in this package.
* **Picture + caption + voice.** "A 5-year-old's letter is legitimately a
  drawing, three words, and a recorded 'I love you Grandad.'" So the picture is
  the only required part, the words are optional, and the voice is optional.
* **Show the reply.** "A one-way outbox is not an audience." The inbox shelf is
  in v1 for exactly that reason, even read-only.
* **A prompt scaffold, not a template.** "Tell them one thing that happened
  today" is spoken and replayable; nothing is filled in for the child.
* **No spelling correction** -- invented spelling *is* the Year 1 curriculum.
  :class:`~letters_to_family.letter.Letter` receives the caption and never
  touches it: not stripped, not cased, not checked, all the way to
  ``caption.txt``, the rendered card and the outbox.

And the constraint that shapes the ending: **the letter never leaves the machine
by itself** (SYNTHESIS H1 -- no network egress from the child session). The
activity writes a Journal entry and an outbox folder, marks it *waiting for a
grown-up to send*, and says so out loud: "Posted! A grown-up will send it to
Grandad." It promises nothing about when a reply comes back, because nothing on
this machine knows.

The flow, once, in order, and it is the only one:

    **Who for?** -> **Make it** (a picture, then words or a voice or a grown-up's
    hand) -> **Post it** -> *"Letters for you"* whenever there is something in
    the inbox.

**Importing this package imports no GTK.** Everything the activity knows -- who
may be written to, what a letter is, where the outbox goes, what is in the
inbox, which of the child's own pictures can be sent, what is said, what a key
means -- is in the pure modules here and is tested headless.
:mod:`letters_to_family.draw` imports ``cairo``, which is also displayless, so
even the letter card itself is exercised without a window. The window lives in
:mod:`letters_to_family.activity` and is imported only by the entry point.

The one-line acceptance test: *a five-year-old can press Grandad's face, choose
the dinosaur they drew on Tuesday, type ``i sor a dinosor``, record "I love you
Grandad", press Post it, hear "Posted! A grown-up will send it to Grandad", and
a grown-up finds all three files in* ``/var/lib/kidnix/outbox`` *with the
spelling exactly as it was typed.*
"""

from .assemble import Posted, post_letter
from .draw import draw_placeholder, render_card, render_scribble
from .env import quiet
from .i18n import N_
from .journal_read import JournalPicture, read_entry, recent_pictures
from .keys import guard_ring, ring_consumes
from .letter import (
    KIND,
    STATUS_UNPOSTED,
    STATUS_WAITING,
    CaptionSource,
    Letter,
    PictureSource,
    Step,
    letter_title,
    outbox_name,
)
from .mailbox import (
    INBOX_ROOT,
    OUTBOX_ROOT,
    Reply,
    inbox_dir,
    inbox_replies,
    outbox_dir,
    post,
)
from .recipients import Recipient, load_recipients, recipients_from_document, slugify
from .scribble import COLOURS, Colour, Scribble, Stroke
from .words import posted_line, reply_line, your_letter_for

#: The manifest id the shell launches this as, and the id every Journal entry is
#: filed under. A slug, and the identity everywhere that matters.
ACTIVITY_ID = "letters"
#: The window title, and the word on the tile. A msgid: the use site calls
#: ``_()`` on it once a child's language is known (ADR-0012).
TITLE = N_("Letters")

__all__ = [
    "ACTIVITY_ID",
    "COLOURS",
    "INBOX_ROOT",
    "KIND",
    "OUTBOX_ROOT",
    "STATUS_UNPOSTED",
    "STATUS_WAITING",
    "TITLE",
    "CaptionSource",
    "Colour",
    "JournalPicture",
    "Letter",
    "PictureSource",
    "Posted",
    "Recipient",
    "Reply",
    "Scribble",
    "Step",
    "Stroke",
    "draw_placeholder",
    "guard_ring",
    "inbox_dir",
    "inbox_replies",
    "letter_title",
    "load_recipients",
    "outbox_dir",
    "outbox_name",
    "post",
    "post_letter",
    "posted_line",
    "quiet",
    "read_entry",
    "recent_pictures",
    "recipients_from_document",
    "render_card",
    "render_scribble",
    "reply_line",
    "ring_consumes",
    "slugify",
    "your_letter_for",
]

__version__ = "0.1.0"
