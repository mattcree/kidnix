"""One line of descriptive feedback for the Goodbye screen (SYNTHESIS E1).

Two reviewers found the same hole from different directions (forum #30, #52):
E1's *specific descriptive feedback* -- "you used five colours" -- "is in
SYNTHESIS and nowhere in the code", and it is not decoration. It is the only
**informational-competence** channel in the product: the one kind of feedback
Deci's meta-analysis says raises intrinsic motivation rather than eroding it,
precisely because it is descriptive rather than evaluative. "You made three
things today" is a count; "You drew two pictures and used five colours" is the
machine having noticed what the child actually did.

The rules the line follows:

* **descriptive, never evaluative.** No "well done", no "great", no stars, no
  comparison with last time. It says what happened and stops.
* **words, never digits** (01 #19, 03 #32), and never an awkward number: past
  :data:`MANY_ABOVE` colours it says "lots of colours", which is both true and
  what an adult would say.
* **only what is in the Journal.** If put away had to kill an activity at the
  hard stop, whatever was on that canvas was never imported, so it is not
  counted here -- the same rule that makes the count safe to say out loud
  (spec 7c).
* **it is allowed to say nothing.** A session with nothing kept gets no line,
  not a consolation prize.

Pure. The one impure part -- actually counting the colours in a PNG -- is
:func:`count_colours`, which is a best-effort read that returns ``None`` on any
problem at all, because a missing colour count must never cost a child their
Goodbye screen.
"""

from __future__ import annotations

import logging
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from .i18n import N_, NP_, _, ngettext
from .words import number_word as _number_word

log = logging.getLogger(__name__)

#: Words, not digits. Shared with the Goodbye headline. The words themselves
#: live in :mod:`kidnix_shell.words` (0-20, translatable); this is the slice
#: the Goodbye sentence is willing to say out loud.
WORDS = ("nothing", "one", "two", "three", "four", "five")

#: "one thing" / "two things", as a msgid pair. The *form* is chosen by the
#: catalogue's ``Plural-Forms`` -- Welsh has six of them -- and the count is
#: substituted as a **word**, never a digit.
THINGS = NP_("{count} thing", "{count} things")

#: The E1 sentence, and the two ways it grows. Named placeholders throughout:
#: a translator may put the verb last, which Welsh does.
MADE_SENTENCE = N_("You {verb} {count} {noun}")
COLOUR_CLAUSE = NP_("used {count} colour", "used {count} colours")
AND_JOIN = N_("{made} and {clause}")
FULL_STOP = N_("{sentence}.")

#: Above this the shell stops counting out loud and says "lots". A five-year-old
#: has no use for "eleven colours", and neither has the sentence.
MANY_ABOVE = 5


def count_phrase(count: int) -> str:
    """ "two things", "five things" -- and never a numeral (03 #32)."""
    if count <= 0:
        return _number_word(0)
    # Past the words this sentence is willing to say, the number itself is the
    # least bad answer -- it is a grown-up-facing count by then. Everything
    # below that is a word, and the noun's form is the catalogue's business.
    word = _number_word(count) if count < len(WORDS) else str(count)
    return ngettext(*THINGS, count).format(count=word)


def number_word(count: int) -> str:
    """ "two", or "lots" once the number stops being useful."""
    return _number_word(count, many_above=MANY_ABOVE)


#: What the child did, by activity, then by category. Present tense is wrong
#: here: the session is over, and the sentence is about what happened.
BY_ACTIVITY: dict[str, tuple[str, str, str]] = {
    "tuxpaint": (N_("drew"), *NP_("picture", "pictures")),
    "ktuberling": (N_("made"), *NP_("face", "faces")),
}
BY_CATEGORY: dict[str, tuple[str, str, str]] = {
    "make": (N_("made"), *NP_("thing", "things")),
    "learn": (N_("found out about"), *NP_("thing", "things")),
    "play": (N_("played"), *NP_("game", "games")),
}
DEFAULT_WORDS = (N_("made"), *NP_("thing", "things"))


def words_for(activity_ids: Iterable[str], categories: Iterable[str]) -> tuple[str, str, str]:
    """The verb and nouns for a session, or the general ones if it was mixed.

    A child who drew *and* played gets "made things", because a sentence that
    picked one of the two would be describing half the session as if it were
    all of it.
    """
    ids = {i for i in activity_ids if i}
    if len(ids) == 1:
        only = next(iter(ids))
        if only in BY_ACTIVITY:
            return BY_ACTIVITY[only]
    kinds = {c for c in categories if c}
    if len(kinds) == 1:
        return BY_CATEGORY.get(next(iter(kinds)), DEFAULT_WORDS)
    return DEFAULT_WORDS


