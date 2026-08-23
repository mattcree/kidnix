"""Posting: Journal first, outbox second, and never the other way round.

One function, and the order in it is the whole design.

1. **Render the card** (:func:`letters_to_family.draw.render_card`) into a
   scratch directory. If this fails there is still a picture and still a
   caption, and the letter is posted without a card rather than not at all.
2. **Write the Journal entry** with the SDK's own ``save_entry``. This is the
   child's copy, on the child's own disk, in the layout My Things reads. It
   raises ``JournalError`` if it cannot, and that is correct: SDK section 8 --
   "losing the thing they just made is the one failure that is not survivable".
3. **Copy into the outbox** (:func:`letters_to_family.mailbox.post`). This is
   the *grown-up's* copy. Every failure is swallowed and logged, because the
   child's letter is already safe and a permissions problem on
   ``/var/lib/kidnix`` must not become "your letter did not work".

The Journal entry is ``kind = "letter"``, which is what makes the card in My
Things a letter rather than a drawing, and its ``meta`` carries the recipient
and :data:`~letters_to_family.letter.STATUS_WAITING`. Nothing in the child
session ever writes any other status, because nothing in the child session can
send anything (SYNTHESIS H1).

The files kept, in version order, are the **card first** and the picture second.
Version order is what the shell thumbnails and what "resume" opens, so the card
-- the letter, with the words on it -- is the thing a child sees on the shelf,
and the bare drawing is kept behind it because a grown-up exporting the entry
should get both.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from . import draw
from .letter import CARD_NAME, KIND, STATUS_WAITING, Letter, letter_title
from .mailbox import post

log = logging.getLogger(__name__)

__all__ = ["Posted", "SaveEntry", "post_letter"]


class SaveEntry(Protocol):
    """The SDK's ``save_entry``, as much of it as this module uses.

    A protocol rather than an import so that the pure tests can post a letter,
    assert the whole shape of what was kept, and never need ``kidnix_shell`` or
    a display.

    **The signature is exact, and ``**kwargs`` is deliberately not in it.** An
    earlier version ended in ``**kwargs: Any``, which made the protocol *wider
    than any real callee*: a test double swallowed ``activity_name`` happily,
    every headless test passed, and the first press of **Post it** on a real
    machine raised ``TypeError`` -- because the callee the activity actually
    passed was :meth:`kidnix_activity.app.ActivityApplication.save_entry`,
    which pins ``activity_name`` to the window title and takes no such argument.
    A protocol that cannot be satisfied by the wrong function is the only kind
    worth having, so this one names every parameter and no more.

    The two functions that satisfy it:

    * :func:`kidnix_activity.journal.save_entry` -- the SDK's own writer, which
      takes ``activity_name`` (and ``launch``);
    * :meth:`letters_to_family.activity.LettersActivity.save_entry` -- the thin
      wrapper that supplies ``launch`` and is what the activity passes.

    ``ActivityApplication.save_entry`` does **not** satisfy it, and
    ``tests/test_assemble.py`` asserts that by introspection so the mistake
    cannot be made twice.
    """

    def __call__(
        self,
        kind: str,
        files: list[Path],
        caption: str | None = ...,
        voice: Path | None = ...,
        meta: dict | None = ...,
        *,
        activity_name: str = ...,
    ) -> Any: ...


@dataclass(frozen=True)
class Posted:
    """What happened. Both halves, so the caller can say the honest thing."""

    entry: Any
    card: Path
    outbox: Path | None

    @property
    def entry_id(self) -> str:
        return str(getattr(self.entry, "id", ""))

    @property
    def in_outbox(self) -> bool:
        """Did the grown-up's copy land? Logged, and shown to nobody.

        A child is told "Posted! A grown-up will send it to Grandad" either way,
        because that sentence is true either way: the grown-up's route to a
        letter that is only in the Journal is Export, which is the same route
        they use for everything else on this machine.
        """
        return self.outbox is not None


def post_letter(
    letter: Letter,
    save_entry: SaveEntry,
    scratch: Path,
    profile_id: str = "",
    *,
    status: str = STATUS_WAITING,
    to_outbox: bool = True,
    outbox_root: Path | None = None,
    render: Any = None,
) -> Posted:
    """Keep the letter, then copy it out. Raises only if the Journal fails.

    ``to_outbox=False`` with ``status=STATUS_UNPOSTED`` is the put-away path:
    the session ended before the child pressed **Post it**, so the work is kept
    in the Journal -- where it is theirs and where My Things shows it -- and
    nothing is put in the folder a grown-up sends things out of.
    """
    scratch.mkdir(parents=True, exist_ok=True)
    card = scratch / CARD_NAME
    renderer = render if render is not None else draw.render_card
    try:
        renderer(
            card,
            letter.picture,
            letter.caption,
            letter.recipient.name,
            child_hand=letter.caption_source.value != "grown-up",
        )
    except Exception as exc:  # pragma: no cover - cairo on a broken machine
        log.warning("could not render the letter card (%s); posting the picture alone", exc)

    files = [path for path in (card, letter.picture) if path is not None and path.is_file()]

    entry = save_entry(
        KIND,
        files,
        # The child's own spelling, byte for byte, all the way to caption.txt.
        letter.caption or None,
        letter.voice if letter.has_voice else None,
        letter.meta(status),
        # Only used when there are no written words: "A letter for Grandad" is
        # a better card title for a picture-and-voice letter than the name of
        # the activity, and it says the thing the activity is about.
        activity_name=letter_title(letter.recipient),
    )

    outbox = (
        post(letter, card, profile_id, outbox_root, entry_id=str(getattr(entry, "id", "")))
        if to_outbox
        else None
    )
    return Posted(entry=entry, card=card, outbox=outbox)