@dataclass(frozen=True)
class MadeSummary:
    """What this sitting put in the Journal, in the shape the sentence needs."""

    count: int = 0
    verb: str = DEFAULT_WORDS[0]
    singular: str = DEFAULT_WORDS[1]
    plural: str = DEFAULT_WORDS[2]
    #: Distinct colours across the things that were made, or ``None`` when
    #: nobody could count them (no images, no GdkPixbuf, an unreadable file).
    colours: int | None = None


def descriptive_line(summary: MadeSummary) -> str:
    """E1's line. Empty string when there is nothing true to say."""
    if summary.count <= 0:
        return ""
    # The noun's form is the catalogue's decision, not ours: "singular or
    # plural" is an English answer, and Welsh has six forms.
    noun = ngettext(summary.singular, summary.plural, summary.count)
    what = _(MADE_SENTENCE).format(
        verb=_(summary.verb), count=number_word(summary.count), noun=noun
    )
    if summary.colours and summary.colours > 1:
        clause = ngettext(*COLOUR_CLAUSE, summary.colours).format(
            count=number_word(summary.colours)
        )
        what = _(AND_JOIN).format(made=what, clause=clause)
    return _(FULL_STOP).format(sentence=what)


# --- counting the colours in a picture -----------------------------------
#
# Cheap on purpose: it runs on the 256 px thumbnails the Journal already
# wrote, samples rather than reading every pixel, and quantises hard. The
# question is "did this child use a lot of colours or a few?", not "what is
# the palette?" -- and the answer has to be ready before the Goodbye screen
# paints.

#: Bits kept per channel. Four is 16 levels: enough to tell red from pink,
#: coarse enough that anti-aliasing along a crayon stroke is not a colour.
QUANTISE_BITS = 4
#: Sample at most this many pixels per picture.
MAX_SAMPLES = 4096
#: A colour has to be at least this share of the sampled pixels to count, so
#: the halo around a stroke does not become "another colour".
MIN_SHARE = 0.005
#: One colour covering more than this much of a picture is its paper.
PAPER_SHARE = 0.40


def count_colours(paths: Iterable[Path]) -> int | None:
    """Distinct colours across some images, or ``None`` if they cannot be read.

    Best effort in every direction: a missing GdkPixbuf, an unreadable file, a
    non-image, or an exception from anywhere in the stack all come back as
    ``None``, and the Goodbye line simply drops the colour clause.
    """
    seen: dict[tuple[int, int, int], int] = {}
    total = 0
    for path in paths:
        counted = _sample_one(path, seen)
        if counted is None:
            continue
        total += counted
    if not total:
        return None
    floor = max(1, int(total * MIN_SHARE))
    counts = sorted((count for count in seen.values() if count >= floor), reverse=True)
    if counts and counts[0] > total * PAPER_SHARE:
        # The paper is not a colour the child chose. One colour covering most
        # of the picture is the background, and counting it would make every
        # blank-ish drawing claim one more colour than it has.
        counts = counts[1:]
    return len(counts)


def _sample_one(path: Path, seen: dict[tuple[int, int, int], int]) -> int | None:
    try:
        import gi

        gi.require_version("GdkPixbuf", "2.0")
        from gi.repository import GdkPixbuf

        pixbuf = GdkPixbuf.Pixbuf.new_from_file(str(path))
        width, height = pixbuf.get_width(), pixbuf.get_height()
        channels = pixbuf.get_n_channels()
        rowstride = pixbuf.get_rowstride()
        data = pixbuf.get_pixels()
        if width <= 0 or height <= 0 or channels < 3:
            return None
        step = max(1, int(((width * height) / MAX_SAMPLES) ** 0.5))
        shift = 8 - QUANTISE_BITS
        counted = 0
        for y in range(0, height, step):
            row = y * rowstride
            for x in range(0, width, step):
                offset = row + x * channels
                if channels == 4 and data[offset + 3] < 128:
                    continue  # transparent: not a colour the child chose
                key = (
                    data[offset] >> shift,
                    data[offset + 1] >> shift,
                    data[offset + 2] >> shift,
                )
                seen[key] = seen.get(key, 0) + 1
                counted += 1
        return counted
    except Exception as exc:  # pragma: no cover - depends on the image stack
        log.debug("could not count the colours in %s: %s", path, exc)
        return None
